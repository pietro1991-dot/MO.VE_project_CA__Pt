"""
Configurazione del bot
Carica token, percorsi e impostazioni dai file in Config/
"""

import os
from pathlib import Path

# Directory base del progetto (radice, non funzioni/)
BASE_DIR = Path(__file__).parent.parent

# Directory Config
CONFIG_DIR = BASE_DIR / 'Config'

# Directory Database CONDIVISO (a livello superiore)
DATABASE_DIR = BASE_DIR.parent / 'Database'

# Directory Archivio (cartella madre per video e allegati)
ARCHIVIO_DIR = BASE_DIR / 'archivio'
ARCHIVIO_DIR.mkdir(exist_ok=True)

# Directory Video (dentro archivio/)
VIDEOS_DIR = ARCHIVIO_DIR / 'video'
VIDEOS_DIR.mkdir(exist_ok=True)

# Directory Allegati (dentro archivio/)
ALLEGATI_DIR = ARCHIVIO_DIR / 'allegati'
ALLEGATI_DIR.mkdir(exist_ok=True)

# Directory Export (per report Excel)
EXPORTS_DIR = BASE_DIR / 'exports'
EXPORTS_DIR.mkdir(exist_ok=True)

# Directory Logs
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)


def read_config_file(filename: str) -> str:
    """Legge un file dalla directory Config"""
    filepath = CONFIG_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"File di configurazione non trovato: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    return content


# ==================== TELEGRAM ====================

try:
    TELEGRAM_BOT_TOKEN = read_config_file('telegram_bot_token.txt')
except FileNotFoundError:
    print("⚠️ ATTENZIONE: telegram_bot_token.txt non trovato!")
    TELEGRAM_BOT_TOKEN = None

# ID Telegram degli amministratori
# Puoi ottenerlo inviando un messaggio a @userinfobot
# Supporta più admin: un ID per riga nel file admin_telegram_id.txt
try:
    admin_content = read_config_file('admin_telegram_id.txt')
    # Supporta più ID separati da newline o virgola
    ADMIN_TELEGRAM_IDS = []
    for line in admin_content.replace(',', '\n').split('\n'):
        line = line.strip()
        if line and line.isdigit():
            ADMIN_TELEGRAM_IDS.append(int(line))
    
    # Per retrocompatibilità, manteniamo anche ADMIN_TELEGRAM_ID come primo admin
    ADMIN_TELEGRAM_ID = ADMIN_TELEGRAM_IDS[0] if ADMIN_TELEGRAM_IDS else None
    
    if not ADMIN_TELEGRAM_IDS:
        print("⚠️ Nessun admin ID valido trovato in admin_telegram_id.txt")
    elif 0 in ADMIN_TELEGRAM_IDS:
        print("⚠️ ADMIN_ID = 0 (temporaneo). Controlla i log dopo /start per vedere il tuo ID")
    else:
        print(f"✅ {len(ADMIN_TELEGRAM_IDS)} amministratore/i configurato/i")
except FileNotFoundError:
    print("⚠️ ATTENZIONE: admin_telegram_id.txt non trovato!")
    print("   Crea il file Config/admin_telegram_id.txt con il/i tuo/i ID Telegram")
    ADMIN_TELEGRAM_IDS = []
    ADMIN_TELEGRAM_ID = None


def is_admin(telegram_id: int) -> bool:
    """Verifica se un utente è amministratore"""
    return telegram_id in ADMIN_TELEGRAM_IDS


# ==================== GPS ====================

# Distanza massima in metri per considerare un appartamento "vicino"
GPS_TOLERANCE_METERS = 300

# Abilita/disabilita controllo GPS
GPS_CHECK_ENABLED = True


# ==================== VIDEO ====================

# Durata massima video in secondi (0 = illimitata)
MAX_VIDEO_DURATION = 0

# Dimensione massima video in MB (Telegram ha limite di 50MB per file)
MAX_VIDEO_SIZE_MB = 50


# ==================== ORARI ====================

# Ore dopo le quali inviare alert per turno non chiuso
ALERT_TURNO_APERTO_ORE = 8

