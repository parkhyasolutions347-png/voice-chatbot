import os
import sys
import subprocess
import speech_recognition as sr
import random
import json

try:
    from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
except ImportError:
    print("Please install transformers: pip install transformers")
    sys.exit(1)

# Initialize recognizer
recognizer = sr.Recognizer()

def speak_macos(text, output_file=None):
    """
    Cross-platform Text-to-Speech (STABLE FIXED VERSION)
    - Flask mode: returns audio file
    - CLI mode: plays audio safely
    """

    try:
        from gtts import gTTS
        import os
        import platform
        import subprocess

        # safety check (empty text crash fix)
        if not text or not text.strip():
            return None

        # Flask mode (only generate file)
        if output_file:
            tts = gTTS(text=text, lang='en')
            tts.save(output_file)
            return output_file

        # CLI mode (play audio)
        temp_file = "temp_audio.mp3"
        tts = gTTS(text=text, lang='en')
        tts.save(temp_file)

        system = platform.system()

        try:
            if system in ["Linux", "Darwin"]:
                subprocess.run(
                    ["mpg123", temp_file],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False
                )

            elif system == "Windows":
                os.startfile(temp_file)

            else:
                print("Unsupported OS for autoplay")

        except Exception as play_error:
            print("Audio playback failed:", play_error)
            print("Fallback text:", text)

        # safe cleanup (important fix)
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except:
            pass

    except Exception as e:
        print(f"TTS Error: {e}")
        print(f"[VOICE FALLBACK]: {text}")
        
def update_intents(text, response):
    try:
        with open('intents.json', 'r') as file:
            intents = json.load(file)

        tag = "unknown_intent"

        keywords = {
            "help": ["help", "assist"],
            "greeting": ["hi", "hello"],
            "goodbye": ["bye", "goodbye"],
        }

        for t, words in keywords.items():
            if any(w in text.lower() for w in words):
                tag = t
                break

        found = False
        for intent in intents['intents']:
            if intent['tag'] == tag:
                if text not in intent['patterns']:
                    intent['patterns'].append(text)
                if response not in intent['responses']:
                    intent['responses'].append(response)
                found = True
                break

        if not found:
            intents['intents'].append({
                "tag": tag,
                "patterns": [text],
                "responses": [response]
            })

        with open('intents.json', 'w') as f:
            json.dump(intents, f, indent=4)

        return True

    except Exception as e:
        print("Intent update error:", e)
        return False

def recognize_speech():
    try:
        with sr.Microphone() as source:
            print("Listening...")
            recognizer.adjust_for_ambient_noise(source)

            audio = recognizer.listen(source, timeout=5)
            text = recognizer.recognize_google(audio)

            print("You:", text)
            return text

    except Exception as e:
        print("Speech error:", e)
        return None

def load_intents():
    try:
        with open('intents.json') as f:
            return json.load(f)
    except:
        return {
            "intents": [
                {"tag": "greeting", "patterns": ["hi"], "responses": ["Hello!"]},
                {"tag": "bye", "patterns": ["bye"], "responses": ["Goodbye!"]}
            ]
        }

# def enhanced_match_intent(text, intents):
#     text = text.lower()

#     for intent in intents['intents']:
#         for pattern in intent['patterns']:
#             if pattern.lower() in text:
#                 return random.choice(intent['responses'])

#     # fallback learning
#     speak_macos("I don't know this. Please tell me the correct response.")
#     user_resp = recognize_speech()

#     if user_resp:
#         update_intents(text, user_resp)
#         return user_resp

#     return "I didn't understand."

def enhanced_match_intent(text, intents):
    text = text.lower()

    for intent in intents['intents']:
        for pattern in intent['patterns']:
            if pattern.lower() in text or text in pattern.lower():
                return random.choice(intent['responses'])

    # CLEAN fallback (NO LEARNING LOOP)
    return None

def initialize_chatbot():
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    model_name = "microsoft/DialoGPT-medium"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)

    chatbot = pipeline("text-generation", model=model, tokenizer=tokenizer)

    return chatbot, tokenizer

def generate_response(chatbot, tokenizer, text, history):
    try:
        prompt = " ".join(history[-3:]) + " " + text
        result = chatbot(prompt, max_length=100)

        return result[0]['generated_text'].replace(prompt, "").strip()

    except:
        return "Error generating response"

def chat():
    intents = load_intents()
    chatbot, tokenizer = initialize_chatbot()

    print("JTalk Assistant Started")
    speak_macos("JTalk Assistant Started")

    history = []

    while True:
        text = recognize_speech()
        if not text:
            continue

        if "bye" in text:
            speak_macos("Goodbye")
            break

        response = enhanced_match_intent(text, intents)

        if not response:
            history.append(text)
            response = generate_response(chatbot, tokenizer, text, history)

        history.append(response)

        print("Bot:", response)
        speak_macos(response)

if __name__ == "__main__":
    chat()

