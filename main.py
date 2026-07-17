import os
import telebot
from telebot import types
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

BOT_TOKEN = '8893365405:AAGrucdJBJhNfE-g6Q1qbmqtqYpB5nIYfIQ'
bot = telebot.TeleBot(BOT_TOKEN)

# Foydalanuvchi qidiruvlarini saqlash uchun kesh
user_searches = {}

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
    bot.reply_to(message, "Salom! Menga biror qo'shiq nomi yoki ijrochini yozing, men sizga toza MP3 formatida topib beraman. 🎵")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    query = message.text
    chat_id = message.chat.id
    status_msg = bot.reply_to(message, "Musiqa bazasidan qidirilmoqda... 🔎")
    
    try:
        # Deezer rasmiy va ochiq API xizmati (Bloklanmaydi va faqat MP3 qaytaradi)
        url = f"https://api.deezer.com/search?q={requests.utils.quote(query)}&limit=10"
        response = requests.get(url, timeout=10).json()
        
        if response.get('data') and len(response['data']) > 0:
            results = response['data']
            user_searches[chat_id] = results
            
            response_text = f"🔍 **{query} (MP3)**\n\n"
            keyboard = types.InlineKeyboardMarkup(row_width=5)
            buttons = []
            
            for index, track in enumerate(results):
                title = track.get('title', 'Musiqa')
                artist_info = track.get('artist', {})
                artist = artist_info.get('name', 'Ijrochi')
                
                # Davomiyligini hisoblash
                duration_sec = track.get('duration', 0)
                minutes = duration_sec // 60
                seconds = duration_sec % 60
                duration_str = f"{minutes}:{seconds:02d}"
                
                if len(title) > 35:
                    title = title[:32] + "..."
                    
                response_text += f"{index + 1}. {artist} - {title}  {duration_str}\n"
                buttons.append(types.InlineKeyboardButton(text=str(index + 1), callback_data=f"dzmp3_{index}"))
            
            keyboard.add(*buttons[:5])
            if len(buttons) > 5:
                keyboard.add(*buttons[5:])
                
            keyboard.add(types.InlineKeyboardButton(text="❌", callback_data="close_search"))
            
            bot.edit_message_text(
                text=response_text, 
                chat_id=chat_id, 
                message_id=status_msg.message_id, 
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            bot.edit_message_text("Hech narsa topilmadi. Iltimos, nomini to'g'riroq yozib ko'ring. 🔍", chat_id=chat_id, message_id=status_msg.message_id)
            
    except Exception as e:
        print(f"XATO: {e}")
        bot.edit_message_text("Kechirasiz, musiqani topishda xatolik yuz berdi. Qayta urinib ko'ring. 😔", chat_id=chat_id, message_id=status_msg.message_id)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    chat_id = call.message.chat.id
    
    if call.data == "close_search":
        bot.delete_message(chat_id=chat_id, message_id=call.message.message_id)
        return
        
    if call.data.startswith("dzmp3_"):
        index = int(call.data.split("_")[1])
        
        if chat_id in user_searches and index < len(user_searches[chat_id]):
            track = user_searches[chat_id][index]
            audio_url = track.get('preview') # To'g'ridan-to'g'ri yuqori sifatli MP3 havola
            title = track.get('title', 'Musiqa')
            artist_info = track.get('artist', {})
            artist = artist_info.get('name', 'Ijrochi')
            
            if audio_url:
                bot.answer_callback_query(call.id, text="MP3 jo'natilmoqda... 📤")
                
                try:
                    bot.send_audio(
                        chat_id=chat_id,
                        audio=audio_url,
                        title=title,
                        performer=artist
                    )
                except Exception as send_err:
                    print(f"Yuborishda xato: {send_err}")
                    bot.answer_callback_query(call.id, text="Faylni yuborishda xato bo'ldi.", show_alert=True)
            else:
                bot.answer_callback_query(call.id, text="Kechirasiz, ushbu MP3 fayl topilmadi.", show_alert=True)

if __name__ == '__main__':
    threading.Thread(target=run_web_server, daemon=True).start()
    bot.infinity_polling()
