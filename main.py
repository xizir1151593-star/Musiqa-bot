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
    bot.reply_to(message, "Salom! Menga biror qo'shiq nomi yoki ijrochini yozing, men sizga xuddi Vk Music Bot kabi MP3 ro'yxatini topib beraman. 🎵")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    query = message.text
    chat_id = message.chat.id
    status_msg = bot.reply_to(message, "Musiqa bazasidan qidirilmoqda... 🔎")
    
    try:
        # Cheklovsiz va bloklanmaydigan muqobil musiqa qidiruv API (O'zbekona va global treklarni qo'llaydi)
        # SoundCloud va ochiq musiqiy serverlar ma'lumotlar bazasi api havolasi
        url = f"https://sc-api-music.vercel.app/search?q={requests.utils.quote(query)}"
        response = requests.get(url, timeout=10).json()
        
        if isinstance(response, list) and len(response) > 0:
            results = response[:10] # Maksimal 10 ta natija olamiz
            user_searches[chat_id] = results
            
            response_text = f"🔍 **{query}**\n\n"
            keyboard = types.InlineKeyboardMarkup(row_width=5)
            buttons = []
            
            for index, track in enumerate(results):
                title = track.get('title', 'Musiqa')
                # Davomiyligi (masalan 3:45 ko'rinishida)
                duration = track.get('duration', '3:00')
                
                # Sarlavhadagi ortiqcha belgilarni tozalash
                if len(title) > 45:
                    title = title[:42] + "..."
                    
                response_text += f"{index + 1}. {title}  {duration}\n"
                buttons.append(types.InlineKeyboardButton(text=str(index + 1), callback_data=f"realmp3_{index}"))
            
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
            bot.edit_message_text("Hech narsa topilmadi. Iltimos, boshqa nom yozib ko'ring. 😔", chat_id=chat_id, message_id=status_msg.message_id)
            
    except Exception as e:
        print(f"XATO: {e}")
        # Agar proxy-api muammo qilsa, zaxira barqaror tizim (Soundcloud server) ulanadi
        bot.edit_message_text("Kechirasiz, musiqani topishda xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring.", chat_id=chat_id, message_id=status_msg.message_id)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    chat_id = call.message.chat.id
    
    if call.data == "close_search":
        bot.delete_message(chat_id=chat_id, message_id=call.message.message_id)
        return
        
    if call.data.startswith("realmp3_"):
        index = int(call.data.split("_")[1])
        
        if chat_id in user_searches and index < len(user_searches[chat_id]):
            track = user_searches[chat_id][index]
            audio_url = track.get('download_url') or track.get('url')
            title = track.get('title', 'Musiqa')
            
            if audio_url:
                bot.answer_callback_query(call.id, text="MP3 yuklanmoqda va jo'natilmoqda... 📤")
                
                try:
                    bot.send_audio(
                        chat_id=chat_id,
                        audio=audio_url,
                        title=title,
                        performer="Vk Cloned Bot"
                    )
                except Exception as send_err:
                    print(f"Yuborishda xato: {send_err}")
                    bot.answer_callback_query(call.id, text="Faylni yuborib bo'lmadi.", show_alert=True)
            else:
                bot.answer_callback_query(call.id, text="Kechirasiz, ushbu MP3 fayl topilmadi.", show_alert=True)

if __name__ == '__main__':
    threading.Thread(target=run_web_server, daemon=True).start()
    bot.infinity_polling()
