import subprocess

import requests
import os
from pydub import AudioSegment
from .config import config
import binascii


class TelegramService:
    def __init__(self):
        self.TELEGRAM_API_URL = config.TELEGRAM_API_URL
        self.MORSEVERSE_TEXT_API_URL = config.MORSEVERSE_TEXT_API_URL
        self.MORSEVERSE_VOICE_API_URL = config.MORSEVERSE_VOICE_API_URL
        self.MORSEVERSE_VOICE_AI = config.MORSEVERSE_VOICE_AI
        self.COMPANY_ID = config.COMPANY_ID
        self.user_languages = {}  # Store user language preferences in memory

    def set_user_language(self, user_id, language_code):
        """Store the user's selected language."""
        self.user_languages[user_id] = language_code

    def get_user_language(self, user_id):
        """Retrieve the user's selected language, default to 'EN-US' if not set."""
        return self.user_languages.get(user_id, "EN-US")

    def download_voice_file(self, file_id, save_path='downloads/'):
        # Get the file path from Telegram
        file_info_url = self.TELEGRAM_API_URL + f"getFile?file_id={file_id}"
        file_info = requests.get(file_info_url).json()

        file_path = file_info["result"]["file_path"]
        download_url = f"https://api.telegram.org/file/bot{config.TELEGRAM_BOT_TOKEN}/{file_path}"

        # Download the file
        os.makedirs(save_path, exist_ok=True)
        ogg_file_path = os.path.join(save_path, file_path.split('/')[-1])

        with open(ogg_file_path, 'wb') as f:
            f.write(requests.get(download_url).content)

        print(f"Downloaded OGG file to {ogg_file_path}")
        return ogg_file_path

    def convert_to_wav(self, ogg_file_path):
        wav_file_path = ogg_file_path.replace('.oga', '.wav').replace('.ogg', '.wav')
        print(ogg_file_path)
        # Using ffmpeg to convert OGG to WAV
        AudioSegment.from_file(ogg_file_path).export(wav_file_path, format='wav')

        print(f"Converted to WAV file at {wav_file_path}")
        return wav_file_path

    def send_text_to_morseverse(self, user_id, question):
        language = self.get_user_language(user_id)
        print(self.COMPANY_ID)
        payload = {
            "companyId": self.COMPANY_ID,
            "userId": user_id,
            "lang": language,
            "question": question
        }
        try:
            response = requests.post(self.MORSEVERSE_TEXT_API_URL, json=payload)
            if response.status_code == 200:
                try:
                    return response.json()  # Attempt to parse the JSON response
                except ValueError:
                    # Handle cases where the response is not JSON
                    return {"error": "Invalid JSON response from Morseverse API"}
            else:
                # Handle HTTP errors
                return {"error": f"HTTP error {response.status_code}: {response.text}"}
        except requests.exceptions.RequestException as e:
            # Handle any request-related errors (e.g., network issues)
            return {"error": f"Request failed: {str(e)}"}

    def send_voice_to_morseverse(self, user_id, wav_file_path):
        language = self.get_user_language(user_id)
        with open(wav_file_path, 'rb') as wav_file:
            wav_data = wav_file.read()
        import base64
        wav_data_base64 = base64.b64encode(wav_data).decode('utf-8')
        payload = {
            "companyId": self.COMPANY_ID,
            "userId": user_id,
            "lang": language,
            "wavData": wav_data_base64
        }

        response = requests.post(self.MORSEVERSE_VOICE_API_URL, json=payload)
        print(response)
        return response.json()

    def send_voice_answer_to_user(self, chat_id, morseverse_response):
        # Prepare the text for the API request
        voice_answer_text = morseverse_response.get("voice_answer", "Please try again.")

        # Make a POST request to the text-to-audio API
        response = requests.post(self.MORSEVERSE_VOICE_AI, json={"text": voice_answer_text})

        if response.status_code == 200:
            # Assume the API returns the WAV file directly in the response content
            wav_data = response.content
            wav_file_path = "response.wav"

            # Save the response WAV file locally
            with open(wav_file_path, 'wb') as f:
                f.write(wav_data)
            ogg_file_path = wav_file_path.replace('.wav', '.ogg')
            self.convert_wav_to_ogg(wav_file_path, ogg_file_path)
            # Send the WAV file back to the user via Telegram
            self.send_voice(chat_id, ogg_file_path)

            # Optionally, delete the temporary WAV file
            os.remove(ogg_file_path)

    def convert_wav_to_ogg(self, wav_file_path, output_ogg_path):
        # Use ffmpeg to convert the WAV file to OGG with OPUS encoding
        subprocess.run(['ffmpeg', '-i', wav_file_path, '-c:a', 'libopus', output_ogg_path], check=True)

    def send_voice(self, chat_id, ogg_file_path):
        url = self.TELEGRAM_API_URL + "sendVoice"

        with open(ogg_file_path, 'rb') as voice_file:
            files = {
                'voice': voice_file
            }
            data = {
                'chat_id': chat_id
            }

            response = requests.post(url, data=data, files=files)

        return response.json()

    def send_message(self, chat_id, text):
        url = self.TELEGRAM_API_URL + "sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text
        }
        requests.post(url, json=payload)

    def send_language_options(self, chat_id):
        """Send language options to the user."""
        print("I am setting language")
        url = self.TELEGRAM_API_URL + "sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": "Please select your language:",
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": "Italian", "callback_data": "set_lang_IT"}],
                    [{"text": "English", "callback_data": "set_lang_EN-US"}]

                ]
            }
        }
        requests.post(url, json=payload)


