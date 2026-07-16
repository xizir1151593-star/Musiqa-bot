import os
import telebot
from yt_dlp import YoutubeDL
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# Sizning haqiqiy bot tokeningiz joylandi!
BOT_TOKEN = '8893365405:AAGrucdJBJhNfE-g6Q1qbmqtqYpB5nIYfIQ'
bot = telebot.TeleBot(BOT_TOKEN)

class WebServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot ishlayapti!")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), WebServer)
    server.serve_forever()

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Salom! Menga biror qo'shiq nomi yoki ijrochini yozing, men uni sizga topib beraman. 🎵")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    query = message.text
    status_msg = bot.reply_to(message, "Qidirilmoqda... 🔎")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': '%(title)s.%(ext)s',
        'default_search': 'ytsearch1',
        'noplaylist': True,
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        'quiet': True
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)
            video_info = info['entries'][0] if 'entries' in info else info
            title = video_info.get('title', 'music')
            file_path = f"{title}.mp3"

            bot.edit_message_text("Musiqa topildi! Yuklanmoqda... 📤", chat_id=message.chat.id, message_id=status_msg.message_id)
            
            with open(file_path, 'rb') as audio:
                bot.send_audio(chat_id=message.chat.id, audio=audio, title=title, performer="Musiqa Bot")
            
            os.remove(file_path)
            bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)
    except Exception as e:
        bot.edit_message_text("Kechirasiz, musiqani topishda xatolik yuz berdi. 😔", chat_id=message.chat.id, message_id=status_msg.message_id)

if __name__ == '__main__':
    threading.Thread(target=run_web_server, daemon=True).start()
    print("Bot doimiy rejimda ishga tushdi...")
    bot.infinity_polling()
