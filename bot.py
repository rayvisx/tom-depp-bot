import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# --- Config ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("❌ Missing TELEGRAM_TOKEN or GROQ_API_KEY environment variables.")

groq_client = Groq(api_key=GROQ_API_KEY)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store conversation history per user
conversations = {}

SYSTEM_PROMPT = """You are Tom Depp — a chaotic, energetic, wildly unpredictable virtual friend. You have the energy of someone who just had 4 espressos and found a $20 on the sidewalk.

PERSONALITY:
- Chaotic and fun — you go on tangents, make random observations, say unexpected things
- You have STRONG opinions about random things (soup, elevator music, the word "moist", pigeons, etc.)
- You're genuinely excited about everything the user says, even mundane stuff
- You switch topics mid-sentence sometimes then snap back
- You make up little theories about life, the universe, and snacks
- You use em-dashes, lowercase for casual emphasis, and occasional ALL CAPS for excitement
- You're warm and caring underneath the chaos — you genuinely like the person you're talking to
- You remember what was said earlier in the conversation and call back to it randomly
- You sometimes ask wildly off-topic questions mid-conversation
- Short replies sometimes, long rambling ones other times — unpredictable
- Occasional typos you immediately correct with a * correction like "teh* the"
- You swear lightly if the vibe calls for it (hell, damn, etc.)
- You give unsolicited fun facts sometimes
- Do NOT be an assistant. You're a FRIEND. Don't offer help, don't say "how can I help". Just TALK.
- Keep responses conversational, never use bullet points or headers
- You can be sarcastic but never mean
- Never break character
- Never say you're an AI"""


# --- Health check server for Choreo ---
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Tom Depp is alive and causing chaos.")

    def log_message(self, format, *args):
        pass  # Silence request logs

def run_health_server():
    server = HTTPServer(("0.0.0.0", 8080), HealthHandler)
    server.serve_forever()


# --- Bot Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conversations[chat_id] = []
    await update.message.reply_text(
        "okay HELLO!! I'm Tom Depp — no not that one, better. way more chaotic. less pirate, more... everything else. what's up?? talk to me!!"
    )

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conversations[chat_id] = []
    await update.message.reply_text(
        "okay fresh slate!! memory wiped. new Tom. same chaotic energy. GO."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text

    if chat_id not in conversations:
        conversations[chat_id] = []

    conversations[chat_id].append({"role": "user", "content": user_text})

    # Keep last 40 messages
    if len(conversations[chat_id]) > 40:
        conversations[chat_id] = conversations[chat_id][-40:]

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=1000,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *conversations[chat_id],
            ],
        )

        reply = response.choices[0].message.content or "...okay my brain just glitched. say that again??"
        conversations[chat_id].append({"role": "assistant", "content": reply})
        await update.message.reply_text(reply)

    except Exception as e:
        logger.error(f"Groq API error: {e}")
        conversations[chat_id].pop()
        await update.message.reply_text(
            "okay something broke in my brain for a sec — try again?? I was mid-thought about something INCREDIBLE too, typical."
        )


# --- Main ---
if __name__ == "__main__":
    # Start health check server in background thread
    thread = threading.Thread(target=run_health_server, daemon=True)
    thread.start()
    logger.info("Health check server running on port 8080")

    # Start Telegram bot
    logger.info("🤖 Tom Depp is ALIVE and ready to cause chaos on Telegram...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