class WhatsAppService:
    def __init__(self):
        self.TWILIO_API_URL = "https://api.twilio.com/2010-04-01/Accounts"
        self.MORSEVERSE_TEXT_API_URL = config.MORSEVERSE_TEXT_API_URL
        self.MORSEVERSE_VOICE_API_URL = config.MORSEVERSE_VOICE_API_URL
        self.MORSEVERSE_VOICE_AI = config.MORSEVERSE_VOICE_AI
        self.TWILIO_ACCOUNT_SID = config.TWILIO_ACCOUNT_SID
        self.TWILIO_AUTH_TOKEN = config.TWILIO_AUTH_TOKEN
        self.TWILIO_WHATSAPP_NUMBER = config.TWILIO_WHATSAPP_NUMBER
        self.COMPANY_ID = config.COMPANY_ID
        self.user_languages = {}  # Store user language preferences in memory

    def set_user_language(self, user_id, language_code):
        """Store the user's selected language."""
        self.user_languages[user_id] = language_code

    def get_user_language(self, user_id):
        """Retrieve the user's selected language, default to 'EN-US' if not set."""
        return self.user_languages.get(user_id, "EN-US")

    def send_message(self, to_number, message_body):
        """Send a message via Twilio WhatsApp API."""
        url = f"{self.TWILIO_API_URL}/{self.TWILIO_ACCOUNT_SID}/Messages.json"
        payload = {
            "Body": message_body,
            "From": f"whatsapp:{self.TWILIO_WHATSAPP_NUMBER}",
            "To": f"whatsapp:{to_number}"
        }
        auth = (self.TWILIO_ACCOUNT_SID, self.TWILIO_AUTH_TOKEN)
        response = requests.post(url, data=payload, auth=auth)
        return response.json()

    def download_voice_file(self, media_url, save_path='downloads/'):
        """Download the voice file from Twilio."""
        os.makedirs(save_path, exist_ok=True)
        ogg_file_path = os.path.join(save_path, media_url.split('/')[-1])
        with open(ogg_file_path, 'wb') as f:
            f.write(requests.get(media_url).content)
        print(f"Downloaded OGG file to {ogg_file_path}")
        return ogg_file_path

    def convert_to_wav(self, ogg_file_path):
        """Convert OGG file to WAV format."""
        wav_file_path = ogg_file_path.replace('.ogg', '.wav')
        AudioSegment.from_file(ogg_file_path).export(wav_file_path, format='wav')
        print(f"Converted to WAV file at {wav_file_path}")
        return wav_file_path

    def send_text_to_morseverse(self, user_id, question):
        """Send text question to Morseverse API."""
        language = self.get_user_language(user_id)
        payload = {
            "companyId": self.COMPANY_ID,
            "userId": user_id,
            "lang": language,
            "question": question
        }
        print(payload)
        try:
            response = requests.post(self.MORSEVERSE_TEXT_API_URL, json=payload)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP error {response.status_code}: {response.text}"}
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}

    def send_voice_to_morseverse(self, user_id, wav_file_path):
        """Send voice data to Morseverse API."""
        language = self.get_user_language(user_id)
        with open(wav_file_path, 'rb') as wav_file:
            wav_data = wav_file.read()
        import base64
        wav_data_base64 = base64.b64encode(wav_data).decode('utf-8')
        payload = {
            "companyId": self.COMPANY_ID,
            "userId": user_id,
            "lang": language,
            "wavData": wav_data_base64
        }

        response = requests.post(self.MORSEVERSE_VOICE_API_URL, json=payload)
        return response.json()

    def send_voice_answer_to_user(self, to_number, morseverse_response):
        """Send the voice response back to the user."""
        voice_answer_text = morseverse_response.get("voice_answer", "Please try again.")
        response = requests.post(self.MORSEVERSE_VOICE_AI, json={"text": voice_answer_text})

        if response.status_code == 200:
            wav_data = response.content
            wav_file_path = "response.wav"
            with open(wav_file_path, 'wb') as f:
                f.write(wav_data)
            ogg_file_path = wav_file_path.replace('.wav', '.ogg')
            self.convert_wav_to_ogg(wav_file_path, ogg_file_path)
            self.send_voice(to_number, ogg_file_path)
            os.remove(ogg_file_path)

    def convert_wav_to_ogg(self, wav_file_path, output_ogg_path):
        """Convert WAV file to OGG format."""
        subprocess.run(['ffmpeg', '-i', wav_file_path, '-c:a', 'libopus', output_ogg_path], check=True)

    def send_voice(self, to_number, ogg_file_path):
        """Send a voice message via Twilio WhatsApp API."""
        url = f"{self.TWILIO_API_URL}/{self.TWILIO_ACCOUNT_SID}/Messages.json"
        with open(ogg_file_path, 'rb') as voice_file:
            files = {'Media': voice_file}
            payload = {
                "From": f"whatsapp:{self.TWILIO_WHATSAPP_NUMBER}",
                "To": f"whatsapp:{to_number}"
            }
            response = requests.post(url, data=payload, files=files,
                                     auth=(self.TWILIO_ACCOUNT_SID, self.TWILIO_AUTH_TOKEN))
        return response.json()

    def send_language_options(self, to_number):
        """Send language options to the user."""
        message_body = "Please select your language:\n1. Italian\n2. English"
        self.send_message(to_number, message_body)
