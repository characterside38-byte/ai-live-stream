import os
import time
import threading
import json
import urllib.request
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from flask import Flask

app = Flask(__name__)

STREAM_KEY = os.environ.get("STREAM_KEY", "your_stream_key")

# Hardcoded fallback questions agar GitHub file load na ho
QUESTIONS = [
    {
        "q_hi": "ताजमहल किसने बनवाया था?",
        "q_en": "Who built the Taj Mahal?",
        "options": ["A) शाहजहाँ (Shah Jahan)", "B) अकबर (Akbar)", "C) बाबर (Babar)", "D) औरंगजेब (Aurangzeb)"],
        "answer": "A) शाहजहाँ (Shah Jahan)"
    },
    {
        "q_hi": "भारत की राजधानी क्या है?",
        "q_en": "What is the capital of India?",
        "options": ["A) मुंबई (Mumbai)", "B) दिल्ली (Delhi)", "C) कोलकाता (Kolkata)", "D) चेन्नई (Chennai)"],
        "answer": "B) दिल्ली (Delhi)"
    }
]

# GitHub se questions.json load karne ka code (Characterside38-byte / ai-live-stream)
try:
    url = "https://raw.githubusercontent.com/Characterside38-byte/ai-live-stream/main/questions.json"
    req = urllib.request.urlopen(url)
    QUESTIONS = json.loads(req.read().decode('utf-8'))
except Exception as e:
    print("Error loading questions from GitHub, using fallback:", e)

current_q_index = 0
timer_seconds = 10
quiz_state = "QUESTION" # "QUESTION" or "ANSWER"

@app.route('/')
def keep_alive():
    return "XOOMY Quiz Arena is LIVE!"

def generate_video_stream():
    global current_q_index, timer_seconds, quiz_state
    
    width, height, fps = 720, 1280, 24
    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"
    
    # FFmpeg command with continuous ambient gaming background audio generator
    command = [
        'ffmpeg', '-y', 
        '-f', 'rawvideo', '-vcodec', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f"{width}x{height}", '-r', str(fps), '-i', '-',
        '-f', 'lavfi', '-i', 'sine=f=150:r=44100,volume=0.12[s1]; sine=f=300:r=44100,volume=0.06[s2]; [s1][s2]amix=inputs=2',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'ultrafast', '-b:v', '1200k',
        '-g', '48', '-keyint_min', '48',
        '-c:a', 'aac', '-b:a', '128k',
        '-f', 'flv', rtmp_url
    ]
    
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 32)
        font_med = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 24)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 20)
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 36)
    except:
        font_large = ImageFont.load_default()
        font_med = ImageFont.load_default()
        font_small = ImageFont.load_default()
        title_font = ImageFont.load_default()

    last_time = time.time()

    while True:
        # Timer logic (10 seconds per question, then show answer for 4 seconds)
        if time.time() - last_time >= 1.0:
            timer_seconds -= 1
            last_time = time.time()
            if timer_seconds <= 0:
                if quiz_state == "QUESTION":
                    quiz_state = "ANSWER"
                    timer_seconds = 4  # Show answer for 4 seconds
                else:
                    quiz_state = "QUESTION"
                    timer_seconds = 10
                    current_q_index = (current_q_index + 1) % len(QUESTIONS)

        img = Image.new('RGB', (width, height), color=(15, 22, 36))
        draw = ImageDraw.Draw(img)
        
        # Header
        current_time_str = time.strftime('%H:%M:%S')
        draw.rectangle([0, 0, width, 80], fill=(26, 37, 55))
        draw.text((25, 20), "🎮 XOOMY GAMING ARENA", font=title_font, fill=(0, 255, 180))
        draw.text((530, 28), f"{current_time_str}", font=font_small, fill=(255, 255, 255))
        
        q_data = QUESTIONS[current_q_index]

        # Quiz Card Box
        draw.rectangle([35, 120, 685, 950], fill=(22, 32, 48), outline=(0, 255, 180), width=4)
        draw.text((60, 150), "🎯 LIVE QUIZ CHALLENGE 🎯", font=font_med, fill=(255, 200, 0))
        
        # Timer Display
        draw.text((570, 150), f"⏱️ {timer_seconds}s", font=font_med, fill=(255, 75, 75))

        if quiz_state == "QUESTION":
            # Question Hindi & English
            draw.text((60, 230), q_data["q_hi"], font=font_large, fill=(255, 255, 255))
            draw.text((60, 290), f"({q_data['q_en']})", font=font_small, fill=(180, 200, 220))
            
            # Options
            y_off = 380
            for opt in q_data["options"]:
                draw.rectangle([60, y_off, 660, y_off + 70], fill=(30, 45, 68), outline=(70, 130, 180), width=2)
                draw.text((80, y_off + 22), opt, font=font_med, fill=(0, 255, 180))
                y_off += 90
                
            draw.text((60, 840), "👉 Apne jawab live chat me dein! (Type in chat)", font=font_small, fill=(255, 200, 0))
            
        else:
            # Show Correct Answer
            draw.text((60, 300), "🎉 TIME UP! CORRECT ANSWER:", font=font_med, fill=(255, 150, 0))
            draw.rectangle([60, 400, 660, 500], fill=(20, 80, 50), outline=(0, 255, 120), width=3)
            draw.text((80, 432), q_data["answer"], font=font_large, fill=(255, 255, 255))
            draw.text((60, 600), "🔄 Agla question aa raha hai...", font=font_med, fill=(200, 200, 200))

        # Bottom info panel
        draw.rectangle([35, 980, 685, 1235], fill=(26, 37, 55), outline=(70, 130, 180), width=2)
        draw.text((60, 1020), f"📊 Question No: {current_q_index + 1} / {len(QUESTIONS)}", font=font_med, fill=(255, 255, 255))
        draw.text((60, 1090), "🔥 Non-Stop Live Quiz Arena", font=font_small, fill=(0, 255, 180))

        frame = np.array(img).tobytes()
        try:
            process.stdin.write(frame)
        except Exception:
            break
        time.sleep(1/fps)

if __name__ == "__main__":
    threading.Thread(target=generate_video_stream, daemon=True).start()
    app.run(host='0.0.0.0', port=10000)
