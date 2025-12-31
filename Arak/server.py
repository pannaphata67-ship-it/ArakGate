import os
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai
import json
import re

# 1. โหลด API Key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("❌ ไม่พบ API Key ในไฟล์ .env")

genai.configure(api_key=api_key)

app = Flask(__name__)
CORS(app)

# --- 🧠 Memory Store (ส่วนที่เพิ่มมา) ---
# เก็บห้องแชทของผู้ใช้แต่ละคนไว้ใน RAM
# รูปแบบ: { "session_id_A": chat_object_A, "session_id_B": chat_object_B }
user_sessions = {}

# 2. ตั้งค่าโมเดล
generation_config = {
    "temperature": 0.4,
    "top_p": 0.9,
    "top_k": 32,
    "max_output_tokens": 2048,
}

# หมายเหตุ: แก้ชื่อโมเดลเป็น 1.5-flash เพื่อความชัวร์ (2.5 ยังไม่มี)
model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-exp",
    generation_config=generation_config,
)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.json
    text = data.get('message', '')
    
    # 🌟 รับ session_id จากหน้าเว็บ (ถ้าไม่มีให้ตั้งเป็น guest)
    session_id = data.get('session_id', 'guest_user')
    
    print(f"📩 รับข้อความจาก ({session_id}): {text}")

    # --- 🧠 Logic การจัดการความจำ ---
    
    # 1. เช็คว่าคนนี้เคยคุยไหม? ถ้าไม่เคย ให้เปิดห้องใหม่
    if session_id not in user_sessions:
        print(f"✨ สร้างห้องแชทใหม่ให้: {session_id}")
        user_sessions[session_id] = model.start_chat(history=[
            {
                "role": "user",
                "parts": ["System Instruction: คุณคือ AI ผู้เชี่ยวชาญ Cyber Security หน้าที่คือวิเคราะห์ข้อความ Scam ภาษาไทย"]
            },
            {
                "role": "model",
                "parts": ["รับทราบครับ ผมพร้อมวิเคราะห์และจดจำบริบทครับ"]
            }
        ])
    
    # 2. ดึงห้องแชทของคนนั้นออกมา
    chat_session = user_sessions[session_id]

    # Prompt สั้นลง เพราะเราใส่ System Instruction ไปใน history แล้ว
    prompt = f"""
    Role: You are a sharp, witty assistant helping the user handle a scammer on the phone.
    Input: "{text}"
    
    Task:
    1. Detect Scam: True/False?
    2. Reply: Create a short, clever Thai response to stall or expose them. (Max 1 sentence)

    Respond ONLY with a valid JSON object. Keep it VERY SHORT.
    Context: Remember previous messages.

    Format:
    {{
        "is_scam": true or false,
        "risk_score": integer (0-100),
        "reason": "Explain in Thai (short <= 10 words)",
        "advice": "Advice in Thai (short <= 10 words)",
        "reply": "Short Thai conversational response to the caller",
    }}
    """
    
    try:
        # 🌟 เปลี่ยนจาก model.generate_content เป็น chat_session.send_message
        response = chat_session.send_message(prompt)
        raw_text = response.text
        
        # --- 🚀 Speed Optimization (Rolling Window) ---
        # ถ้าจำเยอะเกินไป AI จะช้าและเอ๋อ ให้ตัดความจำเก่าทิ้ง (เหลือไว้แค่ System Prompt + 10 ข้อความล่าสุด)
        if len(chat_session.history) > 20:
            # เก็บ 2 อันแรกไว้ (System Prompt) + 10 อันหลังสุด
            chat_session.history = chat_session.history[:2] + chat_session.history[-10:]
            print("✂️ ตัดแต่งความจำเพื่อความเร็ว")

        # --- Cleaner Code (ของเดิมของคุณ ดีอยู่แล้ว) ---
        print(f"🤖 AI ตอบกลับ (Raw): {raw_text}") 

        clean_text = re.sub(r"```json|```", "", raw_text).strip()
        match = re.search(r"\{.*\}", clean_text, re.DOTALL)
        if match:
            clean_text = match.group(0)

        result = json.loads(clean_text)
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        # ถ้า Error ให้ลบ Session ทิ้ง เผื่อห้องแชทค้าง
        if session_id in user_sessions:
            del user_sessions[session_id]
            
        return jsonify({
            "is_scam": False,
            "risk_score": 0,
            "reason": "ระบบรีเซ็ตความจำ (ลองใหม่)",
            "advice": "กรุณาตรวจสอบอีกครั้ง",
            "reply": "ผิดพลาด"
        })

if __name__ == '__main__':
    app.run(debug=True, port=5000)