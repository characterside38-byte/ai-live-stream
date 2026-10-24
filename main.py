import os
import time
import threading
import subprocess
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from flask import Flask
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

# Global state variables
current_mode = "GAME"  # Modes: "GAME" or "QUIZ"
display_content = "Game Loading..."
quiz_timer = time.time()
snake_pos = [[200, 200], [220, 200], [240, 200]]
snake_dir = [20, 0]
food_pos = [400, 300]
score = 0
commentary = "AI Bot playing retro game & waiting for players!"

@app.route('/')
def keep_alive():
    return "XOOMY Arcade & Quiz Stream is LIVE 24/7!"

def generate_video_stream():
    global current_mode, display_content, snake_pos, snake_dir, food_pos, score, commentary
    width, height, fps = 1280, 720, 24
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
        font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 36)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 24)
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 40)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
        title_font = ImageFont.load_default()

    frame_count = 0
    while True:
        frame_count += 1
        img = Image.new('RGB', (width, height), color=(15, 22, 36))
        draw = ImageDraw.Draw(img)
        
        # Draw Header & Live Clock
        current_time = time.strftime('%H:%M:%S')
        draw.rectangle([0, 0, width, 70], fill=(26, 37, 55))
        draw.text((30, 18), "🎮 XOOMY 24/7 ARCADE & QUIZ ARENA", font=title_font, fill=(0, 255, 180))
        draw.text((1020, 22), f"TIME: {current_time}", font=small_font, fill=(255, 255, 255))
        
        if current_mode == "GAME":
            # Update Snake position every 6 frames (smooth movement)
            if frame_count % 6 == 0:
                head = [snake_pos[0][0] + snake_dir[0], snake_pos[0][1] + snake_dir[1]]
                
                # Boundaries wrap around
                if head[0] < 100: head[0] = 900
                if head[0] > 900: head[0] = 100
                if head[1] < 120: head[1] = 620
                if head[1] > 620: head[1] = 120
                
                snake_pos.insert(0, head)
                
                # Check food collision
                if abs(head[0] - food_pos[0]) < 20 and abs(head[1] - food_pos[1]) < 20:
                    score += 10
                    food_pos = [random.randint(150, 850), random.randint(150, 580)]
                    commentary = random.choice([
                        "Nice move! Score badh raha hai!", 
                        "Agle 5 minute mein naya Quiz aane wala hai!", 
                        "Type 'quiz' in chat for instant challenge!",
                        "AI bot is playing pro level snake!"
                    ])
                else:
                    snake_pos.pop()
                
                # Change direction randomly for autonomous gameplay
                if random.random() < 0.15:
                    snake_dir = random.choice([[20, 0], [-20, 0], [0, 20], [0, -20]])

            # Draw Game Arena Box
            draw.rectangle([90, 100, 920, 640], outline=(70, 130, 180), width=3)
            
            # Draw Snake
            for idx, segment in enumerate(snake_pos):
                color = (0, 255, 120) if idx == 0 else (0, 180, 90)
                draw.rectangle([segment[0], segment[1], segment[0]+18, segment[1]+18], fill=color)
                
            # Draw Food
            draw.ellipse([food_pos[0], food_pos[1], food_pos[0]+18, food_pos[1]+18], fill=(255, 75, 75))
            
            # Draw Side Panel for Stats & Commentary
            draw.rectangle([940, 100, 1250, 640], fill=(22, 32, 48), outline=(70, 130, 180), width=2)
            draw.text((960, 130), "📊 LIVE STATS", font=font, fill=(255, 200, 0))
            draw.text((960, 200), f"Score: {score}", font=small_font, fill=(255, 255, 255))
            draw.text((960, 250), "Mode: AI Arcade", font=small_font, fill=(0, 255, 180))
            draw.text((960, 320), "💬 COMMENTARY:", font=font, fill=(255, 200, 0))
            
            # Wrap commentary text
            y_offset = 380
            for line in [commentary[i:i+25] for i in range(0, len(commentary), 25)]:
                draw.text((960, y_offset), line, font=small_font, fill=(200, 220, 255))
                y_offset += 35
                
            draw.text((960, 560), "⏳ Next Quiz in few mins", font=small_font, fill=(255, 100, 100))

        elif current_mode == "QUIZ":
            # Draw Quiz Box
            draw.rectangle([150, 120, 1130, 620], fill=(22, 32, 48), outline=(0, 255, 180), width=4)
            draw.text((200, 160), "🔥 LIVE AI QUIZ CHALLENGE 🔥", font=font, fill=(255, 200, 0))
            
            y_offset = 260
            for line in display_content.split('\n'):
                draw.text((200, y_offset), line, font=font, fill=(255, 255, 255))
                y_offset += 55
                
            draw.text((200, 530), "👉 Type your answer in live chat right now!", font=small_font, fill=(0, 255, 180))

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
    global current_mode, display_content, quiz_timer, commentary
    time.sleep(15)

    video_id = None
    while not video_id:
        video_id = get_live_video_id()
        if not video_id:
            time.sleep(10)

    # Background thread to handle YouTube Chat
    threading.Thread(target=handle_chat, args=(video_id,), daemon=True).start()

    while True:
        # Play game for 5 minutes (300 seconds)
        current_mode = "GAME"
        commentary = "Epic gameplay running! Quiz coming soon."
        time.sleep(300) 

        # Switch to QUIZ mode for 1 minute
        current_mode = "QUIZ"
        try:
            response = model.generate_content("Give a short 1-line interesting general knowledge or math puzzle question in Hinglish with options A, B, C.")
            display_content = response.text.strip()
        except:
            display_content = "Q: India ki capital kya hai?\nA) Mumbai\nB) Delhi\nC) Kolkata"
        
        time.sleep(60) # Show quiz for 60 seconds

def handle_chat(video_id):
    global display_content, commentary
    try:
        chat = pytchat.create(video_id=video_id)
        while chat.is_alive():
            for c in chat.get().sync_items():
                msg = c.message.lower()
                commentary = f"{c.author.name}: {c.message[:20]}"
                if "quiz" in msg or "next" in msg:
                    try:
                        response = model.generate_content(f"Viewer {c.author.name} requested a quiz. Give a short 1-line interesting puzzle in Hinglish.")
                        display_content = response.text.strip()
                    except:
                        pass
            time.sleep(2)
    except Exception:
        pass

if __name__ == "__main__":
    threading.Thread(target=generate_video_stream, daemon=True).start()
    threading.Thread(target=ai_brain_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=10000)
