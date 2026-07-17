
import os
import telebot
from telebot import types
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

BOT_TOKEN = '8893365405:AAGrucdJBJhNfE-g6Q1qbmqtqYpB5nIYfIQ'
bot = telebot.TeleBot(BOT_TOKEN)

# Foydalanuvchilarning oxirgi qidiruv natijalarini vaqtinchalik saqlash uchun kesh
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
    bot.reply_to(message, "Salom! Menga biror qo'shiq nomi yoki ijrochini yozing, men sizga ro'yxat ko'rinishida topib beraman. 🎵")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    query = message.text
    chat_id = message.chat.id
    status_msg = bot.reply_to(message, "Qidirilmoqda... 🔎")
    
    try:
        # iTunes ochiq va barqaror API'sidan 10 ta musiqa qidiramiz
        url = f"https://itunes.apple.com/search?term={requests.utils.quote(query)}&media=music&limit=10"
        response = requests.get(url).json()
        
        if response.get('resultCount', 0) > 0:
            results = response['results']
            
            # Natijalarni keshga saqlaymiz, foydalanuvchi tugmani bosganda audio havolasini olish uchun
            user_searches[chat_id] = results
            
            response_text = f"🔍 **{query}**\n\n"
            keyboard = types.InlineKeyboardMarkup(row_width=5)
            buttons = []
            
            for index, track in enumerate(results):
                title = track.get('trackName', 'Musiqa')
                artist = track.get('artistName', 'Ijrochi')
                # Millisekundni minut va sekundga o'giramiz
                duration_ms = track.get('trackTimeMillis', 0)
                minutes = (duration_ms // 1000) // 60
                seconds = (duration_ms // 1000) % 60
                duration_str = f"{minutes}:{seconds:02d}"
                
                # Ro'yxat matni
                response_text += f"{index + 1}. {artist} - {title}  {duration_str}\n"
                
                # Inline tugma (raqamlar)
                buttons.append(types.InlineKeyboardButton(text=str(index + 1), callback_data=f"music_{index}"))
            
            # Tugmalarni 5 tadan qilib joylashtiramiz (1-5 va 6-10)
            keyboard.add(*buttons[:5])
            if len(buttons) > 5:
                keyboard.add(*buttons[5:])
                
            # Pastki boshqaruv tugmalari (yopish X tugmasi)
            keyboard.add(types.InlineKeyboardButton(text="❌", callback_data="close_search"))
            
            # "Qidirilmoqda..." xabarini o'rniga ro'yxatni chiqaramiz
            bot.edit_message_text(
                text=response_text, 
                chat_id=chat_id, 
                message_id=status_msg.message_id, 
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            bot.edit_message_text("Hech narsa topilmadi. 😔", chat_id=chat_id, message_id=status_msg.message_id)
            
    except Exception as e:
        print(f"XATO: {e}")
        bot.edit_message_text("Xatolik yuz berdi, iltimos qayta urinib ko'ring.", chat_id=chat_id, message_id=status_msg.message_id)

# Tugmalar bosilganini eshituvchi qism (Callback Query Handler)
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    chat_id = call.message.chat.id
    
    if call.data == "close_search":
        bot.delete_message(chat_id=chat_id, message_id=call.message.message_id)
        return
        
    if call.data.startswith("music_"):
        index = int(call.data.split("_")[1])
        
        # Keshda ushbu foydalanuvchining qidiruvi borligini tekshiramiz
        if chat_id in user_searches and index < len(user_searches[chat_id]):
            track = user_searches[chat_id][index]
            audio_url = track.get('previewUrl')
            title = track.get('trackName', 'Musiqa')
            artist = track.get('artistName', 'Ijrochi')
            
            if audio_url:
                # Tepada "Yuklanmoqda..." deb bildirishnoma chiqaradi
                bot.answer_callback_query(call.id, text="Musiqa yuborilmoqda... 📤")
                
                # Qo'shiqni yuborish
                bot.send_audio(
                    chat_id=chat_id,
                    audio=audio_url,
                    title=title,
                    performer=artist
                )
            else:
                bot.answer_callback_query(call.id, text="Kechirasiz, audio fayl topilmadi.", show_alert=True)
        else:
            bot.answer_callback_query(call.id, text="Qidiruv muddati eskirgan, iltimos qayta qidiring.", show_alert=True)

if __name__ == '__main__':
    threading.Thread(target=run_web_server, daemon=True).start()
    bot.infinity_polling()
