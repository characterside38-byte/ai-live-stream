import os
import time
import threading
import subprocess
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from Flask import Flask
import pytchat
import google.generativeai as genai
import urllib.request
import re

app = Flask(__name__)

STREAM_KEY = os.environ.get("STREAM_KEY", "your_stream_key")
CHANNEL_HANDLE = os.environ.get("CHANNEL_HANDLE", "@your_channel") 
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "your_api_key")

if GEMINI_API_KEY != "your_api_key":
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')

# Vertical Game & Quiz States (No AI/24/7 labels)
current_mode = "GAME"  # "GAME" or "QUIZ"
score = 0
level = 1
snake_pos = [[360, 400], [340, 400], [320, 400]]
snake_dir = [20, 0]
food_pos = [360, 600]
commentary = "Pro gameplay running smoothly!"

quiz_question = "Q: India ki capital kya hai?"
quiz_options = "A) Mumbai\nB) Delhi\nC) Kolkata\nD) Chennai"
quiz_answer = "Correct Answer: B) Delhi"
timer_seconds = 30
quiz_state = "QUESTION"

@app.route('/')
def keep_alive():
    return "Stream is LIVE!"

def generate_video_stream():
    global current_mode, score, level, snake_pos, snake_dir, food_pos, commentary
    global quiz_question, quiz_options, quiz_answer, timer_seconds, quiz_state
    
    # Vertical Resolution for Shorts Feed (720x1280)
    width, height, fps = 720, 1280, 24
    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"
    
    command = [
        'ffmpeg', '-y', 
        '-f', 'rawvideo', '-vcodec', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f"{width}x{height}", '-r', str(fps), '-i', '-',
        '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'ultrafast', '-b:v', '2500k',
        '-g', '48', '-keyint_min', '48',
        '-c:a', 'aac', '-b:a', '128k',
        '-f', 'flv', rtmp_url
    ]
    
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 32)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 22)
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 36)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
        title_font = ImageFont.load_default()

    frame_count = 0
    last_timer_update = time.time()

    while True:
        frame_count += 1
        
        if current_mode == "QUIZ":
            if time.time() - last_timer_update >= 1.0:
                timer_seconds -= 1
                last_timer_update = time.time()
                if timer_seconds <= 0:
                    if quiz_state == "QUESTION":
                        quiz_state = "ANSWER"
                        timer_seconds = 10 
                    else:
                        current_mode = "GAME"
                        quiz_state = "QUESTION"
                        timer_seconds = 30

        img = Image.new('RGB', (width, height), color=(15, 22, 36))
        draw = ImageDraw.Draw(img)
        
        # Vertical Top Header
        current_time = time.strftime('%H:%M:%S')
        draw.rectangle([0, 0, width, 80], fill=(26, 37, 55))
        draw.text((25, 20), "🎮 XOOMY GAMING ARENA", font=title_font, fill=(0, 255, 180))
        draw.text((530, 28), f"{current_time}", font=small_font, fill=(255, 255, 255))
        
        if current_mode == "GAME":
            if frame_count % 5 == 0:
                head = [snake_pos[0][0] + snake_dir[0], snake_pos[0][1] + snake_dir[1]]
                
                # Vertical Arena Bounds (Width 720 -> Box 40 to 680, Height 1280 -> Box 100 to 850)
                if head[0] < 45: head[0] = 675
                if head[0] > 675: head[0] = 45
                if head[1] < 100: head[1] = 845
                if head[1] > 845: head[1] = 100
                
                snake_pos.insert(0, head)
                
                if abs(head[0] - food_pos[0]) < 18 and abs(head[1] - food_pos[1]) < 18:
                    score += 10
                    if score % 50 == 0:
                        level += 1
                    food_pos = [random.randint(70, 650), random.randint(130, 800)]
                    commentary = random.choice([
                        "Nice shot! Apple kha liya!", 
                        "Pro gamer moves!", 
                        "Next quiz coming up shortly...",
                        "Speeding up, let's go!"
                    ])
                else:
                    snake_pos.pop()
                
                if random.random() < 0.2:
                    snake_dir = random.choice([[20, 0], [-20, 0], [0, 20], [0, -20]])

            # Vertical Game Arena Box
            draw.rectangle([35, 95, 685, 855], outline=(70, 130, 180), width=3)
            
            # Snake
            for idx, seg in enumerate(snake_pos):
                color = (0, 255, 120) if idx == 0 else (0, 180, 90)
                draw.rectangle([seg[0], seg[1], seg[0]+16, seg[1]+16], fill=color)
                
            # Food
            draw.ellipse([food_pos[0], food_pos[1], food_pos[0]+16, food_pos[1]+16], fill=(255, 60, 60))
            
            # Vertical Bottom Stats & Commentary Panel
            draw.rectangle([35, 880, 685, 1235], fill=(22, 32, 48), outline=(70, 130, 180), width=2)
            draw.text((55, 900), f"📊 Score: {score}   |   Level: {level}", font=font, fill=(255, 200, 0))
            draw.text((55, 960), "💬 FEED:", font=small_font, fill=(0, 255, 180))
            draw.text((150, 960), commentary[:38], font=small_font, fill=(220, 230, 255))
            draw.text((55, 1010), "⏳ Next Quiz arriving soon in Arena...", font=small_font, fill=(255, 100, 100))
            draw.text((55, 1100), "👉 Type answers in live chat!", font=font, fill=(0, 255, 180))

        elif current_mode == "QUIZ":
            # Vertical Quiz Box
            draw.rectangle([35, 95, 685, 1235], fill=(22, 32, 48), outline=(0, 255, 180), width=4)
            draw.text((60, 130), "🎯 LIVE QUIZ CHALLENGE 🎯", font=font, fill=(255, 200, 0))
            draw.text((560, 130), f"⏱️ {timer_seconds}s", font=font, fill=(255, 75, 75))
            
            if quiz_state == "QUESTION":
                y_off = 240
                for line in quiz_question.split('\n'):
                    draw.text((60, y_off), line, font=font, fill=(255, 255, 255))
                    y_off += 50
                
                y_off = 420
                for line in quiz_options.split('\n'):
                    draw.text((80, y_off), line, font=font, fill=(0, 255, 180))
                    y_off += 55
                    
                draw.text((60, 750), "👉 Type your answer in live chat right now!", font=small_font, fill=(255, 200, 0))
            else:
                draw.text((60, 300), "🎉 TIME UP! ANSWER:", font=font, fill=(255, 150, 0))
                draw.text((60, 420), quiz_answer, font=title_font, fill=(0, 255, 120))
                draw.text((60, 600), "🔄 Resuming game...", font=small_font, fill=(200, 200, 200))

        frame = np.array(img).tobytes()
        try:
            process.stdin.write(frame)
        except Exception:
            break
        time.sleep(1/fps)

