import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import requests
import json
import re
import random

# โหลด environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# --- 🧠 Memory Store ---
user_sessions = {}

# ==========================================
# 🦙 ฟังก์ชันเรียก Llama ผ่าน Ollama
# ==========================================
def call_llama(prompt, session_history=None):
    """
    เรียกใช้ Llama ผ่าน Ollama API พร้อมบังคับ JSON Mode
    """
    try:
        # สร้าง Context จากประวัติการคุย
        full_prompt = prompt
        if session_history and len(session_history) > 0:
            context_list = []
            for msg in session_history[-3:]: # เอาบริบท 3 รอบล่าสุด
                context_list.append(f"User: {msg['user']}")
                context_list.append(f"Assistant: {msg['assistant']}")
            
            context_str = "\n".join(context_list)
            full_prompt = f"History:\n{context_str}\n\nCurrent Input:\n{prompt}"
        
        print("🚀 กำลังส่งข้อมูลให้ AI คิด...", flush=True)

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2",
                "prompt": full_prompt,
                "format": "json",      # 🔥 FIX 1: บังคับตอบเป็น JSON เท่านั้น (แก้ Error syntax)
                "stream": False,
                "options": {
                    "temperature": 0.75,   # เพิ่มความหลากหลาย
                    "top_p": 0.9,
                    "repeat_penalty": 1.2  # ลงโทษถ้าตอบซ้ำ
                }
            },
            timeout=45
        )
        
        if response.status_code == 200:
            return response.json()["response"]
        else:
            print(f"❌ Ollama Error: {response.status_code}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ เชื่อมต่อ Ollama ไม่ได้ (เช็คว่าเปิดโปรแกรมหรือยัง)")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

# ==========================================
# Routes
# ==========================================
@app.route('/static/css/style.css')
def css():
    response = send_from_directory('static/css', 'style.css')
    response.headers['Content-Type'] = 'text/css'
    return response

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.json
    text = data.get('message', '')
    session_id = data.get('session_id', 'guest_user')
    
    print(f"\n📩 [USER] พูดว่า: {text}", flush=True)

    # 1. เริ่ม Session ใหม่
    if session_id not in user_sessions:
        user_sessions[session_id] = []
    
    session_history = user_sessions[session_id]

    # ดึงคำตอบล่าสุดที่ AI เคยตอบ (เพื่อสั่งห้ามตอบซ้ำ)
    last_reply = ""
    if session_history:
        last_reply = session_history[-1]['assistant']

    # --- 📝 Prompt ---
    # หมายเหตุ: ไม่ใส่ตัวอย่างคำพูดลงไป เพื่อป้องกัน AI ลอก
    prompt = f"""
    Role: คุณคือ 'Arak' ระบบ AI อัจฉริยะที่ช่วยผู้ใช้รับมือกับแก๊งคอลเซ็นเตอร์
    Goal: วิเคราะห์คำพูด วิเคราะห์ความเสี่ยง และช่วยผู้ใช้ตอบโต้แบบกวนๆ หรือฉลาดๆ
    
    Current Input: "{text}"
    Previous Reply to Avoid: "{last_reply}"

    Instructions:
    1. ตรวจสอบว่าเป็นมิจฉาชีพหรือไม่
    2. ให้คะแนนความเสี่ยง (0-100)
    3. สร้างประโยคตอบโต้ (Reply) สำหรับให้ผู้ใช้พูดสวนกลับ
       - 🔥 ห้ามตอบซ้ำกับประโยคเดิมเด็ดขาด
       - ใช้ภาษาไทยที่เป็นธรรมชาติ สั้น กระชับ

    Output Format (JSON):
    {{
        "is_scam": boolean,
        "risk_score": integer,
        "reason": "String",
        "advice": "String",
        "reply": "String"
    }}
    """
    
    # 🔥 FIX 2: ระบบ Retry (ลองใหม่) ถ้า JSON พัง
    max_retries = 2
    result = None

    for attempt in range(max_retries):
        try:
            raw_text = call_llama(prompt, session_history)
            
            if not raw_text:
                raise Exception("Empty response from AI")

            # Clean JSON string (เผื่อมี text ปนมานิดหน่อย)
            clean_text = raw_text.strip()
            # บางที AI อาจจะเผลอใส่ ```json ครอบมา
            if "```" in clean_text:
                clean_text = re.sub(r"```json|```", "", clean_text).strip()
            
            result = json.loads(clean_text)
            break # ถ้าผ่าน ก็ออกจากลูป

        except json.JSONDecodeError as e:
            print(f"⚠️ JSON Error (รอบที่ {attempt+1}): {e}")
            print(f"Raw: {raw_text}")
            if attempt == max_retries - 1:
                # ถ้าลองครบแล้วยังพัง ให้ใช้ค่า Default
                result = {
                    "is_scam": False,
                    "risk_score": 0,
                    "reason": "ระบบประมวลผลผิดพลาด",
                    "advice": "ระวังตัวไว้ก่อน",
                    "reply": "ขอโทษครับ ไม่ค่อยได้ยิน พูดใหม่ได้ไหม"
                }
        except Exception as e:
            print(f"❌ Error: {e}")

    if result:
        # 🔥 FIX 3: Anti-Loop (ด่านสุดท้าย)
        if result.get('reply') == last_reply:
            print("⚠️ AI ตอบซ้ำ! บังคับเปลี่ยนคำตอบ...")
            fallback_replies = [
                "แล้วคุณต้องการอะไรกันแน่ครับ?",
                "ผมไม่สะดวกคุยตอนนี้ครับ",
                "คุณมีหลักฐานอะไรไหมว่าเป็นเจ้าหน้าที่จริง?",
                "เดี๋ยวผมจะโทรเช็คกับสำนักงานใหญ่เองครับ",
                "อย่ามาหลอกกันเลยครับ ผมรู้ทันนะ"
            ]
            result['reply'] = random.choice(fallback_replies)

        print(f"🤖 [AI] ตอบว่า: {result.get('reply')}", flush=True)

        # บันทึกประวัติ
        user_sessions[session_id].append({
            "user": text,
            "assistant": result.get("reply", "")
        })
        
        # ตัดประวัติไม่ให้ยาวเกิน
        if len(user_sessions[session_id]) > 10:
            user_sessions[session_id] = user_sessions[session_id][-10:]
        
        return jsonify(result)

    return jsonify({"reply": "Error"})

if __name__ == '__main__':
    print("🚀 Server Started! (JSON Fix + Anti-Loop)", flush=True)
    app.run(debug=True, port=5000, use_reloader=False)