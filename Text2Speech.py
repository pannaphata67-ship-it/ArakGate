import time
import numpy as np
import sounddevice as sd
import soundfile as sf
import whisper

# ================= CONFIG =================
MODEL_SIZE = "medium"      # เปลี่ยนเป็น large ได้ถ้ามี GPU
SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_DURATION = 0.3       # วินาที
SILENCE_LIMIT = 2.0        # วินาที

VOLUME_THRESHOLD = 0.012   # ปรับตามไมค์

AUDIO_FILE = "recorded_audio.wav"
TEXT_FILE = "transcription.txt"

PROMPT_HINT = "การสนทนาภาษาไทยทั่วไป ไม่มีเสียงดนตรี"
# ==========================================


def record_audio():
    print("🎙️ เริ่มอัดเสียง (หยุดพูด 2 วินาทีเพื่อจบ)")
    audio_chunks = []
    last_voice_time = time.time()

    block_size = int(SAMPLE_RATE * BLOCK_DURATION)

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
    ) as stream:
        while True:
            data, _ = stream.read(block_size)
            audio_chunks.append(data)

            volume = np.sqrt(np.mean(data ** 2))
            if volume > VOLUME_THRESHOLD:
                last_voice_time = time.time()

            if time.time() - last_voice_time > SILENCE_LIMIT:
                print("🔇 ตรวจพบ silence → หยุดอัด")
                break

    audio = np.concatenate(audio_chunks, axis=0)
    sf.write(AUDIO_FILE, audio, SAMPLE_RATE)
    print(f"💾 บันทึกเสียง: {AUDIO_FILE}")

    return AUDIO_FILE


def speech_to_text(audio_path):
    print(f"📦 โหลด Whisper model ({MODEL_SIZE})")
    model = whisper.load_model(MODEL_SIZE)

    print("🧠 กำลังถอดเสียง...")
    result = model.transcribe(
        audio_path,
        language="th",
        fp16=False,
        initial_prompt=PROMPT_HINT
    )
    data = sd.rec(
    int(SAMPLE_RATE * BLOCK_DURATION),
    samplerate=SAMPLE_RATE,
    channels=CHANNELS,
    dtype="float32",
    blocking=True
)

    text = result["text"].strip()

    with open(TEXT_FILE, "w", encoding="utf-8") as f:
        f.write(text)

    print("\n================ RESULT ================")
    print(text)
    print("=======================================\n")

    return text


if __name__ == "__main__":
    audio_path = record_audio()
    speech_to_text(audio_path)
