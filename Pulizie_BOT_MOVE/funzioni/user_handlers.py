"""
Handlers per le funzionalità utente
Gestisce registrazione, turni (ingresso/uscita), segnalazioni prodotti
"""

import logging
from datetime import datetime
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from . import database as db
from .utils import (
    format_turno_info, format_ora, format_ore, 
    calcola_distanza_haversine, format_distanza, parse_coordinate
)
from .video_handler import download_and_save_video
from .config import GPS_TOLERANCE_METERS, NOTIFICHE_ADMIN_ENABLED, ADMIN_TELEGRAM_ID, is_admin

logger = logging.getLogger(__name__)

# Stati conversazione
(REGISTRAZIONE_NOME, SELEZIONE_IMMOBILE, VIDEO_INGRESSO, 
 IN_LAVORO, VIDEO_USCITA, SEGNALA_PRODOTTI, RICERCA_APPARTAMENTO,
 MANCA_PULIZIE_SELEZIONE, MANCA_PULIZIE_ALTRO, MANCA_PULIZIE_APPARTAMENTO, MANCA_PULIZIE_INFO_CONSEGNA,
 MANCA_APP_SELEZIONE, MANCA_APP_ALTRO, MANCA_APP_PRODOTTI) = range(14)


# ==================== REGISTRAZIONE ====================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start - Registrazione o menu principale"""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # DEBUG: Mostra ID utente (da rimuovere dopo configurazione)
    logger.info(f"🆔 User ID: {user_id}, Username: @{username}")
    
    try:
        # Verifica se utente è già registrato
        logger.info(f"Recupero dati utente {user_id}...")
        user = db.get_user(user_id)
        logger.info(f"Risultato get_user: {user}")
        
        if user:
            # Utente già registrato, mostra menu
            logger.info(f"Utente esistente, mostro menu per {user['nome']}")
            await show_main_menu(update, context, user)
            return ConversationHandler.END
        else:
            # Primo accesso, chiedi registrazione
            logger.info("Nuovo utente, chiedo registrazione")
            await update.message.reply_text(
                "👋 *Benvenuta!*\n\n"
                "Per iniziare, inserisci il tuo *nome e cognome*\n"
                "_(Es: Maria Rossi)_",
                parse_mode='Markdown'
            )
            return REGISTRAZIONE_NOME
    except Exception as e:
        logger.error(f"Errore in cmd_start: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Errore: {e}\n\n"
            "Riprova con /start"
        )
        return ConversationHandler.END


