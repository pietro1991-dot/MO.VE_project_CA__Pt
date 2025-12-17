"""
Utility functions per il bot delle pulizie
Calcolo ore, distanze GPS, formattazione, logging
"""

import logging
from datetime import datetime, timedelta
from typing import Tuple, Optional
from math import radians, cos, sin, asin, sqrt

from .config import (
    DATE_FORMAT, TIME_FORMAT, DATETIME_FORMAT,
    LOG_FILE, LOG_LEVEL, GPS_TOLERANCE_METERS
)


# ==================== LOGGING ====================

def setup_logging():
    """Configura il sistema di logging con file giornalieri"""
    from pathlib import Path
    from .config import LOGS_DIR
    
    # Crea logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # Nome file con data: bot_2025-12-03.log
    oggi = datetime.now().strftime('%Y-%m-%d')
    log_file = LOGS_DIR / f"bot_{oggi}.log"
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler giornaliero
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(getattr(logging, LOG_LEVEL))
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Aggiungi handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


# ==================== CALCOLO ORE ====================

def calcola_ore_lavorate(timestamp_ingresso: datetime, timestamp_uscita: datetime) -> float:
    """Calcola ore lavorate tra due timestamp"""
    delta = timestamp_uscita - timestamp_ingresso
    ore = delta.total_seconds() / 3600
    return round(ore, 2)


def format_ore(ore: float) -> str:
    """Formatta ore in formato leggibile (es: 3.75 -> '3h 45m')"""
    ore_int = int(ore)
    minuti = int((ore - ore_int) * 60)
    return f"{ore_int}h {minuti:02d}m"


def parse_ore(ore_str: str) -> float:
    """Parse stringa ore (es: '3h 45m' -> 3.75)"""
    try:
        if 'h' in ore_str:
            parts = ore_str.lower().replace('h', '').replace('m', '').split()
            ore = float(parts[0])
            minuti = float(parts[1]) if len(parts) > 1 else 0
            return ore + (minuti / 60)
        else:
            return float(ore_str)
    except:
        return 0.0


# ==================== GPS / DISTANZE ====================

def calcola_distanza_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcola distanza in metri tra due coordinate GPS usando formula Haversine
    
    Args:
        lat1, lon1: Coordinate punto 1
        lat2, lon2: Coordinate punto 2
    
    Returns:
        float: Distanza in metri
    """
    # Converti gradi in radianti
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Formula Haversine
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Raggio della Terra in metri
    r = 6371000
    
    return c * r


def is_vicino(user_lat: float, user_lon: float, app_lat: float, app_lon: float,
              tolerance: float = GPS_TOLERANCE_METERS) -> Tuple[bool, float]:
    """
    Verifica se utente è vicino ad un appartamento
    
    Returns:
        Tuple[bool, float]: (è_vicino, distanza_metri)
    """
    distanza = calcola_distanza_haversine(user_lat, user_lon, app_lat, app_lon)
    return distanza <= tolerance, distanza


def format_distanza(distanza_metri: float) -> str:
    """Formatta distanza in formato leggibile"""
    if distanza_metri < 1000:
        return f"{int(distanza_metri)}m"
    else:
        km = distanza_metri / 1000
        return f"{km:.1f}km"


def parse_coordinate(coord_str: str) -> Optional[Tuple[float, float]]:
    """
    Parse stringa coordinate in formato 'lat,lon' o '(lat, lon)' con validazione robusta
    
    Returns:
        Tuple[float, float]: (latitudine, longitudine) o None se errore
    """
    if not coord_str:
        return None
    
    try:
        # Normalizza separatori (gestisce , ; spazio)
        coord_str = coord_str.strip().replace('(', '').replace(')', '')
        coord_str = coord_str.replace(' ', ',').replace(';', ',')
        
        # Rimuovi virgole multiple consecutive
        while ',,' in coord_str:
            coord_str = coord_str.replace(',,', ',')
        
        parts = [p.strip() for p in coord_str.split(',') if p.strip()]
        
        if len(parts) != 2:
            logging.getLogger(__name__).warning(f"Coordinate malformate (parti != 2): '{coord_str}'")
            return None
        
        lat = float(parts[0])
        lon = float(parts[1])
        
        # Valida range GPS
        if not (-90 <= lat <= 90):
            logging.getLogger(__name__).warning(f"Latitudine fuori range: {lat}")
            return None
        
        if not (-180 <= lon <= 180):
            logging.getLogger(__name__).warning(f"Longitudine fuori range: {lon}")
            return None
        
        return (lat, lon)
        
    except (ValueError, IndexError) as e:
        logging.getLogger(__name__).warning(f"Errore parsing coordinate '{coord_str}': {e}")
        return None
    except Exception as e:
        logging.getLogger(__name__).error(f"Errore inatteso parsing coordinate: {e}")
        return None


# ==================== FORMATTAZIONE DATE ====================

def format_data(data: datetime.date) -> str:
    """Formatta data in italiano (es: 03/12/2025)"""
    return data.strftime(DATE_FORMAT)


def format_ora(timestamp: datetime) -> str:
    """Formatta ora (es: 08:30)"""
    return timestamp.strftime(TIME_FORMAT)


def format_datetime(timestamp: datetime) -> str:
    """Formatta data e ora completa"""
    return timestamp.strftime(DATETIME_FORMAT)


def format_data_italiana(data: datetime.date) -> str:
    """Formatta data in italiano esteso (es: Martedì 03 Dicembre 2025)"""
    giorni = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
    mesi = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
            'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre']
    
    giorno_settimana = giorni[data.weekday()]
    mese = mesi[data.month - 1]
    
    return f"{giorno_settimana} {data.day:02d} {mese} {data.year}"


def get_settimana_corrente() -> Tuple[datetime.date, datetime.date]:
    """Ottiene primo e ultimo giorno della settimana corrente (Lun-Dom)"""
    oggi = datetime.now().date()
    inizio_settimana = oggi - timedelta(days=oggi.weekday())  # Lunedì
    fine_settimana = inizio_settimana + timedelta(days=6)  # Domenica
    return inizio_settimana, fine_settimana


def get_mese_corrente() -> Tuple[datetime.date, datetime.date]:
    """Ottiene primo e ultimo giorno del mese corrente"""
    oggi = datetime.now().date()
    primo_giorno = oggi.replace(day=1)
    
    # Ultimo giorno del mese
    if oggi.month == 12:
        ultimo_giorno = oggi.replace(day=31)
    else:
        prossimo_mese = oggi.replace(month=oggi.month + 1, day=1)
        ultimo_giorno = prossimo_mese - timedelta(days=1)
    
    return primo_giorno, ultimo_giorno


# ==================== VALIDAZIONE ====================

def is_valid_phone(phone: str) -> bool:
    """Valida numero di telefono italiano"""
    # Rimuovi spazi e caratteri
    phone = phone.replace(' ', '').replace('+', '').replace('-', '')
    
    # Numero italiano: 10 cifre o +39 seguito da 10 cifre
    if phone.startswith('39'):
        phone = phone[2:]
    
    return len(phone) == 10 and phone.isdigit()


def sanitize_filename(filename: str) -> str:
    """Rimuove caratteri non validi da un nome file"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename


