# 👨‍💼 Guida Amministratore - Bot Pulizie MO.VE

## Panoramica

Questa guida spiega tutte le funzionalità amministrative del Bot Pulizie. Come amministratore hai accesso a funzioni speciali per monitorare turni, gestire richieste e visualizzare statistiche.

---

## 🔐 Accesso Admin

### Configurazione
L'ID Telegram dell'amministratore è configurato nel file:
```
Config/admin_telegram_id.txt
```

Per aggiungere più amministratori, inserisci un ID per riga:
```
5783861406
1234567890
```

### Verifica Accesso
- Usa il comando `/admin` per accedere al pannello amministratore
- Nella tastiera principale vedrai pulsanti aggiuntivi visibili solo agli admin

---

## 📱 Tastiera Principale (Admin)

Come admin, la tua tastiera principale include pulsanti extra:

| Pulsante | Funzione |
|----------|----------|
| 🏠 Inizia Appartamento | Inizia un turno (come operatore) |
| ✅ Finisci Appartamento | Termina un turno |
| 🧹 Manca Materiale Pulizie | Segnala materiali mancanti |
| 🏠 Manca Qualcosa Appartamento | Segnala oggetti mancanti |
| 📎 Allega Liberamente | Allega foto/video/note |
| 📋 Richieste in Sospeso | **[ADMIN]** Vedi richieste da gestire |
| 🔄 Turni in Corso | **[ADMIN]** Vedi chi sta lavorando |
| ✅ Turni Finiti | **[ADMIN]** Vedi turni completati |

---

## 👨‍💼 Pannello Admin (/admin)

Accedi con il comando `/admin` per vedere il menu completo:

### 📋 Turni in Corso
Mostra tutti gli operatori attualmente al lavoro:
- Nome e cognome operatore
- Appartamento
- Ora di ingresso
- Tempo trascorso

### ✅ Turni Finiti
Menu con opzioni per visualizzare i turni completati:

| Opzione | Descrizione |
|---------|-------------|
| 📅 Turni di Oggi | Solo turni completati nella giornata odierna |
| 📊 Tutti i Turni | Ultimi 50 turni completati (globali) |
| 📥 Esporta Oggi (Excel) | Scarica file Excel con turni di oggi |
| 📥 Esporta Tutti (Excel) | Scarica file Excel con tutti i turni |

Il file Excel esportato contiene:
- ID turno
- Nome e Cognome operatore
- Appartamento
- Data
- Ora ingresso e uscita
- Ore lavorate

### 📦 Richieste Prodotti
Gestione delle segnalazioni di materiali mancanti:

1. Vedi tutte le richieste in sospeso
2. Per ogni richiesta puoi vedere:
   - Tipo (Pulizie 🧹 o Appartamento 🏠)
   - Chi ha fatto la richiesta
   - Quale appartamento
   - Cosa manca
   - Info consegna
   - Data/ora richiesta
3. Premi **✅** per segnare come completata
4. L'operatore riceverà una notifica automatica
5. Usa **🗑️ Rimuovi completati** per pulire le richieste già gestite

### ⏰ Report Ore
Statistiche ore lavorate per periodo:

| Periodo | Descrizione |
|---------|-------------|
| Oggi | Ore lavorate nella giornata |
| Ieri | Ore lavorate il giorno precedente |
| Questa settimana | Da lunedì a oggi |
| Questo mese | Dall'inizio del mese |

Il report mostra:
- Ore totali del periodo
- Suddivisione per operatore
- Dettaglio turni

### 📹 Archivio Video
Accesso ai video registrati:
- Sfoglia per data
- Visualizza video ingresso/uscita
- Statistiche storage (spazio occupato)

### 👥 Gestione Utenti
Lista di tutti gli utenti registrati con:
- ID Telegram
- Nome e cognome
- Data registrazione

### 📊 Statistiche
Panoramica generale del sistema:
- Totale utenti
- Totale turni
- Totale richieste
- Statistiche storage

---

## 📂 Struttura File

### Database Excel
Tutti i dati sono salvati in file Excel nella cartella `Database/`:

| File | Contenuto |
|------|-----------|
| `users.xlsx` | Utenti registrati |
| `turni.xlsx` | Storico turni |
| `richieste_prodotti.xlsx` | Richieste materiali |
| `appartamenti.xlsx` | Lista appartamenti |
| `materiali_pulizie e appartamenti.xlsx` | Liste materiali segnalabili |

