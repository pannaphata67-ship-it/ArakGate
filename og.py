# ===== Speech-to-Text ภาษาไทยด้วย Whisper =====
# ติดตั้ง: pip install openai-whisper
# ต้องติดตั้ง ffmpeg ด้วย (สำหรับ Windows: https://ffmpeg.org/download.html)
#pip install openai-whisper sounddevice numpy


import whisper
import os

def transcribe_microphone(model_size='base', duration=15):
    """
    บันทึกเสียงจากไมโครโฟนแล้วแปลงเป็นข้อความภาษาไทย
    
    Args:
        model_size: ขนาดโมเดล ('tiny', 'base', 'small', 'medium', 'large')
        duration: ระยะเวลาบันทึก (วินาที)
    """
    try:
        import sounddevice as sd
        import soundfile as sf
        import numpy as np
        
        print(f"กำลังโหลดโมเดล Whisper ({model_size})...")
        model = whisper.load_model(model_size)
        
        # ตั้งค่าการบันทึกเสียง
        sample_rate = 16000
        temp_file = "temp_recording.wav"
        
        print(f"\nเริ่มบันทึกเสียง {duration} วินาที...")
        print("พูดเลย!")
        
        # บันทึกเสียง
        audio_data = sd.rec(int(duration * sample_rate), 
                           samplerate=sample_rate, 
                           channels=1, 
                           dtype=np.int16)
        sd.wait()
        print("บันทึกเสียงเสร็จสิ้น!")
        
        # บันทึกเป็นไฟล์ชั่วคราว
        sf.write(temp_file, audio_data, sample_rate)
        
        # แปลงเสียงเป็นข้อความ
        print("กำลังประมวลผล...")
        result = model.transcribe(temp_file, language='th', fp16=False)
        
        # ลบไฟล์ชั่วคราว
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        print(f"\n{'='*50}")
        print(f"ข้อความ: {result['text']}")
        print(f"{'='*50}\n")
        
        return result['text']
        
    except ImportError:
        print("กรุณาติดตั้ง sounddevice และ soundfile:")
        print("pip install sounddevice soundfile")
        return None
    except Exception as e:
        print(f"เกิดข้อผิดพลาด: {e}")
        return None


def transcribe_file(filename, model_size='base'):
    """
    แปลงเสียงจากไฟล์เป็นข้อความภาษาไทย
    รองรับไฟล์: mp3, wav, m4a, flac, ogg, และอื่นๆ
    
    Args:
        filename: ชื่อไฟล์เสียง
        model_size: ขนาดโมเดล
    """
    try:
        print(f"กำลังโหลดโมเดล Whisper ({model_size})...")
        model = whisper.load_model(model_size)
        
        print(f"กำลังประมวลผลไฟล์: {filename}")
        result = model.transcribe(filename, language='th', fp16=False)
        
        print(f"\n{'='*50}")
        print(f"ข้อความ: {result['text']}")
        print(f"{'='*50}\n")
        
        return result['text']
        
    except FileNotFoundError:
        print(f"ไม่พบไฟล์: {filename}")
        return None
    except Exception as e:
        print(f"เกิดข้อผิดพลาด: {e}")
        return None


def transcribe_file_with_timestamps(filename, model_size='base'):
    """
    แปลงเสียงพร้อมแสดงช่วงเวลา (timestamps)
    
    Args:
        filename: ชื่อไฟล์เสียง
        model_size: ขนาดโมเดล
    """
    try:
        print(f"กำลังโหลดโมเดล Whisper ({model_size})...")
        model = whisper.load_model(model_size)
        
        print(f"กำลังประมวลผลไฟล์: {filename}")
        result = model.transcribe(filename, language='th', fp16=False)
        
        print(f"\n{'='*50}")
        print("ข้อความพร้อมช่วงเวลา:")
        print(f"{'='*50}")
        
        for segment in result['segments']:
            start_time = format_timestamp(segment['start'])
            end_time = format_timestamp(segment['end'])
            text = segment['text']
            print(f"[{start_time} --> {end_time}] {text}")
        
        print(f"\n{'='*50}")
        print(f"ข้อความเต็ม: {result['text']}")
        print(f"{'='*50}\n")
        
        return result
        
    except Exception as e:
        print(f"เกิดข้อผิดพลาด: {e}")
        return None