# Orario entro cui aspettarsi l'inizio del primo turno (es: 10:00)
ORARIO_INIZIO_PREVISTO = "10:00"


# ==================== NOTIFICHE ====================

# Abilita notifiche admin
NOTIFICHE_ADMIN_ENABLED = True

# Tipi di notifiche
NOTIFICA_INIZIO_TURNO = True
NOTIFICA_FINE_TURNO = True
NOTIFICA_RICHIESTA_PRODOTTI = True
NOTIFICA_ALERT_TURNO_LUNGO = True


# ==================== DATABASE ====================

DATABASE_PATH = DATABASE_DIR / 'pulizie.db'


# ==================== LOGGING ====================

LOG_FILE = LOGS_DIR / 'bot.log'

# Livello di log: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = 'INFO'


# ==================== FORMATTAZIONE ====================

# Formato data per visualizzazione
DATE_FORMAT = '%d/%m/%Y'

# Formato ora per visualizzazione
TIME_FORMAT = '%H:%M'

# Formato datetime completo
DATETIME_FORMAT = f'{DATE_FORMAT} {TIME_FORMAT}'


# ==================== API KEYS (opzionali) ====================

# Google Maps API (per calcolo distanze GPS)
try:
    GOOGLE_MAPS_API_KEY = read_config_file('google_maps_api_key.txt')
except FileNotFoundError:
    GOOGLE_MAPS_API_KEY = None

# OpenAI GPT API (per future funzionalità)
try:
    GPT_API_KEY = read_config_file('gpt_api_key.txt')
except FileNotFoundError:
    GPT_API_KEY = None


# ==================== FUNZIONI HELPER ====================

def get_video_path(user_nome: str, user_cognome: str, appartamento_nome: str, 
                   tipo: str, timestamp) -> Path:
    """
    Genera il percorso per salvare un video
    Struttura: videos/YYYY/MM/DD/Appartamento_Nome/Nome_Cognome_tipo_HH-MM.mp4
    """
    data = timestamp.date()
    ora = timestamp.strftime('%H-%M')
    
    # Normalizza nomi (rimuovi spazi e caratteri speciali)
    app_safe = appartamento_nome.replace(' ', '_').replace('/', '-')
    user_safe = f"{user_nome}_{user_cognome}".replace(' ', '_')
    
    # Crea struttura directory
    video_dir = VIDEOS_DIR / str(data.year) / f"{data.month:02d}" / f"{data.day:02d}" / app_safe
    video_dir.mkdir(parents=True, exist_ok=True)
    
    # Nome file: Maria_Rossi_ingresso_08-30.mp4
    filename = f"{user_safe}_{tipo}_{ora}.mp4"
    
    return video_dir / filename


def get_export_path(tipo_export: str, data=None) -> Path:
    """Genera percorso per file export"""
    if data:
        filename = f"{tipo_export}_{data.strftime('%Y-%m-%d')}.xlsx"
    else:
        filename = f"{tipo_export}.xlsx"
    
    return EXPORTS_DIR / filename


def validate_config():
    """Valida che tutte le configurazioni essenziali siano presenti"""
    errors = []
    
    if not TELEGRAM_BOT_TOKEN:
        errors.append("❌ telegram_bot_token.txt mancante o vuoto")
    
    if ADMIN_TELEGRAM_ID is None:
        errors.append("❌ admin_telegram_id.txt mancante o vuoto")
    
    if errors:
        print("\n⚠️  ERRORI DI CONFIGURAZIONE:")
        for error in errors:
            print(f"   {error}")
        print("\n📝 Crea i file mancanti nella directory Config/\n")
        return False
    
    print("✅ Configurazione valida")
    return True


if __name__ == '__main__':
    # Test configurazione
    print(f"📂 Base directory: {BASE_DIR}")
    print(f"📂 Videos directory: {VIDEOS_DIR}")
    print(f"📂 Database: {DATABASE_PATH}")
    print(f"🔑 Bot token: {'✅ Presente' if TELEGRAM_BOT_TOKEN else '❌ Mancante'}")
    print(f"👨‍💼 Admin ID: {'✅ Presente' if ADMIN_TELEGRAM_ID else '❌ Mancante'}")
    print()
    validate_config()
