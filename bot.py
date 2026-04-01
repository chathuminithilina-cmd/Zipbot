import os
import zipfile
import asyncio
import shutil
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile

API_TOKEN = os.getenv("BOT_TOKEN")
TEMP_DIR = "user_files"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
user_data = {}

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("✅ **Ready!**\nSend me photos or files, then type /zip.")

# This handler now captures BOTH Documents AND Photos
@dp.message(F.document | F.photo)
async def handle_files(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in user_data:
        user_data[user_id] = []
    
    os.makedirs(os.path.join(TEMP_DIR, user_id), exist_ok=True)

    # Logic to handle if it's a photo or a document
    if message.photo:
        # Get the highest resolution version of the photo
        file_id = message.photo[-1].file_id
        file_name = f"photo_{file_id[:8]}.jpg"
    else:
        file_id = message.document.file_id
        file_name = message.document.file_name or f"file_{file_id[:8]}"

    file = await bot.get_file(file_id)
    destination = os.path.join(TEMP_DIR, user_id, file_name)
    
    await bot.download_file(file.file_path, destination)
    user_data[user_id].append(destination)
    
    await message.answer(f"📥 Added: `{file_name}`")

@dp.message(Command("zip"))
async def cmd_zip(message: types.Message):
    user_id = str(message.from_user.id)
    
    if user_id not in user_data or not user_data[user_id]:
        return await message.answer("❌ Send some files first!")

    status_msg = await message.answer("📦 Creating zip...")
    zip_name = f"archive_{user_id}.zip"
    
    try:
        with zipfile.ZipFile(zip_name, 'w') as zipf:
            for file in user_data[user_id]:
                if os.path.exists(file):
                    zipf.write(file, os.path.basename(file))

        await message.reply_document(FSInputFile(zip_name))
        
    except Exception as e:
        await message.answer(f"⚠️ Error: {e}")
    
    finally:
        if os.path.exists(zip_name): os.remove(zip_name)
        shutil.rmtree(os.path.join(TEMP_DIR, user_id), ignore_errors=True)
        user_data[user_id] = []
        await status_msg.delete()

async def main():
    os.makedirs(TEMP_DIR, exist_ok=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
