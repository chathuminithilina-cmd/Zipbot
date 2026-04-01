import os
from telegram.request 
import HTTPXRequest
import zipfile
import shutil
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 1. Logging Setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 2. Configuration
TOKEN = os.getenv('BOT_TOKEN')
# Replace 'api-server.railway.internal' with your Railway API service internal domain
LOCAL_API_URL = "telegram-bot-api-production-6cae.up.railway.app:8081" 

# Dictionary to store file paths for each user
user_files = {}

# --- HELPER FUNCTIONS ---

def get_user_dir(user_id):
    return f"downloads_{user_id}"

# --- COMMAND HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    # Clean start: remove old directory if it exists
    if os.path.exists(get_user_dir(user_id)):
        shutil.rmtree(get_user_dir(user_id))
    os.makedirs(get_user_dir(user_id), exist_ok=True)
    
    user_files[user_id] = []
    
    await update.message.reply_text(
        "⚡️ **2GB Zip Bot Active**\n\n"
        "Forward or send me any media (Photos, Videos, Files).\n"
        "Commands:\n"
        "▶️ /zip - Create the archive\n"
        "▶️ /clear - Reset your queue\n"
        "▶️ /help - Show instructions"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 **How to use:**\n"
        "1. Send files one by one (up to 2GB each).\n"
        "2. I will save them on the server.\n"
        "3. Type /zip and I will bundle them.\n"
        "4. I will send the ZIP back and delete my copies."
    )

async def clear_queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if os.path.exists(get_user_dir(user_id)):
        shutil.rmtree(get_user_dir(user_id))
    user_files[user_id] = []
    await update.message.reply_text("🗑 Queue cleared successfully.")

# --- MEDIA HANDLER ---

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    # Initialize user session if they forgot /start
    if user_id not in user_files:
        user_files[user_id] = []
        os.makedirs(get_user_dir(user_id), exist_ok=True)

    status_msg = await update.message.reply_text("📥 Downloading to high-speed server...")

    try:
        # Determine media type
        if update.message.photo:
            tg_file = await update.message.photo[-1].get_file()
            file_name = f"{tg_file.file_id}.jpg"
        elif update.message.video:
            tg_file = await update.message.video.get_file()
            file_name = update.message.video.file_name or f"{tg_file.file_id}.mp4"
        elif update.message.document:
            tg_file = await update.message.document.get_file()
            file_name = update.message.document.file_name or f"{tg_file.file_id}.file"
        else:
            await status_msg.edit_text("❓ Unsupported media type.")
            return

        save_path = os.path.join(get_user_dir(user_id), file_name)
        
        # Download using local API (Fast)
        await tg_file.download_to_drive(custom_path=save_path)
        user_files[user_id].append(save_path)
        
        await status_msg.edit_text(f"✅ Received: `{file_name}`\nTotal in queue: {len(user_files[user_id])}", parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error downloading: {e}")
        await status_msg.edit_text(f"❌ Error: {str(e)}")

# --- ZIPPER ---

async def create_zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if user_id not in user_files or not user_files[user_id]:
        await update.message.reply_text("❌ Your queue is empty!")
        return

    wait_msg = await update.message.reply_text("🗜 Compressing... (This can take a while for large files)")
    zip_path = f"Archive_{user_id}.zip"

    try:
        # Create the ZIP
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in user_files[user_id]:
                zipf.write(file, os.path.basename(file))

        await wait_msg.edit_text("📤 Uploading ZIP to Telegram...")
        
        # Upload the ZIP
        with open(zip_path, 'rb') as f:
            await update.message.reply_document(
                document=f, 
                caption="✅ Here is your compressed archive!",
                read_timeout=3600, # 1 hour timeout for 2GB uploads
                write_timeout=3600
            )

    except Exception as e:
        logger.error(f"Error zipping: {e}")
        await update.message.reply_text(f"⚠️ Failed to create ZIP: {str(e)}")
    
    finally:
        # CLEANUP: Crucial for Railway disk space
        if os.path.exists(get_user_dir(user_id)):
            shutil.rmtree(get_user_dir(user_id))
        if os.path.exists(zip_path):
            os.remove(zip_path)
        user_files[user_id] = []
        await wait_msg.delete()

# --- MAIN ---

def main():
    # ... your TOKEN and URL logic ...

    # Create a request object with very long timeouts (in seconds)
    # 3600 seconds = 1 hour
    t_request = HTTPXRequest(connect_timeout=60, read_timeout=3600, write_timeout=3600)

    app = (
        Application.builder()
        .token(TOKEN)
        .base_url(f"http://{LOCAL_API_URL}/bot")
        .local_mode(True)
        .request(t_request) # <--- Add this line here
        .build()
    )

    # Build application with LOCAL MODE enabled
    app = (
        Application.builder()
        .token(TOKEN)
        .base_url(f"http://{LOCAL_API_URL}/bot") 
        .local_mode(True)
        .build()
    )

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("clear", clear_queue))
    app.add_handler(CommandHandler("zip", create_zip))
    
    # Accept Photos, Videos, and all Documents
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, handle_media))

    print("--- Bot is Running with 2GB Support ---")
    app.run_polling()

if __name__ == '__main__':
    main()
