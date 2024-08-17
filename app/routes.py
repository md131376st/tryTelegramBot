from fastapi import FastAPI, Request
from .services import TelegramService

app = FastAPI()
telegram_service = TelegramService()


@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        user_id = str(data["message"]["from"]["id"])

        # Present language options to the user
        if data["message"].get("text", "").lower() == "start":
            telegram_service.send_language_options(chat_id)

        # Handle text messages
        elif "text" in data["message"]:
            question = data["message"]["text"]
            morseverse_response = telegram_service.send_text_to_morseverse(user_id, question)
            print(morseverse_response)
            print()
            response_message = morseverse_response.get("response", "No response from Morseverse")
            telegram_service.send_message(chat_id, response_message.get("answer", "please try again"))

        # # Handle voice messages
        # elif "voice" in data["message"]:
        #     voice_file_id = data["message"]["voice"]["file_id"]
        #
        #     # Download the voice message
        #     ogg_file = telegram_service.download_voice_file(voice_file_id)
        #
        #     # Convert the OGG file to WAV
        #     wav_file = telegram_service.convert_to_wav(ogg_file)
        #
        #     # Send the WAV file data to Morseverse API
        #     morseverse_response = telegram_service.send_voice_to_morseverse(user_id, wav_file)
        #     response_message = morseverse_response.get("response", "Please Try again")
        #     telegram_service.send_message(chat_id, response_message)

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
