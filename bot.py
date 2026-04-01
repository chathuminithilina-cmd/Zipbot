import os
import zipfile
import asyncio
import shutil
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile

# Get token from Railway Environment Variables
API_TOKEN = os.getenv("BOT_TOKEN")
TEMP_DIR = "user_files"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Dictionary to keep track of files per user
user_data = {}

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 **Welcome to Zip Maker!**\n\n"
        "1. Send me any files/documents.\n"
        "2. Type /zip when you are finished.\n"
        "3. I'll send you the archive and clean up!"
    )

@dp.message(F.document)
async def handle_docs(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in user_data:
        user_data[user_id] = []
    
    # Create a unique folder for the user
    path = os.path.join(TEMP_DIR, user_id)
    os.makedirs(path, exist_ok=True)
    
    file_id = message.document.file_id
    file = await bot.get_file(file_id)
    file_name = message.document.file_name or f"file_{file_id[:5]}"
    destination = os.path.join(path, file_name)
    
    await bot.download_file(file.file_path, destination)
    user_data[user_id].append(destination)
    
    await message.answer(f"✅ Added: `{file_name}`")

@dp.message(Command("zip"))
async def cmd_zip(message: types.Message):
    user_id = str(message.from_user.id)
    
    if user_id not in user_data or not user_data[user_id]:
        return await message.answer("❌ You haven't sent any files yet!")

    status_msg = await message.answer("📦 Zipping your files... please wait.")
    zip_name = f"archive_{user_id}.zip"
    
    try:
        # Create the zip file
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in user_data[user_id]:
                if os.path.exists(file):
                    zipf.write(file, os.path.basename(file))

        # Send the file
        await message.reply_document(FSInputFile(zip_name))
        
    except Exception as e:
        await message.answer(f"⚠️ An error occurred: {e}")
    
    finally:
        # Cleanup: Delete the zip and the user's folder
        if os.path.exists(zip_name):
            os.remove(zip_name)
        
        user_folder = os.path.join(TEMP_DIR, user_id)
        if os.path.exists(user_folder):
            shutil.rmtree(user_folder)
            
        user_data[user_id] = []
        await status_msg.delete()

async def main():
    # Ensure temp directory exists on startup
    os.makedirs(TEMP_DIR, exist_ok=True)
    print("Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
