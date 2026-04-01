import os
import zipfile
import shutil
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 1. Setup Logging (Helps you see errors in Railway logs)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# 2. Get Token from Environment Variable
TOKEN = os.getenv('BOT_TOKEN')
user_files = {}

# --- COMMANDS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    # Clear previous session data if it exists
    if os.path.exists(f"folder_{user_id}"):
        shutil.rmtree(f"folder_{user_id}")
    os.makedirs(f"folder_{user_id}", exist_ok=True)
    user_files[user_id] = []
    
    await update.message.reply_text(
        "👋 **Welcome to Zip Bot!**\n\n"
        "1️⃣ Forward or send me photos, videos, or files.\n"
        "2️⃣ Use /zip to bundle them into one file.\n"
        "3️⃣ Use /clear to delete your current queue."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ **How to use me:**\n"
        "• Just send me files. I will count them.\n"
        "• Send /zip when you are ready.\n"
        "• Send /clear if you made a mistake."
    )

async def clear_queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if os.path.exists(f"folder_{user_id}"):
        shutil.rmtree(f"folder_{user_id}")
    user_files[user_id] = []
    await update.message.reply_text("🗑 Queue cleared!")

# --- MEDIA HANDLING ---

async def collect_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_files:
        user_files[user_id] = []
        os.makedirs(f"folder_{user_id}", exist_ok=True)
    
    # Identify file type and get ID
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

    path = f"folder_{user_id}/{file.file_id}{ext}"
    await file.download_to_drive(path)
    user_files[user_id].append(path)
    await update.message.reply_text(f"📥 Received! (Total: {len(user_files[user_id])})")

# --- ZIPPING ---

async def create_zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_files or not user_files[user_id]:
        await update.message.reply_text("❌ Send some files first!")
        return

    status_msg = await update.message.reply_text("🗜 Creating ZIP...")
    zip_n = f"Archive_{user_id}.zip"

    try:
        with zipfile.ZipFile(zip_n, 'w') as z:
            for f in user_files[user_id]:
                z.write(f, os.path.basename(f))

        await update.message.reply_document(document=open(zip_n, 'rb'), caption="Here is your ZIP file!")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")
    finally:
        # Cleanup
        if os.path.exists(f"folder_{user_id}"):
            shutil.rmtree(f"folder_{user_id}")
        if os.path.exists(zip_n):
            os.remove(zip_n)
        user_files[user_id] = []
        await status_msg.delete()

# --- MAIN ---

def main():
    if not TOKEN:
        print("ERROR: No BOT_TOKEN found in environment variables!")
        return

    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("clear", clear_queue))
    app.add_handler(CommandHandler("zip", create_zip))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, collect_media))
    
    print("Bot is alive...")
    app.run_polling()

if __name__ == '__main__':
    main()