def get_live_video_id():
    url = f"https://www.youtube.com/{CHANNEL_HANDLE}/live"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req).read().decode('utf-8')
        match = re.search(r'\"videoId\":\"([a-zA-Z0-9_-]{11})\"', html)
        if match:
            return match.group(1)
    except:
        pass
    return None

def ai_brain_loop():
    global current_mode, quiz_question, quiz_options, quiz_answer, timer_seconds, quiz_state, commentary
    time.sleep(15)

    video_id = None
    while not video_id:
        video_id = get_live_video_id()
        if not video_id:
            time.sleep(10)

    threading.Thread(target=handle_chat, args=(video_id,), daemon=True).start()

    while True:
        current_mode = "GAME"
        commentary = "Arcade gameplay session active!"
        time.sleep(300) 

        current_mode = "QUIZ"
        quiz_state = "QUESTION"
        timer_seconds = 30
        
        try:
            response = model.generate_content("Give a short interesting general knowledge or math puzzle question in Hinglish with options A, B, C, D and also mention the correct answer clearly at the end starting with 'Correct Answer:'.")
            text = response.text.strip()
            parts = text.split("Correct Answer:")
            quiz_question = parts[0].strip()
            if len(parts) > 1:
                quiz_answer = "Correct Answer:" + parts[1].strip()
            else:
                quiz_answer = "Correct Answer: B"
        except:
            quiz_question = "Q: Bharat ka sabse lamba nadi kaun sa hai?"
            quiz_options = "A) Yamuna\nB) Ganga\nC) Brahmaputra\nD) Godavari"
            quiz_answer = "Correct Answer: B) Ganga"

def handle_chat(video_id):
    global commentary
    try:
        chat = pytchat.create(video_id=video_id)
        while chat.is_alive():
            for c in chat.get().sync_items():
                commentary = f"{c.author.name}: {c.message[:25]}"
            time.sleep(2)
    except Exception:
        pass

if __name__ == "__main__":
    threading.Thread(target=generate_video_stream, daemon=True).start()
    threading.Thread(target=ai_brain_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=10000)
