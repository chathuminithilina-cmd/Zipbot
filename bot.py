import os
import zipfile
import asyncio
import shutil
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.client.default import DefaultBotProperties

# Get token from Railway Environment Variables
API_TOKEN = os.getenv("BOT_TOKEN")
TEMP_DIR = "user_files"

# Added a longer request_timeout for large video uploads
bot = Bot(
    token=API_TOKEN, 
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()

user_data = {}

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🎬 **Zip Maker Pro**\n\n"
        "I now accept:\n"
        "• 📄 Documents/Files\n"
        "• 🖼️ Photos\n"
        "• 📹 Videos\n\n"
        "Send your items, then type /zip"
    )

# Updated filter to include F.video
@dp.message(F.document | F.photo | F.video | F.video_note)
async def handle_files(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in user_data:
        user_data[user_id] = []
    
    os.makedirs(os.path.join(TEMP_DIR, user_id), exist_ok=True)

    # Determine file type and get ID/Name
    if message.document:
        file_id = message.document.file_id
        file_name = message.document.file_name or f"file_{file_id[:6]}"
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_name = f"photo_{file_id[:6]}.jpg"
    elif message.video:
        file_id = message.video.file_id
        file_name = message.video.file_name or f"video_{file_id[:6]}.mp4"
    elif message.video_note:
        file_id = message.video_note.file_id
        file_name = f"round_video_{file_id[:6]}.mp4"

    status = await message.answer(f"⏳ Downloading `{file_name}`...")
    
    try:
        file = await bot.get_file(file_id)
        destination = os.path.join(TEMP_DIR, user_id, file_name)
        await bot.download_file(file.file_path, destination)
        user_data[user_id].append(destination)
        await status.edit_text(f"✅ Added: `{file_name}`")
    except Exception as e:
        await status.edit_text(f"❌ Failed to download: {e}")

@dp.message(Command("zip"))
async def cmd_zip(message: types.Message):
    user_id = str(message.from_user.id)
    
    if user_id not in user_data or not user_data[user_id]:
        return await message.answer("❌ No files found to zip!")

    progress = await message.answer("📦 Compression in progress...")
    zip_name = f"archive_{user_id}.zip"
    
    try:
        with zipfile.ZipFile(zip_name, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
            for file in user_data[user_id]:
                if os.path.exists(file):
                    zipf.write(file, os.path.basename(file))

        await message.reply_document(
            FSInputFile(zip_name), 
            caption="Here is your zipped bundle! 📁"
        )
        
    except Exception as e:
        await message.answer(f"⚠️ Error during zipping: {e}")
    
    finally:
        # Cleanup
        if os.path.exists(zip_name):
            os.remove(zip_name)
        shutil.rmtree(os.path.join(TEMP_DIR, user_id), ignore_errors=True)
        user_data[user_id] = []
        await progress.delete()

async def main():
    os.makedirs(TEMP_DIR, exist_ok=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
