import os
import time
import threading
import subprocess
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

display_text = "Welcome to XOOMY Live!\nGet ready for the next puzzle..."

@app.route('/')
def keep_alive():
    return "AI Stream is LIVE 24/7!"

def generate_video_stream():
    global display_text
    width, height, fps = 1280, 720, 24
    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"
    
    # Yahan '-g 48' aur '-keyint_min 48' add kiya hai jo YouTube ka keyframe error fix karega
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
        font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 50)
    except:
        font = ImageFont.load_default()

    while True:
        img = Image.new('RGB', (width, height), color=(15, 25, 45))
        draw = ImageDraw.Draw(img)
        
        margin = 100
        offset = 250
        for line in display_text.split('\n'):
            draw.text((margin, offset), line, font=font, fill=(255, 255, 255))
            offset += 60
            
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

def ai_brain_and_chat():
    global display_text
    time.sleep(20) 

    try:
        response = model.generate_content("Give me a short 1-line interesting logic or math puzzle in Hinglish.")
        display_text = f"NEW PUZZLE:\n\n{response.text.strip()}\n\nAnswer in chat!"
    except:
        pass

    video_id = None
    while not video_id:
        video_id = get_live_video_id()
        if not video_id:
            time.sleep(10)
    
    try:
        chat = pytchat.create(video_id=video_id)
        while chat.is_alive():
            for c in chat.get().sync_items():
                msg = c.message.lower()
                if "puzzle" in msg or "next" in msg:
                    display_text = f"Wait {c.author.name}, naya puzzle aa raha hai..."
                    try:
                        prompt = f"Viewer {c.author.name} asked for a puzzle. Give a very short 1-line interesting math or word puzzle in Hinglish."
                        response = model.generate_content(prompt)
                        display_text = f"Puzzle for {c.author.name}:\n\n{response.text.strip()}"
                    except:
                        pass
            time.sleep(2)
    except Exception:
        print("Chat abhi active nahi hai.")

if __name__ == "__main__":
    threading.Thread(target=generate_video_stream, daemon=True).start()
    threading.Thread(target=ai_brain_and_chat, daemon=True).start()
    app.run(host='0.0.0.0', port=10000)
