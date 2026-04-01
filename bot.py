import os
import zipfile
import shutil
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 1. Setup Logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# 2. Configuration
TOKEN = os.getenv('BOT_TOKEN')
# IMPORTANT: Change this to your Railway API Server URL
LOCAL_API_URL = "telegram-bot-api-production-6cae.up.railway.app" 

user_files = {}

# --- COMMANDS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    # Clean workspace
    if os.path.exists(f"data_{user_id}"):
        shutil.rmtree(f"data_{user_id}")
    os.makedirs(f"data_{user_id}", exist_ok=True)
    user_files[user_id] = []
    
    await update.message.reply_text(
        "🚀 **2GB Mode Active**\n\n"
        "Send/Forward any large media. I will store them locally.\n"
        "Commands:\n"
        "/zip - Create the archive\n"
        "/clear - Reset everything"
    )

# --- MEDIA COLLECTION ---

async def collect_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_files:
        user_files[user_id] = []
        os.makedirs(f"data_{user_id}", exist_ok=True)

    msg = await update.message.reply_text("📥 Downloading to server...")

    try:
        # Detect media type
        if update.message.photo:
            file = await update.message.photo[-1].get_file()
            ext = ".jpg"
        elif update.message.video:
            file = await update.message.video.get_file()
            ext = ".mp4"
        elif update.message.document:
            file = await update.message.document.get_file()
            ext = os.path.splitext(update.message.document.file_name)[1]
        else:
            return

        # Increased timeout for large 2GB files
        file_path = f"data_{user_id}/{file.file_id}{ext}"
        await file.download_to_drive(custom_path=file_path, read_timeout=3600, write_timeout=3600)
        
        user_files[user_id].append(file_path)
        await msg.edit_text(f"✅ Received! Total files in queue: {len(user_files[user_id])}")

    except Exception as e:
        await msg.edit_text(f"❌ Download Failed: {str(e)}")

# --- ZIP PROCESSING ---

async def create_zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_files or not user_files[user_id]:
        await update.message.reply_text("Queue is empty!")
        return

    status = await update.message.reply_text("🗜 Compressing large files... This may take a while.")
    zip_name = f"Final_Archive_{user_id}.zip"

    try:
        # Using ZIP_DEFLATED to actually compress the size
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as z:
            for f in user_files[user_id]:
                z.write(f, os.path.basename(f))

        await status.edit_text("📤 Uploading ZIP to Telegram...")
        
        # Send the large file (Up to 2GB via Local API)
        with open(zip_name, 'rb') as doc:
            await update.message.reply_document(
                document=doc, 
                caption=f"📦 Archive complete!\nFiles: {len(user_files[user_id])}",
                read_timeout=3600,
                write_timeout=3600
            )

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error during Zipping/Uploading: {str(e)}")
    
    finally:
        # Final Cleanup to save Disk Space
        if os.path.exists(f"data_{user_id}"):
            shutil.rmtree(f"data_{user_id}")
        if os.path.exists(zip_name):
            os.remove(zip_name)
        user_files[user_id] = []
        await status.delete()

# --- MAIN ENGINE ---

def main():
    if not TOKEN:
        print("CRITICAL: BOT_TOKEN is missing!")
        return

    # Connection to YOUR Local Bot API Server
    app = (
        Application.builder()
        .token(TOKEN)
        .base_url(f"http://{LOCAL_API_URL}/bot") # No https if internal, use http
        .local_mode(True)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("zip", create_zip))
    app.add_handler(CommandHandler("clear", start)) # reuse start logic for clear
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, collect_media))

    print("🚀 Bot Started in 2GB Mode")
    app.run_polling()

if __name__ == '__main__':
    main()
