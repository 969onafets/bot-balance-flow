import os
import time
import sqlite3
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

# --- INIZIALIZZAZIONE DATABASE SQLITE ---
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY,
            profile_data TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_user_profile(user_id, profile_text):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO profiles (user_id, profile_data)
        VALUES (?, ?)
    ''', (user_id, profile_text))
    conn.commit()
    conn.close()

def get_user_profile(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT profile_data FROM profiles WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 'Profilo non ancora impostato.'

init_db()
# ----------------------------------------

# --- MINI SERVER FLASK PER LA PORTA DI RENDER ---
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Balance & Flow AI Bot è attivo e online con Database! 🚀"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host='0.0.0.0', port=port)
# ------------------------------------------------

# Inizializzazione del client Google GenAI
gemini_api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=gemini_api_key)

# Selezione sicura del modello Flash
def get_ai_model():
    model_to_use = 'gemini-3.8-flash'
    try:
        models = client.models.list()
        for m in models:
            if m.name and 'flash' in m.name:
                # Pulisce il nome rimuovendo il prefisso models/ se presente
                model_to_use = m.name.replace('models/', '')
                break
    except Exception as e:
        logging.warning(f"Impossibile elencare i modelli, utilizzo il default ({model_to_use}): {e}")
    return model_to_use

# Generazione con retry ottimizzato per gestire i 503 di Google
def generate_content_with_retry(prompt, system_instruction, photo_bytes=None, max_retries=3):
    model = get_ai_model()
    for attempt in range(max_retries):
        try:
            if photo_bytes:
                contents = [
                    types.Part.from_bytes(data=bytes(photo_bytes), mime_type='image/jpeg'),
                    prompt
                ]
            else:
                contents = prompt

            response = client.models.generate_content(
                model=model,
                contents=contents,
                config={'system_instruction': system_instruction}
            )
            return response.text
        except Exception as e:
            if "503" in str(e) and attempt < max_retries - 1:
                logging.warning(f"Google GenAI occupato (503). Tentativo {attempt + 1}/{max_retries}, attesa di 3 secondi...")
                time.sleep(3)
            else:
                raise e

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

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
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
                "La analizzerò in modo confidenziale insieme ai tuoi dati fisici salvati nel database per darti feedback mirati!"
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
        profile = get_user_profile(chat_id)
        system_instruction = (
            f"Sei 'Balance & Flow', un'assistente virtuale empatica, professionale e rispettosa "
            f"specializzata in benessere, postura, chinesiologia leggera e nutrizione veloce. "
            f"Dati dell'utente: {profile}. "
            "Rispondi in modo caldo, conciso, pratico e incoraggiante."
        )

        bot_reply = generate_content_with_retry(
            prompt=user_prompt,
            system_instruction=system_instruction
        )
    except Exception as e:
        logging.error(f"Errore IA da pulsante: {e}")
        bot_reply = "I server di Google sono momentaneamente sovraccarichi. Riprova tra qualche istante!"

    await context.bot.send_message(chat_id=chat_id, text=bot_reply)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    chat_id = update.effective_chat.id

    if context.user_data.get('waiting_for_profile'):
        save_user_profile(chat_id, user_message)
        context.user_data['waiting_for_profile'] = False
        await update.message.reply_text(
            "✅ **Profilo salvato permanentemente nel database!**\n\n"
            "I tuoi dati sono al sicuro e verranno usati per personalizzare ogni consiglio e analisi fotografica.",
            parse_mode='Markdown'
        )
        return

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        profile = get_user_profile(chat_id)
        system_instruction = (
            f"Sei 'Balance & Flow', un'assistente virtuale empatica e professionale "
            f"specializzata in benessere, postura e produttività. Dati utente: {profile}."
        )

        bot_reply = generate_content_with_retry(
            prompt=user_message,
            system_instruction=system_instruction
        )
    except Exception as e:
        logging.error(f"Errore generazione testo: {e}")
        bot_reply = "I server di Google sono momentaneamente sovraccarichi. Riprova tra qualche istante!"

    await update.message.reply_text(bot_reply)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()

        profile = get_user_profile(chat_id)
        caption = update.message.caption or "Analizza questa foto dal punto di vista della postura, della tonicità e del benessere generale, offrendo suggerimenti gentili e professionali."

        system_instruction = (
            f"Sei 'Balance & Flow', un'esperta di benessere, postura e forma fisica. "
            f"L'utente ha condiviso una foto per monitorare i suoi progressi o valutare la postura. "
            f"Dati utente: {profile}. "
            "Fornisci un'analisi rispettosa, costruttiva, motivante ed evita giudizi estetici severi, "
            "concentrandoti su salute, allineamento posturale e benessere."
        )

        bot_reply = generate_content_with_retry(
            prompt=caption,
            system_instruction=system_instruction,
            photo_bytes=photo_bytes
        )
    except Exception as e:
        logging.error(f"Errore nell'analisi della foto: {e}")
        bot_reply = "Non sono riuscito ad analizzare la foto a causa di un sovraccarico temporaneo dei server. Riprova tra poco!"

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

    print("Bot IA multimodale con database avviato con successo e in ascolto...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