async def registrazione_nome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Riceve nome e cognome e completa registrazione"""
    user_id = update.effective_user.id
    username = update.effective_user.username
    nome_completo = update.message.text.strip()
    
    # Validazione lunghezza
    if len(nome_completo) < 5 or len(nome_completo) > 100:
        await update.message.reply_text(
            "⚠️ Nome troppo corto o troppo lungo\n"
            "_(Inserisci nome e cognome, es: Maria Rossi)_",
            parse_mode='Markdown'
        )
        return REGISTRAZIONE_NOME
    
    # Parse nome e cognome
    parts = nome_completo.split(maxsplit=1)
    
    if len(parts) < 2:
        await update.message.reply_text(
            "⚠️ Inserisci sia il nome che il cognome\n"
            "_(Es: Maria Rossi)_",
            parse_mode='Markdown'
        )
        return REGISTRAZIONE_NOME
    
    nome = parts[0].strip().capitalize()
    cognome = parts[1].strip().capitalize()
    
    # Validazione minima lunghezza nome/cognome
    if len(nome) < 2 or len(cognome) < 2:
        await update.message.reply_text(
            "⚠️ Nome e cognome devono avere almeno 2 caratteri ciascuno",
            parse_mode='Markdown'
        )
        return REGISTRAZIONE_NOME
    
    # Registra utente
    success = db.register_user(user_id, username, nome, cognome)
    
    if success:
        user_data = db.get_user(user_id)
        await show_main_menu(update, context, user_data)
        logger.info(f"Nuovo utente registrato: {nome} {cognome} ({user_id})")
    else:
        await update.message.reply_text(
            "❌ Errore durante la registrazione.\n"
            "Riprova con /start"
        )
    
    return ConversationHandler.END


# ==================== MENU PRINCIPALE ====================

def get_main_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    """Restituisce la tastiera del menu principale"""
    keyboard = [
        [KeyboardButton("🏠 Inizia Appartamento")],
        [KeyboardButton("✅ Finischi Appartamento")],
        [KeyboardButton("🧹 Manca Materiale Pulizie")],
        [KeyboardButton("🏠 Manca Qualcosa Appartamento")],
        [KeyboardButton("📎 Allega Liberamente")]
    ]
    
    # Aggiungi pulsante admin solo per gli amministratori
    if is_admin(user_id):
        keyboard.append([KeyboardButton("📋 Richieste in Sospeso")])
        keyboard.append([KeyboardButton("🔄 Turni in Corso"), KeyboardButton("✅ Turni Finiti")])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user: dict):
    """Mostra menu principale con tastiera personalizzata"""
    user_id = user['telegram_id']
    nome = user['nome']
    
    # Verifica se ha turno in corso
    turno_in_corso = db.get_turno_in_corso(user_id)
    
    # Usa la funzione helper per la tastiera
    reply_markup = get_main_keyboard(user_id)
    
    if turno_in_corso:
        # Ha un turno aperto
        text = f"👋 Ciao {nome}!\n\n"
        text += "🏠 *Turno in corso:*\n"
        text += format_turno_info(turno_in_corso)
        text += "\nUsa i pulsanti qui sotto per continuare 👇"
    else:
        # Nessun turno in corso
        text = f"👋 Ciao {nome}!\n\n"
        text += "Pronta per iniziare?\n"
        text += "Usa i pulsanti qui sotto 👇"
    
    if update.callback_query:
        await update.callback_query.message.reply_text(
            text, reply_markup=reply_markup, parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            text, reply_markup=reply_markup, parse_mode='Markdown'
        )


# ==================== SELEZIONE APPARTAMENTO ====================

async def seleziona_appartamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra lista appartamenti per selezione"""
    query = update.callback_query
    if query:
        await query.answer()
    
    user = db.get_user(update.effective_user.id)
    
    # Chiedi posizione o cerca (senza mostra tutti per evitare troppi pulsanti)
    keyboard = [
        [InlineKeyboardButton("📱 Condividi posizione GPS", callback_data="chiedi_gps")],
        [InlineKeyboardButton("🔍 Cerca per nome/indirizzo", callback_data="cerca_appartamento")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = ("📍 *Come vuoi selezionare l'appartamento?*\n\n"
            "• Usa il GPS per vedere quelli vicini (300 m)\n"
            "• Cerca per nome o indirizzo")
    
    if query:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    return SELEZIONE_IMMOBILE


async def mostra_appartamenti(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                               user_location: Optional[tuple] = None):
    """Mostra lista appartamenti (opzionalmente filtrati per distanza con Google Maps API)"""
    query = update.callback_query
    if query:
        await query.answer()
    
    appartamenti = db.get_all_appartamenti()
    
    # Arricchisci appartamenti con geocoding se mancano coordinate
    from .google_maps_helper import enrich_appartamenti_with_geocoding, get_distance_matrix
    from .config import GOOGLE_MAPS_API_KEY
    
    # Se Google Maps è configurato, usa geocoding per indirizzi senza coordinate
    if GOOGLE_MAPS_API_KEY:
        appartamenti = enrich_appartamenti_with_geocoding(appartamenti)
    
    # Se abbiamo posizione utente, calcola distanze
    appartamenti_con_distanza = []
    
    for app in appartamenti:
        app_data = dict(app)
        
        if user_location and app.get('coordinate'):
            # Parse coordinate appartamento
            coords = parse_coordinate(app['coordinate'])
            if coords:
                app_lat, app_lon = coords
                user_lat, user_lon = user_location
                
                # Usa Haversine per distanza veloce
                distanza = calcola_distanza_haversine(user_lat, user_lon, app_lat, app_lon)
                app_data['distanza'] = distanza
            else:
                app_data['distanza'] = None
        else:
            app_data['distanza'] = None
        
        appartamenti_con_distanza.append(app_data)
    
    # Ordina per distanza se disponibile
    if user_location:
        appartamenti_con_distanza.sort(key=lambda x: x['distanza'] if x['distanza'] is not None else float('inf'))
    
    # Crea keyboard - se GPS attivo, mostra solo quelli entro 300m
    keyboard = []
    
    if user_location:
        # Filtra solo appartamenti entro 300m
        text = "📍 *Appartamenti vicini (entro 300 m):*\n\n"
        
        for app in appartamenti_con_distanza[:20]:
            if app['distanza'] is not None and app['distanza'] <= GPS_TOLERANCE_METERS:
                dist_str = format_distanza(app['distanza'])
                label = f"📍 {app['nome']} ({dist_str})"
                keyboard.append([
                    InlineKeyboardButton(label, callback_data=f"app_{app['id']}")
                ])
        
        if not keyboard:
            # Nessun appartamento vicino - offri ricerca
            keyboard = [
                [InlineKeyboardButton("🔍 Cerca appartamento", callback_data="cerca_appartamento")]
            ]
            text = "😕 *Nessun appartamento trovato entro 300 m*\n\nUsa la ricerca per trovare l'appartamento:"
        else:
            keyboard.append([InlineKeyboardButton("🔍 Cerca", callback_data="cerca_appartamento")])
    else:
        # Senza GPS, mostra tutti (questo caso non dovrebbe più verificarsi)
        text = "📍 *Seleziona l'appartamento:*\n\n"
        
        for app in appartamenti_con_distanza:
            label = f"🏠 {app['nome']}"
            keyboard.append([
                InlineKeyboardButton(label, callback_data=f"app_{app['id']}")
            ])
    
    keyboard.append([InlineKeyboardButton("« Indietro", callback_data="back_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    return SELEZIONE_IMMOBILE


async def chiedi_posizione_gps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chiede all'utente di condividere la posizione"""
    query = update.callback_query
    await query.answer()
    
    # Keyboard con bottone di condivisione posizione
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("📍 Condividi posizione", request_location=True)]],
        one_time_keyboard=True,
        resize_keyboard=True
    )
    
    await query.edit_message_text(
        "📍 Condividi la tua posizione GPS usando il bottone qui sotto:",
        parse_mode='Markdown'
    )
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="👇 Clicca qui:",
        reply_markup=keyboard
    )
    
    return SELEZIONE_IMMOBILE


async def ricevi_posizione(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Riceve posizione GPS e mostra appartamenti vicini"""
    location = update.message.location
    user_location = (location.latitude, location.longitude)
    
    # Salva posizione nel context per uso successivo
    context.user_data['last_location'] = user_location
    
    # Ripristina la tastiera del menu principale (sostituisce quella GPS)
    await update.message.reply_text(
        "✅ Posizione ricevuta! Cerco appartamenti vicini...",
        reply_markup=get_main_keyboard(update.effective_user.id)
    )
    
    # Verifica se è per allegato
    if context.user_data.get('waiting_location_for') == 'allegato':
        context.user_data.pop('waiting_location_for', None)
        await mostra_appartamenti_per_allegato_gps(update, context, user_location)
        return ConversationHandler.END
    
    return await mostra_appartamenti(update, context, user_location)


async def appartamento_selezionato(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce selezione appartamento e chiede video ingresso"""
    query = update.callback_query
    await query.answer()
    
    # Estrai ID appartamento da query.data o da context (per ricerca)
    if 'selected_app_id' in context.user_data:
        app_id = context.user_data.pop('selected_app_id')
    else:
        app_id = int(query.data.split('_')[1])
    
    appartamento = db.get_appartamento(app_id)
    
    if not appartamento:
        await query.edit_message_text("❌ Appartamento non trovato")
        return ConversationHandler.END
    
    # Salva nel context
    context.user_data['appartamento_selezionato'] = appartamento
    
    # Chiedi video ingresso
    text = f"🏠 *{appartamento['nome']}*\n"
    text += f"📍 {appartamento['indirizzo']}\n\n"
    text += "📹 *Registra video di INGRESSO:*\n\n"
    text += "_Puoi registrare il video direttamente dall'app\n"
    text += "o allegare un video già esistente._"
    
    keyboard = [[InlineKeyboardButton("« Cambia appartamento", callback_data="mostra_tutti")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    return VIDEO_INGRESSO


# ==================== VIDEO INGRESSO ====================

async def ricevi_video_ingresso(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Riceve video di ingresso e crea turno"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    appartamento = context.user_data.get('appartamento_selezionato')
    
    if not appartamento:
        await update.message.reply_text(
            "❌ Errore: nessun appartamento selezionato",
            reply_markup=get_main_keyboard(user_id)
        )
        return ConversationHandler.END
    
    # Verifica che sia un video
    if not update.message.video and not (update.message.document and update.message.document.mime_type and 'video' in update.message.document.mime_type):
        await update.message.reply_text(
            "❌ *Devi inviare un VIDEO per iniziare il turno!*\n\n"
            "📹 Registra un video dell'appartamento all'ingresso.",
            parse_mode='Markdown'
        )
        return VIDEO_INGRESSO
    
    try:
        # Scarica e salva video
        loading_msg = await update.message.reply_text("⏳ Sto salvando il video...")
        
        video_path, video_file_id, timestamp = await download_and_save_video(
            update, context,
            user['nome'], user['cognome'],
            appartamento['nome'],
            'ingresso'
        )
        
        # Cancella messaggio di caricamento
        try:
            await loading_msg.delete()
        except:
            pass
        
        # Crea turno nel database (con gestione turno doppio)
        try:
            turno_id = db.create_turno(
                user_id=user_id,
                appartamento_id=appartamento['id'],
                video_path=video_path,
                video_file_id=video_file_id,
                timestamp=timestamp
            )
            
            if turno_id == 0:
                await update.message.reply_text(
                    "❌ Errore durante la creazione del turno. Riprova.",
                    parse_mode='Markdown'
                )
                return ConversationHandler.END
                
        except ValueError as e:
            # Turno già aperto
            await update.message.reply_text(
                f"❌ {str(e)}\n\n"
                "Finisci il turno in corso prima di iniziarne uno nuovo.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        # Salva nel context
        context.user_data['turno_id'] = turno_id
        
        # Messaggio conferma con tastiera persistente
        text = "✅ *Turno iniziato!*\n\n"
        text += f"🏠 {appartamento['nome']}\n"
        text += f"⏰ Ingresso: {format_ora(timestamp)}\n\n"
        text += "Buon lavoro! 💪\n"
        text += "Usa i pulsanti qui sotto 👇"
        
        # Tastiera persistente
        keyboard = [
            [KeyboardButton("🏠 Inizia Appartamento")],
            [KeyboardButton("✅ Finischi Appartamento")],
            [KeyboardButton("🧹 Manca Materiale Pulizie")],
            [KeyboardButton("🏠 Manca Qualcosa Appartamento")],
            [KeyboardButton("📎 Allega Liberamente")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
        # Notifica admin
        if NOTIFICHE_ADMIN_ENABLED and ADMIN_TELEGRAM_ID:
            await notifica_admin(
                context,
                f"🎥 *{user['nome']} {user['cognome']}* ha iniziato turno\n"
                f"🏠 {appartamento['nome']}\n"
                f"⏰ {format_ora(timestamp)}"
            )
        
        logger.info(f"Turno {turno_id} iniziato: {user['nome']} @ {appartamento['nome']}")
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Errore video ingresso: {e}")
        await update.message.reply_text(
            f"❌ Errore durante il salvataggio del video:\n{str(e)}\n\n"
            "Riprova con 🏠 Inizia Appartamento"
        )
        return ConversationHandler.END


# ==================== VIDEO USCITA ====================

async def termina_turno(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chiede video di uscita per terminare turno"""
    query = update.callback_query
    await query.answer()
    
    # Estrai turno_id
    turno_id = int(query.data.split('_')[1])
    turno = db.get_turno_in_corso(update.effective_user.id)
    
    if not turno or turno['id'] != turno_id:
        await query.edit_message_text("❌ Turno non trovato o già completato")
        return ConversationHandler.END
    
    # Salva nel context
    context.user_data['turno_da_completare'] = turno
    
    text = f"🏠 *{turno['appartamento_nome']}*\n"
    
    ts_ingresso = datetime.fromisoformat(turno['timestamp_ingresso'])
    text += f"⏰ Ingresso: {format_ora(ts_ingresso)}\n\n"
    text += "📹 *Registra video di USCITA:*"
    
    await query.edit_message_text(text, parse_mode='Markdown')
    
    return VIDEO_USCITA


async def ricevi_video_uscita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Riceve video di uscita e completa turno"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    # Verifica che sia un video
    if not update.message.video and not (update.message.document and update.message.document.mime_type and 'video' in update.message.document.mime_type):
        await update.message.reply_text(
            "❌ *Devi inviare un VIDEO per completare il turno!*\n\n"
            "📹 Registra un video dell'appartamento all'uscita.",
            parse_mode='Markdown'
        )
        return VIDEO_USCITA
    
    # Prendi turno in corso
    turno = db.get_turno_in_corso(user_id)
    
    if not turno:
        await update.message.reply_text(
            "❌ *Non hai turni in corso!*\n\n"
            "Prima devi iniziare un turno con '🏠 Inizia Appartamento'",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard(user_id)
        )
        return ConversationHandler.END
    
    try:
        # Scarica e salva video
        loading_msg = await update.message.reply_text("⏳ Sto salvando il video...")
        
        video_path, video_file_id, timestamp = await download_and_save_video(
            update, context,
            user['nome'], user['cognome'],
            turno['appartamento_nome'],
            'uscita'
        )
        
        # Cancella messaggio di caricamento
        try:
            await loading_msg.delete()
        except:
            pass
        
        # Completa turno nel database
        ore_lavorate = db.complete_turno(
            turno_id=turno['id'],
            video_path=video_path,
            video_file_id=video_file_id,
            timestamp=timestamp
        )
        
        # Parse timestamp ingresso dal turno
        from datetime import datetime
        ts_ingresso = datetime.fromisoformat(turno['timestamp_ingresso']) if isinstance(turno['timestamp_ingresso'], str) else turno['timestamp_ingresso']
        
        # Messaggio conferma con tastiera persistente
        text = "✅ *Turno completato!*\n\n"
        text += f"🏠 {turno['appartamento_nome']}\n"
        text += f"⏰ Ingresso: {format_ora(ts_ingresso)}\n"
        text += f"⏰ Uscita:   {format_ora(timestamp)}\n"
        text += f"⏱️  Totale:   *{format_ore(ore_lavorate)}*\n\n"
        text += "Ottimo lavoro! 👏"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
        # Notifica admin
        if NOTIFICHE_ADMIN_ENABLED and ADMIN_TELEGRAM_ID:
            await notifica_admin(
                context,
                f"✅ *{user['nome']} {user['cognome']}* ha completato turno\n"
                f"🏠 {turno['appartamento_nome']}\n"
                f"⏱️  {format_ore(ore_lavorate)}"
            )
        
        logger.info(f"Turno {turno['id']} completato: {ore_lavorate:.2f}h")
        
        # Salva info per eventuali allegati
        context.user_data['ultimo_turno_id'] = turno['id']
        context.user_data['ultimo_appartamento'] = turno['appartamento_nome']
        
        # Torna al menu principale
        user_data = db.get_user(user_id)
        await show_main_menu(update, context, user_data)
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Errore video uscita: {e}")
        await update.message.reply_text(
            f"❌ Errore durante il salvataggio del video:\n{str(e)}\n\n"
            "Riprova con /start"
        )
        return ConversationHandler.END


# ==================== SEGNALAZIONE PRODOTTI ====================

async def segnala_prodotti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chiede lista prodotti mancanti - sempre disponibile anche senza turno"""
    user_id = update.effective_user.id
    query = update.callback_query
    
    # Da callback con turno_id (es: segnala_123)
    if query and query.data.startswith('segnala_') and query.data.split('_')[1].isdigit():
        await query.answer()
        turno_id = int(query.data.split('_')[1])
        context.user_data['turno_segnalazione'] = turno_id
        
        await query.edit_message_text(
            "📦 *Cosa manca?*\n\n"
            "Scrivi l'elenco dei prodotti mancanti:\n"
            "_(Es: Detersivo bagno, 2 spugne, ammorbidente)_",
            parse_mode='Markdown'
        )
        return SEGNALA_PRODOTTI
    
    # Da pulsante - controlla se ha turno aperto
    turno = db.get_turno_in_corso(user_id)
    
    if turno:
        # Ha turno aperto - usa quello
        context.user_data['turno_segnalazione'] = turno['id']
        context.user_data['appartamento_segnalazione'] = turno['appartamento_id']
        
        await update.message.reply_text(
            f"📦 *Cosa manca?*\n\n"
            f"🏠 Appartamento: *{turno['appartamento_nome']}*\n\n"
            f"Scrivi l'elenco dei prodotti mancanti:\n"
            f"_(Es: Detersivo bagno, 2 spugne, ammorbidente)_",
            parse_mode='Markdown'
        )
    else:
        # NO turno - usa GPS se già disponibile, altrimenti chiedi
        last_location = context.user_data.get('last_location')
        
        if last_location:
            # Riusa GPS già fornito
            await mostra_appartamenti_per_segnalazione(update, context, last_location)
        else:
            # Chiedi GPS o ricerca (senza mostra tutti)
            keyboard = [
                [InlineKeyboardButton("📱 Condividi posizione GPS", callback_data="segnala_chiedi_gps")],
                [InlineKeyboardButton("🔍 Cerca per nome/indirizzo", callback_data="segnala_cerca_appartamento")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "📦 *Cosa manca?*\n\n"
                "📍 *Come vuoi selezionare l'appartamento?*\n\n"
                "• Usa il GPS per vedere quelli vicini (300 m)\n"
                "• Cerca per nome o indirizzo",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    return SEGNALA_PRODOTTI


async def mostra_appartamenti_per_segnalazione(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                                user_location: Optional[tuple] = None):
    """Mostra appartamenti per segnalazione prodotti (con o senza GPS)"""
    query = update.callback_query
    message = update.message
    
    if query:
        await query.answer()
    
    appartamenti = db.get_all_appartamenti()
    
    # Arricchisci con geocoding se necessario
    from .google_maps_helper import enrich_appartamenti_with_geocoding
    from .config import GOOGLE_MAPS_API_KEY
    
    if GOOGLE_MAPS_API_KEY:
        appartamenti = enrich_appartamenti_with_geocoding(appartamenti)
    
    # Calcola distanze se abbiamo GPS
    appartamenti_con_distanza = []
    
    for app in appartamenti:
        app_data = dict(app)
        
        if user_location and app.get('coordinate'):
            coords = parse_coordinate(app['coordinate'])
            if coords:
                app_lat, app_lon = coords
                user_lat, user_lon = user_location
                distanza = calcola_distanza_haversine(user_lat, user_lon, app_lat, app_lon)
                app_data['distanza'] = distanza
            else:
                app_data['distanza'] = None
        else:
            app_data['distanza'] = None
        
        appartamenti_con_distanza.append(app_data)
    
    # Ordina per distanza
    if user_location:
        appartamenti_con_distanza.sort(key=lambda x: x['distanza'] if x['distanza'] is not None else float('inf'))
    
    # Crea keyboard - se GPS attivo, mostra solo quelli entro 300m
    keyboard = []
    
    if user_location:
        text = "📦 *Cosa manca?*\n\n📍 *Appartamenti vicini (entro 300 m):*\n\n"
        
        for app in appartamenti_con_distanza[:20]:
            if app['distanza'] is not None and app['distanza'] <= GPS_TOLERANCE_METERS:
                dist_str = format_distanza(app['distanza'])
                label = f"📍 {app['nome']} ({dist_str})"
                keyboard.append([
                    InlineKeyboardButton(label, callback_data=f"segnala_app_{app['id']}")
                ])
        
        if not keyboard:
            keyboard = [
                [InlineKeyboardButton("🔍 Cerca appartamento", callback_data="segnala_cerca_appartamento")]
            ]
            text = "📦 *Cosa manca?*\n\n😕 *Nessun appartamento trovato entro 300 m*\n\nUsa la ricerca:"
        else:
            keyboard.append([InlineKeyboardButton("🔍 Cerca", callback_data="segnala_cerca_appartamento")])
    else:
        text = "📦 *Cosa manca?*\n\n📍 *Seleziona l'appartamento:*\n\n"
        
        for app in appartamenti_con_distanza:
            label = f"🏠 {app['nome']}"
            keyboard.append([
                InlineKeyboardButton(label, callback_data=f"segnala_app_{app['id']}")
            ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    elif message:
        await message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    return SEGNALA_PRODOTTI


async def segnala_chiedi_gps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chiede GPS per segnalazione prodotti"""
    query = update.callback_query
    await query.answer()
    
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("📍 Condividi posizione", request_location=True)]],
        one_time_keyboard=True,
        resize_keyboard=True
    )
    
    await query.edit_message_text(
        "📍 Condividi la tua posizione GPS usando il bottone qui sotto:",
        parse_mode='Markdown'
    )
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="👇 Clicca qui:",
        reply_markup=keyboard
    )
    
    context.user_data['segnala_attende_gps'] = True
    
    return SEGNALA_PRODOTTI


async def segnala_ricevi_gps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Riceve GPS per segnalazione e mostra appartamenti"""
    location = update.message.location
    user_location = (location.latitude, location.longitude)
    
    # Salva per usi futuri
    context.user_data['last_location'] = user_location
    context.user_data.pop('segnala_attende_gps', None)
    
    # Ripristina la tastiera del menu principale (sostituisce quella GPS)
    await update.message.reply_text(
        "✅ Posizione ricevuta! Cerco appartamenti vicini...",
        reply_markup=get_main_keyboard(update.effective_user.id)
    )
    
    await mostra_appartamenti_per_segnalazione(update, context, user_location)
    
    return SEGNALA_PRODOTTI


async def ricevi_segnalazione(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Riceve segnalazione prodotti e notifica admin"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    query = update.callback_query
    message = update.message
    
    # Gestione GPS per segnalazione
    if message and message.location and context.user_data.get('segnala_attende_gps'):
        return await segnala_ricevi_gps(update, context)
    
    # Gestione callback GPS
    if query and query.data == 'segnala_chiedi_gps':
        return await segnala_chiedi_gps(update, context)
    
    # Mostra tutti (senza GPS)
    if query and query.data == 'segnala_mostra_tutti':
        await query.answer()
        return await mostra_appartamenti_per_segnalazione(update, context, None)
    
    # Se clicca su appartamento (senza turno)
    if query and query.data.startswith('segnala_app_'):
        await query.answer()
        app_id = int(query.data.split('_')[2])
        appartamento = db.get_appartamento(app_id)
        
        context.user_data['appartamento_segnalazione'] = app_id
        
        await query.edit_message_text(
            f"📦 *Cosa manca?*\n\n"
            f"🏠 {appartamento['nome']}\n\n"
            f"Scrivi l'elenco dei prodotti mancanti:",
            parse_mode='Markdown'
        )
        return SEGNALA_PRODOTTI
    
    # Riceve testo segnalazione
    turno_id = context.user_data.get('turno_segnalazione')
    appartamento_id = context.user_data.get('appartamento_segnalazione')
    descrizione = update.message.text.strip()
    
    # Usa turno se disponibile, altrimenti appartamento selezionato
    turno = db.get_turno_in_corso(user_id)
    
    if turno:
        appartamento_id = turno['appartamento_id']
        appartamento_nome = turno['appartamento_nome']
    elif appartamento_id:
        appartamento = db.get_appartamento(appartamento_id)
        appartamento_nome = appartamento['nome']
    else:
        await update.message.reply_text(
            "❌ Errore: appartamento non trovato",
            reply_markup=get_main_keyboard(user_id)
        )
        return ConversationHandler.END
    
    # Crea richiesta (con gestione errori di validazione)
    try:
        richiesta_id = db.create_richiesta(
            user_id=user_id,
            appartamento_id=appartamento_id,
            descrizione=descrizione,
            turno_id=turno_id
        )
        
        if richiesta_id == 0:
            await update.message.reply_text(
                "❌ Errore durante la creazione della richiesta. Riprova.",
                parse_mode='Markdown',
                reply_markup=get_main_keyboard(user_id)
            )
            return ConversationHandler.END
    
    except ValueError as e:
        # Errori di validazione (rate limit, descrizione corta)
        await update.message.reply_text(str(e), parse_mode='Markdown')
        return SEGNALA_PRODOTTI
    
    await update.message.reply_text(
        "✅ *Segnalazione inviata!*\n\n"
        "L'amministratore riceverà la richiesta a breve.",
        parse_mode='Markdown'
    )
    
    # Notifica admin con bottone e salva message_id
    if NOTIFICHE_ADMIN_ENABLED and ADMIN_TELEGRAM_ID:
        keyboard = [[
            InlineKeyboardButton("✅ Segna come completato", callback_data=f"completa_{richiesta_id}")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        admin_message = await context.bot.send_message(
            chat_id=ADMIN_TELEGRAM_ID,
            text=f"⚠️ *NUOVA RICHIESTA PRODOTTI*\n\n"
                 f"👤 {user['nome']} {user['cognome']}\n"
                 f"🏠 {appartamento_nome}\n"
                 f"📦 {descrizione}\n"
                 f"⏰ {format_ora(datetime.now())}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # Aggiorna richiesta con message_id per edit successivo
        db.update_richiesta_message_id(richiesta_id, admin_message.message_id)
    
    logger.info(f"Richiesta prodotti {richiesta_id}: {user['nome']} @ {appartamento_nome}")
    
    # Torna al menu principale
    user_data = db.get_user(user_id)
    await show_main_menu(update, context, user_data)
    
    return ConversationHandler.END


# ==================== MANCA QUALCOSA MATERIALE PULIZIE ====================

async def manca_materiale_pulizie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inizia flusso per segnalazione materiale pulizie mancante"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    # Leggi prodotti da Excel
    materiali = db.get_materiali_pulizie()
    
    if not materiali:
        await update.message.reply_text(
            "❌ Nessun materiale disponibile.\n"
            "Contatta l'amministratore.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    # Reset selezione
    context.user_data['prodotti_selezionati_pulizie'] = []
    context.user_data['tipo_segnalazione'] = 'pulizie'
    
    # Crea keyboard con prodotti
    keyboard = []
    for i, mat in enumerate(materiali):
        keyboard.append([InlineKeyboardButton(f"⬜ {mat}", callback_data=f"matpul_{i}")])
    
    keyboard.append([InlineKeyboardButton("✏️ Scrivi manualmente", callback_data="matpul_altro")])
    keyboard.append([InlineKeyboardButton("✅ Conferma selezione", callback_data="matpul_conferma")])
    keyboard.append([InlineKeyboardButton("❌ Annulla", callback_data="matpul_annulla")])
    
    await update.message.reply_text(
        "🧹 *Manca Qualcosa - Materiale Pulizie*\n\n"
        "Seleziona i prodotti che ti servono:\n"
        "_(Premi sui prodotti per selezionarli)_",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    return MANCA_PULIZIE_SELEZIONE


async def manca_pulizie_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce callback per selezione materiale pulizie"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    materiali = db.get_materiali_pulizie()
    selezionati = context.user_data.get('prodotti_selezionati_pulizie', [])
    
    if data == "matpul_annulla":
        context.user_data.pop('prodotti_selezionati_pulizie', None)
        context.user_data.pop('tipo_segnalazione', None)
        await query.edit_message_text("❌ Operazione annullata")
        return ConversationHandler.END
    
    if data == "matpul_altro":
        await query.edit_message_text(
            "✏️ *Scrivi manualmente cosa ti serve:*\n\n"
            "_Es: Straccio pavimenti, panno microfibra..._",
            parse_mode='Markdown'
        )
        return MANCA_PULIZIE_ALTRO
    
    if data == "matpul_conferma":
        if not selezionati:
            await query.answer("⚠️ Seleziona almeno un prodotto!", show_alert=True)
            return MANCA_PULIZIE_SELEZIONE
        
        # Vai a scelta appartamento per consegna
        context.user_data['prodotti_testo_pulizie'] = ", ".join(selezionati)
        return await manca_pulizie_scegli_appartamento(update, context)
    
    if data.startswith("matpul_"):
        try:
            idx = int(data.split('_')[1])
            mat = materiali[idx]
            
            if mat in selezionati:
                selezionati.remove(mat)
            else:
                selezionati.append(mat)
            
            context.user_data['prodotti_selezionati_pulizie'] = selezionati
            
            # Aggiorna keyboard
            keyboard = []
            for i, m in enumerate(materiali):
                if m in selezionati:
                    keyboard.append([InlineKeyboardButton(f"✅ {m}", callback_data=f"matpul_{i}")])
                else:
                    keyboard.append([InlineKeyboardButton(f"⬜ {m}", callback_data=f"matpul_{i}")])
            
            keyboard.append([InlineKeyboardButton("✏️ Scrivi manualmente", callback_data="matpul_altro")])
            keyboard.append([InlineKeyboardButton("✅ Conferma selezione", callback_data="matpul_conferma")])
            keyboard.append([InlineKeyboardButton("❌ Annulla", callback_data="matpul_annulla")])
            
            sel_text = "\n".join([f"• {s}" for s in selezionati]) if selezionati else "_Nessuna selezione_"
            
            await query.edit_message_text(
                f"🧹 *Manca Qualcosa - Materiale Pulizie*\n\n"
                f"*Selezionati:*\n{sel_text}\n\n"
                f"_(Premi sui prodotti per selezionarli)_",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            return MANCA_PULIZIE_SELEZIONE
        except:
            pass
    
    return MANCA_PULIZIE_SELEZIONE


async def manca_pulizie_testo_manuale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Riceve testo manuale per materiale pulizie"""
    testo = update.message.text.strip()
    
    if len(testo) < 3:
        await update.message.reply_text(
            "⚠️ Descrizione troppo corta. Riprova:",
            parse_mode='Markdown'
        )
        return MANCA_PULIZIE_ALTRO
    
    # Aggiungi a selezionati
    selezionati = context.user_data.get('prodotti_selezionati_pulizie', [])
    selezionati.append(f"📝 {testo}")
    context.user_data['prodotti_selezionati_pulizie'] = selezionati
    context.user_data['prodotti_testo_pulizie'] = ", ".join(selezionati)
    
    # Vai a scelta appartamento
    return await manca_pulizie_scegli_appartamento_msg(update, context)


async def manca_pulizie_scegli_appartamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra lista appartamenti per scegliere dove consegnare (da callback)"""
    query = update.callback_query
    
    # Pulsanti GPS e cerca
    keyboard = [
        [InlineKeyboardButton("📱 Condividi posizione GPS", callback_data="matpul_chiedi_gps")],
        [InlineKeyboardButton("🔍 Cerca appartamento", callback_data="matpul_cerca_app")]
    ]
    
    await query.edit_message_text(
        "📍 *Dove vuoi ricevere i materiali?*\n\n"
        "• Usa il GPS per vedere quelli vicini (300 m)\n"
        "• Cerca per nome o indirizzo",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    return MANCA_PULIZIE_APPARTAMENTO


async def manca_pulizie_scegli_appartamento_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra lista appartamenti per scegliere dove consegnare (da messaggio)"""
    # Pulsanti GPS e cerca
    keyboard = [
        [InlineKeyboardButton("📱 Condividi posizione GPS", callback_data="matpul_chiedi_gps")],
        [InlineKeyboardButton("🔍 Cerca appartamento", callback_data="matpul_cerca_app")]
    ]
    
    await update.message.reply_text(
        "📍 *Dove vuoi ricevere i materiali?*\n\n"
        "• Usa il GPS per vedere quelli vicini (300 m)\n"
        "• Cerca per nome o indirizzo",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    return MANCA_PULIZIE_APPARTAMENTO


async def matpul_chiedi_gps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chiede all'utente di condividere la posizione per materiale pulizie"""
    query = update.callback_query
    await query.answer()
    
    # Keyboard con bottone di condivisione posizione
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("📍 Condividi posizione", request_location=True)]],
        one_time_keyboard=True,
        resize_keyboard=True
    )
    
    await query.edit_message_text(
        "📍 Condividi la tua posizione GPS usando il bottone qui sotto:",
        parse_mode='Markdown'
    )
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="👇 Clicca qui:",
        reply_markup=keyboard
    )
    
    context.user_data['waiting_location_for'] = 'matpul'
    return MANCA_PULIZIE_APPARTAMENTO


async def matpul_ricevi_posizione(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Riceve posizione GPS e mostra appartamenti vicini per materiale pulizie"""
    location = update.message.location
    user_location = (location.latitude, location.longitude)
    
    # Salva posizione nel context per uso successivo
    context.user_data['last_location'] = user_location
    context.user_data.pop('waiting_location_for', None)
    
    # Ripristina la tastiera del menu principale (sostituisce quella GPS)
    await update.message.reply_text(
        "✅ Posizione ricevuta! Cerco appartamenti vicini...",
        reply_markup=get_main_keyboard(update.effective_user.id)
    )
    
    appartamenti = db.get_all_appartamenti()
    
    # Calcola distanze
    appartamenti_con_distanza = []
    for app in appartamenti:
        app_data = dict(app)
        if app.get('coordinate'):
            coords = parse_coordinate(app['coordinate'])
            if coords:
                app_lat, app_lon = coords
                user_lat, user_lon = user_location
                distanza = calcola_distanza_haversine(user_lat, user_lon, app_lat, app_lon)
                app_data['distanza'] = distanza
            else:
                app_data['distanza'] = None
        else:
            app_data['distanza'] = None
        appartamenti_con_distanza.append(app_data)
    
    # Ordina per distanza
    appartamenti_con_distanza.sort(key=lambda x: x['distanza'] if x['distanza'] is not None else float('inf'))
    
    # Crea keyboard - solo quelli entro 300m
    keyboard = []
    for app in appartamenti_con_distanza[:20]:
        if app['distanza'] is not None and app['distanza'] <= GPS_TOLERANCE_METERS:
            dist_str = format_distanza(app['distanza'])
            label = f"📍 {app['nome']} ({dist_str})"
            keyboard.append([
                InlineKeyboardButton(label, callback_data=f"matpul_app_{app['id']}")
            ])
    
    if not keyboard:
        # Nessun appartamento vicino - offri ricerca
        keyboard = [
            [InlineKeyboardButton("🔍 Cerca appartamento", callback_data="matpul_cerca_app")]
        ]
        await update.message.reply_text(
            "😕 *Nessun appartamento trovato entro 300 m*\n\n"
            "Usa la ricerca per trovare l'appartamento:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        keyboard.append([InlineKeyboardButton("🔍 Cerca", callback_data="matpul_cerca_app")])
        await update.message.reply_text(
            "📍 *Appartamenti vicini (entro 300 m):*\n\n"
            "_Seleziona l'appartamento:_",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    return MANCA_PULIZIE_APPARTAMENTO


async def manca_pulizie_appartamento_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce callback selezione appartamento per pulizie"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "matpul_chiedi_gps":
        return await matpul_chiedi_gps(update, context)
    
    if data == "matpul_cerca_app":
        await query.edit_message_text(
            "🔍 *Cerca appartamento*\n\n"
            "Scrivi il nome dell'appartamento o parte dell'indirizzo:",
            parse_mode='Markdown'
        )
        context.user_data['ricerca_context'] = 'matpul'
        return RICERCA_APPARTAMENTO
    
    if data == "matpul_mostra_tutti_app":
        appartamenti = db.get_all_appartamenti()
        keyboard = []
        for app in appartamenti:
            keyboard.append([
                InlineKeyboardButton(f"🏠 {app['nome']}", callback_data=f"matpul_app_{app['id']}")
            ])
        keyboard.append([InlineKeyboardButton("🔍 Cerca", callback_data="matpul_cerca_app")])
        
        await query.edit_message_text(
            "📍 *Seleziona l'appartamento:*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return MANCA_PULIZIE_APPARTAMENTO
    
    if data.startswith("matpul_app_"):
        app_id = int(data.split('_')[2])
        appartamento = db.get_appartamento(app_id)
        
        if not appartamento:
            await query.edit_message_text("❌ Appartamento non trovato")
            return ConversationHandler.END
        
        context.user_data['appartamento_consegna_pulizie'] = appartamento
        
        await query.edit_message_text(
            f"📍 *Consegna a:* {appartamento['nome']}\n\n"
            f"📝 *Info aggiuntive sulla consegna:*\n"
            f"_(Es: 'Lunedì mattina', 'Entro venerdì', 'Lasciare in portineria'...)_\n\n"
            f"Scrivi le info oppure invia /skip per saltare:",
            parse_mode='Markdown'
        )
        return MANCA_PULIZIE_INFO_CONSEGNA
    
    return MANCA_PULIZIE_APPARTAMENTO


async def manca_pulizie_info_consegna(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Riceve info consegna e completa richiesta materiale pulizie"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    info_consegna = ""
    if update.message.text and not update.message.text.startswith('/skip'):
        info_consegna = update.message.text.strip()
    
    prodotti = context.user_data.get('prodotti_testo_pulizie', '')
    appartamento = context.user_data.get('appartamento_consegna_pulizie', {})
    
    if not appartamento:
        await update.message.reply_text(
            "❌ Errore: appartamento non trovato",
            reply_markup=get_main_keyboard(user_id)
        )
        return ConversationHandler.END
    
    try:
        richiesta_id = db.create_richiesta(
            user_id=user_id,
            appartamento_id=appartamento['id'],
            descrizione=prodotti,
            tipo_richiesta='pulizie',
            info_consegna=info_consegna
        )
        
        if richiesta_id == 0:
            await update.message.reply_text(
                "❌ Errore durante la creazione della richiesta",
                reply_markup=get_main_keyboard(user_id)
            )
            return ConversationHandler.END
            
    except ValueError as e:
        await update.message.reply_text(str(e), parse_mode='Markdown')
        return MANCA_PULIZIE_INFO_CONSEGNA
    
    await update.message.reply_text(
        "✅ *Richiesta materiale pulizie inviata!*\n\n"
        f"📦 *Prodotti:* {prodotti}\n"
        f"📍 *Consegna a:* {appartamento['nome']}\n"
        f"📝 *Info:* {info_consegna or 'Nessuna'}\n\n"
        "L'amministratore riceverà la richiesta.",
        parse_mode='Markdown'
    )
    
    # Notifica admin
    if NOTIFICHE_ADMIN_ENABLED and ADMIN_TELEGRAM_ID:
        keyboard = [[
            InlineKeyboardButton("✅ Completato", callback_data=f"completa_{richiesta_id}")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        admin_message = await context.bot.send_message(
            chat_id=ADMIN_TELEGRAM_ID,
            text=f"🧹 *RICHIESTA MATERIALE PULIZIE*\n\n"
                 f"👤 {user['nome']} {user['cognome']}\n"
                 f"📦 {prodotti}\n"
                 f"📍 Consegna: {appartamento['nome']}\n"
                 f"📝 Info: {info_consegna or 'Nessuna'}\n"
                 f"⏰ {format_ora(datetime.now())}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        db.update_richiesta_message_id(richiesta_id, admin_message.message_id)
    
    # Pulisci context
    context.user_data.pop('prodotti_selezionati_pulizie', None)
    context.user_data.pop('prodotti_testo_pulizie', None)
    context.user_data.pop('appartamento_consegna_pulizie', None)
    context.user_data.pop('tipo_segnalazione', None)
    
    logger.info(f"Richiesta materiale pulizie {richiesta_id}: {user['nome']} @ {appartamento['nome']}")
    
    # Mostra menu principale con keyboard
    await update.message.reply_text(
        "✅ Usa il menu qui sotto per continuare 👇",
        reply_markup=get_main_keyboard(user_id)
    )
    
    return ConversationHandler.END


# ==================== MANCA QUALCOSA APPARTAMENTO ====================

async def manca_appartamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inizia flusso per segnalazione materiale appartamento mancante (operazioni mensili)"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    # Reset
    context.user_data['tipo_segnalazione'] = 'appartamento'
    
    # Pulsanti GPS e cerca
    keyboard = [
        [InlineKeyboardButton("📱 Condividi posizione GPS", callback_data="matapp_chiedi_gps")],
        [InlineKeyboardButton("🔍 Cerca appartamento", callback_data="matapp_cerca_app")]
    ]
    
    await update.message.reply_text(
        "🏠 *Manca Qualcosa - Appartamento*\n\n"
        "• Usa il GPS per vedere quelli vicini (300 m)\n"
        "• Cerca per nome o indirizzo",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    return MANCA_APP_SELEZIONE


async def matapp_chiedi_gps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chiede all'utente di condividere la posizione per manca appartamento"""
    query = update.callback_query
    await query.answer()
    
    # Keyboard con bottone di condivisione posizione
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("📍 Condividi posizione", request_location=True)]],
        one_time_keyboard=True,
        resize_keyboard=True
    )
    
    await query.edit_message_text(
        "📍 Condividi la tua posizione GPS usando il bottone qui sotto:",
        parse_mode='Markdown'
    )
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="👇 Clicca qui:",
        reply_markup=keyboard
    )
    
    context.user_data['waiting_location_for'] = 'matapp'
    return MANCA_APP_SELEZIONE


async def matapp_ricevi_posizione(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Riceve posizione GPS e mostra appartamenti vicini per manca appartamento"""
    location = update.message.location
    user_location = (location.latitude, location.longitude)
    
    # Salva posizione nel context per uso successivo
    context.user_data['last_location'] = user_location
    context.user_data.pop('waiting_location_for', None)
    
    # Ripristina la tastiera del menu principale (sostituisce quella GPS)
    await update.message.reply_text(
        "✅ Posizione ricevuta! Cerco appartamenti vicini...",
        reply_markup=get_main_keyboard(update.effective_user.id)
    )
    
    appartamenti = db.get_all_appartamenti()
    
    # Calcola distanze
    appartamenti_con_distanza = []
    for app in appartamenti:
        app_data = dict(app)
        if app.get('coordinate'):
            coords = parse_coordinate(app['coordinate'])
            if coords:
                app_lat, app_lon = coords
                user_lat, user_lon = user_location
                distanza = calcola_distanza_haversine(user_lat, user_lon, app_lat, app_lon)
                app_data['distanza'] = distanza
            else:
                app_data['distanza'] = None
        else:
            app_data['distanza'] = None
        appartamenti_con_distanza.append(app_data)
    
    # Ordina per distanza
    appartamenti_con_distanza.sort(key=lambda x: x['distanza'] if x['distanza'] is not None else float('inf'))
    
    # Crea keyboard - solo quelli entro 300m
    keyboard = []
    for app in appartamenti_con_distanza[:20]:
        if app['distanza'] is not None and app['distanza'] <= GPS_TOLERANCE_METERS:
            dist_str = format_distanza(app['distanza'])
            label = f"📍 {app['nome']} ({dist_str})"
            keyboard.append([
                InlineKeyboardButton(label, callback_data=f"matapp_app_{app['id']}")
            ])
    
    if not keyboard:
        # Nessun appartamento vicino - offri ricerca
        keyboard = [
            [InlineKeyboardButton("🔍 Cerca appartamento", callback_data="matapp_cerca_app")]
        ]
        await update.message.reply_text(
            "😕 *Nessun appartamento trovato entro 300 m*\n\n"
            "Usa la ricerca per trovare l'appartamento:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        keyboard.append([InlineKeyboardButton("🔍 Cerca", callback_data="matapp_cerca_app")])
        await update.message.reply_text(
            "📍 *Appartamenti vicini (entro 300 m):*\n\n"
            "_Seleziona l'appartamento:_",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    return MANCA_APP_SELEZIONE


async def manca_app_selezione_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce selezione appartamento per manca appartamento"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "matapp_chiedi_gps":
        return await matapp_chiedi_gps(update, context)
    
    if data == "matapp_cerca_app":
        await query.edit_message_text(
            "🔍 *Cerca appartamento*\n\n"
            "Scrivi il nome dell'appartamento o parte dell'indirizzo:",
            parse_mode='Markdown'
        )
        context.user_data['ricerca_context'] = 'matapp'
        return RICERCA_APPARTAMENTO
    
    if data == "matapp_mostra_tutti_app":
        appartamenti = db.get_all_appartamenti()
        keyboard = []
        for app in appartamenti:
            keyboard.append([
                InlineKeyboardButton(f"🏠 {app['nome']}", callback_data=f"matapp_app_{app['id']}")
            ])
        keyboard.append([InlineKeyboardButton("🔍 Cerca", callback_data="matapp_cerca_app")])
        
        await query.edit_message_text(
            "🏠 *Seleziona l'appartamento:*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return MANCA_APP_SELEZIONE
    
    if data.startswith("matapp_app_"):
        app_id = int(data.split('_')[2])
        appartamento = db.get_appartamento(app_id)
        
        if not appartamento:
            await query.edit_message_text("❌ Appartamento non trovato")
            return ConversationHandler.END
        
        context.user_data['appartamento_manca_app'] = appartamento
        context.user_data['prodotti_selezionati_app'] = []
        
        # Mostra prodotti appartamento
        materiali = db.get_materiali_appartamento()
        
        keyboard = []
        for i, mat in enumerate(materiali):
            keyboard.append([InlineKeyboardButton(f"⬜ {mat}", callback_data=f"matapp_prod_{i}")])
        
        keyboard.append([InlineKeyboardButton("✏️ Scrivi manualmente", callback_data="matapp_altro")])
        keyboard.append([InlineKeyboardButton("✅ Conferma selezione", callback_data="matapp_conferma")])
        keyboard.append([InlineKeyboardButton("❌ Annulla", callback_data="matapp_annulla")])
        
        await query.edit_message_text(
            f"🏠 *Appartamento:* {appartamento['nome']}\n\n"
            f"Seleziona cosa manca:\n"
            f"_(Operazioni mensili)_",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return MANCA_APP_PRODOTTI
    
    return MANCA_APP_SELEZIONE


async def manca_app_prodotti_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce callback per selezione prodotti appartamento"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    materiali = db.get_materiali_appartamento()
    selezionati = context.user_data.get('prodotti_selezionati_app', [])
    appartamento = context.user_data.get('appartamento_manca_app', {})
    
    if data == "matapp_annulla":
        context.user_data.pop('prodotti_selezionati_app', None)
        context.user_data.pop('appartamento_manca_app', None)
        context.user_data.pop('tipo_segnalazione', None)
        await query.edit_message_text("❌ Operazione annullata")
        return ConversationHandler.END
    
    if data == "matapp_altro":
        await query.edit_message_text(
            "✏️ *Scrivi manualmente cosa manca:*\n\n"
            "_Es: Coperte extra, Cuscino, Tende..._",
            parse_mode='Markdown'
        )
        return MANCA_APP_ALTRO
    
    if data == "matapp_conferma":
        if not selezionati:
            await query.answer("⚠️ Seleziona almeno un prodotto!", show_alert=True)
            return MANCA_APP_PRODOTTI
        
        # Completa richiesta
        return await manca_app_completa(update, context)
    
    if data.startswith("matapp_prod_"):
        try:
            idx = int(data.split('_')[2])
            mat = materiali[idx]
            
            if mat in selezionati:
                selezionati.remove(mat)
            else:
                selezionati.append(mat)
            
            context.user_data['prodotti_selezionati_app'] = selezionati
            
            # Aggiorna keyboard
            keyboard = []
            for i, m in enumerate(materiali):
                if m in selezionati:
                    keyboard.append([InlineKeyboardButton(f"✅ {m}", callback_data=f"matapp_prod_{i}")])
                else:
                    keyboard.append([InlineKeyboardButton(f"⬜ {m}", callback_data=f"matapp_prod_{i}")])
            
            keyboard.append([InlineKeyboardButton("✏️ Scrivi manualmente", callback_data="matapp_altro")])
            keyboard.append([InlineKeyboardButton("✅ Conferma selezione", callback_data="matapp_conferma")])
            keyboard.append([InlineKeyboardButton("❌ Annulla", callback_data="matapp_annulla")])
            
            sel_text = "\n".join([f"• {s}" for s in selezionati]) if selezionati else "_Nessuna selezione_"
            
            await query.edit_message_text(
                f"🏠 *Appartamento:* {appartamento['nome']}\n\n"
                f"*Selezionati:*\n{sel_text}\n\n"
                f"_(Premi sui prodotti per selezionarli)_",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            return MANCA_APP_PRODOTTI
        except:
            pass
    
    return MANCA_APP_PRODOTTI


async def manca_app_testo_manuale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Riceve testo manuale per materiale appartamento"""
    testo = update.message.text.strip()
    
    if len(testo) < 3:
        await update.message.reply_text(
            "⚠️ Descrizione troppo corta. Riprova:",
            parse_mode='Markdown'
        )
        return MANCA_APP_ALTRO
    
    # Aggiungi a selezionati
    selezionati = context.user_data.get('prodotti_selezionati_app', [])
    selezionati.append(f"📝 {testo}")
    context.user_data['prodotti_selezionati_app'] = selezionati
    
    # Completa richiesta
    return await manca_app_completa_msg(update, context)


async def manca_app_completa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Completa richiesta manca appartamento (da callback)"""
    query = update.callback_query
    user_id = query.from_user.id
    user = db.get_user(user_id)
    
    selezionati = context.user_data.get('prodotti_selezionati_app', [])
    appartamento = context.user_data.get('appartamento_manca_app', {})
    prodotti = ", ".join(selezionati)
    
    try:
        richiesta_id = db.create_richiesta(
            user_id=user_id,
            appartamento_id=appartamento['id'],
            descrizione=prodotti,
            tipo_richiesta='appartamento'
        )
        
        if richiesta_id == 0:
            await query.edit_message_text("❌ Errore durante la creazione della richiesta")
            return ConversationHandler.END
            
    except ValueError as e:
        await query.edit_message_text(str(e), parse_mode='Markdown')
        return MANCA_APP_PRODOTTI
    
    await query.edit_message_text(
        "✅ *Richiesta materiale appartamento inviata!*\n\n"
        f"🏠 *Appartamento:* {appartamento['nome']}\n"
        f"📦 *Manca:* {prodotti}\n\n"
        "L'amministratore riceverà la richiesta.",
        parse_mode='Markdown'
    )
    
    # Notifica admin
    if NOTIFICHE_ADMIN_ENABLED and ADMIN_TELEGRAM_ID:
        keyboard = [[
            InlineKeyboardButton("✅ Completato", callback_data=f"completa_{richiesta_id}")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        admin_message = await context.bot.send_message(
            chat_id=ADMIN_TELEGRAM_ID,
            text=f"🏠 *MANCA QUALCOSA - APPARTAMENTO*\n\n"
                 f"👤 {user['nome']} {user['cognome']}\n"
                 f"🏠 {appartamento['nome']}\n"
                 f"📦 {prodotti}\n"
                 f"⏰ {format_ora(datetime.now())}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        db.update_richiesta_message_id(richiesta_id, admin_message.message_id)
    
    # Pulisci context
    context.user_data.pop('prodotti_selezionati_app', None)
    context.user_data.pop('appartamento_manca_app', None)
    context.user_data.pop('tipo_segnalazione', None)
    
    logger.info(f"Richiesta manca appartamento {richiesta_id}: {user['nome']} @ {appartamento['nome']}")
    
    return ConversationHandler.END


async def manca_app_completa_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Completa richiesta manca appartamento (da messaggio)"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    selezionati = context.user_data.get('prodotti_selezionati_app', [])
    appartamento = context.user_data.get('appartamento_manca_app', {})
    prodotti = ", ".join(selezionati)
    
    try:
        richiesta_id = db.create_richiesta(
            user_id=user_id,
            appartamento_id=appartamento['id'],
            descrizione=prodotti,
            tipo_richiesta='appartamento'
        )
        
        if richiesta_id == 0:
            await update.message.reply_text(
                "❌ Errore durante la creazione della richiesta",
                reply_markup=get_main_keyboard(user_id)
            )
            return ConversationHandler.END
            
    except ValueError as e:
        await update.message.reply_text(str(e), parse_mode='Markdown')
        return MANCA_APP_ALTRO
    
    await update.message.reply_text(
        "✅ *Richiesta materiale appartamento inviata!*\n\n"
        f"🏠 *Appartamento:* {appartamento['nome']}\n"
        f"📦 *Manca:* {prodotti}\n\n"
        "L'amministratore riceverà la richiesta.",
        parse_mode='Markdown'
    )
    
    # Notifica admin
    if NOTIFICHE_ADMIN_ENABLED and ADMIN_TELEGRAM_ID:
        keyboard = [[
            InlineKeyboardButton("✅ Completato", callback_data=f"completa_{richiesta_id}")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        admin_message = await context.bot.send_message(
            chat_id=ADMIN_TELEGRAM_ID,
            text=f"🏠 *MANCA QUALCOSA - APPARTAMENTO*\n\n"
                 f"👤 {user['nome']} {user['cognome']}\n"
                 f"🏠 {appartamento['nome']}\n"
                 f"📦 {prodotti}\n"
                 f"⏰ {format_ora(datetime.now())}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        db.update_richiesta_message_id(richiesta_id, admin_message.message_id)
    
    # Pulisci context
    context.user_data.pop('prodotti_selezionati_app', None)
    context.user_data.pop('appartamento_manca_app', None)
    context.user_data.pop('tipo_segnalazione', None)
    
    logger.info(f"Richiesta manca appartamento {richiesta_id}: {user['nome']} @ {appartamento['nome']}")
    
    return ConversationHandler.END


# ==================== ORE OGGI ====================

async def mostra_ore_oggi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra riepilogo ore lavorate oggi"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    oggi = datetime.now().date()
    
    # Ottieni turni di oggi
    turni = db.get_turni_by_user(user_id, oggi, oggi)
    
    if not turni:
        await query.edit_message_text(
            "📊 Nessun turno completato oggi.",
            parse_mode='Markdown'
        )
        return
    
    text = f"📊 *Ore lavorate oggi* ({oggi.strftime('%d/%m/%Y')})\n\n"
    
    ore_totali = 0
    
    for turno in turni:
        text += f"🏠 {turno['appartamento_nome']}\n"
        
        if turno['status'] == 'completato' and turno.get('ore_lavorate'):
            text += f"   ⏱️  {format_ore(turno['ore_lavorate'])}\n"
            ore_totali += turno['ore_lavorate']
        else:
            text += f"   ⏱️  _In corso..._\n"
        
        text += "\n"
    
    text += f"*Totale: {format_ore(ore_totali)}*"
    
    keyboard = [[InlineKeyboardButton("« Indietro", callback_data="back_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


# ==================== UTILITY ====================

async def notifica_admin(context: ContextTypes.DEFAULT_TYPE, messaggio: str, 
                         keyboard: InlineKeyboardMarkup = None):
    """Invia notifica all'amministratore"""
    if not ADMIN_TELEGRAM_ID:
        return
    
    try:
        await context.bot.send_message(
            chat_id=ADMIN_TELEGRAM_ID,
            text=messaggio,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Errore invio notifica admin: {e}")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Annulla conversazione"""
    await update.message.reply_text(
        "Operazione annullata. Usa /start per ricominciare."
    )
    context.user_data.clear()
    return ConversationHandler.END


# ==================== ALLEGATI LIBERI ====================

async def chiedi_allegati_liberi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Informa l'utente che può allegare liberamente senza entrare in uno stato specifico"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    text = "📎 *Allega Liberamente*\n\n"
    text += "Puoi inviare in qualsiasi momento:\n"
    text += "• 📷 Foto\n"
    text += "• 🎥 Video\n"
    text += "• 📝 Note di testo\n"
    text += "• 📄 Documenti\n\n"
    text += "_Invia semplicemente il file, verrà salvato automaticamente._"
    
    await update.message.reply_text(
        text, 
        parse_mode='Markdown',
        reply_markup=get_main_keyboard(update.effective_user.id)
    )
    
    # Non cambia stato - rimane dove si trova
    return ConversationHandler.END


async def ricevi_allegati_liberi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Riceve e salva allegati liberi - handler sempre attivo"""
    from pathlib import Path
    from . import allegati_handler as ah
    
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    # Verifica se ha appartamento attivo o chiedi quale
    appartamento = None
    
    # Prova a recuperare appartamento dal turno in corso
    turno_attivo = db.get_turno_in_corso(user_id)
    if turno_attivo:
        appartamento = db.get_appartamento(turno_attivo['appartamento_id'])
    
    # Se non ha turno attivo, DEVE scegliere appartamento
    if not appartamento:
        logger.info(f"Allegato libero senza turno attivo - chiedo appartamento a user {user_id}")
        
        # Solo GPS e ricerca - niente lista appartamenti iniziale
        keyboard = [
            [InlineKeyboardButton("📱 Condividi posizione GPS", callback_data="allega_chiedi_gps")],
            [InlineKeyboardButton("🔍 Cerca appartamento", callback_data="cerca_appartamento_allegato")]
        ]
        
        await update.message.reply_text(
            "📍 *Di quale appartamento si tratta?*\n\n"
            "L'allegato verrà salvato nella cartella dell'appartamento.\n\n"
            "• Usa il GPS per vedere quelli vicini (300 m)\n"
            "• Cerca per nome o indirizzo",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        # Salva allegato temporaneamente nel context
        context.user_data['allegato_pending'] = update.message
        logger.info(f"Allegato salvato in context: {type(update.message)}")
        return ConversationHandler.END
    
    try:
        allegato_info = ""
        file_path = None
        timestamp = datetime.now()
        
        if update.message.photo:
            file_path, _ = await ah.salva_foto(
                update, context, user['nome'], user['cognome'], appartamento['nome']
            )
            allegato_info = "📷 Foto ricevuta"
            
        elif update.message.video:
            file_path, _ = await ah.salva_video_allegato(
                update, context, user['nome'], user['cognome'], appartamento['nome']
            )
            allegato_info = "🎥 Video ricevuto"
            
        elif update.message.document:
            file_path, _ = await ah.salva_documento(
                update, context, user['nome'], user['cognome'], appartamento['nome']
            )
            allegato_info = f"📄 {update.message.document.file_name}"
            
        elif update.message.text:
            testo = update.message.text
            file_path = await ah.salva_nota(
                testo, user['nome'], user['cognome'], appartamento['nome']
            )
            allegato_info = "📝 Nota ricevuta"
        
        await update.message.reply_text(
            f"✅ {allegato_info}\n"
            f"🏠 {appartamento['nome']}\n"
            f"📁 Salvato in archivio organizzato"
        )
        
        if NOTIFICHE_ADMIN_ENABLED and ADMIN_TELEGRAM_ID and file_path:
            await notifica_admin(
                context,
                f"📎 *Allegato da {user['nome']} {user['cognome']}*\n\n"
                f"🏠 Appartamento: {appartamento['nome']}\n"
                f"{allegato_info}\n"
                f"📁 {file_path}"
            )
        
        logger.info(f"Allegato salvato: {file_path}")
        
    except Exception as e:
        logger.error(f"Errore allegato: {e}")
        await update.message.reply_text(f"❌ Errore: {e}")


async def scegli_appartamento_per_allegato(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra lista appartamenti per selezionare dove salvare l'allegato"""
    query = update.callback_query
    await query.answer()
    
    appartamenti = db.get_all_appartamenti()
    
    keyboard = []
    
    # Aggiungi pulsante ricerca
    keyboard.append([InlineKeyboardButton("🔍 Cerca per nome/indirizzo", callback_data="cerca_appartamento_allegato")])
    
    for app in appartamenti[:15]:  # Primi 15 per non sovraccaricare
        keyboard.append([
            InlineKeyboardButton(
                f"🏠 {app['nome']}", 
                callback_data=f"allega_app_{app['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("❌ Annulla", callback_data="annulla")])
    
    await query.edit_message_text(
        "📍 *Seleziona l'appartamento:*\n\n"
        "_L'allegato verrà salvato nella cartella di questo appartamento._\n\n"
        "💡 Usa la ricerca se hai molti appartamenti!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def appartamento_selezionato_per_allegato(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Salva allegato nell'appartamento selezionato"""
    query = update.callback_query
    await query.answer()
    
    # Estrai ID appartamento
    app_id = int(query.data.split('_')[2])
    appartamento = db.get_appartamento(app_id)
    
    if not appartamento:
        await query.edit_message_text("❌ Appartamento non trovato")
        return
    
    # Recupera allegato pendente
    pending_message = context.user_data.get('allegato_pending')
    if not pending_message:
        await query.edit_message_text("❌ Nessun allegato da salvare")
        return
    
    user_id = query.from_user.id
    user = db.get_user(user_id)
    
    from . import allegati_handler as ah
    
    try:
        allegato_info = ""
        file_path = None
        timestamp = datetime.now()
        
        if pending_message.photo:
            # Simula update per salva_foto
            temp_update = Update(update.update_id, message=pending_message)
            file_path, _ = await ah.salva_foto(
                temp_update, context, user['nome'], user['cognome'], appartamento['nome']
            )
            allegato_info = "📷 Foto ricevuta"
            
        elif pending_message.video:
            temp_update = Update(update.update_id, message=pending_message)
            file_path, _ = await ah.salva_video_allegato(
                temp_update, context, user['nome'], user['cognome'], appartamento['nome']
            )
            allegato_info = "🎥 Video ricevuto"
            
        elif pending_message.document:
            temp_update = Update(update.update_id, message=pending_message)
            file_path, _ = await ah.salva_documento(
                temp_update, context, user['nome'], user['cognome'], appartamento['nome']
            )
            allegato_info = f"📄 {pending_message.document.file_name}"
            
        elif pending_message.text:
            file_path = await ah.salva_nota(
                pending_message.text, user['nome'], user['cognome'], appartamento['nome']
            )
            allegato_info = "📝 Nota ricevuta"
        
        await query.edit_message_text(
            f"✅ {allegato_info}\n"
            f"🏠 {appartamento['nome']}\n"
            f"📁 Salvato in archivio organizzato"
        )
        
        # Rimuovi allegato pendente
        context.user_data.pop('allegato_pending', None)
        
        logger.info(f"Allegato salvato: {file_path}")
        
    except Exception as e:
        logger.error(f"Errore salvataggio allegato: {e}")
        await query.edit_message_text(f"❌ Errore: {e}")


# ==================== RICERCA APPARTAMENTI ====================

async def avvia_ricerca_appartamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Avvia modalità ricerca appartamento testuale"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🔍 *Cerca appartamento*\n\n"
        "Scrivi il nome dell'appartamento o parte dell'indirizzo.\n"
        "_Es: 'Villa Rosa', 'Via Roma', 'Milano'_\n\n"
        "Invierò la lista degli appartamenti che corrispondono alla tua ricerca.",
        parse_mode='Markdown'
    )
    
    # Salva contesto per sapere se è per turno o allegato
    context.user_data['ricerca_context'] = 'turno'  # default
    
    return RICERCA_APPARTAMENTO


async def ricerca_appartamento_testo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ricerca appartamenti per testo e mostra risultati come pulsanti"""
    testo_ricerca = update.message.text.strip().lower()
    
    if len(testo_ricerca) < 2:
        await update.message.reply_text(
            "⚠️ Inserisci almeno 2 caratteri per la ricerca",
            parse_mode='Markdown'
        )
        return RICERCA_APPARTAMENTO
    
    appartamenti = db.get_all_appartamenti()
    ricerca_context = context.user_data.get('ricerca_context', 'turno')
    
    # Filtra appartamenti che matchano la ricerca
    risultati = []
    for app in appartamenti:
        nome_lower = app['nome'].lower()
        indirizzo_lower = app['indirizzo'].lower()
        
        if testo_ricerca in nome_lower or testo_ricerca in indirizzo_lower:
            risultati.append(app)
    
    if not risultati:
        await update.message.reply_text(
            f"😕 Nessun appartamento trovato per: *{testo_ricerca}*\n\n"
            "Scrivi un altro nome o parte dell'indirizzo.\n"
            "_Oppure scrivi /annulla per annullare._",
            parse_mode='Markdown'
        )
        return RICERCA_APPARTAMENTO
    
    # Mostra risultati come pulsanti
    keyboard = []
    for app in risultati:
        if ricerca_context == 'allegato':
            keyboard.append([
                InlineKeyboardButton(
                    f"🏠 {app['nome']}",
                    callback_data=f"allega_app_{app['id']}"
                )
            ])
        elif ricerca_context == 'segnalazione':
            keyboard.append([
                InlineKeyboardButton(
                    f"🏠 {app['nome']}",
                    callback_data=f"segnala_app_{app['id']}"
                )
            ])
        elif ricerca_context == 'matpul':
            keyboard.append([
                InlineKeyboardButton(
                    f"🏠 {app['nome']}",
                    callback_data=f"matpul_app_{app['id']}"
                )
            ])
        elif ricerca_context == 'matapp':
            keyboard.append([
                InlineKeyboardButton(
                    f"🏠 {app['nome']}",
                    callback_data=f"matapp_app_{app['id']}"
                )
            ])
        else:
            keyboard.append([
                InlineKeyboardButton(
                    f"🏠 {app['nome']} - {app['indirizzo'][:30]}...",
                    callback_data=f"selapp_{app['id']}"
                )
            ])
    
    # Aggiungi pulsante per nuova ricerca
    keyboard.append([InlineKeyboardButton("🔍 Nuova ricerca", callback_data="cerca_appartamento")])
    
    if ricerca_context == 'allegato':
        next_state = ConversationHandler.END
    elif ricerca_context == 'segnalazione':
        next_state = SEGNALA_PRODOTTI
    elif ricerca_context == 'matpul':
        next_state = MANCA_PULIZIE_APPARTAMENTO
    elif ricerca_context == 'matapp':
        next_state = MANCA_APP_SELEZIONE
    else:
        next_state = SELEZIONE_IMMOBILE
    
    await update.message.reply_text(
        f"✅ Trovati *{len(risultati)}* appartamenti:\n\n"
        "_Seleziona quello desiderato:_",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    return next_state


async def avvia_ricerca_appartamento_allegato(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Avvia ricerca appartamento per allegati"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🔍 *Cerca appartamento*\n\n"
        "Scrivi il nome dell'appartamento o parte dell'indirizzo.\n"
        "_Es: 'Villa Rosa', 'Via Roma', 'Milano'_",
        parse_mode='Markdown'
    )
    
    context.user_data['ricerca_context'] = 'allegato'
    
    return RICERCA_APPARTAMENTO


async def avvia_ricerca_appartamento_segnalazione(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Avvia ricerca appartamento per segnalazioni"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🔍 *Cerca appartamento*\n\n"
        "Scrivi il nome dell'appartamento o parte dell'indirizzo.\n"
        "_Es: 'Villa Rosa', 'Via Roma', 'Milano'_",
        parse_mode='Markdown'
    )
    
    context.user_data['ricerca_context'] = 'segnalazione'
    
    return RICERCA_APPARTAMENTO


async def allega_chiedi_gps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chiede GPS per selezionare appartamento per allegato"""
    query = update.callback_query
    await query.answer()
    
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("📍 Condividi posizione", request_location=True)]],
        one_time_keyboard=True,
        resize_keyboard=True
    )
    
    await query.edit_message_text(
        "📍 *Condividi la tua posizione*\n\n"
        "Premi il pulsante qui sotto per condividere la tua posizione GPS.",
        parse_mode='Markdown'
    )
    
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="👇 Usa il pulsante qui sotto:",
        reply_markup=keyboard
    )
    
    # Imposta flag per gestire location
    context.user_data['waiting_location_for'] = 'allegato'
    
    return ConversationHandler.END


async def ricevi_location_per_allegato(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler globale per location quando si cerca appartamento (allegato, matpul, matapp)"""
    waiting_for = context.user_data.get('waiting_location_for')
    
    if waiting_for == 'allegato':
        location = update.message.location
        user_location = (location.latitude, location.longitude)
        
        context.user_data.pop('waiting_location_for', None)
        # Ripristina la tastiera del menu principale (sostituisce quella GPS)
        await update.message.reply_text(
            "✅ Posizione ricevuta! Cerco appartamenti vicini...",
            reply_markup=get_main_keyboard(update.effective_user.id)
        )
        await mostra_appartamenti_per_allegato_gps(update, context, user_location)
    
    elif waiting_for == 'matpul':
        return await matpul_ricevi_posizione(update, context)
    
    elif waiting_for == 'matapp':
        return await matapp_ricevi_posizione(update, context)
    
    # Se non è per nessuno dei contesti, ignora
    return


async def ricevi_testo_ricerca_allegato(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler globale per ricerca testo appartamento per allegato"""
    if context.user_data.get('ricerca_context') != 'allegato':
        return  # Non gestire se non è per allegato
    
    # Chiama la funzione di ricerca esistente
    await ricerca_appartamento_testo(update, context)


async def mostra_appartamenti_per_allegato_gps(update: Update, context: ContextTypes.DEFAULT_TYPE, user_location: tuple):
    """Mostra appartamenti vicini per allegato"""
    appartamenti = db.get_all_appartamenti()
    
    # Calcola distanze
    appartamenti_con_distanza = []
    for app in appartamenti:
        app_data = dict(app)
        if app.get('coordinate'):
            coords = parse_coordinate(app['coordinate'])
            if coords:
                app_lat, app_lon = coords
                user_lat, user_lon = user_location
                distanza = calcola_distanza_haversine(user_lat, user_lon, app_lat, app_lon)
                app_data['distanza'] = distanza
            else:
                app_data['distanza'] = None
        else:
            app_data['distanza'] = None
        appartamenti_con_distanza.append(app_data)
    
    # Ordina per distanza
    appartamenti_con_distanza.sort(key=lambda x: x['distanza'] if x['distanza'] is not None else float('inf'))
    
    # Crea keyboard - solo quelli entro 300m
    keyboard = []
    for app in appartamenti_con_distanza[:20]:
        if app['distanza'] is not None and app['distanza'] <= GPS_TOLERANCE_METERS:
            dist_str = format_distanza(app['distanza'])
            label = f"📍 {app['nome']} ({dist_str})"
            keyboard.append([
                InlineKeyboardButton(label, callback_data=f"allega_app_{app['id']}")
            ])
    
    if not keyboard:
        # Nessun appartamento vicino - offri ricerca
        keyboard = [
            [InlineKeyboardButton("🔍 Cerca appartamento", callback_data="cerca_appartamento_allegato")]
        ]
        await update.message.reply_text(
            "😕 *Nessun appartamento trovato entro 300 m*\n\n"
            "Usa la ricerca per trovare l'appartamento:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        keyboard.append([InlineKeyboardButton("🔍 Cerca", callback_data="cerca_appartamento_allegato")])
        keyboard.append([InlineKeyboardButton("❌ Annulla", callback_data="annulla")])
        
        await update.message.reply_text(
            "📍 *Appartamenti vicini (entro 300 m):*\n\n"
            "_Seleziona l'appartamento:_",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
