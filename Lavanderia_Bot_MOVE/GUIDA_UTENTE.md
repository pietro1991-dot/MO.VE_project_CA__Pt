# 📖 GUIDA UTENTE - Bot Lavanderia MO.VE

## Indice
1. [Introduzione](#introduzione)
2. [Come Usare il Bot](#come-usare-il-bot)
3. [Struttura del PDF Generato](#struttura-del-pdf-generato)
4. [Leggere il Report: Simboli e Colori](#leggere-il-report-simboli-e-colori)
5. [Pulizie Esterne vs Interne](#pulizie-esterne-vs-interne)
6. [Materiali e Calcoli Automatici](#materiali-e-calcoli-automatici)
7. [File di Configurazione](#file-di-configurazione)
8. [Risoluzione Problemi](#risoluzione-problemi)

---

## Introduzione

Il **Bot Lavanderia MO.VE** è uno strumento Telegram che automatizza la gestione dei report pulizie giornalieri. Riceve un PDF con le prenotazioni del giorno, lo analizza e genera:

- Un **report PDF professionale** con percorso ottimizzato
- Un **sommario per operatore** con gli immobili assegnati
- Il **calcolo automatico dei materiali** necessari
- Un **link Google Maps** per il percorso ottimale

---

## Come Usare il Bot

### Passo 1: Avviare il Bot
1. Apri Telegram e cerca il bot
2. Invia il comando `/start`
3. Apparirà il pulsante **"📄 Carica PDF Pulizie"**

### Passo 2: Caricare il PDF
1. Clicca su **"📄 Carica PDF Pulizie"**
2. Il bot chiederà di inviare il file PDF
3. Carica il PDF delle prenotazioni giornaliere (es. export da Ciao Booking)
4. Attendi l'elaborazione (circa 10-30 secondi)

### Passo 3: Ricevere il Report
Il bot invierà:
- ✅ Un **file PDF** con il report completo
- ✅ Un **messaggio riepilogativo** con statistiche e link Google Maps

---

## Struttura del PDF Generato

Il PDF è organizzato in sezioni logiche per facilitare la lettura:

### 📊 1. RIEPILOGO GENERALE
Prima pagina con:
- **Totale Appartamenti** da pulire nel giorno
- Data del report

### 👤 2. SOMMARIO PER OPERATORE
Sezione che raggruppa tutti gli immobili **per operatore assegnato**:

```
👤 Maria Rossi (4 immobili)
   1. Casa Blu | Check-in | 👥 4 pers. | 📍 Via Roma 10...
   2. Apt Centro | Check-out | 👥 2 pers. | 📍 Piazza Dante...
   ...

👤 Giovanni Bianchi (3 immobili)
   1. Villa Mare | Check-in | 👥 6 pers. | 📍 Lungomare 5...
   ...
```

> **💡 Suggerimento:** Ogni operatore può guardare solo la sua sezione per sapere rapidamente cosa deve fare!

### 🗺️ 3. PERCORSO OTTIMIZZATO
Informazioni sul percorso calcolato da Google Maps:
- **Distanza totale** in km
- **Durata stimata** in minuti
- **Link Google Maps** cliccabile per la navigazione

### 📦 4. MATERIALI NECESSARI TOTALI
Tabella con tutti i materiali da preparare per l'intera giornata:

| Materiale | Quantità |
|-----------|----------|
| Carta Igienica | 24 pz |
| Asciugamani Grandi | 18 pz |
| Set Lenzuola Matrimoniali | 8 set |
| Cialde Caffè | 40 pz |
| ... | ... |

### 📋 5. LISTA APPARTAMENTI (Dettaglio)
Dalla seconda pagina, ogni appartamento ha un box dedicato con:

```
┌─────────────────────────────────────────────────┐
│ #1 - Nome Appartamento                          │  ← Header (blu o arancione)
├─────────────────────────────────────────────────┤
│ 👤 Operatore: Maria Rossi                       │
│ 🔑 MATERIALI IN CANTINA                         │  ← Dove lasciare i materiali
│ 🏠 Check-in - Pulizia completa                  │
│ 📍 Via Roma 10, Milano                          │
│ 👥 4 persone | 🛏️ 2M + 1S | 🚿 2 bagni         │
├─────────────────────────────────────────────────┤
│ 📦 Materiali:                                   │
│ • Carta Igienica: 4 pz                          │
│ • Asciugamani Grandi: 4 pz                      │
│ • Set Lenzuola Matrimoniali: 2 set              │
│ • Cialde Caffè: 8 pz                            │
│ ☕ Macchina caffè: Nespresso                    │
├─────────────────────────────────────────────────┤
│ 📝 NOTE: Ospiti arrivano alle 15:00             │
└─────────────────────────────────────────────────┘
```

---

## Leggere il Report: Simboli e Colori

### Simboli Utilizzati

| Simbolo | Significato |
|---------|-------------|
| 👤 | Operatore assegnato |
| 📍 | Indirizzo dell'immobile |
| 👥 | Numero persone in arrivo |
| 🛏️ | Camere (M=Matrimoniali, S=Singole) |
| 🚿 | Numero bagni |
| 📦 | Materiali da portare |
| ☕ | Tipo macchina caffè |
| 📝 | Note speciali |
| 🔑 | Materiali da lasciare in cantina |
| ⬆️ | Salire in appartamento con materiali |
| 🔶 | **ATTENZIONE: Pulizie esterne!** |

### Codice Colori Header Appartamento

| Colore | Significato |
|--------|-------------|
| 🔵 **BLU** | Appartamento con pulizie **INTERNE** (gestite da noi) |
| 🟠 **ARANCIONE** | Appartamento con pulizie **ESTERNE** (solo materiali!) |

---

## Pulizie Esterne vs Interne

### ⚠️ ATTENZIONE ALLE PULIZIE ESTERNE!

Alcuni appartamenti hanno le **pulizie gestite esternamente** (non da noi). Questi sono evidenziati con:
- Header **ARANCIONE** invece che blu
- Badge **🔶 ESTERNO** nel titolo

### Cosa significa "Pulizie Esterne"?

| Aspetto | Pulizie INTERNE | Pulizie ESTERNE 🔶 |
|---------|-----------------|-------------------|
| Chi pulisce? | Il nostro team | Team esterno |
| Materiali | Li portiamo NOI | Li portiamo NOI |
| Lenzuola | Le prepariamo NOI | Le prepariamo NOI |
| Pulizia fisica | La facciamo NOI | **NON** la facciamo |

> **📌 IMPORTANTE:** Per gli appartamenti ESTERNI dobbiamo comunque preparare e consegnare i materiali (lenzuola, asciugamani, prodotti), ma **NON effettuiamo la pulizia fisica**.

### Come Riconoscerli nel PDF

1. **Nel Sommario Operatore:** Badge 🔶 accanto al nome
2. **Nella Lista Dettagliata:** 
   - Header ARANCIONE invece che blu
   - Scritta "🔶 ESTERNO" nel titolo

---

## Materiali e Calcoli Automatici

Il sistema calcola automaticamente i materiali basandosi su:

### Regole per Bagno
I materiali bagno vengono calcolati in base a:
- **Per persona**: alcuni articoli moltiplicati per numero ospiti
- **Per bagno**: altri articoli moltiplicati per numero bagni

### Regole per Camera
- **Set lenzuola matrimoniali**: 1 set per ogni camera matrimoniale
- **Set lenzuola singole**: 1 set per ogni camera singola

### Regole Cucina
Articoli base per ogni appartamento (cialde caffè, detersivi, ecc.)

### Dove Lasciare i Materiali

Nel report vedrai una delle seguenti indicazioni:

| Indicazione | Cosa Fare |
|-------------|-----------|
| 🔑 MATERIALI IN CANTINA | L'appartamento ha cantina, lascia lì i materiali |
| ⬆️ SALIRE IN APPARTAMENTO | Porta i materiali direttamente nell'appartamento |
| 📦 PORTARE IN MAGAZZINO: [Nome] | Porta al magazzino indicato |

---

## File di Configurazione

Il sistema usa diversi file di configurazione nella cartella `Config/`:

| File | Descrizione |
|------|-------------|
| `telegram_bot_token.txt` | Token del bot Telegram |
| `gpt_api_key.txt` | Chiave API OpenAI per parsing PDF |
| `google_maps_api_key.txt` | Chiave Google Maps per percorsi |
| `gpt_prompts.json` | Prompts per l'analisi GPT |

### File Regole Materiali
Nella cartella `Database/Regole/`:

| File | Descrizione |
|------|-------------|
| `regole_materiali.xlsx` | Regole calcolo materiali (bagno + cucina) |

#### Struttura regole_materiali.xlsx

**Foglio "Regole per Bagno":**
| Articolo | Quantità per Bagno | Tipo Calcolo | Note |
|----------|-------------------|--------------|------|
| Carta Igienica | 2 | 2 | |
| Asciugamani | 1 | 1 | |

**Foglio "Regole Cucina":**
| Articolo | Quantità Base | Tipo Calcolo | Note |
|----------|--------------|--------------|------|
| Cialde caffè | 4 | 1 | |
| Sacchetti spazzatura | 2 | 2 | |

**Codici Tipo Calcolo:**
- `1` = Moltiplica per numero **persone**
- `2` = Moltiplica per numero **bagni**
- `0` = Solo messaggio informativo (non conta)

---

## Risoluzione Problemi

### Il bot non risponde
1. Verifica che il bot sia in esecuzione
2. Controlla il file `telegram_bot_token.txt`
3. Riavvia il bot con `python bot.py`

### PDF non elaborato correttamente
1. Verifica che il PDF sia un export valido da Ciao Booking
2. Controlla che `gpt_api_key.txt` contenga una chiave valida
3. Verifica i log nella cartella `logs/`

### Materiali non calcolati
1. Verifica che l'appartamento esista in `Database/appartamenti.xlsx`
2. Controlla che il nome corrisponda esattamente alla colonna "Ciao Booking Nome"
3. Se l'appartamento non viene trovato, vengono usati materiali minimi standard

### Percorso Google Maps non funziona
1. Verifica `google_maps_api_key.txt`
2. Controlla che gli indirizzi siano corretti nel database appartamenti

### Operatore non assegnato
Se vedi "Non assegnato" come operatore:
1. L'appartamento non ha operatore nel database
2. Oppure il PDF non contiene l'informazione operatore

---

## File Generati

Ogni elaborazione crea file nelle seguenti cartelle:

| Cartella | Contenuto |
|----------|-----------|
| `pdf_input/` | PDF originali caricati (con timestamp) |
| `pdf_output/` | Report PDF generati |
| `logs/` | File di log dettagliati per debug |

---

## Contatti e Supporto

Per problemi tecnici o modifiche al sistema, contattare l'amministratore.

---

*Guida aggiornata: Dicembre 2024*
*Bot Lavanderia MO.VE - Versione 1.0*
