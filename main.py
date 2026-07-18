import os
import re
import telebot
from telebot import types
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from yt_dlp import YoutubeDL

BOT_TOKEN = '8893365405:AAGrucdJBJhNfE-g6Q1qbmqtqYpB5nIYfIQ'
bot = telebot.TeleBot(BOT_TOKEN)

# URL aniqlash uchun regex
LINK_PATTERN = re.compile(r'(https?://(?:www\.)?(?:youtube\.com|youtu\.be|instagram\.com)/[^\s]+)')

# Foydalanuvchilarning kesh ma'lumotlari
user_data = {}

# ==========================================
# RENDER UCHUN UXLASHGA QO'YMAYDIGAN TIZIM
# ==========================================
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

# ==========================================
# DEEZER QIDIRUV FUNKSIYALARI
# ==========================================
def generate_page_keyboard(chat_id):
    data = user_data.get(chat_id, {})
    results = data.get('results', [])
    page = data.get('page', 0)
    start_idx = page * 10
    end_idx = start_idx + 10
    page_results = results[start_idx:end_idx]
    
    keyboard = types.InlineKeyboardMarkup()
    row1, row2 = [], []
    
    for i in range(len(page_results)):
        display_num = i + 1
        global_index = start_idx + i
        btn = types.InlineKeyboardButton(text=str(display_num), callback_data=f"dzmp3_{global_index}")
        if i < 5: row1.append(btn)
        else: row2.append(btn)
            
    if row1: keyboard.row(*row1)
    if row2: keyboard.row(*row2)
        
    total_pages = (len(results) + 9) // 10
    nav_buttons = []
    if page > 0: nav_buttons.append(types.InlineKeyboardButton(text="⬅️ Orqaga", callback_data="prev_page"))
    nav_buttons.append(types.InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="page_info"))
    if end_idx < len(results): nav_buttons.append(types.InlineKeyboardButton(text="Keyingi ➡️", callback_data="next_page"))
        
    keyboard.row(*nav_buttons)
    keyboard.row(types.InlineKeyboardButton(text="❌ Yopish", callback_data="close_search"))
    return keyboard

def get_page_text(query, chat_id):
    data = user_data.get(chat_id, {})
    results = data.get('results', [])
    page = data.get('page', 0)
    start_idx = page * 10
    end_idx = start_idx + 10
    page_results = results[start_idx:end_idx]
    
    text = f"🔍 **{query} (MP3)**\n\n"
    for i, track in enumerate(page_results):
        title = track.get('title', 'Musiqa')[:30]
        artist = track.get('artist', {}).get('name', 'Ijrochi')
        duration = divmod(track.get('duration', 0), 60)
        text += f"{i + 1}. {artist} - {title} ({duration[0]}:{duration[1]:02d})\n"
    return text

# ==========================================
# ASOSIY BOT LOGIKASI
# ==========================================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Salom! Menga musiqa nomini yozing yoki YouTube/Instagram havolasini yuboring! 🎵")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    chat_id = message.chat.id
    query = message.text
    
    # 1. YOUTUBE YOKI INSTAGRAM HAVOLASINI TEKSHIRISH
    if LINK_PATTERN.search(query):
        url = LINK_PATTERN.search(query).group(0)
        status_msg = bot.reply_to(message, "📥 Havola aniqlandi. Yuklanmoqda...")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'quiet': True
        }
        
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                audio_file = os.path.splitext(filename)[0] + '.mp3'
            
            with open(audio_file, 'rb') as audio:
                bot.send_audio(chat_id, audio, caption="✨ @Musiqa_Topuvchi_Bot")
            
            bot.delete_message(chat_id, status_msg.message_id)
            if os.path.exists(audio_file): os.remove(audio_file)
        except Exception as e:
            bot.edit_message_text(f"Xatolik: {e}", chat_id, status_msg.message_id)

    # 2. DEEZER QIDIRUV
    else:
        status_msg = bot.reply_to(message, "Musiqa qidirilmoqda... 🔎")
        try:
            url = f"https://api.deezer.com/search?q={requests.utils.quote(query)}&limit=100"
            data = requests.get(url, timeout=10).json().get('data', [])
            if data:
                user_data[chat_id] = {'query': query, 'results': data, 'page': 0}
                bot.edit_message_text(get_page_text(query, chat_id), chat_id, status_msg.message_id, reply_markup=generate_page_keyboard(chat_id), parse_mode="Markdown")
            else:
                bot.edit_message_text("Hech narsa topilmadi.", chat_id, status_msg.message_id)
        except:
            bot.edit_message_text("Xatolik yuz berdi.", chat_id, status_msg.message_id)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    chat_id = call.message.chat.id
    if call.data == "close_search": bot.delete_message(chat_id, call.message.message_id)
    elif call.data in ["next_page", "prev_page"]:
        user_data[chat_id]['page'] += (1 if call.data == "next_page" else -1)
        bot.edit_message_text(get_page_text(user_data[chat_id]['query'], chat_id), chat_id, call.message.message_id, reply_markup=generate_page_keyboard(chat_id), parse_mode="Markdown")
    elif call.data.startswith("dzmp3_"):
        idx = int(call.data.split("_")[1])
        track = user_data[chat_id]['results'][idx]
        bot.send_audio(chat_id, track['preview'], title=track['title'], performer=track['artist']['name'])

if __name__ == '__main__':
    threading.Thread(target=run_web_server, daemon=True).start()
    bot.infinity_polling()
