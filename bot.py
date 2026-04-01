import os
import zipfile
import shutil
import time
from pyrogram import Client, filters
from pyrogram.types import Message

# Config from Railway
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DOWNLOAD_DIR = "./downloads"

app = Client("zip_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_storage = {}

def get_readable_size(size_bytes):
    if size_bytes == 0: return "0B"
    size_name = ("B", "KB", "MB", "GB")
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

@app.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    await message.reply("✅ **Zip Bot Active**\nSend files to see a summary and estimated time!")

@app.on_message(filters.document | filters.video | filters.photo | filters.video_note)
async def collect_files(client, message: Message):
    user_id = message.from_user.id
    if user_id not in user_storage:
        user_storage[user_id] = []

    # Get file info
    if message.photo:
        file_obj = message.photo[-1]
        file_name = f"photo_{file_obj.file_id[:6]}.jpg"
    else:
        file_obj = message.document or message.video or message.video_note
        file_name = getattr(file_obj, 'file_name', f"file_{file_obj.file_id[:6]}")

    file_size = file_obj.file_size
    
    # Estimate time (Assuming ~2MB/s download speed from Telegram to Railway)
    # Formula: Size / Speed = Seconds
    est_seconds = max(1, int(file_size / (2 * 1024 * 1024))) 
    
    summary_text = (
        f"📂 **File Summary**\n"
        f"━━━━━━━━━━━━━━\n"
        f"📝 **Name:** `{file_name}`\n"
        f"⚖️ **Size:** `{get_readable_size(file_size)}`\n"
        f"⏱️ **Est. Time:** `~{est_seconds}s`\n"
        f"📁 **Total in Queue:** `{len(user_storage[user_id]) + 1}`\n"
        f"━━━━━━━━━━━━━━\n"
        f"📥 *Downloading now...*"
    )
    
    status = await message.reply(summary_text, quote=True)
    
    try:
        start_time = time.time()
        file_path = await message.download(file_name=f"{DOWNLOAD_DIR}/{user_id}/")
        end_time = time.time()
        
        actual_duration = round(end_time - start_time, 1)

        if file_path:
            user_storage[user_id].append(file_path)
            await status.edit(
                f"✅ **Downloaded!**\n"
                f"━━━━━━━━━━━━━━\n"
                f"📄 `{file_name}`\n"
                f"⚡ **Took:** `{actual_duration}s`\n"
                f"📦 Total Files: `{len(user_storage[user_id])}`\n"
                f"Use /zip to finish."
            )
        else:
            await status.edit("❌ Download failed.")
            
    except Exception as e:
        await status.edit(f"⚠️ Error: {str(e)}")

@app.on_message(filters.command("zip"))
async def zip_cmd(client, message: Message):
    user_id = message.from_user.id
    files = user_storage.get(user_id, [])

    if not files:
        return await message.reply("❌ No files to zip!")

    total_size = sum(os.path.getsize(f) for f in files if os.path.exists(f))
    
    progress = await message.reply(
        f"📦 **Zipping {len(files)} files...**\n"
        f"Total size: `{get_readable_size(total_size)}`"
    )

    zip_path = f"archive_{user_id}.zip"
    try:
        with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for f in files:
                if os.path.exists(f):
                    z.write(f, os.path.basename(f))
        
        await message.reply_document(
            document=zip_path,
            caption=f"✅ **Success!**\nFiles: `{len(files)}`\nFinal Size: `{get_readable_size(os.path.getsize(zip_path))}`"
        )
    finally:
        if os.path.exists(zip_path): os.remove(zip_path)
        shutil.rmtree(f"{DOWNLOAD_DIR}/{user_id}", ignore_errors=True)
        user_storage[user_id] = []
        await progress.delete()

if __name__ == "__main__":
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    app.run()
