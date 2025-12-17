# 🏠 MO.VE Property Management - Bot Suite

Sistema integrato di bot Telegram per la gestione operativa di appartamenti turistici.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Telegram Bot API](https://img.shields.io/badge/Telegram-Bot%20API-26A5E4.svg)
![License](https://img.shields.io/badge/License-Private-red.svg)

---

## 📋 Panoramica

Questa repository contiene due bot Telegram complementari per la gestione completa delle operazioni di pulizia e lavanderia per appartamenti turistici:

| Bot | Scopo | Utenti Target |
|-----|-------|---------------|
| **🧺 Lavanderia Bot** | Generazione report pulizie giornalieri da PDF | Coordinatrici, Operatori Lavanderia |
| **🧹 Pulizie Bot** | Gestione turni operatori e segnalazioni | Operatori Pulizie, Amministratori |

---

## 📁 Struttura Repository

```
MO.VE/
├── 📄 README.md                      # Questo file
├── 📄 FLUSSO_OPERATIVO_MOVE.md       # Documentazione flusso operativo
├── 📄 dipendenti.xlsx                # Lista dipendenti
├── 📄 Flusso di Lavoro.pdf           # Diagramma flusso (PDF)
├── 📄 flusso di lavoro.png           # Diagramma flusso (immagine)
│
├── 🧺 Lavanderia_Bot_MOVE/           # Bot per report lavanderia
│   ├── .gitignore
│   ├── requirements.txt
│   ├── GUIDA_UTENTE.md               # Documentazione utente
│   ├── Config/                       # Configurazioni (API keys, token)
│   ├── Database/
│   │   ├── appartamenti.xlsx         # Database appartamenti
│   │   ├── tipologie_contratti.xlsx  # Tipologie contratti
│   │   └── Regole/
│   │       └── regole_materiali.xlsx # Regole calcolo materiali
│   └── Telegram/                     # Codice bot principale
│       ├── telegram_bot.py           # Entry point
│       ├── Funzioni/                 # Moduli elaborazione
│       │   ├── elabora_giro_giornaliero.py
│       │   ├── gpt_pdf_parser.py
│       │   └── route_optimizer.py
│       ├── logs/                     # Log elaborazioni
│       ├── pdf_input/                # PDF ricevuti
│       └── pdf_output/               # Report generati
│
└── 🧹 Pulizie_BOT_MOVE/              # Bot per gestione turni
    ├── requirements.txt
    ├── bot.py                        # Entry point
    ├── GUIDA_OPERATORE.md            # Guida per operatori
    ├── GUIDA_ADMIN.md                # Guida per amministratori
    ├── Config/                       # Configurazioni
    ├── Database/
    │   ├── appartamenti.xlsx         # Database appartamenti
    │   ├── users.xlsx                # Utenti registrati
    │   ├── turni.xlsx                # Storico turni
    │   ├── richieste_prodotti.xlsx   # Segnalazioni materiali mancanti
    │   ├── materieli_pulizie e appartamenti.xlsx  # Materiali per appartamento
    │   └── backups/                  # Backup automatici
    ├── funzioni/                     # Moduli Python
    │   ├── __init__.py
    │   ├── admin_handlers.py         # Handler pannello admin
    │   ├── user_handlers.py          # Handler utenti/operatori
    │   ├── database.py               # Gestione database Excel
    │   ├── video_handler.py          # Download e salvataggio video
    │   ├── allegati_handler.py       # Gestione foto/documenti/note
    │   ├── google_maps_helper.py     # Integrazione Google Maps
    │   ├── config.py                 # Configurazioni e costanti
    │   └── utils.py                  # Utility varie
    ├── archivio/                     # Video e allegati salvati
    │   ├── video/                    # Video turni
    │   └── allegati/                 # Foto, documenti
    ├── exports/                      # Export Excel
    └── logs/                         # Log operazioni
```

---

## 🧺 Lavanderia Bot

### Funzionalità
- 📄 **Parsing PDF** - Analizza PDF prenotazioni (Ciao Booking) con GPT-4
- 🗺️ **Ottimizzazione Percorso** - Calcola percorso ottimale con Google Maps API
- 📊 **Calcolo Materiali** - Calcola automaticamente materiali per ogni appartamento
- 👤 **Sommario Operatori** - Raggruppa appartamenti per operatore assegnato
- 📑 **Report PDF** - Genera report professionale stampabile

### Tecnologie
- Python 3.9+
- python-telegram-bot
- OpenAI GPT-4 API
- Google Maps Directions API
- ReportLab (generazione PDF)
- Pandas + OpenPyXL

### Avvio
```bash
cd Lavanderia_Bot_MOVE/Telegram
pip install -r ../requirements.txt
python telegram_bot.py
```

### Documentazione
- [📖 Guida Utente](Lavanderia_Bot_MOVE/GUIDA_UTENTE.md)

---

## 🧹 Pulizie Bot

### Funzionalità
- 👤 **Registrazione Utenti** - Sistema di registrazione con approvazione admin
- ⏱️ **Gestione Turni** - Inizio/fine turno con video obbligatori
- 📍 **Geolocalizzazione** - Tracciamento posizione inizio/fine turno
- 📸 **Allegati** - Foto, video, documenti e note per ogni turno
- ⚠️ **Segnalazioni** - Sistema richiesta prodotti mancanti
- 📊 **Dashboard Admin** - Pannello gestione turni e export Excel

### Tecnologie
- Python 3.9+
- python-telegram-bot (ConversationHandler)
- OpenPyXL (database Excel)
- FileLock (gestione concorrenza)
- Geopy (calcoli geolocalizzazione)

### Avvio
```bash
cd Pulizie_BOT_MOVE
pip install -r requirements.txt
python bot.py
```

### Documentazione
- [📖 Guida Operatore](Pulizie_BOT_MOVE/GUIDA_OPERATORE.md)
- [📖 Guida Admin](Pulizie_BOT_MOVE/GUIDA_ADMIN.md)

---

## ⚙️ Configurazione

### File di Configurazione Richiesti

Entrambi i bot richiedono file di configurazione nella cartella `Config/`:

| File | Descrizione | Lavanderia | Pulizie |
|------|-------------|:----------:|:-------:|
| `telegram_bot_token.txt` | Token bot da @BotFather | ✅ | ✅ |
| `gpt_api_key.txt` | Chiave API OpenAI | ✅ | ❌ |
| `gpt_prompts.json` | Prompts per GPT | ✅ | ❌ |
| `google_maps_api_key.txt` | Chiave Google Maps | ✅ | ❌ |
| `admin_telegram_id.txt` | ID Telegram admin (uno per riga) | ❌ | ✅ |
| `email_list.txt` | Lista email notifiche | ⚪ | ⚪ |
| `gmail_config.txt` | Configurazione SMTP Gmail | ⚪ | ⚪ |

✅ = Obbligatorio | ❌ = Non usato | ⚪ = Opzionale

### Esempio telegram_bot_token.txt
```
1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ
```

### Esempio admin_telegram_id.txt
```
123456789
987654321
```

---

## 🔄 Flusso Operativo

Il sistema supporta il seguente flusso operativo:

```
CHECKOUT APPARTAMENTO
        │
        ▼
┌───────────────────┐
│   COORDINATRICE   │ ──► Carica PDF su Lavanderia Bot
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  REPORT GENERATO  │ ──► PDF con percorso + materiali + sommario operatori
└─────────┬─────────┘
          │
    ┌─────┴─────┐
    │           │
    ▼           ▼
┌───────┐   ┌───────────┐
│PULIZIE│   │LAVANDERIA │
└───┬───┘   └─────┬─────┘
    │             │
    ▼             ▼
Pulizie Bot   Preparazione
(turni)       CONF_A/CONF_B
```

Per dettagli completi, vedere [FLUSSO_OPERATIVO_MOVE.md](FLUSSO_OPERATIVO_MOVE.md)

---

## 📦 Installazione Completa

### Prerequisiti
- Python 3.9 o superiore
- pip (gestore pacchetti Python)
- Account Telegram
- Bot Telegram creato via @BotFather

### Passaggi

1. **Clona la repository**
```bash
git clone <repository-url>
cd MO.VE
```

2. **Installa dipendenze Lavanderia Bot**
```bash
cd Lavanderia_Bot_MOVE
pip install -r requirements.txt
```

3. **Installa dipendenze Pulizie Bot**
```bash
cd ../Pulizie_BOT_MOVE
pip install -r requirements.txt
```

4. **Configura i file**
- Crea i file di configurazione in `Config/` per entrambi i bot
- Inserisci i token e le chiavi API

5. **Avvia i bot**
```bash
# Terminal 1 - Lavanderia Bot
cd Lavanderia_Bot_MOVE/Telegram
python telegram_bot.py

# Terminal 2 - Pulizie Bot
cd Pulizie_BOT_MOVE
python bot.py
```

---

## 🔒 Sicurezza

⚠️ **IMPORTANTE**: I file nella cartella `Config/` contengono credenziali sensibili.

- Non committare mai file `Config/` nel repository pubblico
- Usa `.gitignore` per escludere file sensibili
- Mantieni backup sicuri delle chiavi API

### .gitignore consigliato
```gitignore
# Configurazioni sensibili
Config/

# File temporanei
*.bak
*.lock
__pycache__/
*.pyc

# Dati operativi (non versionare)
logs/
archivio/
exports/
pdf_input/
pdf_output/
Database/backups/
```

---

## 🐛 Troubleshooting

### Bot non risponde
1. Verifica che il token in `telegram_bot_token.txt` sia corretto
2. Controlla che il bot sia avviato (nessun errore in console)
3. Verifica la connessione internet

### Errore "API key invalid"
1. Rigenera la chiave API (OpenAI/Google)
2. Verifica che non ci siano spazi o newline nel file

### PDF non elaborato
1. Verifica che sia un PDF valido da Ciao Booking
2. Controlla i log in `Telegram/logs/`
3. Verifica la chiave OpenAI

### Database bloccato
1. Verifica che non ci siano processi Python in esecuzione
2. Elimina eventuali file `.lock` nella cartella Database

---

## 📄 Licenza

Questo software è proprietario e riservato.  
© 2024-2025 MO.VE Property Management. Tutti i diritti riservati.

---

## 👥 Contatti

Per supporto tecnico o richieste di funzionalità, contattare l'amministratore del sistema.

---

*Ultimo aggiornamento: Dicembre 2025*
