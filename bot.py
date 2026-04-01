import os
import zipfile
import shutil
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

# Config from Railway Environment Variables
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DOWNLOAD_DIR = "./downloads"

app = Client(
    "zip_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Store file paths per user
user_storage = {}

@app.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    await message.reply(
        "🚀 **Large File Zip Maker (No 20MB Limit)**\n\n"
        "1. Send me any Photos, Videos, or Files.\n"
        "2. Type /zip to finish.\n"
        "3. Type /clear to reset your list."
    )

@app.on_message(filters.document | filters.video | filters.photo | filters.video_note)
async def collect_files(client, message: Message):
    user_id = message.from_user.id
    if user_id not in user_storage:
        user_storage[user_id] = []

    status = await message.reply("📥 *Downloading to cloud...*", quote=True)
    
    try:
        # Pyrogram's download_media has no 20MB limit
        file_path = await message.download(file_name=f"{DOWNLOAD_DIR}/{user_id}/")
        
        if file_path:
            user_storage[user_id].append(file_path)
            await status.edit(f"✅ Added: `{os.path.basename(file_path)}`")
        else:
            await status.edit("❌ Download failed.")
            
    except Exception as e:
        await status.edit(f"⚠️ Error: {str(e)}")

@app.on_message(filters.command("zip"))
async def zip_cmd(client, message: Message):
    user_id = message.from_user.id
    files = user_storage.get(user_id, [])

    if not files:
        return await message.reply("❌ No files in your list!")

    progress = await message.reply("📦 *Zipping... this may take a moment for large files.*")
    zip_path = f"archive_{user_id}.zip"

    try:
        with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for f in files:
                if os.path.exists(f):
                    z.write(f, os.path.basename(f))
        
        await message.reply_document(
            document=zip_path,
            caption=f"📂 Packed {len(files)} files into one archive!"
        )
    except Exception as e:
        await message.reply(f"❌ Zipping error: {e}")
    finally:
        # Clean up
        if os.path.exists(zip_path):
            os.remove(zip_path)
        shutil.rmtree(f"{DOWNLOAD_DIR}/{user_id}", ignore_errors=True)
        user_storage[user_id] = []
        await progress.delete()

@app.on_message(filters.command("clear"))
async def clear_cmd(client, message: Message):
    user_id = message.from_user.id
    shutil.rmtree(f"{DOWNLOAD_DIR}/{user_id}", ignore_errors=True)
    user_storage[user_id] = []
    await message.reply("🗑️ Your file list has been cleared.")

if __name__ == "__main__":
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    print("Bot is running with Pyrogram...")
    app.run()
