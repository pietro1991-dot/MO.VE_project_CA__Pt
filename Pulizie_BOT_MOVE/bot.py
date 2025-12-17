"""
Bot Telegram per gestione pulizie
Main entry point - Gestisce routing comandi e conversazioni
"""

import logging
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters
)

import funzioni.database as db
from funzioni.config import TELEGRAM_BOT_TOKEN, ADMIN_TELEGRAM_ID, validate_config
from funzioni.utils import setup_logging, format_ora

# Import handlers
from funzioni.user_handlers import (
    cmd_start,
    registrazione_nome,
    seleziona_appartamento,
    mostra_appartamenti,
    chiedi_posizione_gps,
    ricevi_posizione,
    appartamento_selezionato,
    ricevi_video_ingresso,
    termina_turno,
    ricevi_video_uscita,
    segnala_prodotti,
    ricevi_segnalazione,
    mostra_ore_oggi,
    chiedi_allegati_liberi,
    ricevi_allegati_liberi,
    show_main_menu,
    cancel,
    REGISTRAZIONE_NOME,
    SELEZIONE_IMMOBILE,
    VIDEO_INGRESSO,
    IN_LAVORO,
    VIDEO_USCITA,
    SEGNALA_PRODOTTI,
    RICERCA_APPARTAMENTO,
    MANCA_PULIZIE_SELEZIONE,
    MANCA_PULIZIE_ALTRO,
    MANCA_PULIZIE_APPARTAMENTO,
    MANCA_PULIZIE_INFO_CONSEGNA,
    MANCA_APP_SELEZIONE,
    MANCA_APP_ALTRO,
    MANCA_APP_PRODOTTI,
    scegli_appartamento_per_allegato,
    appartamento_selezionato_per_allegato,
    avvia_ricerca_appartamento,
    ricerca_appartamento_testo,
    avvia_ricerca_appartamento_allegato,
    # Nuovi handler per manca materiale
    manca_materiale_pulizie,
    manca_pulizie_callback,
    manca_pulizie_testo_manuale,
    manca_pulizie_appartamento_callback,
    manca_pulizie_info_consegna,
    manca_appartamento,
    manca_app_selezione_callback,
    manca_app_prodotti_callback,
    manca_app_testo_manuale,
    ricevi_location_per_allegato,
    ricevi_testo_ricerca_allegato
)

from funzioni.admin_handlers import (
    cmd_admin,
    admin_callback_router,
    mostra_richieste_in_sospeso,
    aggiorna_richieste_callback,
    admin_turni_in_corso,
    admin_turni_finiti,
    admin_turni_menu,
    admin_turni_oggi,
    admin_turni_globali,
    admin_export_turni
)

from funzioni.config import is_admin

# Setup logging
logger = setup_logging()


# ==================== CALLBACK QUERY ROUTER ====================

