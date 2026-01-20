import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import requests
import json
import re

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
    เรียกใช้ Llama ผ่าน Ollama API
    """
    try:
        # สร้าง context จาก history
        full_prompt = prompt
        if session_history and len(session_history) > 0:
            context = "\n".join([
                f"User: {msg['user']}\nAssistant: {msg['assistant']}" 
                for msg in session_history[-3:]  # เอาแค่ 3 รอบล่าสุด
            ])
            full_prompt = f"Previous conversation:\n{context}\n\nCurrent request:\n{prompt}"
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2",
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.4,
                    "top_p": 0.9,
                    "top_k": 32,
                }
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()["response"]
        else:
            print(f"❌ Ollama Error: {response.status_code}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ ไม่สามารถเชื่อมต่อ Ollama - ตรวจสอบว่ารัน 'ollama serve' แล้วหรือยัง")
        return None
    except Exception as e:
        print(f"❌ Llama Error: {e}")
        return None

# ==========================================
# 🔥 แก้ปัญหา CSS ไม่โหลดบน Windows
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
    
    print(f"📩 รับข้อความจาก ({session_id}): {text}")

    # --- 🧠 Logic การจัดการความจำ ---
    if session_id not in user_sessions:
        print(f"✨ สร้างเซสชันใหม่ให้: {session_id}")
        user_sessions[session_id] = []
    
    session_history = user_sessions[session_id]

    prompt = f"""คุณคือผู้เชี่ยวชาญด้าน Cyber Security ที่เก่งวิเคราะห์มิจฉาชีพ

ข้อความที่ได้รับ: "{text}"

หน้าที่:
1. ตรวจจับว่าเป็นข้อความหลอกลวง (Scam) หรือไม่
2. ให้คะแนนความเสี่ยง 0-100 (0=ปลอดภัย, 100=อันตรายมาก)
3. อธิบายเหตุผลสั้นๆ ไม่เกิน 10 คำ
4. ให้คำแนะนำสั้นๆ ไม่เกิน 10 คำ
5. สร้างคำตอบภาษาไทยที่ฉลาด เพื่อซักถามหรือเปิดโปงมิจฉาชีพ (1 ประโยคเท่านั้น)

กฎสำคัญ:
- ตอบเป็น JSON เท่านั้น ห้ามมีคำอธิบายอื่น
- ใช้ภาษาไทยทั้งหมด ยกเว้น key ของ JSON
- ต้องมีครบทุก field

ตัวอย่าง JSON ที่ถูกต้อง:
{{
    "is_scam": true,
    "risk_score": 85,
    "reason": "ขอข้อมูลบัตรเครดิต อ้างเป็นธนาคาร",
    "advice": "ไม่ให้ข้อมูลส่วนตัว วางสายทันที",
    "reply": "คุณโทรมาจากธนาคารไหนครับ ขอชื่อเต็มและหมายเลขพนักงานหน่อย"
}}

ตอบเป็น JSON เท่านั้น:"""
    
    try:
        # เรียก Llama
        raw_text = call_llama(prompt, session_history)
        
        if not raw_text:
            raise Exception("Llama ไม่ตอบกลับ - ตรวจสอบว่า Ollama รันอยู่หรือไม่")

        print(f"🤖 Llama ตอบกลับ (Raw): {raw_text}")

        # ทำความสะอาด JSON
        clean_text = re.sub(r"```json|```", "", raw_text).strip()
        match = re.search(r"\{.*\}", clean_text, re.DOTALL)
        if match:
            clean_text = match.group(0)

        result = json.loads(clean_text)
        
        # บันทึกประวัติ (เก็บแค่ 10 รอบล่าสุด)
        user_sessions[session_id].append({
            "user": text,
            "assistant": result.get("reply", "")
        })
        
        if len(user_sessions[session_id]) > 10:
            user_sessions[session_id] = user_sessions[session_id][-10:]
            print("✂️ ตัดแต่งความจำเพื่อความเร็ว")
        
        return jsonify(result)
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON Parse Error: {e}")
        print(f"Raw text: {raw_text}")
        return jsonify({
            "is_scam": False,
            "risk_score": 0,
            "reason": "ไม่สามารถวิเคราะห์ได้",
            "advice": "ลองใหม่อีกครั้ง",
            "reply": "ระบบขัดข้อง กรุณาลองใหม่"
        })
        
    except Exception as e:
        print(f"❌ Error: {e}")
        if session_id in user_sessions:
            del user_sessions[session_id]
            
        return jsonify({
            "is_scam": False,
            "risk_score": 0,
            "reason": "เกิดข้อผิดพลาด",
            "advice": "ตรวจสอบว่า Ollama รันอยู่หรือไม่",
            "reply": "ระบบขัดข้อง"
        })

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 เริ่มต้น Flask Server")
    print("📌 ตรวจสอบ: Ollama ต้องรันอยู่ที่ localhost:11434")
    print("💡 ทดสอบด้วย: ollama run llama3.2")
    print("=" * 50)
    app.run(debug=True, port=5000)