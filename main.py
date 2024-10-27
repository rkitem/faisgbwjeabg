#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import speech_recognition as sr
from pydub import AudioSegment
from pydub.playback import play
import serial
import cv2
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import os
import json
import requests
from gtts import gTTS
from datetime import datetime
import logging
import time
import threading
import re
logging.basicConfig(filename='mira.log',
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')

def load_config():
    logging.info("Attempting to load configuration.")
    try:
        with open("config.json", "r") as file:
            config = json.load(file)
            logging.info("Successfully loaded configuration.")
            return config
    except FileNotFoundError:
        logging.critical(
            "Configuration file not found. Please ensure 'config.json' exists.")
        print("Configuration file not found. Please ensure 'config.json' exists.")
        exit(1)
    except json.JSONDecodeError:
        logging.critical(
            "Error reading 'config.json'. Please ensure it contains valid JSON.")
        print("Error reading 'config.json'. Please ensure it contains valid JSON.")
        exit(1)

room_mapping = {
    "bedroom": 210,
    "livingroom": 220,
    "kitchen": 230
}
date = datetime.now()

config = load_config()
api_key_weather = config.get("api_key_weather")
api_key_gemini = config.get("api_key_gemini")
city = config.get("city")
country = config.get("country_code")
webhook_url = config.get("discord_webhook")
print("Configs loaded!")
logging.info("Configs Confirmed.")

try:
    genai.configure(api_key=api_key_gemini)
    logging.info("Gemini API key has been confirmed.")
except Exception as e:
    logging.error(f"Failed to configure Gemini API: {e}")

print("Loading. . . ")
logging.info("Starting up the application.")

def realtime_camera():
    logging.info("Attempting to capture an image from the webcam.")
    cap2 = cv2.VideoCapture(0)
    ret, frame = cap2.read()
    if ret:
        cv2.imwrite('webcam_shot.jpg', frame)
        logging.info("Successfully captured and saved webcam image.")
        print("Realtime Image saved")
    else:
        logging.error("Failed to capture image from webcam.")
        print("Failed to get realtime webcam data")
    cap2.release()
    cv2.destroyAllWindows()
def process_respond(data):
    if "function" in data:
        if data["function"] == "light_toggle":
            if "light_toggle" in data and data["light_toggle"] in ("on", "off"):
                if "location" in data and "context" in data:
                    return data, "light_toggle"
        elif data["function"] == "timer":
            if "timer_seconds" in data and "context" in data:
                return data, "timer"
        elif data["function"] == "send_message":
            if "respond" in data and "send_webhook" in data and "context" in data:
                return data, "send_message"
    if "send_webhook" in data and data["send_webhook"]:
        if "respond" in data and "context" in data:
            return data, "send_message"
    if "context" in data:
        return data, "general"


def send_webhook(content, name_type, url):
    data = {
        "content": content,
        "username": name_type
    }
    result = requests.post(url, json=data)


def timer(duration):
    print(f"Timer set for {duration} seconds")
    time.sleep(duration)
    print("Time's up!")
    with open("timer_expired.txt", "w") as f:
        f.write("expired")


def load_chat_history(session_id):
    logging.info("Attempting to load chat history.")
    file_path = f"chat_history_{session_id}.json"
    try:
        with open(file_path, 'r') as f:
            history = json.load(f)
            logging.info(f"Successfully loaded chat history from {file_path}")
            return history
    except FileNotFoundError:
        logging.warning(f"Chat history file not found: {file_path}")
        return []


def save_chat_history(session_id, history):
    logging.info("Attempting to save chat history.")
    file_path = f"chat_history_{session_id}.json"
    try:
        with open(file_path, 'w') as f:
            json.dump(history, f)
        logging.info(f"Successfully saved chat history to {file_path}")
    except Exception as e:
        logging.error(f"Failed to save chat history: {e}")


def get_weather(city=city, country=country):
    logging.info("Requesting Weather information.")
    api_key = api_key_weather
    base_url = "http://api.openweathermap.org/data/2.5/weather?"
    complete_url = base_url + "appid=" + api_key + "&q=" + city + "," + country
    response = requests.get(complete_url)
    data = response.json()
    if data["cod"] != "404":
        weather = data["weather"][0]["description"]
        temperature = round(data["main"]["temp"] - 273.15, 1)
        weather_info = f"The weather in {city} is {weather} with a temperature of {temperature}°C"
        logging.info(f"Weather Information: {weather_info}")
        return weather_info
    else:
        logging.warning("City Not Found while fetching weather information.")
        return "City Not Found"


def text_to_speech(text, lang="en"):
    logging.info("Attempting text-to-speech conversion.")
    try:
        tts = gTTS(text, lang="th")
        tts.save("tts.mp3")
        sound = AudioSegment.from_mp3("tts.mp3")
        play(sound)
        os.remove("tts.mp3")
        logging.info("Successfully converted text to speech.")
    except Exception as e:
        logging.error(f"Text-to-speech conversion failed: {e}")


def check_timer():
    while True:
        if os.path.exists("timer_expired.txt"):
            print("Timer expired! Playing TTS announcement...")
            text_to_speech("หมดเวลาแล้ว")
            os.remove("timer_expired.txt")
        time.sleep(1)


def main():
    session_id = input("session id: ")
    if session_id == "":
        session_id = f"{date}"
    chat_history = load_chat_history(session_id)
    timer_thread = threading.Thread(target=check_timer)
    timer_thread.daemon = True
    timer_thread.start()

    while True:
        now = datetime.now()
        current_time = now.strftime("%I:%M %p")

        if debug_mode == "false":
            recognizer = sr.Recognizer()
            mic = sr.Microphone()
            with mic as source:
                print("Listening...")
                logging.info("Listening for user input.")
                audio = recognizer.listen(source)
        try:
            if debug_mode == "true":
                text = input(">>>")

            else:
                logging.info("Recognizing speech...")
                text = recognizer.recognize_google(audio, language="th-TH")
                print("You said:", text)
                logging.info(f"User said: {text}")
            match = "a"

            if match:
                if cv_toggle == "true":
                    realtime_camera()
                    try:
                        rt_file = genai.upload_file(
                            path=".", display_name="Realtime camera")
                        file = genai.get_file(name=rt_file.name)
                        rt_model = genai.GenerativeModel(
                            model_name="gemini-1.5-flash")
                        rt_context = rt_model.generate_content(
                            [rt_file, "expain what did you see in the picture?"])
                        fl_context = rt_context.text
                        logging.info(f"Image analysis result: {fl_context}")
                    except Exception as e:
                        logging.error(f"Image analysis failed: {e}")
                        fl_context = "Image analysis failed."
                    os.remove("webcam_shot.jpg")
                else:
                    fl_context = "The camera is offline"

                generation_config = {
                    "temperature": 1,
                    "top_p": 0.95,
                    "top_k": 1,
                    "max_output_tokens": 8192,
                    "response_mime_type": "application/json",
                }

                model = genai.GenerativeModel(
                    model_name="gemini-1.5-pro-latest",
                    generation_config=generation_config,
                    safety_settings={
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                    },
                    system_instruction="""secret!!""")

                chat_session = model.start_chat(history=chat_history)
                chat_history.append({"role": "user", "parts": [text]})

                prompt = f"Input: \"{text}\" Information(Tell this infomation only when user asking for): The time Right now is {current_time}, The date is {date} , The weather is {get_weather()} and you currently see in the realtime camera: \"{fl_context}\""
                response = chat_session.send_message([prompt])
                try:
                    structured_data = json.loads(response.text)
                    extracted_data, function_type = process_respond(
                        structured_data)

                    if extracted_data:
                        print(extracted_data["context"])

                    if function_type == "light_toggle":
                        location_code = room_mapping.get(
                            extracted_data['location'])
                        state_code = 1 if extracted_data['light_toggle'] == "on" else 0
                        if location_code is not None:
                            command = f"1:{location_code}:{state_code}\n"
                            try:
                                pass
                                # ser.write(command.encode())
                            except serial.SerialTimeoutException as e:
                                print(
                                    f"Error sending command to micro:bit: {e}")
                        else:
                            print(
                                f"Invalid location: {extracted_data['location']}")
                    elif function_type == "timer":
                        print(f"Function: {extracted_data['function']}")
                        print(
                            f"Timer seconds: {extracted_data['timer_seconds']}")
                        threading.Thread(target=timer, args=(
                            extracted_data['timer_seconds'],)).start()

                    elif function_type == "send_message":
                        print(f"Function: {extracted_data['function']}") 
                        print(f"Respond: {extracted_data['respond']}")
                        print(
                            f"Send Webhook: {extracted_data['send_webhook']}")

                        if extracted_data['send_webhook']:
                            send_webhook(
                                extracted_data['respond'], "Mira", webhook_url)
                            print("Webhook sent successfully!")
                    else:
                        print(response.text)
                except json.JSONDecodeError:
                    print(response.text)
                if response:
                    chat_history.append(
                        {"role": "model", "parts": extracted_data['context']})
                    save_chat_history(session_id, chat_history)
                    print(response.text)
                    logging.info(
                        f"Mira's response: {extracted_data['context']}")
                    text_to_speech(extracted_data["context"])
                else:
                    print("Gemini did not respond. Please try again.")
                    logging.warning("Gemini did not provide a response.")

        except sr.UnknownValueError:
            logging.warning("Could not understand audio.")
            print("Could not understand audio")
        except sr.RequestError as e:
            logging.error(
                f"Could not request results from Google Speech Recognition: {e}")
            print("Could not request results; {0}".format(e))
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            print("An error occurred:", e)

if __name__ == "__main__":
    debug_mode = input("debug mode (true/false): ")
    cv_toggle = input("camera (true/false): ")
    main()