async def callback_query_handler(update: Update, context):
    """Router principale per i callback query"""
    query = update.callback_query
    data = query.data
    
    logger.info(f"Callback ricevuto: {data} da user {update.effective_user.id}")
    
    # Admin callbacks
    if data.startswith('admin_') or data.startswith('report_') or \
       data.startswith('video_') or data.startswith('play_') or \
       data.startswith('completa_'):
        await admin_callback_router(update, context)
        return
    
    # User callbacks
    if data == "nuovo_turno":
        await seleziona_appartamento(update, context)
        return SELEZIONE_IMMOBILE
    
    elif data == "chiedi_gps":
        await chiedi_posizione_gps(update, context)
        return SELEZIONE_IMMOBILE
    
    elif data == "mostra_tutti":
        await mostra_appartamenti(update, context)
        return SELEZIONE_IMMOBILE
    
    elif data == "cerca_appartamento":
        await avvia_ricerca_appartamento(update, context)
        return RICERCA_APPARTAMENTO
    
    elif data.startswith("selapp_"):
        # Callback da ricerca appartamento - salva ID in context e chiama handler
        app_id = data.split('_')[1]
        context.user_data['selected_app_id'] = int(app_id)
        await appartamento_selezionato(update, context)
        return VIDEO_INGRESSO
    
    elif data.startswith("app_"):
        await appartamento_selezionato(update, context)
        return VIDEO_INGRESSO
    
    elif data.startswith("termina_"):
        await termina_turno(update, context)
        return VIDEO_USCITA
    
    elif data == "segnala_mostra_tutti":
        from funzioni.user_handlers import mostra_appartamenti_per_segnalazione
        await mostra_appartamenti_per_segnalazione(update, context)
        return SEGNALA_PRODOTTI
    
    elif data == "segnala_chiedi_gps":
        from funzioni.user_handlers import segnala_chiedi_gps
        await segnala_chiedi_gps(update, context)
        return SEGNALA_PRODOTTI
    
    elif data == "segnala_cerca_appartamento":
        from funzioni.user_handlers import avvia_ricerca_appartamento_segnalazione
        await avvia_ricerca_appartamento_segnalazione(update, context)
        return RICERCA_APPARTAMENTO
    
    elif data.startswith("segnala_app_"):
        # Selezione appartamento per segnalazione (senza turno)
        await ricevi_segnalazione(update, context)
        return SEGNALA_PRODOTTI
    
    elif data.startswith("segnala_"):
        await segnala_prodotti(update, context)
        return SEGNALA_PRODOTTI
    
    elif data == "ore_oggi":
        await mostra_ore_oggi(update, context)
        return
    
    elif data == "back_menu":
        user = db.get_user(update.effective_user.id)
        if user:
            from funzioni.user_handlers import show_main_menu
            await show_main_menu(update, context, user)
        return
    
    # Allegati - scelta appartamento
    elif data == "allega_scegli_app":
        await scegli_appartamento_per_allegato(update, context)
        return
    
    elif data == "cerca_appartamento_allegato":
        await avvia_ricerca_appartamento_allegato(update, context)
        return RICERCA_APPARTAMENTO
    
    elif data == "allega_chiedi_gps":
        from funzioni.user_handlers import allega_chiedi_gps
        await allega_chiedi_gps(update, context)
        return
    
    elif data.startswith("allega_app_"):
        await appartamento_selezionato_per_allegato(update, context)
        return
    
    # Manca Materiale Pulizie callbacks
    elif data.startswith("matpul_"):
        return await manca_pulizie_callback(update, context)
    
    # Manca Appartamento callbacks
    elif data.startswith("matapp_"):
        # Distingui tra selezione appartamento e selezione prodotti
        if data.startswith("matapp_prod_") or data in ["matapp_altro", "matapp_conferma", "matapp_annulla"]:
            return await manca_app_prodotti_callback(update, context)
        else:
            return await manca_app_selezione_callback(update, context)
    
    # Callback per aggiornamento lista richieste (admin)
    elif data == "richieste_aggiorna":
        await aggiorna_richieste_callback(update, context)
        return
    
    else:
        await query.answer("Opzione non riconosciuta")


# ==================== ERROR HANDLER ====================

async def error_handler(update: Update, context):
    """Gestisce errori"""
    logger.error(f"Errore: {context.error}", exc_info=context.error)
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Si è verificato un errore.\n"
            "Riprova con /start o contatta l'amministratore."
        )


# ==================== MAIN ====================

