import os
import logging
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Configurazione del Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- MINI SERVER FLASK PER SODDISFARE LA PORTA DI RENDER ---
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Balance & Flow Bot è attivo e online! 🚀"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host='0.0.0.0', port=port)
# -----------------------------------------------------------

# Funzione per mostrare il menu principale con i pulsanti interattivi
def main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🧘 Micro-Pausa (3-5 min)", callback_data='pausa'),
            InlineKeyboardButton("🥗 Cena Espresso (15 min)", callback_data='cena')
        ],
        [
            InlineKeyboardButton("⚡ Check Energia / Stress", callback_data='check_energia'),
            InlineKeyboardButton("📅 Consiglio Time-Smart", callback_data='time_smart')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 **Benvenuta in Balance & Flow!**\n\n"
        "Sono la tua assistente personale per ritrovare equilibrio, "
        "energia e tempo per te stessa durante la giornata.\n\n"
        "Come posso aiutarti in questo momento?"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=main_keyboard())

# Gestione dei click sui pulsanti della tastiera inline
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'pausa':
        text = (
            "🧘 **Micro-Pausa Rigenerante (3 Minuti)**\n\n"
            "1. Stacca gli occhi dallo schermo e guarda un punto lontano.\n"
            "2. Fai 5 respiri profondi: inspira per 4 secondi, mantieni per 4, espira per 6.\n"
            "3. Ruota le spalle all'indietro per 10 volte per sciogliere la tensione del collo.\n\n"
            "💡 *Piccolo promemoria:* La tua salute merita questi 3 minuti."
        )
    elif query.data == 'cena':
        text = (
            "🥗 **Idea Cena Espresso (Pronta in 15 min)**\n\n"
            "**Salmone grigliato con Insalata di Avocado e Noci**\n"
            "• Ricco di Omega-3 e grassi buoni per l'energia ormonale.\n"
            "• Cuoci il filetto di salmone in padella 4 min per lato.\n"
            "• Unisci spinacini freschi, mezzo avocado e noci in una ciotola.\n"
            "• Condisci con limone e olio EVO!"
        )
    elif query.data == 'check_energia':
        text = (
            "⚡ **Check Energia**\n\n"
            "Come ti senti in questo momento?\n"
            "• **Se ti senti stanca/scarica:** Bevi un grande bicchiere d'acqua fresca e fai 2 minuti di stretching.\n"
            "• **Se ti senti sopraffatta dalle cose da fare:** Scegli UNA sola attività prioritaria e ignora tutto il resto per i prossimi 30 minuti."
        )
    elif query.data == 'time_smart':
        text = (
            "📅 **Regola Time-Smart del Giorno**\n\n"
            "**La regola dei 2 minuti:**\n"
            "Se un'attività richiede meno di 2 minuti per essere fatta (rispondere a un messaggio breve, riporre una cosa, avviare la lavatrice), farla *subito* anziché inserirla nella lista delle cose da fare. Svuoterà istantaneamente la tua mente!"
        )

    await query.edit_message_text(text=text, parse_mode='Markdown', reply_markup=main_keyboard())

def main():
    # Avvia Flask in un thread separato in background per mantenere la porta aperta su Render
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Token del bot
    token = "8743824615:AAFF_uL3YKRJgIkjlrKLmQD_gYGEclJwMp4"

    # Inizializzazione dell'applicazione Telegram
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot avviato con successo e in ascolto...")
    app.run_polling()

if __name__ == '__main__':
    main()
