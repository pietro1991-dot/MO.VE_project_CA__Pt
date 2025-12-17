# 🔄 FLUSSO OPERATIVO MO.VE - Processo Pulizie e Lavanderia

## Diagramma del Processo

```
                    ┌─────────────────────┐
                    │  Trigger = checkout │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────────────┐
                    │ Elaborazione da coordinatrice│
                    └──────────┬──────────────────┘
                               │
                               ▼
                    ┌─────────────────────────────┐
                    │  Generazione Report Pulizie │
                    └──────────┬──────────────────┘
                               │
              ┌────────────────┴────────────────┐
              │                                 │
              ▼                                 ▼
    ┌─────────────────┐               ┌─────────────────────┐
    │ Operatore Pulizie│               │ Operatore Lavanderia │
    └────────┬────────┘               └──────────┬──────────┘
             │                                   │
             ▼                                   ▼
      [Flusso Pulizie]                    [Flusso Lavanderia]
```

---

## 🔵 FASE INIZIALE

### 1. Trigger = Checkout
Il processo si attiva quando c'è un **checkout** programmato.

### 2. Elaborazione da Coordinatrice
La coordinatrice elabora le informazioni e prepara il lavoro.

### 3. Generazione Report Pulizie
Viene generato il report pulizie giornaliero con tutti gli appartamenti da gestire.

---

## 🟣 RAMO 1: OPERATORE PULIZIE

### Operatore Pulizie (Operazioni NO CHECK-IN)

1. **Rifornimento materiale pulizie a consumo**
2. **Rifornimento Materiali in appartamento per pulizie:**
   - Mocio con bastone e secchio
   - Scopa
   - Paletta
   - Sacchi del pattume per clienti
   - Pastiglie lavastoviglie per clienti
   - Piatti, Tazze e Bicchieri
   - Pinze
   - Scopettino del cesso
3. **Controllo stock lenzuola e segnalazione appartamento per emergenza** (possibilità di integrare questa logica sul web app in modo che sarà possibile vedere le operazioni solo autonomamente)

---

### Operatore Pulizie (Operazioni IN LOCO)

1. Ricezione CONF_A DA OPERATORE_A
2. *(Opzionale)* Preparazione CONF_B (da realizzare ad operatore A o ad operatore B)
3. Cambio Lenzuola
4. Pulizia Bagno
5. Pulizia Cucina
6. Posizionamento materiale per soggiorno clienti (cialde, asciugamani)
7. Lavaggio Pavimenti

---

### Materiali per Pulizie a Consumo
*(Operazioni magazzino - Materiali per effettuare la pulizia ad OPERATORE_A, non consegnato per clienti)*

1. Sgrassatore
2. Sgrassatore universale (adatto anche ai vetri)
3. Sgrassatore anticalcare
4. Lava WC
5. Vetril
6. Candeggina
7. Lavapavimenti

---

### Materiali per Pulizie e Soggiorno Ospiti in Appartamento
*(Operazione universale da lasciare, rifornire e pulire. Consegnato a operatore pulizie)*

- Mocio con bastone e secchio
- Scopa
- Paletta
- Sacchi del pattume per clienti
- Pastiglie lavastoviglie per clienti
- Piatti, Tazze e Bicchieri
- Pinze
- Scopettino del cesso

---

## 🟣 RAMO 2: OPERATORE LAVANDERIA

### Operatore A (Operazioni)

**OPERAZIONE: PREPARAZIONE CONF_A**
- Lenzuola
- Asciugamani
- Carta igienica
- Shampoo e sapone
- Tappetini bagno
- Cioccolatino sul cuscino (welcome gift)
- Cialde del caffè
- Tovaglioli

---

### Operatore B (Operazioni GIORNALIERE)

1. Ricezione CONF_B da operatore A (ricezione merce per lavaggio corretto)
2. Lavaggio
3. Asciugatura
4. Stiratura
5. Posizionamento in scaffali

---

### Operatore B (Operazioni ANNUALI)

6. Selezione lenzuola macchiate
7. Posizionamento e stoccaggio lenzuola macchiate (separate in attesa di trattamento)

---

### Operatore B (Operazioni MENSILI)

4. Lavaggio Piumoni
5. Risciacquo e passaggio asciugatura Piumoni
6. Controllo pulizia e scarico piumoni
7. Tirare e riporre nelle macchine

---

### Operatore B (Operazioni SETTIMANALI)

8. Lavaggio degli articoli da stiro
9. Asciugatura aria calda fino a fine ciclo
10. Posizionamento e stoccaggio articoli finiti

---

### Operatore A (Autista/Lavanderia)

1. Consegna CONF_A al OPERATORE PULIZIE
2. Ritiro CONF_B:
   - Lenzuola sporche
   - Asciugamani sporchi
   - Federe e trapuntino sporchi (se operatore pulisce)
3. Consegna CONF_B a OPERATORE_B

---

## 📊 SCHEMA RIASSUNTIVO DEI FLUSSI

```
CHECKOUT
    │
    ▼
COORDINATRICE → Genera Report
    │
    ├──────────────────────────────────────────┐
    │                                          │
    ▼                                          ▼
OPERATORE PULIZIE                    OPERATORE LAVANDERIA
    │                                          │
    │                                    ┌─────┴─────┐
    │                                    │           │
    │                                    ▼           ▼
    │                              OPERATORE A   OPERATORE B
    │                              (Preparazione) (Lavaggio)
    │                                    │           │
    │                                    │           │
    │◄───────── CONF_A ─────────────────┘           │
    │                                               │
    │──────────── CONF_B ──────────────────────────►│
    │           (lenzuola sporche)                  │
    ▼                                               ▼
PULIZIA APPARTAMENTO                    LAVAGGIO E STOCCAGGIO
```

---

## 📦 LEGENDA CONF (Confezioni)

| Codice | Contenuto | Direzione |
|--------|-----------|-----------|
| **CONF_A** | Lenzuola pulite, asciugamani, materiali per ospiti | Lavanderia → Pulizie |
| **CONF_B** | Lenzuola sporche, asciugamani sporchi | Pulizie → Lavanderia |

---

## 👥 RUOLI COINVOLTI

| Ruolo | Responsabilità Principale |
|-------|---------------------------|
| **Coordinatrice** | Elaborazione checkout, generazione report |
| **Operatore Pulizie** | Pulizia appartamenti, cambio lenzuola, rifornimento |
| **Operatore A (Lavanderia)** | Preparazione CONF_A con materiali puliti |
| **Operatore B (Lavanderia)** | Lavaggio, asciugatura, stiratura, stoccaggio |
| **Autista/Lavanderia** | Consegna CONF_A, ritiro CONF_B |

---

## ⚠️ NOTE IMPORTANTI

1. **CONF_A** deve essere preparata PRIMA che l'operatore pulizie arrivi all'appartamento
2. **CONF_B** viene ritirata DOPO la pulizia dell'appartamento
3. Le lenzuola macchiate richiedono trattamento speciale (stoccaggio separato)
4. Il controllo stock lenzuola può attivare segnalazioni di emergenza

---

*Documento generato dal diagramma Lucidspark MO.VE*
*Ultimo aggiornamento: Dicembre 2024*