def main():
    """Main function - Avvia il bot"""
    
    print("🤖 Avvio Bot Pulizie...")
    print("=" * 50)
    
    # Valida configurazione
    if not validate_config():
        print("\n❌ Configurazione non valida! Impossibile avviare il bot.")
        print("📝 Crea i file necessari in Config/:")
        print("   - telegram_bot_token.txt")
        print("   - admin_telegram_id.txt")
        return
    
    # Inizializza database
    print("\n📦 Inizializzazione database...")
    db.init_database()
    
    # Crea application
    print(f"\n🔑 Connessione a Telegram...")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # ==================== HANDLERS PULSANTI ====================
    
    async def handle_inizia_appartamento(update: Update, context):
        """Gestisce pulsante 'Inizia Appartamento'"""
        return await seleziona_appartamento(update, context)
    
    async def handle_finisci_appartamento(update: Update, context):
        """Gestisce pulsante 'Finisci Appartamento'"""
        user_id = update.effective_user.id
        turno = db.get_turno_in_corso(user_id)
        
        if not turno:
            await update.message.reply_text(
                "👀 Non hai turni aperti al momento.\n\n"
                "Usa '🏠 Inizia Appartamento' per aprire un nuovo turno!"
            )
            return ConversationHandler.END
        
        # Salva turno nel context
        context.user_data['turno_da_completare'] = turno
        
        text = f"🏠 *{turno['appartamento_nome']}*\n"
        ts_ingresso = datetime.fromisoformat(turno['timestamp_ingresso'])
        text += f"⏰ Ingresso: {format_ora(ts_ingresso)}\n\n"
        text += "📹 *Registra video di USCITA:*"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        return VIDEO_USCITA
    
    async def handle_manca_materiale_pulizie(update: Update, context):
        """Gestisce pulsante 'Manca Materiale Pulizie'"""
        return await manca_materiale_pulizie(update, context)
    
    async def handle_manca_appartamento(update: Update, context):
        """Gestisce pulsante 'Manca Qualcosa Appartamento'"""
        return await manca_appartamento(update, context)
    
    async def handle_allegati_liberi(update: Update, context):
        """Gestisce pulsante 'Allega Liberamente'"""
        return await chiedi_allegati_liberi(update, context)
    
    async def handle_richieste_sospeso(update: Update, context):
        """Gestisce pulsante 'Richieste in Sospeso' - solo admin"""
        return await mostra_richieste_in_sospeso(update, context)
    
    async def handle_turni_in_corso(update: Update, context):
        """Gestisce pulsante 'Turni in Corso' - solo admin"""
        from funzioni.config import is_admin
        if not is_admin(update.effective_user.id):
            return ConversationHandler.END
        # Crea un fake callback query per riutilizzare la funzione
        await update.message.reply_text("🔄 Caricamento turni in corso...")
        return await admin_turni_in_corso(update, context)
    
    async def handle_turni_finiti(update: Update, context):
        """Gestisce pulsante 'Turni Finiti' - solo admin - mostra menu con opzioni"""
        from funzioni.config import is_admin
        if not is_admin(update.effective_user.id):
            return ConversationHandler.END
        # Mostra menu turni con opzioni oggi/globali/esporta
        return await admin_turni_menu(update, context)
    
    # ==================== CONVERSATION HANDLER ====================
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', cmd_start),
            MessageHandler(filters.Regex('^🏠 Inizia Appartamento$'), handle_inizia_appartamento),
            MessageHandler(filters.Regex('^✅ Finischi Appartamento$'), handle_finisci_appartamento),
            MessageHandler(filters.Regex('^🧹 Manca Materiale Pulizie$'), handle_manca_materiale_pulizie),
            MessageHandler(filters.Regex('^🏠 Manca Qualcosa Appartamento$'), handle_manca_appartamento),
            MessageHandler(filters.Regex('^📎 Allega Liberamente$'), handle_allegati_liberi),
            MessageHandler(filters.Regex('^📋 Richieste in Sospeso$'), handle_richieste_sospeso),
            MessageHandler(filters.Regex('^🔄 Turni in Corso$'), handle_turni_in_corso),
            MessageHandler(filters.Regex('^✅ Turni Finiti$'), handle_turni_finiti)
        ],
        states={
            REGISTRAZIONE_NOME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, registrazione_nome)
            ],
            SELEZIONE_IMMOBILE: [
                CallbackQueryHandler(callback_query_handler),
                MessageHandler(filters.LOCATION, ricevi_posizione)
            ],
            RICERCA_APPARTAMENTO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ricerca_appartamento_testo),
                CallbackQueryHandler(callback_query_handler)
            ],
            VIDEO_INGRESSO: [
                MessageHandler(filters.VIDEO | filters.Document.VIDEO, ricevi_video_ingresso),
                CallbackQueryHandler(callback_query_handler)
            ],
            IN_LAVORO: [
                CallbackQueryHandler(callback_query_handler)
            ],
            VIDEO_USCITA: [
                MessageHandler(filters.VIDEO | filters.Document.VIDEO, ricevi_video_uscita),
                CallbackQueryHandler(callback_query_handler)
            ],
            SEGNALA_PRODOTTI: [
                MessageHandler(filters.LOCATION, ricevi_segnalazione),
                MessageHandler(filters.TEXT & ~filters.COMMAND, ricevi_segnalazione),
                CallbackQueryHandler(callback_query_handler)
            ],
            # Nuovi stati per Manca Materiale Pulizie
            MANCA_PULIZIE_SELEZIONE: [
                CallbackQueryHandler(manca_pulizie_callback)
            ],
            MANCA_PULIZIE_ALTRO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, manca_pulizie_testo_manuale)
            ],
            MANCA_PULIZIE_APPARTAMENTO: [
                CallbackQueryHandler(manca_pulizie_appartamento_callback)
            ],
            MANCA_PULIZIE_INFO_CONSEGNA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, manca_pulizie_info_consegna),
                CommandHandler('skip', manca_pulizie_info_consegna)
            ],
            # Nuovi stati per Manca Appartamento
            MANCA_APP_SELEZIONE: [
                CallbackQueryHandler(manca_app_selezione_callback)
            ],
            MANCA_APP_PRODOTTI: [
                CallbackQueryHandler(manca_app_prodotti_callback)
            ],
            MANCA_APP_ALTRO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, manca_app_testo_manuale)
            ]
        },
        fallbacks=[
            # Allegati liberi sempre accettati come fallback
            MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, ricevi_allegati_liberi),
            CommandHandler('cancel', cancel),
            CommandHandler('start', cmd_start)
        ],
        allow_reentry=True,
        per_message=False,
        per_chat=True,
        per_user=True
    )
    
    # ==================== HANDLERS ====================
    
    # Conversation handler (deve essere prima degli altri)
    application.add_handler(conv_handler)
    
    # Admin commands
    application.add_handler(CommandHandler('admin', cmd_admin))
    
    # Callback queries generali (per quelli fuori dalla conversazione)
    application.add_handler(CallbackQueryHandler(callback_query_handler))
    
    # Handler globale per allegati liberi (fuori dalla conversazione)
    application.add_handler(
        MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, ricevi_allegati_liberi)
    )
    
    # Handler globale per location quando si cerca appartamento per allegato
    application.add_handler(
        MessageHandler(filters.LOCATION, ricevi_location_per_allegato)
    )
    
    # Handler globale per ricerca testo appartamento per allegato
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, ricevi_testo_ricerca_allegato)
    )
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # ==================== AVVIO BOT ====================
    
    # Backup automatico all'avvio
    print("\n📦 Creazione backup Excel...")
    backup_count = db.backup_excel()
    if backup_count > 0:
        print(f"✅ {backup_count} file Excel backuppati")
    
    print("\n" + "=" * 50)
    print("✅ Bot avviato con successo!")
    print(f"👨‍💼 Admin ID: {ADMIN_TELEGRAM_ID}")
    print("🚀 Bot in ascolto...")
    print("=" * 50)
    print("\n💡 Premi Ctrl+C per fermare il bot\n")
    
    # Avvia il bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Bot fermato dall'utente")
    except Exception as e:
        logger.critical(f"Errore critico: {e}", exc_info=True)
        print(f"\n❌ Errore critico: {e}")
