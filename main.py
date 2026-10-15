import os
import logging
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai

# Configurazione del Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- MINI SERVER FLASK PER SODDISFARE LA PORTA DI RENDER ---
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Balance & Flow AI Bot è attivo e online! 🚀"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host='0.0.0.0', port=port)
# -----------------------------------------------------------

# Inizializzazione del client Google GenAI
gemini_api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=gemini_api_key)

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 **Benvenuta in Balance & Flow AI!**\n\n"
        "Sono la tua assistente personale intelligente per il benessere, l'energia e la gestione del tempo.\n\n"
        "Scrivimi pure come ti senti oggi o chiedimi un consiglio: ti risponderò in tempo reale!"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

# Gestione dei messaggi di testo tramite l'Intelligenza Artificiale
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    # Mostra l'indicatore di scrittura su Telegram
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        system_instruction = (
            "Sei 'Balance & Flow', un'assistente virtuale empatica e professionale "
            "specializzata in benessere psicofisico, gestione dello stress, micro-pause rigeneranti, "
            "nutrizione veloce e produttività intelligente (Time-Smart). "
            "Rispondi in modo caldo, conciso, pratico e incoraggiante."
        )

        # Chiamata al modello Gemini aggiornato
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=user_message,
            config={
                'system_instruction': system_instruction,
            }
        )
        
        bot_reply = response.text
    except Exception as e:
        logging.error(f"Errore nella generazione con l'IA: {e}")
        bot_reply = "Scusa, ho avuto un piccolo momento di stanchezza e non riesco a elaborare la risposta adesso. Riprova tra poco!"

    await update.message.reply_text(bot_reply)

def main():
    # Avvia Flask in un thread separato
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    telegram_token = os.environ.get("TELEGRAM_TOKEN")
    app = Application.builder().token(telegram_token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot IA avviato con successo e in ascolto...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
