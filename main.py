import os
import telebot
from telebot import types
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

BOT_TOKEN = '8893365405:AAGrucdJBJhNfE-g6Q1qbmqtqYpB5nIYfIQ'
bot = telebot.TeleBot(BOT_TOKEN)

# Foydalanuvchilarning qidiruv natijalari va joriy sahifalarini saqlash uchun kesh
user_data = {}

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

def generate_page_keyboard(chat_id):
    """Joriy sahifaga mos tugmalarni (1-10) va pastki navigatsiyani chiqaradi"""
    data = user_data.get(chat_id, {})
    results = data.get('results', [])
    page = data.get('page', 0)
    
    start_idx = page * 10
    end_idx = start_idx + 10
    page_results = results[start_idx:end_idx]
    
    keyboard = types.InlineKeyboardMarkup()
    
    row1 = []
    row2 = []
    
    # 1 dan 10 gacha raqamli tugmalar
    for i in range(len(page_results)):
        display_num = i + 1
        global_index = start_idx + i
        btn = types.InlineKeyboardButton(text=str(display_num), callback_data=f"dzmp3_{global_index}")
        
        if i < 5:
            row1.append(btn)
        else:
            row2.append(btn)
            
    if row1:
        keyboard.row(*row1)
    if row2:
        keyboard.row(*row2)
        
    # Navigatsiya tugmalari (❌ o'rniga Keyingi va Orqaga)
    total_pages = (len(results) + 9) // 10
    current_page_display = page + 1
    
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton(text="⬅️ Orqaga", callback_data="prev_page"))
        
    nav_buttons.append(types.InlineKeyboardButton(text=f"📄 {current_page_display}/{total_pages}", callback_data="page_info"))
    
    if end_idx < len(results):
        nav_buttons.append(types.InlineKeyboardButton(text="Keyingi ➡️", callback_data="next_page"))
        
    keyboard.row(*nav_buttons)
    
    # Qidiruv oynasini butunlay yopish tugmasi eng pastda turadi
    keyboard.row(types.InlineKeyboardButton(text="❌ Yopish", callback_data="close_search"))
    
    return keyboard

def get_page_text(query, chat_id):
    """Joriy sahifadagi 10 ta qo'shiq matnini tayyorlaydi"""
    data = user_data.get(chat_id, {})
    results = data.get('results', [])
    page = data.get('page', 0)
    
    start_idx = page * 10
    end_idx = start_idx + 10
    page_results = results[start_idx:end_idx]
    
    response_text = f"🔍 **{query} (MP3)**\n\n"
    
    for i, track in enumerate(page_results):
        title = track.get('title', 'Musiqa')
        artist_info = track.get('artist', {})
        artist = artist_info.get('name', 'Ijrochi')
        
        duration_sec = track.get('duration', 0)
        minutes = duration_sec // 60
        seconds = duration_sec % 60
        duration_str = f"{minutes}:{seconds:02d}"
        
        if len(title) > 35:
            title = title[:32] + "..."
            
        # Ekrandagi tartib raqami har doim 1 dan 10 gacha chiqadi
        response_text += f"{i + 1}. {artist} - {title}  {duration_str}\n"
        
    return response_text

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Salom! Menga biror qo'shiq nomi yoki ijrochini yozing, men sizga uning barcha qo'shiqlarini toza MP3 formatida topib beraman. 🎵")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    query = message.text
    chat_id = message.chat.id
    status_msg = bot.reply_to(message, "Musiqa bazasidan barcha taronalar qidirilmoqda... 🔎")
    
    try:
        # Maksimal ko'p qo'shiq chiqishi uchun limitni 100 qildik
        url = f"https://api.deezer.com/search?q={requests.utils.quote(query)}&limit=100"
        response = requests.get(url, timeout=10).json()
        
        if response.get('data') and len(response['data']) > 0:
            # Foydalanuvchi ma'lumotlarini keshga yozamiz
            user_data[chat_id] = {
                'query': query,
                'results': response['data'],
                'page': 0
            }
            
            response_text = get_page_text(query, chat_id)
            keyboard = generate_page_keyboard(chat_id)
            
            bot.edit_message_text(
                text=response_text, 
                chat_id=chat_id, 
                message_id=status_msg.message_id, 
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            bot.edit_message_text("Hech narsa topilmadi. Iltimos, boshqa nom yozib ko'ring. 🔍", chat_id=chat_id, message_id=status_msg.message_id)
            
    except Exception as e:
        print(f"XATO: {e}")
        bot.edit_message_text("Kechirasiz, musiqani topishda xatolik yuz berdi. Qayta urinib ko'ring. 😔", chat_id=chat_id, message_id=status_msg.message_id)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    chat_id = call.message.chat.id
    
    if call.data == "close_search":
        bot.delete_message(chat_id=chat_id, message_id=call.message.message_id)
        return
        
    if call.data == "page_info":
        bot.answer_callback_query(call.id)
        return
        
    # Keyingi sahifaga o'tish logikasi
    if call.data == "next_page":
        if chat_id in user_data:
            user_data[chat_id]['page'] += 1
            query = user_data[chat_id]['query']
            
            bot.edit_message_text(
                text=get_page_text(query, chat_id),
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=generate_page_keyboard(chat_id),
                parse_mode="Markdown"
            )
        bot.answer_callback_query(call.id)
        return

    # Orqaga qaytish logikasi
    if call.data == "prev_page":
        if chat_id in user_data and user_data[chat_id]['page'] > 0:
            user_data[chat_id]['page'] -= 1
            query = user_data[chat_id]['query']
            
            bot.edit_message_text(
                text=get_page_text(query, chat_id),
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=generate_page_keyboard(chat_id),
                parse_mode="Markdown"
            )
        bot.answer_callback_query(call.id)
        return
        
    # Qo'shiq yuklash qismi
    if call.data.startswith("dzmp3_"):
        index = int(call.data.split("_")[1])
        
        if chat_id in user_data and index < len(user_data[chat_id]['results']):
            track = user_data[chat_id]['results'][index]
            audio_url = track.get('preview')
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
