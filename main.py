import os
import logging
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from google import genai
from google.genai import types

# Configurazione del Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- MINI SERVER FLASK PER LA PORTA DI RENDER ---
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Balance & Flow AI Bot è attivo e online! 🚀"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host='0.0.0.0', port=port)
# ------------------------------------------------

# Inizializzazione del client Google GenAI
gemini_api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=gemini_api_key)

# Funzione di utilità per impostare il modello corretto e stabile
def get_ai_model():
    model_to_use = 'gemini-3.8-flash'
    try:
        models = client.models.list()
        for m in models:
            if 'flash' in m.name and 'generateContent' in m.supported_generation_methods:
                model_to_use = m.name
                break
    except Exception:
        pass
    return model_to_use

# Comando /start con pulsanti iniziali e percorsi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 **Benvenuta in Balance & Flow AI!**\n\n"
        "Sono la tua assistente personale per il benessere, la postura e la produttività.\n\n"
        "Scegli un'opzione o inviami una foto per un check personalizzato:"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🧘 Micro-Pausa (3-5 min)", callback_data="path_micropausa"),
            InlineKeyboardButton("🍎 Cena Espresso (15 min)", callback_data="path_cena")
        ],
        [
            InlineKeyboardButton("⚡ Check Energia / Stress", callback_data="path_energia"),
            InlineKeyboardButton("📊 Imposta Miei Dati", callback_data="set_profile")
        ],
        [
            InlineKeyboardButton("📸 Info Percorso Fotografico", callback_data="info_photo")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)

# Gestore dei pulsanti inline
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    # Corretto l'accesso alla chat id sfruttando l'update o il messaggio della query
    chat_id = update.effective_chat.id if update.effective_chat else query.message.chat.id
    
    if data == "set_profile":
        context.user_data['waiting_for_profile'] = True
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "📝 **Configurazione Profilo**\n\n"
                "Scrivimi in un unico messaggio i tuoi dati nel formato:\n"
                "`Età, Altezza (cm), Peso (kg), Obiettivo`\n\n"
                "Esempio: `35, 168, 60, Migliorare postura e tonificare`"
            ),
            parse_mode='Markdown'
        )
        return

    if data == "info_photo":
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "📸 **Percorso Fotografico & Postura**\n\n"
                "Puoi inviarmi in qualsiasi momento una foto (es. di profilo per la postura o per monitorare i tuoi progressi estetici).\n\n"
                "La analizzerò in modo confidenziale insieme ai tuoi dati fisici per darti feedback costruttivi ed esercizi mirati!"
            ),
            parse_mode='Markdown'
        )
        return

    data_map = {
        "path_micropausa": "Consigliami una micro-pausa rigenerante di 3-5 minuti da fare subito.",
        "path_cena": "Dammi un'idea per una cena espresso, veloce e salutare.",
        "path_energia": "Fai un check della mia energia e suggeriscimi come gestire lo stress attuale."
    }
    
    user_prompt = data_map.get(data, "Parlami del benessere quotidiano.")
    
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        profile = context.user_data.get('profile', 'Profilo non ancora impostato.')
        system_instruction = (
            f"Sei 'Balance & Flow', un'assistente virtuale empatica, professionale e rispettosa "
            f"specializzata in benessere, postura, chinesiologia leggera e nutrizione veloce. "
            f"Dati dell'utente: {profile}. "
            "Rispondi in modo caldo, conciso, pratico e incoraggiante."
        )

        response = client.models.generate_content(
            model=get_ai_model(),
            contents=user_prompt,
            config={'system_instruction': system_instruction}
        )
        bot_reply = response.text
    except Exception as e:
        logging.error(f"Errore IA da pulsante: {e}")
        bot_reply = "Scusa, ho avuto un piccolo momento di stanchezza. Riprova tra poco!"

    await context.bot.send_message(chat_id=chat_id, text=bot_reply)

# Gestione dei messaggi di testo
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    chat_id = update.effective_chat.id

    if context.user_data.get('waiting_for_profile'):
        context.user_data['profile'] = user_message
        context.user_data['waiting_for_profile'] = False
        await update.message.reply_text(
            "✅ **Profilo salvato con successo!**\n\n"
            "Ora terrò conto dei tuoi dati per personalizzare ogni consiglio e analisi fotografica. Prova a scrivermi o a inviarmi una foto!",
            parse_mode='Markdown'
        )
        return

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        profile = context.user_data.get('profile', 'Profilo non specificato.')
        system_instruction = (
            f"Sei 'Balance & Flow', un'assistente virtuale empatica e professionale "
            f"specializzata in benessere, postura e produttività. Dati utente: {profile}."
        )

        response = client.models.generate_content(
            model=get_ai_model(),
            contents=user_message,
            config={'system_instruction': system_instruction}
        )
        bot_reply = response.text
    except Exception as e:
        logging.error(f"Errore generazione testo: {e}")
        bot_reply = "Scusa, ho avuto un piccolo momento di stanchezza. Riprova tra poco!"

    await update.message.reply_text(bot_reply)

# Gestione delle foto inviate dall'utente
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()

        profile = context.user_data.get('profile', 'Nessun dato anagrafico inserito.')
        caption = update.message.caption or "Analizza questa foto dal punto di vista della postura, della tonicità e del benessere generale, offrendo suggerimenti gentili e professionali."

        system_instruction = (
            f"Sei 'Balance & Flow', un'esperta di benessere, postura e forma fisica. "
            f"L'utente ha condiviso una foto per monitorare i suoi progressi o valutare la postura. "
            f"Dati utente: {profile}. "
            "Fornisci un'analisi rispettosa, costruttiva, motivante ed evita giudizi estetici severi, "
            "concentrandoti su salute, allineamento posturale e benessere."
        )

        response = client.models.generate_content(
            model=get_ai_model(),
            contents=[
                types.Part.from_bytes(data=bytes(photo_bytes), mime_type='image/jpeg'),
                caption
            ],
            config={'system_instruction': system_instruction}
        )

        bot_reply = response.text
    except Exception as e:
        logging.error(f"Errore nell'analisi della foto: {e}")
        bot_reply = "Non sono riuscito ad analizzare la foto in questo momento. Assicurati che sia in formato chiaro e riprova tra poco!"

    await update.message.reply_text(bot_reply)

def main():
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    telegram_token = os.environ.get("TELEGRAM_TOKEN")
    app = Application.builder().token(telegram_token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot IA multimodale avviato con successo e in ascolto...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