def format_timestamp(seconds):
    """แปลงวินาทีเป็นรูปแบบ HH:MM:SS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def save_transcription_to_file(filename, output_file, model_size='base'):
    """
    แปลงเสียงและบันทึกข้อความลงไฟล์
    
    Args:
        filename: ชื่อไฟล์เสียง
        output_file: ชื่อไฟล์ข้อความที่จะบันทึก (.txt)
        model_size: ขนาดโมเดล
    """
    try:
        print(f"กำลังโหลดโมเดล Whisper ({model_size})...")
        model = whisper.load_model(model_size)
        
        print(f"กำลังประมวลผลไฟล์: {filename}")
        result = model.transcribe(filename, language='th', fp16=False)
        
        # บันทึกลงไฟล์
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result['text'])
        
        print(f"\nบันทึกข้อความลงไฟล์: {output_file}")
        print(f"ข้อความ: {result['text']}\n")
        
        return result['text']
        
    except Exception as e:
        print(f"เกิดข้อผิดพลาด: {e}")
        return None


def real_time_transcription(model_size='base', chunk_duration=5):
    """
    แปลงเสียงแบบต่อเนื่อง (Real-time)
    กด Ctrl+C เพื่อหยุด
    
    Args:
        model_size: ขนาดโมเดล
        chunk_duration: ระยะเวลาบันทึกแต่ละรอบ (วินาที)
    """
    try:
        import sounddevice as sd
        import soundfile as sf
        import numpy as np
        
        print(f"กำลังโหลดโมเดล Whisper ({model_size})...")
        model = whisper.load_model(model_size)
        
        sample_rate = 16000
        temp_file = "temp_chunk.wav"
        
        print("\n=== โหมดแปลงเสียงแบบต่อเนื่อง ===")
        print("กด Ctrl+C เพื่อหยุด\n")
        
        try:
            while True:
                print("กำลังฟัง...")
                
                # บันทึกเสียง
                audio_data = sd.rec(int(chunk_duration * sample_rate),
                                   samplerate=sample_rate,
                                   channels=1,
                                   dtype=np.int16)
                sd.wait()
                
                # บันทึกเป็นไฟล์
                sf.write(temp_file, audio_data, sample_rate)
                
                # แปลงเสียงเป็นข้อความ
                result = model.transcribe(temp_file, language='th', fp16=False)
                
                if result['text'].strip():
                    print(f">>> {result['text']}")
                else:
                    print("[ไม่มีเสียง]")
                print()
                
        except KeyboardInterrupt:
            print("\n\nหยุดการบันทึก")
            if os.path.exists(temp_file):
                os.remove(temp_file)
                
    except ImportError:
        print("กรุณาติดตั้ง sounddevice และ soundfile:")
        print("pip install sounddevice soundfile")
    except Exception as e:
        print(f"เกิดข้อผิดพลาด: {e}")


# ===== ตัวอย่างการใช้งาน =====

if __name__ == "__main__":
    print("=== Whisper Speech-to-Text ภาษาไทย ===\n")
    
    print("ขนาดโมเดล:")
    print("- tiny: เร็วที่สุด แต่แม่นยำน้อยที่สุด")
    print("- base: สมดุลระหว่างความเร็วและความแม่นยำ (แนะนำ)")
    print("- small: แม่นยำกว่า base")
    print("- medium: แม่นยำมาก แต่ช้า")
    print("- large: แม่นยำที่สุด แต่ช้ามาก ต้องการ RAM เยอะ\n")
    
    print("เลือกโหมด:")
    print("1. บันทึกเสียงจากไมโครโฟน")
    print("2. อ่านเสียงจากไฟล์")
    print("3. อ่านเสียงจากไฟล์พร้อม timestamps")
    print("4. อ่านเสียงและบันทึกลงไฟล์ข้อความ")
    print("5. โหมดแปลงเสียงแบบต่อเนื่อง (Real-time)")
    
    choice = input("\nเลือก (1-5): ")
    model = input("ขนาดโมเดล (tiny/base/small/medium/large) [base]: ").strip() or 'base'
    
    if choice == '1':
        duration = int(input("ระยะเวลาบันทึก (วินาที) [5]: ") or 5)
        transcribe_microphone(model_size=model, duration=duration)
    
    elif choice == '2':
        filename = input("ชื่อไฟล์เสียง: ")
        transcribe_file(filename, model_size=model)
    
    elif choice == '3':
        filename = input("ชื่อไฟล์เสียง: ")
        transcribe_file_with_timestamps(filename, model_size=model)
    
    elif choice == '4':
        filename = input("ชื่อไฟล์เสียง: ")
        output = input("ชื่อไฟล์ข้อความที่จะบันทึก (.txt): ")
        save_transcription_to_file(filename, output, model_size=model)
    
    elif choice == '5':
        duration = int(input("ระยะเวลาบันทึกแต่ละรอบ (วินาที) [5]: ") or 5)
        real_time_transcription(model_size=model, chunk_duration=duration)
    
    else:
        print("ตัวเลือกไม่ถูกต้อง")


# ===== คำแนะนำการติดตั้ง =====
"""
1. ติดตั้ง Whisper:
   pip install openai-whisper

2. ติดตั้ง dependencies สำหรับบันทึกเสียง:
   pip install sounddevice soundfile numpy

3. ติดตั้ง ffmpeg:
   - Windows: ดาวน์โหลดจาก https://ffmpeg.org/download.html
   - Mac: brew install ffmpeg
   - Linux: sudo apt install ffmpeg

   
4. ติดตั้ง PyTorch (ถ้ายังไม่มี):
   pip install torch torchvision torchaudio

หมายเหตุ:
- โมเดล 'base' เหมาะสำหรับการใช้งานทั่วไป
- โมเดล 'small' หรือ 'medium' จะแม่นยำกว่าสำหรับภาษาไทย
- ครั้งแรกที่รันจะต้องดาวน์โหลดโมเดล (ใช้เวลาสักครู่)
"""