### Backup Automatici
- I backup vengono creati automaticamente all'avvio del bot
- Salvati in `Database/backups/`
- Mantenuti per 30 giorni, poi eliminati automaticamente

### Video e Allegati
```
archivio/
├── video/
│   └── YYYY/MM/DD/Appartamento/NomeCognome_tipo_HH-MM.mp4
└── allegati/
    └── YYYY/MM/DD/Appartamento/NomeCognome/tipo/HH-MM-SS.ext
```

---

## ⚙️ Configurazione

### File di Configurazione (Config/)

| File | Descrizione |
|------|-------------|
| `telegram_bot_token.txt` | Token del bot Telegram |
| `admin_telegram_id.txt` | ID admin (uno per riga) |
| `google_maps_api_key.txt` | API key Google Maps (opzionale) |
| `gpt_api_key.txt` | API key OpenAI (opzionale) |

### Parametri Modificabili (config.py)

```python
GPS_TOLERANCE_METERS = 300     # Distanza max per riconoscimento GPS
MAX_VIDEO_SIZE_MB = 50         # Dimensione max video
ALERT_TURNO_APERTO_ORE = 8     # Ore dopo cui avvisare turno aperto
```

---

## 🔧 Gestione Appartamenti

Gli appartamenti sono gestiti nel file `Database/appartamenti.xlsx`:

| Colonna | Contenuto |
|---------|-----------|
| A | Gestione |
| B | Nome appartamento |
| C | Nome OTA |
| D | Indirizzo |
| E | Attivo (Vero/Falso) |
| M | Coordinate GPS (lat,lon) |

Per aggiungere un nuovo appartamento:
1. Apri il file Excel
2. Aggiungi una nuova riga
3. Compila almeno le colonne B (nome) e D (indirizzo)
4. Per il GPS, inserisci le coordinate in colonna M nel formato `45.123456,7.654321`
5. Salva e riavvia il bot

---

## 📋 Gestione Materiali

I materiali segnalabili sono nel file `Database/materiali_pulizie e appartamenti.xlsx`:

### Foglio "materiali_pulizie"
Lista materiali per le pulizie (detersivi, panni, ecc.)

### Foglio "materiali_appartamento"
Lista oggetti appartamento (lampadine, batterie, ecc.)

Per modificare le liste:
1. Apri il file Excel
2. Aggiungi/rimuovi righe nei rispettivi fogli
3. Salva e riavvia il bot

---

## 🔄 Avvio e Riavvio Bot

### Avvio
```bash
cd Pulizie_BOT_MOVE
python bot.py
```

### Riavvio
1. Premi `Ctrl+C` nel terminale
2. Attendi il messaggio "Application.stop() complete"
3. Riavvia con `python bot.py`

### Problemi Comuni

**Errore "Conflict: terminated by other getUpdates request"**
- Un'altra istanza del bot è in esecuzione
- Chiudi tutti i processi Python e riavvia

**Errore "Query is too old"**
- Normale all'avvio se c'erano callback pendenti
- Si risolve automaticamente

---

## 📊 Monitoraggio

### Log
I log sono salvati in `logs/bot.log` e mostrati nel terminale.

### Livelli di Log
- `INFO` - Operazioni normali
- `WARNING` - Situazioni anomale (turni lunghi, ecc.)
- `ERROR` - Errori che richiedono attenzione

### Cosa Monitorare
- Turni aperti da troppo tempo (> 8 ore)
- Richieste prodotti in sospeso
- Spazio disco per video/allegati

---

## 🆘 Troubleshooting

### Il bot non risponde
1. Verifica che il bot sia in esecuzione
2. Controlla i log per errori
3. Riavvia il bot

### Errori di scrittura Excel
1. Verifica che i file Excel non siano aperti in un altro programma
2. Controlla i permessi della cartella Database/
3. I backup sono in Database/backups/ in caso di corruzione

### Video non salvati
1. Verifica spazio disco disponibile
2. Controlla che la cartella archivio/ sia scrivibile
3. Video > 50MB vengono rifiutati

### Operatore non trova appartamento con GPS
1. Verifica che l'appartamento abbia coordinate in colonna M
2. Le coordinate devono essere nel formato `lat,lon`
3. La tolleranza è 300 metri

---

## 📞 Supporto Tecnico

Per problemi tecnici non risolvibili:
1. Salva i log del bot
2. Fai backup dei file Excel
3. Contatta lo sviluppatore

---

*Guida aggiornata: Dicembre 2025*
