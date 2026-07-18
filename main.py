import os
import logging
from flask import Flask
from threading import Thread
import telebot
import yt_dlp

# 1. Loglarni sozlash (Xatoliklarni Render panelida ko'rish uchun)
logging.basicConfig(level=logging.INFO)

# 2. Flask veb-server qismi (Render pingeri va cron-job.org uchun)
app = Flask('')

@app.route('/')
def home():
    return "Musiqa bot muvaffaqiyatli ishlayapti!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True  # Asosiy dastur to'xtasa, server ham to'xtashi uchun
    t.start()

# 3. Botni va Tokenni sozlash
# Tokenni Render'dagi Environment Variables'ga qo'shish tavsiya etiladi
BOT_TOKEN = os.getenv('API_TOKEN', 'SIZNING_BOT_TOKENINGIZ')
bot = telebot.TeleBot(BOT_TOKEN)

# 4. CHALA YUKLASH MUAMMOSINI TUZATUVCHI SOZLAMALAR
YDL_OPTS = {
    'format': 'bestaudio/best',
    'keepvideo': False,
    'quiet': True,
    'no_warnings': True,
    'external_downloader': 'native',  # Yuklash uzilib qolmasligi uchun universal drayver
    'nocheckcertificate': True,
    'source_address': '0.0.0.0',
    'http_chunk_size': 1048576,       # Audioni 1MB lik bo'laklar bilan uzluksiz, xavfsiz tortish
    'retries': 15,                    # Internet o'ynab ketsa, 15 martagacha qayta ulanish
    'fragment_retries': 15,           # Audio qismlarini oxirigacha tiklash
    'outtmpl': 'downloads/%(title)s.%(ext)s', # Yuklanadigan fayl nomi va joyi
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',    # Sifatli 192 kbps MP3 formatga o'tkazish
    }],
}

# 5. Bot buyruqlari va ish mantig'i
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(
        message, 
        "👋 Salom! Men musiqa yuklovchi botman.\n\n"
        "Menga YouTube'dan klip yoki musiqa havolasini (link) yuboring, "
        "men uni sizga to'liq MP3 formatida yuklab beraman! 🎧"
    )

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()
    
    # Havolani tekshirish
    if "youtube.com" in url or "youtu.be" in url:
        msg = bot.reply_to(message, "📥 Musiqa tahlil qilinmoqda va yuklanmoqda, iltimos kuting...")
        
        # downloads papkasi bo'lmasa yaratish
        if not os.path.exists('downloads'):
            os.makedirs('downloads')
            
        try:
            with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
                # Video ma'lumotlarini olish va yuklash
                info = ydl.extract_info(url, download=True)
                # yt-dlp mp3 ga o'girgandan keyin fayl nomini aniqlash
                filename = ydl.prepare_filename(info)
                mp3_filename = os.path.splitext(filename)[0] + '.mp3'
                
            if os.path.exists(mp3_filename):
                bot.edit_message_text("🚀 Musiqa tayyor! Telegram'ga yuklanmoqda...", chat_id=message.chat.id, message_id=msg.message_id)
                
                # Audio faylni foydalanuvchiga yuborish
                with open(mp3_filename, 'rb') as audio:
                    bot.send_audio(message.chat.id, audio, caption="🎧 @Musiqa_Ch_bot orqali yuklab olindi")
                
                # Server to'lib qolmasligi uchun faylni o'chirish
                os.remove(mp3_filename)
                bot.delete_message(chat_id=message.chat.id, message_id=msg.message_id)
            else:
                bot.edit_message_text("❌ Audio faylni konvertatsiya qilishda xatolik yuz berdi.", chat_id=message.chat.id, message_id=msg.message_id)
                
        except Exception as e:
            logging.error(f"Yuklashda xato: {e}")
            bot.edit_message_text("❌ Kechirasiz, musiqani yuklab bo'lmadi. Tarmoq uzildi yoki havola xato.", chat_id=message.chat.id, message_id=msg.message_id)
    else:
        bot.reply_to(message, "⚠️ Iltimos, faqat to'g'ri YouTube havola (link) yuboring.")

# 6. Dasturni ishga tushirish qismi
if __name__ == '__main__':
    # Avval Render uyg'oq turishi uchun veb-serverni yoqamiz
    keep_alive()
    logging.info("Flask server muvaffaqiyatli yuklandi.")
    
    # Keyin botning o'zini uzluksiz ishga tushiramiz
    logging.info("Bot polling rejimida ishga tushmoqda...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
