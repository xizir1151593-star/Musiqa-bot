import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests

# Siz yuborgan bot tokeni
BOT_TOKEN = '8893365405:AAGrucdJBJhNfE-g6Q1qbmqtqYpB5nIYfIQ'
bot = telebot.TeleBot(BOT_TOKEN)

USER_SEARCHES = {}
JAMENDO_CLIENT_ID = '55d040ad'

def generate_keyboard(tracks, page, total_pages):
    markup = InlineKeyboardMarkup(row_width=5)
    row1, row2 = [], []
    for i in range(len(tracks)):
        btn = InlineKeyboardButton(str(i + 1), callback_data=f"track_{i}")
        if i < 5: row1.append(btn)
        else: row2.append(btn)
            
    if row1: markup.row(*row1)
    if row2: markup.row(*row2)
    
    page_btn = InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="none")
    if page < total_pages:
        next_btn = InlineKeyboardButton("Keyingi ➡️", callback_data=f"page_{page + 1}")
        markup.row(page_btn, next_btn)
    else:
        markup.row(page_btn)
        
    close_btn = InlineKeyboardButton("❌ Yopish", callback_data="close_menu")
    markup.row(close_btn)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 **Salom! Musiqa nomini yoki ijrochini yozing:**", parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def search_music(message):
    query = message.text
    chat_id = message.chat.id
    searching_msg = bot.reply_to(message, "🔍 Qidirilmoqda...")
    
    try:
        api_url = f"https://api.jamendo.com/v3.0/tracks/?client_id={JAMENDO_CLIENT_ID}&format=json&limit=50&search={query}"
        response = requests.get(api_url).json()
        results = response.get('results', [])
        
        if not results:
            bot.edit_message_text("❌ Hech narsa topilmadi.", chat_id, searching_msg.message_id)
            return
            
        USER_SEARCHES[chat_id] = {"tracks": results, "query": query}
        send_page_results(chat_id, searching_msg.message_id, page=1)
        
    except Exception as e:
        bot.edit_message_text("⚠️ Xatolik yuz berdi.", chat_id, searching_msg.message_id)

def send_page_results(chat_id, message_id, page):
    search_data = USER_SEARCHES.get(chat_id)
    if not search_data: return
        
    all_tracks = search_data["tracks"]
    per_page = 10
    total_pages = (len(all_tracks) + per_page - 1) // per_page
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    current_tracks = all_tracks[start_idx:end_idx]
    
    response_text = ""
    for idx, track in enumerate(current_tracks):
        duration_min = int(track['duration']) // 60
        duration_sec = int(track['duration']) % 60
        response_text += f"{idx + 1}. {track['artist_name']} - {track['name']} ({duration_min}:{duration_sec:02d})\n"
        
    markup = generate_keyboard(current_tracks, page, total_pages)
    search_data["current_page"] = page
    
    bot.edit_message_text(text=response_text, chat_id=chat_id, message_id=message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    data = call.data
    
    if data == "close_menu":
        bot.delete_message(chat_id, call.message.message_id)
        return
    if data.startswith("page_"):
        next_page = int(data.split("_")[1])
        send_page_results(chat_id, call.message.message_id, page=next_page)
        return
    if data.startswith("track_"):
        track_index_on_page = int(data.split("_")[1])
        search_data = USER_SEARCHES.get(chat_id)
        if search_data:
            current_page = search_data["current_page"]
            actual_index = ((current_page - 1) * 10) + track_index_on_page
            track = search_data["tracks"][actual_index]
            bot.answer_callback_query(call.id, text="🎵 Audio yuborilmoqda...")
            bot.send_audio(chat_id=chat_id, audio=track['audio'], title=track['name'], performer=track['artist_name'], caption=f"🎧 **{track['artist_name']} - {track['name']}**\n\n@Musiqa_chi_bot")

if __name__ == '__main__':
    print("Bot muvaffaqiyatli yoqildi...")
    bot.infinity_polling()