# ==================== FORMATTAZIONE MESSAGGI ====================

def format_turno_info(turno: dict) -> str:
    """Formatta info turno per visualizzazione"""
    text = f"🏠 *{turno['appartamento_nome']}*\n"
    text += f"📍 {turno.get('indirizzo', 'N/A')}\n\n"
    
    if turno.get('timestamp_ingresso'):
        ts_ingresso = datetime.fromisoformat(turno['timestamp_ingresso'])
        text += f"⏰ Ingresso: {format_ora(ts_ingresso)}\n"
    
    if turno.get('timestamp_uscita'):
        ts_uscita = datetime.fromisoformat(turno['timestamp_uscita'])
        text += f"⏰ Uscita: {format_ora(ts_uscita)}\n"
        
        if turno.get('ore_lavorate'):
            text += f"⏱️  Totale: *{format_ore(turno['ore_lavorate'])}*\n"
    elif turno['status'] == 'in_corso':
        text += f"⏱️  _Turno in corso..._\n"
    
    return text


def format_richiesta_info(richiesta: dict) -> str:
    """Formatta info richiesta prodotti"""
    status = "✅" if richiesta.get('completato') else "⬜"
    
    text = f"{status} *{richiesta['appartamento_nome']}*\n"
    text += f"   └ {richiesta['descrizione_prodotti']}\n"
    
    if richiesta.get('nome') and richiesta.get('cognome'):
        nome_completo = f"{richiesta['nome']} {richiesta['cognome']}"
        text += f"   _Richiesto da {nome_completo}_\n"
    
    if richiesta.get('data_richiesta'):
        dt = datetime.fromisoformat(richiesta['data_richiesta'])
        text += f"   _⏰ {format_ora(dt)}_\n"
    
    return text


def format_user_stats(user: dict, ore_totali: float, num_turni: int) -> str:
    """Formatta statistiche utente"""
    text = f"👤 *{user['nome']} {user['cognome']}*\n"
    text += f"📊 Turni completati: {num_turni}\n"
    text += f"⏱️  Ore totali: *{format_ore(ore_totali)}*\n"
    
    if num_turni > 0:
        media = ore_totali / num_turni
        text += f"📈 Media per turno: {format_ore(media)}\n"
    
    return text


# ==================== ESCAPE MARKDOWN ====================

def escape_markdown(text: str) -> str:
    """Escape caratteri speciali per Markdown di Telegram"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


if __name__ == '__main__':
    # Test funzioni
    print("📅 Test date:")
    oggi = datetime.now().date()
    print(f"   Oggi: {format_data_italiana(oggi)}")
    
    inizio, fine = get_settimana_corrente()
    print(f"   Settimana: {format_data(inizio)} - {format_data(fine)}")
    
    print("\n⏱️  Test ore:")
    print(f"   3.75 ore = {format_ore(3.75)}")
    print(f"   '4h 30m' = {parse_ore('4h 30m')} ore")
    
    print("\n📍 Test GPS:")
    # Roma Colosseo vs Fontana di Trevi (~1.2km)
    dist = calcola_distanza_haversine(41.8902, 12.4922, 41.9009, 12.4833)
    print(f"   Colosseo -> Fontana Trevi: {format_distanza(dist)}")
    
    vicino, dist2 = is_vicino(41.8902, 12.4922, 41.8905, 12.4925, tolerance=100)
    print(f"   Vicino (100m): {vicino}, distanza: {format_distanza(dist2)}")
