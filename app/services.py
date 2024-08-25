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
        wav_data_hex = binascii.hexlify(wav_data).decode('utf-8')
        payload = {
            "companyId": self.COMPANY_ID,
            "userId": user_id,
            "lang": language,
            "wavData": wav_data_hex
        }

        response = requests.post(self.MORSEVERSE_VOICE_API_URL, json=payload)
        print(response)
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
