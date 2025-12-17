"""
Gestore video per il bot delle pulizie
Gestisce download, salvataggio e organizzazione dei video
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Tuple
import logging

from telegram import Update, File
from telegram.ext import ContextTypes

from .config import get_video_path, MAX_VIDEO_SIZE_MB

logger = logging.getLogger(__name__)


async def download_and_save_video(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_nome: str,
    user_cognome: str,
    appartamento_nome: str,
    tipo: str  # 'ingresso' o 'uscita'
) -> Tuple[str, str, datetime]:
    """
    Scarica video da Telegram e lo salva organizzato
    
    Returns:
        Tuple[str, str, datetime]: (percorso_file, file_id_telegram, timestamp)
    """
    
    # Ottieni video dal messaggio
    if update.message.video:
        video = update.message.video
    elif update.message.document and update.message.document.mime_type.startswith('video/'):
        # Video inviato come documento
        video = update.message.document
    else:
        raise ValueError("Nessun video trovato nel messaggio")
    
    # Verifica dimensione
    file_size_mb = video.file_size / (1024 * 1024)
    if file_size_mb > MAX_VIDEO_SIZE_MB:
        raise ValueError(f"Video troppo grande: {file_size_mb:.1f}MB (massimo {MAX_VIDEO_SIZE_MB}MB)")
    
    # Timestamp del video
    timestamp = datetime.now()
    
    # Genera percorso di salvataggio
    video_path = get_video_path(user_nome, user_cognome, appartamento_nome, tipo, timestamp)
    
    # Download del file da Telegram
    try:
        file = await video.get_file()
        await file.download_to_drive(str(video_path))
        
        logger.info(f"Video salvato: {video_path}")
        
        return str(video_path), video.file_id, timestamp
        
    except PermissionError:
        logger.error(f"Permessi insufficienti per salvare video: {video_path}")
        raise ValueError("❌ Errore permessi: impossibile salvare il video")
    except OSError as e:
        logger.error(f"Errore I/O durante salvataggio video: {e}")
        raise ValueError(f"❌ Errore disco durante salvataggio video: {e}")
    except Exception as e:
        logger.error(f"Errore durante il download del video: {e}")
        raise ValueError(f"❌ Errore durante il download del video: {e}")


def get_video_info(video_path: str) -> dict:
    """Ottiene informazioni su un video salvato"""
    path = Path(video_path)
    
    if not path.exists():
        return None
    
    stat = path.stat()
    
    return {
        'path': str(path),
        'filename': path.name,
        'size_mb': stat.st_size / (1024 * 1024),
        'created': datetime.fromtimestamp(stat.st_ctime),
        'modified': datetime.fromtimestamp(stat.st_mtime)
    }


def list_videos_by_date(data: datetime.date) -> list:
    """Elenca tutti i video di una specifica data"""
    from .config import VIDEOS_DIR
    
    date_dir = VIDEOS_DIR / str(data.year) / f"{data.month:02d}" / f"{data.day:02d}"
    
    if not date_dir.exists():
        return []
    
    videos = []
    
    # Scorre tutti i sottodirectory (appartamenti)
    for app_dir in date_dir.iterdir():
        if app_dir.is_dir():
            appartamento = app_dir.name.replace('_', ' ')
            
            # Elenca video nell'appartamento
            for video_file in app_dir.glob('*.mp4'):
                videos.append({
                    'appartamento': appartamento,
                    'filename': video_file.name,
                    'path': str(video_file),
                    'size_mb': video_file.stat().st_size / (1024 * 1024)
                })
    
    return videos


def list_videos_by_appartamento(appartamento_nome: str, data: datetime.date) -> list:
    """Elenca video di un appartamento in una data"""
    from .config import VIDEOS_DIR
    
    app_safe = appartamento_nome.replace(' ', '_').replace('/', '-')
    date_dir = VIDEOS_DIR / str(data.year) / f"{data.month:02d}" / f"{data.day:02d}" / app_safe
    
    if not date_dir.exists():
        return []
    
    videos = []
    for video_file in date_dir.glob('*.mp4'):
        # Parse filename: Maria_Rossi_ingresso_08-30.mp4
        parts = video_file.stem.split('_')
        
        tipo = None
        ora = None
        
        if 'ingresso' in video_file.stem:
            tipo = 'ingresso'
            # Trova orario dopo 'ingresso'
            idx = parts.index('ingresso')
            if idx + 1 < len(parts):
                ora = parts[idx + 1].replace('-', ':')
        elif 'uscita' in video_file.stem:
            tipo = 'uscita'
            idx = parts.index('uscita')
            if idx + 1 < len(parts):
                ora = parts[idx + 1].replace('-', ':')
        
        videos.append({
            'filename': video_file.name,
            'path': str(video_file),
            'tipo': tipo,
            'ora': ora,
            'size_mb': video_file.stat().st_size / (1024 * 1024)
        })
    
    return sorted(videos, key=lambda x: x['ora'] or '')


def delete_video(video_path: str) -> bool:
    """Elimina un video"""
    try:
        path = Path(video_path)
        if path.exists():
            path.unlink()
            logger.info(f"Video eliminato: {video_path}")
            return True
        return False
    except Exception as e:
        logger.error(f"Errore durante l'eliminazione del video: {e}")
        return False


def get_storage_stats() -> dict:
    """Statistiche sull'occupazione dello storage"""
    from .config import VIDEOS_DIR
    
    total_size = 0
    total_files = 0
    
    for video_file in VIDEOS_DIR.rglob('*.mp4'):
        total_size += video_file.stat().st_size
        total_files += 1
    
    return {
        'total_files': total_files,
        'total_size_mb': total_size / (1024 * 1024),
        'total_size_gb': total_size / (1024 * 1024 * 1024)
    }


async def send_video_by_file_id(context: ContextTypes.DEFAULT_TYPE, chat_id: int, 
                                  file_id: str, caption: str = None):
    """Invia un video usando il file_id di Telegram (più veloce che caricare da disco)"""
    try:
        await context.bot.send_video(
            chat_id=chat_id,
            video=file_id,
            caption=caption
        )
        return True
    except Exception as e:
        logger.error(f"Errore durante l'invio del video: {e}")
        return False


async def send_video_by_path(context: ContextTypes.DEFAULT_TYPE, chat_id: int, 
                              video_path: str, caption: str = None):
    """Invia un video caricandolo da disco"""
    try:
        with open(video_path, 'rb') as video_file:
            await context.bot.send_video(
                chat_id=chat_id,
                video=video_file,
                caption=caption
            )
        return True
    except Exception as e:
        logger.error(f"Errore durante l'invio del video: {e}")
        return False


if __name__ == '__main__':
    # Test funzioni
    from datetime import date
    
    print("📊 Statistiche storage:")
    stats = get_storage_stats()
    print(f"   Video totali: {stats['total_files']}")
    print(f"   Spazio occupato: {stats['total_size_mb']:.2f} MB ({stats['total_size_gb']:.2f} GB)")
