// ================== DOM Elements ==================
const recordBtn = document.getElementById("record-btn");
const statusText = document.getElementById("status-text");
const chatContainer = document.getElementById("chat-container");

// ================== State ==================
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
const sessionId = "12345"; // TODO: Make this dynamic if needed

// ================== Event Listeners ==================
recordBtn.addEventListener("click", () => {
    isRecording ? stopRecording() : startRecording();
});

// ================== Recording Functions ==================
function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = e => {
                if (e.data.size > 0) audioChunks.push(e.data);
            };

            mediaRecorder.onstop = sendAudio;

            mediaRecorder.start();
            isRecording = true;

            updateUI("Stop Recording", "Recording... Speak now!", true);
        })
        .catch(err => {
            console.error("Microphone error:", err);
            statusText.textContent = "Microphone access denied.";
        });
}

function stopRecording() {
    if (mediaRecorder) {
        mediaRecorder.stop();
        isRecording = false;
        updateUI("Start Recording", "Processing your audio...", false);
    }
}

// ================== Send Audio ==================
function sendAudio() {
    const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
    const formData = new FormData();
    formData.append("audio", audioBlob);

    fetch(`/agent/chat/${sessionId}`, { method: "POST", body: formData })
        .then(res => res.json())
        .then(data => handleResponse(data))
        .catch(err => {
            console.error("Fetch error:", err);
            statusText.textContent = "Connection error. Try again.";
        });
}

// ================== Handle Response ==================
function handleResponse(data) {
    if (data.error) {
        statusText.textContent = "Error: " + data.error;
        return;
    }

    displayMessage("You", data.transcription);
    displayMessage("AI", data.llm_response);

    if (data.audio_url) {
        new Audio(data.audio_url).play();
    }

    statusText.textContent = "Press the button to talk again.";
}

// ================== Chat UI ==================
function displayMessage(sender, text) {
    const msg = document.createElement("p");
    msg.innerHTML = `<strong>${sender}:</strong> ${text}`;
    chatContainer.appendChild(msg);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function updateUI(btnText, status, recording) {
    recordBtn.textContent = btnText;
    recordBtn.classList.toggle("recording", recording);
    statusText.textContent = status;
}
