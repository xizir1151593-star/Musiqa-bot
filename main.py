import os
import logging
from flask import Flask
from threading import Thread
import telebot
import yt_dlp

# 1. Loglarni sozlash (Xatoliklarni Render panelida kuzatish uchun)
logging.basicConfig(level=logging.INFO)

# 2. Flask veb-server qismi (Render pingeri va cron-job.org uchun)
app = Flask('')

@app.route('/')
def home():
    return "Musiqa va Kino boti muvaffaqiyatli ishlayapti!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# 3. Bot va Kanal Sozlamalari
BOT_TOKEN = os.getenv('API_TOKEN', 'SIZNING_BOT_TOKENINGIZ')
# Kino kanalingiz ID raqami (-100 bilan boshlanishi shart!)
CHANNEL_ID = int(os.getenv('CHANNEL_ID', '-100XXXXXXXXXX')) 

bot = telebot.TeleBot(BOT_TOKEN)

# 4. CHALA YUKLASHNI TUZATUVCHI MULTIMEDIA SOZLAMALARI (FFmpeg talab qilmaydi)
YDL_OPTS = {
    'format': 'bestaudio/best',
    'keepvideo': False,
    'quiet': True,
    'no_warnings': True,
    'external_downloader': 'native',  # Yuklash uzilib qolmasligi uchun
    'nocheckcertificate': True,
    'source_address': '0.0.0.0',
    'http_chunk_size': 1048576,       # Audioni 1MB lik bo'laklar bilan uzluksiz tortish
    'retries': 15,                    # Tarmoq o'ynab ketsa, 15 martagacha qayta ulanish
    'fragment_retries': 15,
    'outtmpl': 'downloads/%(title)s.%(ext)s',
}

# 5. /start Buyrug'i
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(
        message, 
        "👋 Salom! Men universal Musiqa yuklovchi va Kino qidiruvchi botman.\n\n"
        "🎵 **Musiqa yuklash uchun:** YouTube havola (link) yuboring.\n"
        "🎬 **Kino topish uchun:** Kanaldagi kino kodini (raqamini) yozing."
    )

# 6. Xabarlarni Qayta Ishlash (Musiqa yuklash va Kino qidirish bitta joyda)
@bot.message_handler(func=lambda message: True)
def handle_universal(message):
    text = message.text.strip()
    
    # ---- 1-HOLAT: Agar foydalanuvchi YouTube Link yuborsa (Musiqa Yuklash) ----
    if "youtube.com" in text or "youtu.be" in text:
        msg = bot.reply_to(message, "📥 Musiqa tahlil qilinmoqda va to'liq yuklanmoqda, kuting...")
        
        if not os.path.exists('downloads'):
            os.makedirs('downloads')
            
        try:
            with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
                info = ydl.extract_info(text, download=True)
                filename = ydl.prepare_filename(info)
                
            if os.path.exists(filename):
                bot.edit_message_text("🚀 Musiqa tayyor! Telegram'ga yuklanmoqda...", chat_id=message.chat.id, message_id=msg.message_id)
                
                with open(filename, 'rb') as audio:
                    bot.send_audio(message.chat.id, audio, caption="🎧 @Musiqa_Ch_bot orqali yuklab olindi")
                
                os.remove(filename)  # Server diski to'lib qolmasligi uchun faylni o'chiramiz
                bot.delete_message(chat_id=message.chat.id, message_id=msg.message_id)
            else:
                bot.edit_message_text("❌ Audio faylni yuklashda uzilish bo'ldi.", chat_id=message.chat.id, message_id=msg.message_id)
                
        except Exception as e:
            logging.error(f"Musiqa yuklashda xato: {e}")
            bot.edit_message_text("❌ Kechirasiz, musiqani to'liq yuklab bo'lmadi. Havola xato yoki tarmoq band.", chat_id=message.chat.id, message_id=msg.message_id)

    # ---- 2-HOLAT: Agar foydalanuvchi faqat Raqam (Kod) yuborsa (Kino Qidirish) ----
    elif text.isdigit():
        msg = bot.reply_to(message, "🔍 Kino bazadan qidirilmoqda...")
        movie_msg_id = int(text)
        
        try:
            # Kanaldagi tayyor reklamasiz kinoni foydalanuvchiga nusxalab beradi
            bot.copy_message(
                chat_id=message.chat.id,
                from_chat_id=CHANNEL_ID,
                message_id=movie_msg_id,
                caption=f"🎬 Marhamat, siz so'ragan kino/klip!\n\n🤖 Bizning bot: @Musiqa_Ch_bot"
            )
            bot.delete_message(chat_id=message.chat.id, message_id=msg.message_id)
            
        except Exception as e:
            logging.error(f"Kino yuborishda xato: {e}")
            bot.edit_message_text(
                "❌ Kino topilmadi yoki xatolik yuz berdi.\n\n"
                "**Tekshiring:**\n"
                "1. Bot kanalingizda ADMIN qilinganmi?\n"
                "2. Kanalingizda rostdan ham shunday ID raqamli xabar bormi?", 
                chat_id=message.chat.id, message_id=msg.message_id
            )
            
    # ---- 3-HOLAT: Noto'g'ri buyruq yuborilganda ----
    else:
        bot.reply_to(
            message, 
            "⚠️ Noto'g'ri buyruq!\n\n"
            "Musiqa yuklash uchun **YouTube link** yuboring.\n"
            "Kino olish uchun esa kanaldagi **kino kodini (raqamini)** yozing."
        )

# 7. Botni uzluksiz yurgizish
if __name__ == '__main__':
    keep_alive()  # Render uyg'oq turishi uchun Flaskni yoqamiz
    logging.info("Server va Bot polling rejimida ishga tushdi...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
