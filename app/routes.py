# app.py

import logging
from fastapi import FastAPI, Request
from starlette.responses import JSONResponse
from .services import TelegramService
from .services import WhatsAppService
import hashlib


app = FastAPI()
telegram_service = TelegramService()
whatsapp_service = WhatsAppService()

logging.basicConfig(level=logging.INFO)

def telegram_user_id_to_object_id(user_id):
    # Convert the Telegram user_id (integer) to a string
    user_id_str = str(user_id)

    # Use hashlib to create a consistent 24-character hex string
    hash_object = hashlib.sha1(user_id_str.encode())  # SHA-1 creates a 40-character hex string
    hex_dig = hash_object.hexdigest()

    # Truncate or pad the string to ensure it's 24 characters long
    hex_dig = hex_dig[:24]  # Truncate to 24 characters

    return hex_dig
async def handle_telegram_message(data):
    try:
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            user_id = data["message"]["from"]["id"]
            user_id = telegram_user_id_to_object_id(user_id)

            # Present language options to the user
            if data["message"].get("text", "").lower() in ["start", "/start"]:
                telegram_service.send_language_options(chat_id)

            # Handle text messages
            elif "text" in data["message"]:
                question = data["message"]["text"]
                morseverse_response = telegram_service.send_text_to_morseverse(user_id, question)
                if morseverse_response is None:
                    telegram_service.send_message(chat_id, "Server Error, please try again.")
                    return {"status": "Error (null server answer)"}

                response_message = morseverse_response.get("answer", "Server error, please try later.")
                links = morseverse_response.get("links", [])
                if links:
                    merge_links = '\n'.join(links)
                    response_message += '\n' + merge_links
                telegram_service.send_message(chat_id, response_message)

            # Handle voice messages
            elif "voice" in data["message"]:
                voice_file_id = data["message"]["voice"]["file_id"]

                # Download the voice message
                ogg_file = telegram_service.download_voice_file(voice_file_id)

                # Convert the OGG file to WAV
                wav_file = telegram_service.convert_to_wav(ogg_file)

                # Send the WAV file data to Morseverse API
                morseverse_response = telegram_service.send_voice_to_morseverse(user_id, wav_file)
                if morseverse_response is None:
                    telegram_service.send_message(chat_id, "Server Error, please try again.")
                    return {"status": "Error (null server answer)"}

                response_message = morseverse_response.get("answer", "Please try again.")
                links = morseverse_response.get("links", [])
                if links:
                    merge_links = '\n'.join(links)
                    response_message += '\n' + merge_links
                telegram_service.send_message(chat_id, response_message)
                telegram_service.send_voice_answer_to_user(chat_id, morseverse_response)

        # Handle language selection callback
        elif "callback_query" in data:
            callback_data = data["callback_query"]["data"]
            chat_id = data["callback_query"]["message"]["chat"]["id"]
            user_id = str(data["callback_query"]["from"]["id"])

            if callback_data.startswith("set_lang_"):
                language_code = callback_data.split("_")[-1]
                telegram_service.set_user_language(user_id, language_code)
                telegram_service.send_message(chat_id, f"Language set to {language_code}.")

        return {"status": "success"}

    except Exception as e:
        logging.error(f"Error handling Telegram message: {e}")
        return {"status": "error", "message": str(e)}

async def handle_whatsapp_message(data):
    try:
        from_number = data.get("From")  # e.g., 'whatsapp:+1234567890'
        message_body = data.get("Body")
        num_media = int(data.get("NumMedia", "0"))
        user_id = telegram_user_id_to_object_id(from_number)  # Use the sender's number as the user ID
        # Handle text messages from WhatsApp
        if message_body and num_media == 0:
            logging.info(f"Received text message from {from_number}: {message_body}")
            # Send text to Morseverse and get response
            morseverse_response = whatsapp_service.send_text_to_morseverse(user_id, message_body)
            print(morseverse_response)
            if morseverse_response is None:
                response_message = "Server Error, please try again."
            else:
                response_message = morseverse_response.get("answer", "Sorry, there was an error processing your message.")
            # Send response back to the user
            whatsapp_service.send_message(from_number, response_message)

        # Handle media messages (e.g., voice messages)
        elif num_media > 0:
            media_url = data.get("MediaUrl0")
            media_type = data.get("MediaContentType0")
            if 'audio' in media_type:
                logging.info(f"Received voice message from {from_number}: {media_url}")
                # Download the voice message
                ogg_file_path = whatsapp_service.download_voice_file(media_url)
                # Convert the OGG file to WAV
                wav_file_path = whatsapp_service.convert_to_wav(ogg_file_path)
                # Send the WAV file data to Morseverse API
                morseverse_response = whatsapp_service.send_voice_to_morseverse(user_id, wav_file_path)
                if morseverse_response is None:
                    response_message = "Server Error, please try again."
                    whatsapp_service.send_message(from_number, response_message)
                    return {"status": "Error (null server answer)"}
                # Send voice response back to the user
                whatsapp_service.send_voice_answer_to_user(from_number, morseverse_response)
            else:
                # Handle other media types if needed
                whatsapp_service.send_message(from_number, f"Received your {media_type} file.")
        else:
            # Handle cases where there is no text or media
            whatsapp_service.send_message(from_number, "Sorry, I didn't receive any message content.")

        return {"status": "ok"}

    except Exception as e:
        logging.error(f"Error handling WhatsApp message: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/webhook")
async def webhook_handler(request: Request):
    try:
        # Determine the content type of the incoming request
        content_type = request.headers.get('content-type')

        # If the request is JSON (from Telegram)
        if 'application/json' in content_type:
            data = await request.json()
            if "message" in data or "callback_query" in data:
                # Handle Telegram messages
                return await handle_telegram_message(data)
            else:
                return {"status": "unhandled"}

        # If the request is form data (from WhatsApp via Twilio)
        elif 'application/x-www-form-urlencoded' in content_type:
            form = await request.form()
            data = dict(form)
            if "Body" in data and "From" in data:
                return await handle_whatsapp_message(data)
            else:
                return {"status": "unhandled"}

        else:
            return {"status": "unsupported content type"}

    except Exception as e:
        # Log the error
        logging.error(f"An error occurred: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/health")
def health_check():
    """
    A simple health check endpoint to verify if the server is running.
    """
    return JSONResponse(content={"status": "ok", "message": "Server is running smoothly."})
