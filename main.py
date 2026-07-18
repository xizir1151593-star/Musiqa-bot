import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests

# Bot tokeningiz
BOT_TOKEN = '8893365405:AAGrucdJBJhNfE-g6Q1qbmqtqYpB5nIYfIQ'
bot = telebot.TeleBot(BOT_TOKEN)

USER_SEARCHES = {}

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
    bot.reply_to(message, "👋 **Salom! Qidirmoqchi bo'lgan musiqa nomi yoki ijrochini yozing:**", parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def search_music(message):
    query = message.text
    chat_id = message.chat.id
    searching_msg = bot.reply_to(message, "🔍 Qidirilmoqda...")
    
    try:
        # Muqobil va barqaror ishlovchi musiqa API'si
        api_url = f"https://api.Deezer.com/search?q={query}&limit=30"
        response = requests.get(api_url).json()
        results = response.get('data', [])
        
        if not results:
            bot.edit_message_text(f"❌ '{query}' bo'yicha hech narsa topilmadi.", chat_id, searching_msg.message_id)
            return
            
        USER_SEARCHES[chat_id] = {"tracks": results, "query": query}
        send_page_results(chat_id, searching_msg.message_id, page=1)
        
    except Exception as e:
        print(f"Xato: {e}")
        bot.edit_message_text("⚠️ Tizimda xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring.", chat_id, searching_msg.message_id)

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
        duration_sec = track.get('duration', 0)
        duration_min = duration_sec // 60
        rem_sec = duration_sec % 60
        
        artist = track.get('artist', {}).get('name', 'Noma\'lum')
        title = track.get('title', 'Musiqa')
        
        full_title = f"{artist} - {title}"
        if len(full_title) > 45:
            full_title = full_title[:42] + "..."
            
        response_text += f"{idx + 1}. {full_title} ({duration_min}:{rem_sec:02d})\n"
        
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
            
            audio_url = track.get('preview')  # Qo'shiqning yuqori sifatli audio linki
            title = track.get('title', 'Musiqa')
            artist = track.get('artist', {}).get('name', 'Noma\'lum')
            
            try:
                bot.send_audio(
                    chat_id=chat_id, 
                    audio=audio_url, 
                    title=title, 
                    performer=artist, 
                    caption=f"🎧 **{artist} - {title}**\n\n@Musiqa_chi_bot"
                )
            except Exception as e:
                bot.send_message(chat_id, "❌ Bu audioni yuborishda muammo bo'ldi. Boshqasini tanlab ko'ring.")

if __name__ == '__main__':
    bot.infinity_polling()
