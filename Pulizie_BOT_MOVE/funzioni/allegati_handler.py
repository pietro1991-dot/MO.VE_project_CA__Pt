"""
Gestore allegati per il bot delle pulizie
Organizza foto, video, note e documenti in struttura gerarchica
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional
import logging

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


def get_allegato_path(
    user_nome: str,
    user_cognome: str,
    appartamento_nome: str,
    tipo: str,  # 'foto', 'video', 'note', 'documento'
    timestamp: datetime,
    filename: Optional[str] = None
) -> Path:
    """
    Genera percorso organizzato per allegato:
    allegati/YYYY/MM/DD/APPARTAMENTO/Nome_Cognome/tipo/HH-MM_filename.ext
    
    Args:
        user_nome: Nome utente
        user_cognome: Cognome utente
        appartamento_nome: Nome appartamento
        tipo: Tipo allegato (foto/video/note/documento)
        timestamp: Timestamp allegato
        filename: Nome file originale (opzionale)
    
    Returns:
        Path completo del file
    """
    from .config import ALLEGATI_DIR
    
    # Costruisci percorso base
    base_dir = ALLEGATI_DIR / str(timestamp.year) / f"{timestamp.month:02d}" / f"{timestamp.day:02d}"
    
    # Nome appartamento safe per filesystem
    app_safe = appartamento_nome.replace(' ', '_').replace('/', '-')
    
    # Nome utente safe
    user_safe = f"{user_nome}_{user_cognome}".replace(' ', '_').replace('/', '-')
    
    # Percorso completo
    allegato_dir = base_dir / app_safe / user_safe / tipo
    allegato_dir.mkdir(parents=True, exist_ok=True)
    
    # Nome file con timestamp
    ora = timestamp.strftime('%H-%M-%S')
    
    if filename:
        # Mantieni estensione originale
        file_path = allegato_dir / f"{ora}_{filename}"
    else:
        # Genera nome base
        if tipo == 'foto':
            file_path = allegato_dir / f"{ora}.jpg"
        elif tipo == 'video':
            file_path = allegato_dir / f"{ora}.mp4"
        elif tipo == 'note':
            file_path = allegato_dir / f"{ora}.txt"
        else:
            file_path = allegato_dir / f"{ora}.file"
    
    return file_path


async def salva_foto(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_nome: str,
    user_cognome: str,
    appartamento_nome: str
) -> Tuple[str, str]:
    """
    Salva foto in struttura organizzata
    Returns: (percorso_file, file_id_telegram)
    """
    try:
        photo = update.message.photo[-1]  # Qualità migliore
        timestamp = datetime.now()
        
        file_path = get_allegato_path(user_nome, user_cognome, appartamento_nome, 'foto', timestamp)
        
        file = await context.bot.get_file(photo.file_id)
        await file.download_to_drive(str(file_path))
        
        logger.info(f"Foto salvata: {file_path}")
        return str(file_path), photo.file_id
    except PermissionError:
        logger.error(f"Permessi insufficienti per salvare foto")
        raise ValueError("❌ Errore permessi: impossibile salvare la foto")
    except Exception as e:
        logger.error(f"Errore salvataggio foto: {e}")
        raise ValueError(f"❌ Errore durante il salvataggio della foto: {e}")


async def salva_video_allegato(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_nome: str,
    user_cognome: str,
    appartamento_nome: str
) -> Tuple[str, str]:
    """
    Salva video in struttura organizzata
    Returns: (percorso_file, file_id_telegram)
    """
    try:
        video = update.message.video
        timestamp = datetime.now()
        
        file_path = get_allegato_path(user_nome, user_cognome, appartamento_nome, 'video', timestamp)
        
        file = await context.bot.get_file(video.file_id)
        await file.download_to_drive(str(file_path))
        
        logger.info(f"Video salvato: {file_path}")
        return str(file_path), video.file_id
    except PermissionError:
        logger.error(f"Permessi insufficienti per salvare video")
        raise ValueError("❌ Errore permessi: impossibile salvare il video")
    except Exception as e:
        logger.error(f"Errore salvataggio video: {e}")
        raise ValueError(f"❌ Errore durante il salvataggio del video: {e}")


async def salva_documento(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_nome: str,
    user_cognome: str,
    appartamento_nome: str
) -> Tuple[str, str]:
    """
    Salva documento in struttura organizzata
    Returns: (percorso_file, file_id_telegram)
    """
    try:
        doc = update.message.document
        timestamp = datetime.now()
        
        file_path = get_allegato_path(
            user_nome, user_cognome, appartamento_nome, 
            'documento', timestamp, doc.file_name
        )
        
        file = await context.bot.get_file(doc.file_id)
        await file.download_to_drive(str(file_path))
        
        logger.info(f"Documento salvato: {file_path}")
        return str(file_path), doc.file_id
    except PermissionError:
        logger.error(f"Permessi insufficienti per salvare documento")
        raise ValueError("❌ Errore permessi: impossibile salvare il documento")
    except Exception as e:
        logger.error(f"Errore salvataggio documento: {e}")
        raise ValueError(f"❌ Errore durante il salvataggio del documento: {e}")


async def salva_nota(
    testo: str,
    user_nome: str,
    user_cognome: str,
    appartamento_nome: str
) -> str:
    """
    Salva nota testuale in struttura organizzata
    Returns: percorso_file
    """
    timestamp = datetime.now()
    
    file_path = get_allegato_path(user_nome, user_cognome, appartamento_nome, 'note', timestamp)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"Data: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Utente: {user_nome} {user_cognome}\n")
            f.write(f"Appartamento: {appartamento_nome}\n")
            f.write(f"\n{'-'*50}\n\n")
            f.write(f"{testo}\n")
        
        logger.info(f"Nota salvata: {file_path}")
        return str(file_path)
    except PermissionError:
        logger.error(f"Permessi insufficienti per scrivere nota: {file_path}")
        raise
    except OSError as e:
        logger.error(f"Errore I/O durante salvataggio nota: {e}")
        raise
    except Exception as e:
        logger.error(f"Errore salvataggio nota: {e}")
        raise


def list_allegati_by_appartamento(appartamento_nome: str, data: datetime.date) -> dict:
    """
    Elenca tutti gli allegati di un appartamento in una data
    Returns: dict con liste per tipo (foto, video, note, documento)
    """
    from .config import ALLEGATI_DIR
    
    app_safe = appartamento_nome.replace(' ', '_').replace('/', '-')
    date_dir = ALLEGATI_DIR / str(data.year) / f"{data.month:02d}" / f"{data.day:02d}" / app_safe
    
    if not date_dir.exists():
        return {'foto': [], 'video': [], 'note': [], 'documento': []}
    
    allegati = {
        'foto': [],
        'video': [],
        'note': [],
        'documento': []
    }
    
    # Scorre tutte le cartelle utente
    for user_dir in date_dir.iterdir():
        if not user_dir.is_dir():
            continue
        
        user_name = user_dir.name.replace('_', ' ')
        
        # Scorre ogni tipo
        for tipo in ['foto', 'video', 'note', 'documento']:
            tipo_dir = user_dir / tipo
            if tipo_dir.exists() and tipo_dir.is_dir():
                for file in tipo_dir.iterdir():
                    if file.is_file():
                        allegati[tipo].append({
                            'utente': user_name,
                            'filename': file.name,
                            'path': str(file),
                            'size_kb': file.stat().st_size / 1024
                        })
    
    return allegati


def list_allegati_by_user(user_nome: str, user_cognome: str, data: datetime.date) -> dict:
    """
    Elenca tutti gli allegati di un utente in una data
    """
    from .config import ALLEGATI_DIR
    
    user_safe = f"{user_nome}_{user_cognome}".replace(' ', '_').replace('/', '-')
    date_dir = ALLEGATI_DIR / str(data.year) / f"{data.month:02d}" / f"{data.day:02d}"
    
    if not date_dir.exists():
        return {}
    
    allegati = {}
    
    # Scorre tutti gli appartamenti
    for app_dir in date_dir.iterdir():
        if not app_dir.is_dir():
            continue
        
        appartamento = app_dir.name.replace('_', ' ')
        user_dir = app_dir / user_safe
        
        if not user_dir.exists():
            continue
        
        allegati[appartamento] = {
            'foto': [],
            'video': [],
            'note': [],
            'documento': []
        }
        
        # Scorre ogni tipo
        for tipo in ['foto', 'video', 'note', 'documento']:
            tipo_dir = user_dir / tipo
            if tipo_dir.exists() and tipo_dir.is_dir():
                for file in tipo_dir.iterdir():
                    if file.is_file():
                        allegati[appartamento][tipo].append({
                            'filename': file.name,
                            'path': str(file),
                            'size_kb': file.stat().st_size / 1024
                        })
    
    return allegati


def get_storage_stats_allegati() -> dict:
    """Statistiche occupazione storage allegati"""
    from .config import ALLEGATI_DIR
    
    stats = {
        'foto': {'count': 0, 'size_mb': 0},
        'video': {'count': 0, 'size_mb': 0},
        'note': {'count': 0, 'size_mb': 0},
        'documento': {'count': 0, 'size_mb': 0}
    }
    
    if not ALLEGATI_DIR.exists():
        return stats
    
    for tipo in ['foto', 'video', 'note', 'documento']:
        for file in ALLEGATI_DIR.rglob(f'{tipo}/*'):
            if file.is_file():
                stats[tipo]['count'] += 1
                stats[tipo]['size_mb'] += file.stat().st_size / (1024 * 1024)
    
    return stats
