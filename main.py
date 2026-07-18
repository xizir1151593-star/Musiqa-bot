import logging
import os
import asyncio
from aiogram import Bot, Dispatcher, types, executor
from aiogram.dispatcher.filters import Text
import yt_dlp
import speech_recognition as sr
from pydub import AudioSegment
from aiohttp import web

# --- SOZLAMALAR ---
# Tokenni Render'dagi Environment Variable qismiga joylang yoki shu yerga yozing
API_TOKEN = os.getenv('API_TOKEN', 'SIZNING_TOKENINGIZNI_SHU_YERGA_YOZING')

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

# --- FFMPEG KONFIGURATSIYASI ---
# Render'da ffmpeg avtomatik o'rnatiladi, agar xato bersa, quyidagi qatorni oching:
# AudioSegment.converter = "/usr/bin/ffmpeg"

# --- QIDIRUV FUNKSIYASI ---
def search_song(query):
    """YouTube'dan eng mos videoni topadi"""
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        'default_search': 'ytsearch1',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # ytsearch1 prefiksi orqali qisman yozilgan matnni ham topadi
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            if 'entries' in info and info['entries']:
                return info['entries'][0]['webpage_url']
        except Exception as e:
            logging.error(f"Qidiruvda xatolik: {e}")
    return None

# --- OVOZNI MATNGA O'GIRISH ---
async def voice_to_text(voice_file_path):
    try:
        audio = AudioSegment.from_ogg(voice_file_path)
        wav_path = "voice.wav"
        audio.export(wav_path, format="wav")

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            # O'zbek tili uchun 'uz-UZ'
            text = recognizer.recognize_google(audio_data, language="uz-UZ")
            return text
    except Exception as e:
        logging.error(f"Ovozni matnga o'girishda xatolik: {e}")
        return None

# --- BOT BUYRUQLARI ---
@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.answer("Salom! Menga qo'shiq nomi yoki xonanda nomini yuboring. Ovozli xabar qilib yuborsangiz ham tushunaman.")

@dp.message_handler(content_types=['voice'])
async def handle_voice(message: types.Message):
    await message.answer("🎧 Ovozli xabarni eshitib, matnga o'giryapman...")
    
    file_info = await bot.get_file(message.voice.file_id)
    await bot.download_file(file_info.file_path, "voice.ogg")
    
    text = await voice_to_text("voice.ogg")
    
    if text:
        await message.answer(f"🔍 Siz aytdingiz: *{text}*. Qidiryapman...")
        song_url = search_song(text)
        if song_url:
            await message.answer(f"✅ Topdim: {song_url}")
        else:
            await message.answer("❌ Uzr, bu qo'shiqni topa olmadim.")
    else:
        await message.answer("⚠️ Ovozni tushuna olmadim, iltimos, aniqroq gapiring.")

@dp.message_handler(content_types=['text'])
async def handle_text(message: types.Message):
    await message.answer("🔍 Qidiryapman...")
    song_url = search_song(message.text)
    if song_url:
        await message.answer(f"✅ Marhamat: {song_url}")
    else:
        await message.answer("❌ Topilmadi. Iltimos, xonanda nomi va qo'shiq nomini aniqroq yozing.")

# --- KEEP-ALIVE SERVER (RENDER UCHUN) ---
async def handle(request):
    return web.Response(text="Bot ishlayapti!")

async def start_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(start_server())
    executor.start_polling(dp, skip_updates=True)
