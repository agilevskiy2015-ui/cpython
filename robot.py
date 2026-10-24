import os
import time
import serial
import speech_recognition as sr
import pyttsx3
from openai import OpenAI

# ---------- SETTINGS ----------
PORT = "COM5"
BAUD = 9600
MODEL = "gpt-5.5"

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError(
        "Нет OPENAI_API_KEY. Сначала задай ключ в cmd."
    )

client = OpenAI(api_key=api_key)

# ---------- ARDUINO ----------
arduino = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)

def screen(prefix, text):
    # Send one UTF-8 line to Arduino
    text = " ".join(text.splitlines())
    arduino.write(
        (prefix + text + "\n").encode("utf-8")
    )

# ---------- COMPUTER VOICE ----------
tts = pyttsx3.init()
tts.setProperty("rate", 165)

# Choose a Russian voice if Windows has one
for voice in tts.getProperty("voices"):
    if "ru" in (voice.id + voice.name).lower():
        tts.setProperty("voice", voice.id)
        break

def speak(text):
    print("\nROBOT:", text)
    tts.say(text)
    tts.runAndWait()

# ---------- AI MEMORY ----------
history = []

INSTRUCTIONS = """
Ты — дружелюбный голосовой робот.
Отвечай на русском языке, понятно и естественно.
Обычно отвечай коротко, чтобы ответ было удобно слушать.
Если человек просит объяснить подробнее, объясняй подробнее.
Помни предыдущие сообщения в текущем разговоре.
"""

recognizer = sr.Recognizer()

def ask_ai(question):
    global history

    history.append({
        "role": "user",
        "content": question
    })

    # Keep recent conversation within a reasonable size
    history = history[-12:]

    result = client.responses.create(
        model=MODEL,
        instructions=INSTRUCTIONS,
        input=history
    )

    answer = result.output_text.strip()

    if not answer:
        answer = "Я не получил текстовый ответ. Попробуй ещё раз."

    history.append({
        "role": "assistant",
        "content": answer
    })

    history = history[-12:]
    return answer

# ---------- MAIN LOOP ----------
try:
    screen("S|", "Робот готов!")
    speak("Привет! Я готов общаться. Задавай вопрос.")

    with sr.Microphone() as mic:
        print("Настраиваю микрофон...")
        recognizer.adjust_for_ambient_noise(
            mic, duration=1
        )

        while True:
            try:
                screen("S|", "Слушаю тебя...")
                print("\nГовори. Для выхода скажи: выключись.")

                audio = recognizer.listen(
                    mic,
                    timeout=10,
                    phrase_time_limit=12
                )

                question = recognizer.recognize_google(
                    audio,
                    language="ru-RU"
                )

                print("ТЫ:", question)
                screen("Q|", question)

                if "выключись" in question.lower():
                    screen("S|", "До встречи!")
                    speak("До встречи!")
                    break

                screen("S|", "Думаю над ответом...")

                try:
                    answer = ask_ai(question)
                except Exception as error:
                    print("API ERROR:", error)
                    screen("S|", "Ошибка API. Проверь интернет и ключ.")
                    speak("Не получилось получить ответ. Проверь интернет и настройки API.")
                    continue

                screen("A|", answer)
                speak(answer)

            except sr.WaitTimeoutError:
                print("Не услышал вопрос. Попробуй ещё раз.")

            except sr.UnknownValueError:
                print("Не удалось распознать слова.")
                screen("S|", "Не расслышал. Повтори, пожалуйста.")

            except sr.RequestError as error:
                print("Ошибка распознавания речи:", error)
                screen("S|", "Проверь подключение к интернету.")

except KeyboardInterrupt:
    print("\nРобот остановлен.")

except Exception as error:
    print("Ошибка:", error)

finally:
    if arduino.is_open:
        arduino.close()
