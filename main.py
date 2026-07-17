import os
import telebot
from yt_dlp import YoutubeDL
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

BOT_TOKEN = '8893365405:AAGrucdJBJhNfE-g6Q1qbmqtqYpB5nIYfIQ'
bot = telebot.TeleBot(BOT_TOKEN)

class WebServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot ishlayapti!")

def run_web_server():
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(('0.0.0.0', port), WebServer)
    server.serve_forever()

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Salom! Menga biror qo'shiq nomi yoki ijrochini yozing, men uni sizga topib beraman. 🎵")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    query = message.text
    status_msg = bot.reply_to(message, "Qidirilmoqda... 🔎")
    
    # FFmpeg talab qilmaydigan eng xavfsiz sozlamalar
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'music_file.%(ext)s',  # Fayl nomini oddiy va aniq qilamiz
        'default_search': 'ytsearch1',
        'noplaylist': True,
        'quiet': True
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)
            video_info = info['entries'][0] if 'entries' in info else info
            title = video_info.get('title', 'Musiqa')
            
            # Yuklangan fayl formatini (m4a, webm yoki mp3) aniqlab olamiz
            ext = video_info.get('ext', 'm4a')
            file_path = f"music_file.{ext}"

            bot.edit_message_text("Musiqa topildi! Yuklanmoqda... 📤", chat_id=message.chat.id, message_id=status_msg.message_id)
            
            with open(file_path, 'rb') as audio:
                bot.send_audio(chat_id=message.chat.id, audio=audio, title=title, performer="Musiqa Bot")
            
            if os.path.exists(file_path):
                os.remove(file_path)
                
            bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)
    except Exception as e:
        print(f"XATO YUZ BERDI: {e}")
        bot.edit_message_text("Kechirasiz, musiqani topishda xatolik yuz berdi. 😔\nMuammo davom etsa, qayta urinib ko'ring.", chat_id=message.chat.id, message_id=status_msg.message_id)

if __name__ == '__main__':
    threading.Thread(target=run_web_server, daemon=True).start()
    bot.infinity_polling()

