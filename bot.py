import os
import zipfile
import shutil
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest  # Correctly imported

# 1. Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. Configuration
TOKEN = os.getenv('BOT_TOKEN')
# Use your Railway API internal domain here
LOCAL_API_URL = "telegram-bot-api-production-6cae.up.railway.app:8081" 

user_files = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    path = f"downloads_{user_id}"
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)
    user_files[user_id] = []
    await update.message.reply_text("🚀 Bot Ready! Send media then /zip")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_files:
        user_files[user_id] = []
        os.makedirs(f"downloads_{user_id}", exist_ok=True)

    status = await update.message.reply_text("📥 Downloading...")
    try:
        if update.message.photo:
            tg_file = await update.message.photo[-1].get_file()
            name = f"{tg_file.file_id}.jpg"
        elif update.message.video:
            tg_file = await update.message.video.get_file()
            name = update.message.video.file_name or f"{tg_file.file_id}.mp4"
        elif update.message.document:
            tg_file = await update.message.document.get_file()
            name = update.message.document.file_name or f"{tg_file.file_id}.file"
        else: return

        save_path = os.path.join(f"downloads_{user_id}", name)
        await tg_file.download_to_drive(custom_path=save_path)
        user_files[user_id].append(save_path)
        await status.edit_text(f"✅ Received! Total: {len(user_files[user_id])}")
    except Exception as e:
        await status.edit_text(f"❌ Error: {e}")

async def create_zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_files or not user_files[user_id]:
        await update.message.reply_text("Empty queue!")
        return

    wait = await update.message.reply_text("🗜 Zipping...")
    zip_path = f"Archive_{user_id}.zip"

    try:
        # Use ZIP_STORED for speed on Trial plan (no compression, just bundling)
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_STORED) as zipf:
            for file in user_files[user_id]:
                zipf.write(file, os.path.basename(file))

        await wait.edit_text("📤 Uploading...")
        with open(zip_path, 'rb') as f:
            await update.message.reply_document(document=f, read_timeout=3600, write_timeout=3600)
    finally:
        if os.path.exists(f"downloads_{user_id}"):
            shutil.rmtree(f"downloads_{user_id}")
        if os.path.exists(zip_path):
            os.remove(zip_path)
        user_files[user_id] = []
        await wait.delete()

def main():
    # 3. Create request with 1-hour timeout for 2GB files
    t_request = HTTPXRequest(connect_timeout=60, read_timeout=3600, write_timeout=3600)

    app = (
        Application.builder()
        .token(TOKEN)
        .base_url(f"http://{LOCAL_API_URL}/bot")
        .local_mode(True)
        .request(t_request) # Connects the timeout settings
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("zip", create_zip))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, handle_media))
    app.run_polling()

if __name__ == '__main__':
    main()
