import hashlib

from fastapi import FastAPI, Request
from starlette.responses import JSONResponse

from .services import TelegramService

app = FastAPI()
telegram_service = TelegramService()


def telegram_user_id_to_object_id(user_id):
    # Convert the Telegram user_id (integer) to a string
    user_id_str = str(user_id)

    # Use hashlib to create a consistent 24-character hex string
    hash_object = hashlib.sha1(user_id_str.encode())  # SHA-1 creates a 40-character hex string
    hex_dig = hash_object.hexdigest()

    # Truncate or pad the string to ensure it's 24 characters long
    hex_dig = hex_dig[:24]  # Truncate to 24 characters

    # Convert the 24-character hex string to an ObjectId

    return hex_dig


@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()

        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            user_id = data["message"]["from"]["id"]
            user_id = telegram_user_id_to_object_id(user_id)

            # Present language options to the user
            if data["message"].get("text", "").lower() == "start" or data["message"].get("text",
                                                                                         "").lower() == "/start":
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
                voice_answer_text = morseverse_response.get("voice_answer", "Please try again.")
                telegram_service.send_voice_answer_to_user(chat_id, response_message)


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
        # Log the error (optional)
        print(f"An error occurred: {e}")

        # Send an error message to the user
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            telegram_service.send_message(chat_id,
                                          "An error occurred while processing your request. Please try again later.")
        elif "callback_query" in data:
            chat_id = data["callback_query"]["message"]["chat"]["id"]
            telegram_service.send_message(chat_id,
                                          "An error occurred while processing your request. Please try again later.")

        return {"status": "error", "message": str(e)}


@app.get("/")
def health_check():
    """
    A simple health check endpoint to verify if the server is running.
    """
    return JSONResponse(content={"status": "ok", "message": "Server is running smoothly."})
