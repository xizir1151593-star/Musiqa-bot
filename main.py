import logging
import os
import asyncio
import re
from aiogram import Bot, Dispatcher, types, executor
import yt_dlp
import speech_recognition as sr
from pydub import AudioSegment
from aiohttp import web, ClientSession

# --- SOZLAMALAR ---
API_TOKEN = os.getenv('API_TOKEN', 'SIZNING_BOT_TOKENINGIZ')
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

# --- YOUTUBE QIDIRUVNI TUZATISH (YANGI USUL) ---
async def search_song(query):
    """
    YouTube qidiruv tizimidan videoni aniq va bloklarsiz topish usuli.
    Xonanda nomi yoki qo'shiq matnidan parcha bo'lsa ham eng birinchi natijani oladi.
    """
    try:
        # Qidiruv matnini URL formatiga o'tkazish
        encoded_query = query.replace(" ", "+")
        url = f"https://www.youtube.com/results?search_query={encoded_query}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        async with ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                html = await response.text()
                # Video ID-larini HTML ichidan qidirib topish
                video_ids = re.findall(r"watch\?v=(\S{11})", html)
                if video_ids:
                    return f"https://www.youtube.com/watch?v={video_ids[0]}"
    except Exception as e:
        logging.error(f"YouTube qidiruvida xato: {e}")
    
    # Agar birinchi usul o'xshamasa, zaxira (yt-dlp) usuli:
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': True,
            'extract_flat': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            if 'entries' in info and info['entries']:
                return info['entries'][0]['url']
    except Exception as e:
        logging.error(f"Zaxira qidiruvda xato: {e}")
        
    return None

# --- OVOZLI XABARNI MATNGA O'GIRISH ---
async def voice_to_text(voice_file_path):
    try:
        audio = AudioSegment.from_ogg(voice_file_path)
        wav_path = "voice.wav"
        audio.export(wav_path, format="wav")

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="uz-UZ")
            return text
    except Exception as e:
        logging.error(f"Ovozni matnga o'girishda xatolik: {e}")
        return None

# --- BOT HANDLERLARI ---
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.answer("Salom! Menga qo'shiq nomi, xonanda ismi yoki qo'shiqdan parcha yuboring. Ovozli xabar yuborsangiz ham topaman! 🎧")

@dp.message_handler(content_types=['voice'])
async def handle_voice(message: types.Message):
    msg = await message.answer("🎧 Ovozli xabarni eshitib, matnga o'giryapman...")
    
    file_info = await bot.get_file(message.voice.file_id)
    await bot.download_file(file_info.file_path, "voice.ogg")
    
    text = await voice_to_text("voice.ogg")
    
    if text:
        await msg.edit_text(f"🔍 Siz aytdingiz: *{text}*\nQidiryapman...")
        song_url = await search_song(text)
        if song_url:
            await msg.edit_text(f"✅ Marhamat, topildi:\n{song_url}")
        else:
            await msg.edit_text("Hech narsa topilmadi.")
    else:
        await msg.edit_text("Ovozni aniqlab bo'lmadi, iltimos, aniqroq gapiring.")

@dp.message_handler(content_types=['text'])
async def handle_text(message: types.Message):
    # Rasmda ko'ringan "Hech narsa topilmadi" xabarini yo'qotish va qidirish
    msg = await message.answer("🔍 Qidiryapman...")
    song_url = await search_song(message.text)
    
    if song_url:
        await msg.edit_text(f"✅ Marhamat, topildi:\n{song_url}")
    else:
        await msg.edit_text("Hech narsa topilmadi.")

# --- RENDER KEEP-ALIVE SERVER ---
async def handle(request):
    return web.Response(text="Bot muvaffaqiyatli ishlayapti!")

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
