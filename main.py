import os
import telebot
import requests
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
    bot.reply_to(message, "Salom! Menga biror qo'shiq nomi yoki ijrochini yozing, men uni sizga tez fursatda topib beraman! 🎵")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    query = message.text
    status_msg = bot.reply_to(message, "Musiqa qidirilmoqda... 🔎")
    
    try:
        # iTunes ochiq va bepul API'sidan foydalanamiz (bloklanmaydi, juda tez ishlaydi)
        url = f"https://itunes.apple.com/search?term={requests.utils.quote(query)}&media=music&limit=1"
        response = requests.get(url).json()
        
        if response.get('resultCount', 0) > 0:
            track = response['results'][0]
            title = track.get('trackName', 'Musiqa')
            performer = track.get('artistName', 'Ijrochi')
            audio_url = track.get('previewUrl') # To'g'ridan-to'g'ri audio havola
            
            if audio_url:
                bot.edit_message_text("Musiqa topildi! Yuklanmoqda... 📤", chat_id=message.chat.id, message_id=status_msg.message_id)
                
                # Audioni havola orqali srazu foydalanuvchiga yuboramiz
                bot.send_audio(
                    chat_id=message.chat.id, 
                    audio=audio_url, 
                    title=title, 
                    performer=performer
                )
                bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)
            else:
                bot.edit_message_text("Kechirasiz, ushbu musiqaning audio fayli topilmadi. 😔", chat_id=message.chat.id, message_id=status_msg.message_id)
        else:
            bot.edit_message_text("Hech narsa topilmadi. Iltimos, nomini to'g'riroq yozib ko'ring. 🔍", chat_id=message.chat.id, message_id=status_msg.message_id)
            
    except Exception as e:
        print(f"XATO YUZ BERDI: {e}")
        bot.edit_message_text("Kechirasiz, tizimda xatolik yuz berdi. Oxirroq qayta urinib ko'ring. 😔", chat_id=message.chat.id, message_id=status_msg.message_id)

if __name__ == '__main__':
    threading.Thread(target=run_web_server, daemon=True).start()
    bot.infinity_polling()
