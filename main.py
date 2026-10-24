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

# Game & Quiz Global States
current_mode = "GAME"  # "GAME" or "QUIZ"
score = 0
level = 1
snake_pos = [[200, 200], [180, 200], [160, 200]]
snake_dir = [20, 0]
food_pos = [400, 300]
commentary = "AI Bot is dominating the arcade arena!"

quiz_question = "Q: India ki capital kya hai?"
quiz_options = "A) Mumbai\nB) Delhi\nC) Kolkata\nD) Chennai"
quiz_answer = "Correct Answer: B) Delhi"
timer_seconds = 30
quiz_state = "QUESTION" # "QUESTION" or "ANSWER"

@app.route('/')
def keep_alive():
    return "XOOMY Pro Arcade & Quiz Stream is LIVE 24/7!"

def generate_video_stream():
    global current_mode, score, level, snake_pos, snake_dir, food_pos, commentary
    global quiz_question, quiz_options, quiz_answer, timer_seconds, quiz_state
    
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
        font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 34)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 22)
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 38)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
        title_font = ImageFont.load_default()

    frame_count = 0
    last_timer_update = time.time()

    while True:
        frame_count += 1
        
        # Handle Timer for Quiz Mode
        if current_mode == "QUIZ":
            if time.time() - last_timer_update >= 1.0:
                timer_seconds -= 1
                last_timer_update = time.time()
                if timer_seconds <= 0:
                    if quiz_state == "QUESTION":
                        quiz_state = "ANSWER"
                        timer_seconds = 10 # show answer for 10 seconds
                    else:
                        # Switch back to Game after answer
                        current_mode = "GAME"
                        quiz_state = "QUESTION"
                        timer_seconds = 30

        img = Image.new('RGB', (width, height), color=(15, 22, 36))
        draw = ImageDraw.Draw(img)
        
        # Header & Clock
        current_time = time.strftime('%H:%M:%S')
        draw.rectangle([0, 0, width, 65], fill=(26, 37, 55))
        draw.text((30, 15), "🔥 XOOMY 24/7 ARCADE & LIVE QUIZ ARENA", font=title_font, fill=(0, 255, 180))
        draw.text((1030, 20), f"TIME: {current_time}", font=small_font, fill=(255, 255, 255))
        
        if current_mode == "GAME":
            # Update Snake position smoothly every 5 frames
            if frame_count % 5 == 0:
                head = [snake_pos[0][0] + snake_dir[0], snake_pos[0][1] + snake_dir[1]]
                
                # Boundaries check & wrap
                if head[0] < 90: head[0] = 910
                if head[0] > 910: head[0] = 90
                if head[1] < 110: head[1] = 630
                if head[1] > 630: head[1] = 110
                
                snake_pos.insert(0, head)
                
                # Check if snake eats food
                if abs(head[0] - food_pos[0]) < 18 and abs(head[1] - food_pos[1]) < 18:
                    score += 10
                    if score % 50 == 0:
                        level += 1
                    food_pos = [random.randint(120, 880), random.randint(130, 580)]
                    commentary = random.choice([
                        "Boom! Apple kha liya, score high ho gaya!", 
                        "Let's go! Pro snake movement!", 
                        "Agle quiz mein sabka test hoga!",
                        "Speed badh rahi hai, maza aa raha hai!"
                    ])
                else:
                    snake_pos.pop()
                
                # AI Autonomous Direction Change
                if random.random() < 0.2:
                    possible_dirs = [[20, 0], [-20, 0], [0, 20], [0, -20]]
                    snake_dir = random.choice(possible_dirs)

            # Draw Game Arena Box
            draw.rectangle([80, 90, 930, 650], outline=(70, 130, 180), width=3)
            
            # Draw Snake (Body segments)
            for idx, seg in enumerate(snake_pos):
                color = (0, 255, 120) if idx == 0 else (0, 180, 90)
                draw.rectangle([seg[0], seg[1], seg[0]+16, seg[1]+16], fill=color)
                
            # Draw Food (Apple)
            draw.ellipse([food_pos[0], food_pos[1], food_pos[0]+16, food_pos[1]+16], fill=(255, 60, 60))
            
            # Draw Side Stats Panel
            draw.rectangle([950, 90, 1260, 650], fill=(22, 32, 48), outline=(70, 130, 180), width=2)
            draw.text((970, 120), "📊 LIVE STATS", font=font, fill=(255, 200, 0))
            draw.text((970, 180), f"Score: {score}", font=small_font, fill=(255, 255, 255))
            draw.text((970, 220), f"Level: {level}", font=small_font, fill=(0, 255, 180))
            draw.text((970, 260), "Mode: AI Snake", font=small_font, fill=(200, 200, 255))
            
            draw.text((970, 330), "🗣️ AI COMMENTARY:", font=font, fill=(255, 200, 0))
            y_off = 390
            for line in [commentary[i:i+26] for i in range(0, len(commentary), 26)]:
                draw.text((970, y_off), line, font=small_font, fill=(220, 230, 255))
                y_off += 30
                
            draw.text((970, 580), "⏳ Next Quiz in few mins", font=small_font, fill=(255, 100, 100))

        elif current_mode == "QUIZ":
            # Draw Quiz Arena Box
            draw.rectangle([150, 100, 1130, 630], fill=(22, 32, 48), outline=(0, 255, 180), width=4)
            draw.text((200, 130), "🎯 LIVE AI QUIZ CHALLENGE 🎯", font=font, fill=(255, 200, 0))
            draw.text((950, 130), f"⏱️ {timer_seconds}s", font=font, fill=(255, 75, 75))
            
            if quiz_state == "QUESTION":
                y_off = 220
                for line in quiz_question.split('\n'):
                    draw.text((200, y_off), line, font=font, fill=(255, 255, 255))
                    y_off += 50
                
                y_off = 360
                for line in quiz_options.split('\n'):
                    draw.text((220, y_off), line, font=font, fill=(0, 255, 180))
                    y_off += 45
                    
                draw.text((200, 560), "👉 Type your answer in live chat right now!", font=small_font, fill=(255, 200, 0))
            else:
                # Show Answer
                draw.text((200, 250), "🎉 TIME UP! CORRECT ANSWER:", font=font, fill=(255, 150, 0))
                draw.text((200, 350), quiz_answer, font=title_font, fill=(0, 255, 120))
                draw.text((200, 500), "🔄 Returning to Arcade Game...", font=small_font, fill=(200, 200, 200))

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
        # Play game for 5 minutes
        current_mode = "GAME"
        commentary = "Epic arcade gameplay running smoothly!"
        time.sleep(300) 

        # Switch to Quiz Mode
        current_mode = "QUIZ"
        quiz_state = "QUESTION"
        timer_seconds = 30
        
        try:
            response = model.generate_content("Give a short interesting general knowledge or math puzzle question in Hinglish with options A, B, C, D and also mention the correct answer clearly at the end starting with 'Correct Answer:'.")
            text = response.text.strip()
            # Parse text into question, options, answer
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
