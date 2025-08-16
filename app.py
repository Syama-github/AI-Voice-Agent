from flask import Flask, request, jsonify, render_template
import os
import tempfile
import requests
import assemblyai as aai
import google.generativeai as genai

# ==== Initialize Flask app ====
app = Flask(__name__)

# ====== Load API Keys ======
print("[INIT] Loading API keys...")
ASSEMBLYAI_KEY = os.getenv("ASSEMBLYAI_API_KEY")
MURF_API_KEY = os.getenv("MURF_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not ASSEMBLYAI_KEY:
    print("[ERROR] Missing ASSEMBLYAI_API_KEY")
if not MURF_API_KEY:
    print("[ERROR] Missing MURF_API_KEY")
if not GEMINI_API_KEY:
    print("[ERROR] Missing GEMINI_API_KEY")

aai.settings.api_key = ASSEMBLYAI_KEY
genai.configure(api_key=GEMINI_API_KEY)

# ====== Chat History Store ======
chat_histories = {}  # { session_id: [{"role": "user"/"assistant", "text": "..."}] }


@app.route("/")
def home():
    print("[ROUTE] GET / - Serving index.html")
    return render_template("index.html")


# ========== Day 9 Endpoint ==========
@app.route("/llm/query", methods=["POST"])
def llm_query():
    try:
        print("[DAY 9] Receiving audio file...")
        if "audio" not in request.files:
            return jsonify({"error": "No audio file uploaded"}), 400

        audio_file = request.files["audio"]
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            audio_file.save(temp_audio.name)
            audio_path = temp_audio.name

        # Transcribe
        try:
            transcriber = aai.Transcriber()
            transcript = transcriber.transcribe(audio_path)
            user_text = transcript.text
        except Exception as e:
            print("[ERROR] STT failed:", e)
            return fallback_audio("I'm having trouble hearing you right now.")

        if not user_text:
            return fallback_audio("Sorry, I couldn't understand that.")

        # LLM
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            llm_response = model.generate_content(user_text)
            ai_text = llm_response.text.strip()
        except Exception as e:
            print("[ERROR] LLM failed:", e)
            return fallback_audio("I'm having trouble thinking right now.")

        # TTS
        audio_url = murf_tts(ai_text)
        if not audio_url:
            return fallback_audio("I'm having trouble speaking right now.")

        return jsonify({
            "transcription": user_text,
            "llm_response": ai_text,
            "audio_url": audio_url
        })

    except Exception as e:
        print("[ERROR] Unexpected failure:", e)
        return fallback_audio("Something went wrong. Please try again.")


# ========== Day 10 Chat Endpoint ==========
@app.route("/agent/chat/<session_id>", methods=["POST"])
def agent_chat(session_id):
    try:
        print(f"[DAY 10] Chat request for session: {session_id}")
        if "audio" not in request.files:
            return jsonify({"error": "No audio file uploaded"}), 400

        audio_file = request.files["audio"]
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            audio_file.save(temp_audio.name)
            audio_path = temp_audio.name

        # Transcribe
        try:
            transcriber = aai.Transcriber()
            transcript = transcriber.transcribe(audio_path)
            user_text = transcript.text
        except Exception as e:
            print("[ERROR] STT failed:", e)
            return fallback_audio("I'm having trouble hearing you right now.")

        if not user_text:
            return fallback_audio("Sorry, I couldn't understand that.")

        # Get chat history
        history = chat_histories.get(session_id, [])
        history_text = "\n".join([f"{msg['role']}: {msg['text']}" for msg in history])
        prompt = history_text + f"\nuser: {user_text}"

        # LLM with context
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            llm_response = model.generate_content(prompt)
            ai_text = llm_response.text.strip()
        except Exception as e:
            print("[ERROR] LLM failed:", e)
            return fallback_audio("I'm having trouble thinking right now.")

        # Update chat history
        history.append({"role": "user", "text": user_text})
        history.append({"role": "assistant", "text": ai_text})
        chat_histories[session_id] = history

        # TTS
        audio_url = murf_tts(ai_text)
        if not audio_url:
            return fallback_audio("I'm having trouble speaking right now.")

        return jsonify({
            "transcription": user_text,
            "llm_response": ai_text,
            "audio_url": audio_url,
            "history": history
        })

    except Exception as e:
        print("[ERROR] Unexpected failure:", e)
        return fallback_audio("Something went wrong. Please try again.")


# ====== Murf Helper ======
def murf_tts(text):
    try:
        murf_url = "https://api.murf.ai/v1/speech/generate"
        headers = {
            "accept": "application/json",
            "api-key": MURF_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "voiceId": "en-UK-hazel",
            "text": text,
            "format": "mp3"
        }
        murf_res = requests.post(murf_url, json=payload, headers=headers)
        if murf_res.status_code != 200:
            print("[ERROR] Murf API failed with status:", murf_res.status_code)
            return None
        murf_data = murf_res.json()
        return murf_data.get("audioFile")
    except Exception as e:
        print("[ERROR] Murf TTS exception:", e)
        return None


# ====== Fallback Helper ======
def fallback_audio(message):
    print("[FALLBACK]", message)
    fallback_url = murf_tts(message)
    return jsonify({
        "transcription": None,
        "llm_response": message,
        "audio_url": fallback_url
    })


if __name__ == "__main__":
    print("[START] Flask server starting on http://127.0.0.1:5000")
    app.run(debug=True)
