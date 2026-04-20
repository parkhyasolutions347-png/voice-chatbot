import os
import base64
import uuid
from flask import Flask, request, jsonify, render_template
from chatbot import enhanced_match_intent, generate_response, initialize_chatbot, load_intents
import speech_recognition as sr
from gtts import gTTS
from pydub import AudioSegment

app = Flask(__name__)

# Load intents once
intents = load_intents()

# Lazy load chatbot (important for deployment)
chatbot = None
tokenizer = None

def get_chatbot():
    global chatbot, tokenizer
    if chatbot is None or tokenizer is None:
        chatbot, tokenizer = initialize_chatbot()
    return chatbot, tokenizer


# Limit memory
conversation_history = []
MAX_HISTORY = 5


@app.route("/")
def home():
    return render_template("index.html")


# ---------- TEXT TO SPEECH ----------
def text_to_speech(text):
    try:
        filename = f"response_{uuid.uuid4()}.mp3"

        tts = gTTS(text=text, lang='en')
        tts.save(filename)

        with open(filename, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode("utf-8")

        os.remove(filename)

        print("✅ Audio generated")

        return audio_base64

    except Exception as e:
        print("❌ TTS Error:", e)
        return None


# ---------- AUDIO TO TEXT ----------
def audio_to_text(audio_data):
    try:
        webm_file = f"input_{uuid.uuid4()}.webm"
        wav_file = f"input_{uuid.uuid4()}.wav"

        audio_bytes = base64.b64decode(audio_data)

        with open(webm_file, "wb") as f:
            f.write(audio_bytes)

        # Convert to WAV (requires ffmpeg)
        sound = AudioSegment.from_file(webm_file, format="webm")
        sound.export(wav_file, format="wav")

        r = sr.Recognizer()
        with sr.AudioFile(wav_file) as source:
            audio = r.record(source)

        text = r.recognize_google(audio)

        # Cleanup
        os.remove(webm_file)
        os.remove(wav_file)

        print("🎤 Recognized:", text)

        return text

    except sr.UnknownValueError:
        print("❌ Could not understand audio")
        return None

    except Exception as e:
        print("❌ STT Error:", e)
        return None


# ---------- CHAT API ----------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        global conversation_history

        data = request.json
        input_type = data.get("input_type", "text")
        input_data = data.get("message", "").strip()

        # AUDIO INPUT
        if input_type == "audio":
            user_message = audio_to_text(input_data)

            if not user_message:
                return jsonify({
                    "response": "Sorry, I couldn't understand the audio.",
                    "audio_response": None
                })
        else:
            user_message = input_data

        if not user_message:
            return jsonify({
                "response": "Please say something.",
                "audio_response": None
            })

        print("👤 User:", user_message)

        # INTENT MATCH
        response = enhanced_match_intent(user_message, intents)

        # MODEL RESPONSE
        if not response:
            chatbot, tokenizer = get_chatbot()

            conversation_history.append(user_message)

            if len(conversation_history) > MAX_HISTORY:
                conversation_history.pop(0)

            response = generate_response(chatbot, tokenizer, user_message, conversation_history)

            conversation_history.append(response)

        print("🤖 Bot:", response)

        # TEXT TO SPEECH
        audio_response = text_to_speech(response)

        return jsonify({
            "response": response,
            "audio_response": audio_response
        })

    except Exception as e:
        print("❌ Chat Error:", e)
        return jsonify({
            "response": "Server error, please try again.",
            "audio_response": None
        })


# ---------- SPEECH TO TEXT ----------
@app.route("/speech-to-text", methods=["POST"])
def speech_to_text():
    try:
        audio_data = request.json.get("audio", "").strip()

        if not audio_data:
            return jsonify({"text": "No audio received"})

        text = audio_to_text(audio_data)

        return jsonify({
            "text": text if text else "Could not convert speech"
        })

    except Exception as e:
        return jsonify({"text": f"Error: {str(e)}"})


# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True, port=5001)

# import os
# import base64
# from flask import Flask, request, jsonify, render_template
# from chatbot import enhanced_match_intent, generate_response, initialize_chatbot, load_intents
# import speech_recognition as sr
# from gtts import gTTS
# from pydub import AudioSegment

# # Initialize Flask app
# app = Flask(__name__)

# # Load intents
# intents = load_intents()

# # Initialize chatbot
# chatbot, tokenizer = initialize_chatbot()

# conversation_history = []


# @app.route("/")
# def home():
#     return render_template("index.html")


# # ---------- TEXT TO SPEECH ----------
# def text_to_speech(text):
#     try:
#         audio_path = "response_audio.mp3"

#         # Generate audio
#         tts = gTTS(text=text, lang='en')
#         tts.save(audio_path)

#         # Convert to base64
#         with open(audio_path, "rb") as f:
#             audio_base64 = base64.b64encode(f.read()).decode("utf-8")

#         os.remove(audio_path)

#         print("✅ Audio generated successfully")

#         return audio_base64

#     except Exception as e:
#         print("❌ TTS Error:", e)
#         return None


# # ---------- AUDIO TO TEXT ----------
# def audio_to_text(audio_data):
#     try:
#         # Decode base64
#         audio_bytes = base64.b64decode(audio_data)

#         # Save WebM file
#         with open("input_audio.webm", "wb") as f:
#             f.write(audio_bytes)

#         # Convert WebM → WAV
#         sound = AudioSegment.from_file("input_audio.webm", format="webm")
#         sound.export("input_audio.wav", format="wav")

#         # Speech Recognition
#         r = sr.Recognizer()
#         with sr.AudioFile("input_audio.wav") as source:
#             audio = r.record(source)

#         text = r.recognize_google(audio)

#         # Cleanup
#         os.remove("input_audio.webm")
#         os.remove("input_audio.wav")

#         print("🎤 Recognized Text:", text)

#         return text

#     except sr.UnknownValueError:
#         print("❌ Could not understand audio")
#         return None

#     except Exception as e:
#         print("❌ STT Error:", e)
#         return None


# # ---------- CHAT API ----------
# @app.route("/chat", methods=["POST"])
# def chat():
#     global conversation_history

#     data = request.json
#     input_type = data.get("input_type", "text")
#     input_data = data.get("message", "").strip()

#     # AUDIO INPUT
#     if input_type == "audio":
#         user_message = audio_to_text(input_data)

#         if not user_message:
#             return jsonify({
#                 "response": "Sorry, I couldn't understand the audio.",
#                 "audio_response": None
#             })
#     else:
#         user_message = input_data

#     if not user_message:
#         return jsonify({
#             "response": "Please say something.",
#             "audio_response": None
#         })

#     print("👤 User:", user_message)

#     # INTENT MATCH
#     response = enhanced_match_intent(user_message, intents)

#     # MODEL RESPONSE
#     if not response:
#         conversation_history.append(user_message)
#         response = generate_response(chatbot, tokenizer, user_message, conversation_history)
#         conversation_history.append(response)

#     print("🤖 Bot:", response)

#     # TEXT TO SPEECH
#     audio_response = text_to_speech(response)

#     return jsonify({
#         "response": response,
#         "audio_response": audio_response
#     })


# # ---------- OPTIONAL: SPEECH TO TEXT API ----------
# @app.route("/speech-to-text", methods=["POST"])
# def speech_to_text():
#     try:
#         audio_data = request.json.get("audio", "").strip()

#         if not audio_data:
#             return jsonify({"text": "No audio received"})

#         text = audio_to_text(audio_data)

#         return jsonify({"text": text if text else "Could not convert speech"})

#     except Exception as e:
#         return jsonify({"text": f"Error: {str(e)}"})


# # ---------- RUN ----------
# if __name__ == "__main__":
#     app.run(debug=True, port=5001)