"""
Parser PDF intelligente con GPT-3.5-turbo
Estrae appartamenti dal PDF usando AI invece di regex
INTERPRETA NOTE per calcolare materiali extra automaticamente
USA PRE-FILTRO per ridurre token inviati a GPT (ottimizzazione costi)
"""

import os
import json
import logging
import re
import pandas as pd
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class GPTPDFParser:
    """Parser PDF con GPT-3.5-turbo per riconoscimento intelligente appartamenti"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Inizializza parser GPT con prompts da Config/gpt_prompts.json
        
        Args:
            api_key: OpenAI API key (se None, cerca in Config/gpt_api_key.txt)
        """
        # Percorsi Config (parent di funzioni/)
        base_dir = os.path.dirname(os.path.dirname(__file__))
        config_dir = os.path.join(base_dir, 'Config')
        api_key_file = os.path.join(config_dir, 'gpt_api_key.txt')
        prompts_file = os.path.join(config_dir, 'gpt_prompts.json')
        
        # Carica API key
        if api_key:
            self.api_key = api_key
        else:
            if os.path.exists(api_key_file):
                with open(api_key_file, 'r', encoding='utf-8-sig') as f:  # utf-8-sig rimuove BOM automaticamente
                    self.api_key = f.read().strip()
                    # Rimuovi eventuali caratteri invisibili residui
                    self.api_key = self.api_key.replace('\ufeff', '').replace('\u200b', '')
                logger.info("✅ OpenAI API key caricata da Config/gpt_api_key.txt")
            else:
                self.api_key = None
                logger.warning("⚠️ OpenAI API key non trovata - Parser GPT disabilitato")
        
        # Carica prompts da JSON
        self.prompts = {}
        if os.path.exists(prompts_file):
            try:
                with open(prompts_file, 'r', encoding='utf-8-sig') as f:  # utf-8-sig rimuove BOM automaticamente
                    self.prompts = json.load(f)
                logger.info("✅ Prompts GPT caricati da Config/gpt_prompts.json")
            except Exception as e:
                logger.error(f"❌ Errore caricamento prompts: {e}")
                self.prompts = {}
        else:
            logger.warning(f"⚠️ File prompts non trovato: {prompts_file}, uso prompts default")
        
        # Inizializza client OpenAI
        self.client = None
        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
                self.model = "gpt-4o-mini"  # GPT-4o-mini: economico ma 16K output tokens
                logger.info(f"✅ GPT Parser inizializzato con modello {self.model}")
            except ImportError as e:
                logger.error(f"❌ Libreria 'openai' non installata: {e}")
                logger.error("Installa con: pip install openai")
                self.client = None
            except Exception as e:
                logger.error(f"❌ Errore inizializzazione OpenAI client: {e}")
                self.client = None
    
    def is_available(self) -> bool:
        """Verifica se GPT parser è disponibile"""
        is_avail = self.client is not None
        if not is_avail:
            logger.warning("⚠️ GPT Parser non disponibile - client OpenAI è None")
        return is_avail
    
    def generate_daily_report(self, pdf_path: str) -> dict:
        """
        Genera report giornaliero da PDF usando GPT parser.
        Metodo compatibile con pdf_parser.py classico.
        
        Args:
            pdf_path: Percorso al file PDF
            
        Returns:
            Report dict con 'tasks' e metadati
        """
        if not self.is_available():
            logger.warning("GPT Parser non disponibile")
            return {'tasks': [], 'pdf_source': pdf_path}
        
        try:
            # Estrai testo da PDF
            import pdfplumber
            pdf_text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    pdf_text += page.extract_text() or ""
            
            logger.info(f"📄 PDF estratto: {len(pdf_text)} caratteri")
            
            # Salva TXT estratto in sottocartella pdf_to_txt_input (a root del bot)
            bot_dir = os.path.dirname(os.path.dirname(__file__))
            pdf_input_dir = os.path.join(bot_dir, 'pdf_input')
            txt_extracted_dir = os.path.join(pdf_input_dir, 'pdf_to_txt_input')
            os.makedirs(txt_extracted_dir, exist_ok=True)
            
            timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
            txt_path = os.path.join(txt_extracted_dir, f'estratto_{timestamp}.txt')
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(pdf_text)
            logger.info(f"💾 TXT estratto salvato: {txt_path}")
            
            # Pulisci testo da BOM e caratteri speciali che causano errori Unicode
            pdf_text = pdf_text.replace('\ufeff', '')  # BOM
            pdf_text = pdf_text.replace('\u200b', '')  # Zero-width space
            pdf_text = pdf_text.replace('\xa0', ' ')   # Non-breaking space → spazio normale
            # Rimuovi caratteri di controllo (mantieni solo newline e tab)
            pdf_text = ''.join(char for char in pdf_text if ord(char) >= 32 or char in '\n\r\t')
            logger.info(f"🧹 Testo pulito: {len(pdf_text)} caratteri")
            
            # Carica database appartamenti
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            appartamenti_file = os.path.join(base_dir, 'Database', 'appartamenti.xlsx')
            
            if not os.path.exists(appartamenti_file):
                logger.error(f"File appartamenti non trovato: {appartamenti_file}")
                return {'tasks': [], 'pdf_source': pdf_path}
            
            df_appartamenti = pd.read_excel(appartamenti_file)
            logger.info(f"📊 Database appartamenti: {len(df_appartamenti)} record")
            
            # Parse con GPT
            tasks = self.parse_pdf_text(pdf_text, df_appartamenti)
            
            return {
                'tasks': tasks,
                'pdf_source': os.path.basename(pdf_path),
                'parser_used': 'GPT-3.5-turbo',
                'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"❌ Errore generate_daily_report GPT: {e}")
            import traceback
            traceback.print_exc()
            return {'tasks': [], 'pdf_source': pdf_path}
    
    def parse_pdf_text(self, pdf_text: str, df_appartamenti: pd.DataFrame) -> List[Dict]:
        """
        Estrae appartamenti dal testo PDF usando GPT con interpretazione NOTE
        
        Args:
            pdf_text: Testo estratto dal PDF
            df_appartamenti: DataFrame con appartamenti master
            
        Returns:
            Lista di task con materiali_extra interpretati da GPT
        """
        if not self.is_available():
            logger.warning("GPT Parser non disponibile - usa parser classico")
            return []
        
        try:
            # INVIA TUTTI GLI APPARTAMENTI A GPT (pre-filtro rimosso)
            logger.info("📊 Invio database completo a GPT (senza pre-filtro)...")
            appartamenti_master = []
            for _, apt in df_appartamenti.iterrows():
                appartamenti_master.append({
                    'nome_ciao': apt['Ciao Booking Nome'],
                    'nome_ota': str(apt.get('Nome OTA', '')),
                    'indirizzo': apt['Indirizzo'],
                    'camere_matrimoniali': int(apt.get('Camere Matrimoniali', 0)),
                    'camere_singole': int(apt.get('Camere Singole', 0)),
                    'bagni': int(apt.get('Bagni', 0))
                })
            
            logger.info(f"✅ Database completo preparato: {len(appartamenti_master)} appartamenti totali")
            
            # Carica prompts da Config o usa default
            system_prompt = self.prompts.get('pdf_parser_system', self._get_default_system_prompt())
            user_template = self.prompts.get('pdf_parser_user_template', self._get_default_user_template())
            
            # Limita testo PDF per token
            pdf_text_limited = pdf_text[:8000]
            
            # Costruisci user prompt con template (SOLO appartamenti filtrati)
            user_prompt = user_template.format(
                appartamenti_json=json.dumps(appartamenti_master, indent=2, ensure_ascii=False),
                pdf_text=pdf_text_limited
            )

            # Chiama GPT per parsing PDF
            logger.info("📡 Chiamata GPT-4o-mini per parsing PDF...")
            logger.info(f"   📤 Token INVIATI (stimati): ~{len(system_prompt)//4 + len(user_prompt)//4} token")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=8000
            )
            
            # Log uso token da risposta GPT
            usage = response.usage
            logger.info(f"   📊 TOKEN USAGE:")
            logger.info(f"      • Input (prompt): {usage.prompt_tokens} token")
            logger.info(f"      • Output (risposta): {usage.completion_tokens} token")
            logger.info(f"      • TOTALE: {usage.total_tokens} token")
            
            # Calcola costo approssimativo (GPT-3.5-turbo pricing)
            cost_input = (usage.prompt_tokens / 1000) * 0.0005  # $0.0005 per 1K input tokens
            cost_output = (usage.completion_tokens / 1000) * 0.0015  # $0.0015 per 1K output tokens
            total_cost = cost_input + cost_output
            logger.info(f"      💰 Costo stimato: ${total_cost:.6f} (~€{total_cost * 0.95:.6f})")
            
            # Parse risposta JSON
            content = response.choices[0].message.content.strip()
            result = json.loads(content)
            appartamenti_gpt = result.get('appartamenti', [])
            
            logger.info(f"✅ GPT ha trovato {len(appartamenti_gpt)} appartamenti")
            
            # Converti in formato task con materiali_extra
            tasks = []
            for apt_gpt in appartamenti_gpt:
                usa_note_come_titolo = apt_gpt.get('usa_note_come_titolo', False)
                nome_master = apt_gpt.get('nome_master_matched', apt_gpt.get('nome_master', ''))
                
                # CASO SPECIALE: Appartamento generico (APPARTAMENTO DA PULIRE)
                if usa_note_come_titolo:
                    logger.info(f"🏷️  Appartamento GENERICO rilevato - titolo dalle note")
                    # Crea task generico senza match al database
                    apt_row = None
                    nome_master = 'GENERICO'
                else:
                    if not nome_master:
                        continue
                    
                    # Trova appartamento master
                    apt_master = df_appartamenti[
                        df_appartamenti['Ciao Booking Nome'].str.contains(nome_master, case=False, na=False, regex=False)
                    ]
                    
                    if apt_master.empty:
                        # Prova fuzzy match più permissivo
                        for _, row in df_appartamenti.iterrows():
                            if nome_master.lower() in row['Ciao Booking Nome'].lower() or \
                               row['Ciao Booking Nome'].lower() in nome_master.lower():
                                apt_master = pd.DataFrame([row])
                                break
                    
                    if apt_master.empty:
                        logger.warning(f"⚠️ '{nome_master}' non trovato in master - skip")
                        continue
                    
                    apt_row = apt_master.iloc[0]
                
                # Determina tipo pulizia e tipo_task normalizzato
                tipo_evento = apt_gpt.get('tipo_evento', 'Check-in')
                if 'out' in tipo_evento.lower() or 'partenza' in tipo_evento.lower():
                    tipo_pulizia = 'Pulizia Ordinaria'
                    tipo_task_normalized = 'check-out'
                else:
                    tipo_pulizia = 'Cambio Biancheria'
                    tipo_task_normalized = 'check-in'
                
                # Crea task (con note complete per appartamenti generici)
                if usa_note_come_titolo:
                    # Task GENERICO - usa note come titolo
                    note_raw = apt_gpt.get('note_raw', apt_gpt.get('note', ''))
                    task = {
                        'nome_proprieta': 'APPARTAMENTO GENERICO',
                        'nome_ota': note_raw[:100] if note_raw else 'Dettagli nelle note',  # Prime 100 char note
                        'indirizzo': 'Da definire',
                        'tipo_evento': tipo_evento,
                        'tipo_pulizia': tipo_pulizia,
                        'tipo_task': tipo_task_normalized,
                        'num_persone': int(apt_gpt.get('num_persone', 1)),
                        
                        # NOTE COMPLETE
                        'note_raw': note_raw,
                        
                        # FLAG appartamento generico
                        'titolo_note': True,
                        'appartamento_generico': True,
                        
                        # Dati minimi (senza match DB)
                        'camere_matrimoniali': 0,
                        'camere_singole': 0,
                        'bagni': 1,
                        'magazzino': 'N/A',
                        'destinazione_riferimento': 'Da definire',
                        'operatore': apt_gpt.get('operatore_pdf', 'Non assegnato'),
                        'non_identificato': False,
                        'confidence_gpt': apt_gpt.get('confidence', 0.5),
                        'raw_context': note_raw,
                    }
                else:
                    # Task NORMALE - da database
                    task = {
                        'nome_proprieta': apt_row['Ciao Booking Nome'],
                        'nome_ota': apt_gpt.get('nome_pdf', apt_row.get('Nome OTA', '')),
                        'indirizzo': apt_row['Indirizzo'],
                        'tipo_evento': tipo_evento,
                        'tipo_pulizia': tipo_pulizia,
                        'tipo_task': tipo_task_normalized,
                        'num_persone': int(apt_gpt.get('num_persone', 2)),
                        
                        # NOTE COMPLETE dal PDF
                        'note_raw': apt_gpt.get('note_raw', apt_gpt.get('note', '')),
                        
                        # FLAG
                        'titolo_note': False,
                        'appartamento_generico': False,
                        
                        # Confidence
                        'confidence_gpt': apt_gpt.get('confidence', 0.8),
                        'raw_context': f"GPT Match: {apt_gpt.get('nome_pdf', 'N/A')} -> {apt_row['Ciao Booking Nome']} (confidence: {apt_gpt.get('confidence', 0.8):.2f})",
                        
                        # Info strutturali da master
                        'camere_matrimoniali': int(apt_row.get('Camere Matrimoniali', 0)),
                        'camere_singole': int(apt_row.get('Camere Singole', 0)),
                        'bagni': int(apt_row.get('Bagni', 0)),
                        'magazzino': apt_row.get('Destinazione_Riferimento', 'N/A'),
                        'ha_cantina': str(apt_row.get('Cantina', 'Falso')).lower() == 'vero',
                        'destinazione_riferimento': apt_row.get('Destinazione_Riferimento', 'Abitazione/cantina'),
                        'operatore': apt_gpt.get('operatore_pdf', apt_row.get('Operatore', 'Non assegnato')),
                        'pulizie_interne': apt_row.get('Pulizie Interne', 'Vero'),  # Campo per distinguere esterni
                        'non_identificato': False,
                    }
                
                tasks.append(task)
            
            # Log finale
            if tasks:
                logger.info(f"📊 GPT Parser: {len(tasks)} task creati con successo")
            else:
                logger.warning("⚠️ GPT non ha prodotto task validi")
            
            return tasks
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Errore parsing JSON da GPT: {e}")
            logger.error(f"Risposta GPT: {content if 'content' in locals() else 'N/A'}")
            return []
        except Exception as e:
            logger.error(f"❌ Errore GPT parsing: {e}")
            import traceback
            traceback.print_exc()
            return []
    

    
    def _get_default_system_prompt(self) -> str:
        """Prompt system di default se gpt_prompts.json non disponibile"""
        return """Sei un assistente esperto nell'analisi di report pulizie appartamenti.
Estrai TUTTI gli appartamenti dal testo PDF e matchali con il database master usando fuzzy matching.
Per appartamenti NON identificabili (es: "APPARTAMENTO DA PULIRE"), usa il campo 'usa_note_come_titolo': true e riporta le note complete.
Rispondi SOLO in JSON senza testo aggiuntivo."""
    
    def _get_default_user_template(self) -> str:
        """Template user prompt di default"""
        return """DATABASE APPARTAMENTI MASTER:
{appartamenti_json}

TESTO PDF DA ANALIZZARE:
{pdf_text}

Estrai tutti gli appartamenti e matchali con il database.
Per appartamenti generici ("APPARTAMENTO DA PULIRE"), usa usa_note_come_titolo=true.
Rispondi in JSON con struttura: appartamenti[nome_pdf, nome_master_matched, confidence, tipo_evento, num_persone, note_raw, usa_note_come_titolo]"""
    
    def _filtra_appartamenti_candidati(self, pdf_text: str, df_appartamenti: pd.DataFrame) -> List[Dict]:
        """
        Pre-filtra appartamenti rilevanti usando fuzzy matching locale (GRATIS).
        Riduce drasticamente i token inviati a GPT (risparmio ~85%).
        
        Args:
            pdf_text: Testo estratto dal PDF
            df_appartamenti: DataFrame completo appartamenti
            
        Returns:
            Lista max 15 appartamenti candidati con score similarità
        """
        # Estrai possibili nomi appartamenti dal PDF con regex
        nomi_pdf = self._estrai_nomi_da_pdf(pdf_text)
        
        if not nomi_pdf:
            logger.warning("⚠️ Nessun nome appartamento riconosciuto nel PDF")
            return []
        
        logger.info(f"   📝 Nomi trovati nel PDF: {nomi_pdf[:5]}...")  # Log primi 5
        
        # Calcola similarità con ogni appartamento nel database
        candidati = []
        for _, apt in df_appartamenti.iterrows():
            nome_db = apt['Ciao Booking Nome']
            nome_ota = str(apt.get('Nome OTA', ''))
            
            # Calcola score massimo tra tutti i nomi trovati nel PDF
            max_score = 0
            for nome_pdf in nomi_pdf:
                # Similarità semplice (ratio di caratteri comuni)
                score = self._fuzzy_ratio(nome_pdf.lower(), nome_db.lower())
                
                # Prova anche con nome OTA se disponibile
                if nome_ota:
                    score_ota = self._fuzzy_ratio(nome_pdf.lower(), nome_ota.lower())
                    score = max(score, score_ota)
                
                max_score = max(max_score, score)
            
            # Aggiungi se similarità sufficiente
            if max_score > 50:  # Threshold: 50% similarità minima
                candidati.append({
                    'nome_ciao': nome_db,
                    'nome_ota': nome_ota,
                    'indirizzo': apt['Indirizzo'],
                    'camere_matrimoniali': int(apt.get('Camere Matrimoniali', 0)),
                    'camere_singole': int(apt.get('Camere Singole', 0)),
                    'bagni': int(apt.get('Bagni', 0)),
                    'score': max_score
                })
        
        # Ordina per score decrescente e prendi top 15
        candidati.sort(key=lambda x: x['score'], reverse=True)
        top_candidati = candidati[:15]
        
        if top_candidati:
            logger.info(f"   🎯 Top candidati:")
            for i, c in enumerate(top_candidati[:3], 1):  # Log top 3
                logger.info(f"      {i}. {c['nome_ciao']} (score: {c['score']}%)")
        
        return top_candidati
    
    def _estrai_nomi_da_pdf(self, pdf_text: str) -> List[str]:
        """
        Estrae possibili nomi appartamenti dal PDF usando pattern comuni.
        
        Returns:
            Lista nomi trovati (anche parziali)
        """
        nomi_trovati = set()
        
        # Processo riga per riga per migliore accuratezza
        for line in pdf_text.split('\n'):
            line = line.strip()
            
            # Pattern 1: Keywords specifiche nel nome (case-insensitive)
            keywords = ['Palace', 'Relax', 'Pastore', 'Parini', 'Formigine', 'Stefania', 'Pioppa', 
                       'Adriano', 'Bellaria', 'Gozzi', 'Next Stop', 'Rua']
            for keyword in keywords:
                if keyword.lower() in line.lower():
                    # Estrai nome fino a "x" o numeri di persone
                    match = re.search(rf'([A-Za-zÀ-ÿ\s\-:\'0-9]*{keyword}[A-Za-zÀ-ÿ\s\-:\'0-9]*?)(?:\s*x\s*\d|\s+\d{{1,2}}\s+NO)', line, re.IGNORECASE)
                    if match:
                        nome = match.group(1).strip()
                        # Pulisci da "x" trailing
                        nome = re.sub(r'\s*x\s*$', '', nome).strip()
                        if len(nome) > 3:
                            nomi_trovati.add(nome)
                            break
        
        # Pattern 2: Linee che iniziano con maiuscola e contengono "x" (numero ospiti)
        pattern_ospiti = r'^([A-Z][A-Za-zÀ-ÿ\s\-\'0-9:]+?)\s*x\s*\d'
        for line in pdf_text.split('\n'):
            match = re.search(pattern_ospiti, line.strip())
            if match:
                nome = match.group(1).strip()
                # Escludi date e numeri puri
                if not re.match(r'^\d', nome) and 'Mercoledì' not in nome and len(nome) > 3:
                    nomi_trovati.add(nome)
        
        # Filtra nomi che contengono parole da escludere
        nomi_filtrati = []
        for nome in nomi_trovati:
            nome_lower = nome.lower()
            if not any(exc in nome_lower for exc in ['gia', 'pulito', 'appartamento da', 'note', 'preparare', 'mercoledì']):
                nomi_filtrati.append(nome)
        
        logger.info(f"   📝 Nomi estratti dal PDF: {nomi_filtrati[:10]}")
        return nomi_filtrati
    
    def _fuzzy_ratio(self, s1: str, s2: str) -> int:
        """
        Calcola similarità tra due stringhe (0-100%).
        Implementazione semplice senza librerie esterne.
        
        Returns:
            Score 0-100 (100 = match perfetto)
        """
        # Rimuovi spazi multipli e normalizza
        s1 = ' '.join(s1.split())
        s2 = ' '.join(s2.split())
        
        # Match esatto
        if s1 == s2:
            return 100
        
        # Substring match
        if s1 in s2 or s2 in s1:
            return 85
        
        # Conta parole in comune
        words1 = set(s1.split())
        words2 = set(s2.split())
        
        if not words1 or not words2:
            return 0
        
        common_words = words1.intersection(words2)
        total_words = words1.union(words2)
        
        # Percentuale parole comuni
        score = int((len(common_words) / len(total_words)) * 100)
        
        return score
