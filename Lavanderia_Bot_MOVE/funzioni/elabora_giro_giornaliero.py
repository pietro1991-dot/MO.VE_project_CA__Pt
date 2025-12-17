"""
SCRIPT MASTER - MO.VE Property Management
Elabora PDF booking giornaliero → Organizza giro → Calcola materiali → Invia email

INPUT: PDF in "Planning pulizie giornaliero input/"
OUTPUT: Email con lista ordinata + materiali per ogni tappa
"""

import os
import sys
import glob
import json
from datetime import datetime
import pandas as pd

from route_optimizer import RouteOptimizer
from gpt_pdf_parser import GPTPDFParser


class MasterProcessor:
    """Processore master per workflow completo (solo GPT parser)"""
    
    def __init__(self):
        # Base dir è la root del bot (parent di funzioni/)
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        
        # Directory input PDF
        self.input_dir = os.path.join(self.base_dir, 'pdf_input')
        
        # Carica regole materiali
        self.regole_bagno = self._load_regole_bagno()
        self.regole_camera = self._load_regole_camera()
        self.regole_cucina = self._load_regole_cucina()
        
        # Parser PDF con GPT (unico parser)
        self.gpt_parser = GPTPDFParser()
        
        # Route optimizer
        self.route_optimizer = RouteOptimizer()
        
        print("[OK] Master Processor inizializzato")
    
    def _load_regole_bagno(self):
        """Carica regole materiali per bagno da Excel con tipo_calcolo dinamico"""
        # Database condiviso a livello superiore
        regole_path = os.path.join(os.path.dirname(self.base_dir), 'Database', 'Regole', 'regole_materiali.xlsx')
        
        if not os.path.exists(regole_path):
            print("[ERROR] File regole_materiali.xlsx NON trovato!")
            print(f"[ERROR] Percorso atteso: {regole_path}")
            raise FileNotFoundError(f"File regole_materiali.xlsx obbligatorio non trovato in {regole_path}")
        
        df = pd.read_excel(regole_path, sheet_name='Regole per Bagno', skiprows=1)
        regole = []
        
        for _, row in df.iterrows():
            articolo = str(row['Articolo']).strip()
            qty = row['Quantità per Bagno']
            tipo_calcolo = int(row['se 1=per persona se 2=per numero di bagni se 0= commento in cella di fianco'])
            
            # Leggi messaggio dalla colonna Note (se presente)
            messaggio = row.get('Note', row.get('se 1=per persona se 2=per numero di bagni se 0= commento in cella di fianco', '')) if tipo_calcolo == 0 else ''
            
            regole.append({
                'articolo': articolo,
                'quantita': int(qty) if pd.notna(qty) else 0,
                'tipo_calcolo': tipo_calcolo,  # 1=persona, 2=bagni, 0=messaggio
                'messaggio': str(messaggio).strip() if pd.notna(messaggio) and messaggio else ''
            })
        
        print(f"[OK] Caricate regole bagno: {len(regole)} articoli")
        return regole
    
    def _load_regole_camera(self):
        """
        Carica regole camera (attualmente non utilizzate - lenzuola calcolate 1:1 con num camere).
        Mantenuto per compatibilità futura se servissero regole speciali per tipologie camere.
        """
        # Le lenzuola sono calcolate automaticamente 1:1 con numero camere dal DB appartamenti
        # Questa funzione è mantenuta per futura estensibilità (es: regole speciali per camere doppie)
        return {
            'matrimoniale': 1,  # 1 set per camera matrimoniale
            'singola': 1,       # 1 set per camera singola
            'doppia': 2         # 2 set per camera doppia (se mai usata)
        }
    
    def _load_regole_cucina(self):
        """Carica regole materiali cucina da Excel con tipo_calcolo dinamico"""
        # Database condiviso a livello superiore
        regole_path = os.path.join(os.path.dirname(self.base_dir), 'Database', 'Regole', 'regole_materiali.xlsx')
        
        if not os.path.exists(regole_path):
            print("[ERROR] File regole_materiali.xlsx NON trovato!")
            print(f"[ERROR] Percorso atteso: {regole_path}")
            raise FileNotFoundError(f"File regole_materiali.xlsx obbligatorio non trovato in {regole_path}")
        
        df = pd.read_excel(regole_path, sheet_name='Regole Cucina', skiprows=1)
        regole = []
        
        for _, row in df.iterrows():
            articolo = str(row['Articolo']).strip()
            qty = row['Quantità Base']
            tipo_calcolo = int(row['se 1=per persona se 2=per numero di bagni se 0= commento in cella di fianco'])
            note = row.get('Note', '')
            
            regole.append({
                'articolo': articolo,
                'quantita': int(qty) if pd.notna(qty) else 0,
                'tipo_calcolo': tipo_calcolo,  # 1=persona, 2=bagni, 0=messaggio
                'messaggio': str(note).strip() if pd.notna(note) and note else ''
            })
        
        print(f"[OK] Caricate regole cucina: {len(regole)} articoli")
        return regole
    
    def calcola_materiali_intelligente(self, appartamento_info, num_persone):
        """
        Calcola materiali usando regole dinamiche da Excel:
        - tipo_calcolo = 1: moltiplica per num_persone
        - tipo_calcolo = 2: moltiplica per num_bagni
        - tipo_calcolo = 0: messaggio informativo (non conta nelle somme)
        """
        
        materiali = {}
        messaggi_info = []
        
        # Ottieni info appartamento
        num_bagni = int(appartamento_info.get('Bagni', 1))
        num_camere_matrimoniali = int(appartamento_info.get('Camere Matrimoniali', 0))
        num_camere_singole = int(appartamento_info.get('Camere Singole', 0))
        tipo_macchina_caffe = appartamento_info.get('Tipologia Cialde Caffè', 'Non specificata')
        
        # === REGOLE PER BAGNO (dinamiche) ===
        for regola in self.regole_bagno:
            articolo = regola['articolo']
            qty_base = regola['quantita']
            tipo_calcolo = regola['tipo_calcolo']
            messaggio = regola.get('messaggio', '')
            
            articolo_key = articolo.lower().replace(' ', '_').replace('/', '_')
            
            if tipo_calcolo == 1:
                materiali[articolo_key] = qty_base * num_persone
            elif tipo_calcolo == 2:
                materiali[articolo_key] = qty_base * num_bagni
            elif tipo_calcolo == 0 and messaggio:
                messaggi_info.append(f"ℹ️ {articolo}: {messaggio}")
        
        # === REGOLE PER CAMERA (set lenzuola) ===
        materiali['set_lenzuola_matrimoniali'] = num_camere_matrimoniali
        materiali['set_lenzuola_singole'] = num_camere_singole
        
        # === REGOLE CUCINA (dinamiche) ===
        for regola in self.regole_cucina:
            articolo = regola['articolo']
            qty_base = regola['quantita']
            tipo_calcolo = regola['tipo_calcolo']
            messaggio = regola.get('messaggio', '')
            
            articolo_key = articolo.lower().replace(' ', '_').replace('/', '_').replace('+', '_')
            
            if tipo_calcolo == 1:
                materiali[articolo_key] = qty_base * num_persone
            elif tipo_calcolo == 2:
                materiali[articolo_key] = qty_base * num_bagni
            elif tipo_calcolo == 0 and messaggio:
                messaggi_info.append(f"ℹ️ {articolo}: {messaggio}")
        
        # Info macchina caffè
        materiali['tipo_macchina_caffe'] = tipo_macchina_caffe
        
        # Aggiungi messaggi informativi
        if messaggi_info:
            materiali['_messaggi_info'] = messaggi_info
        
        return materiali
    
    def trova_pdf_input(self):
        """Trova PDF più recente in cartella input"""
        
        if not os.path.exists(self.input_dir):
            os.makedirs(self.input_dir)
            print(f"[INFO] Creata cartella: {self.input_dir}")
            return None
        
        pdf_files = glob.glob(os.path.join(self.input_dir, '*.pdf'))
        
        if not pdf_files:
            print(f"[WARN] Nessun PDF trovato in: {self.input_dir}")
            return None
        
        # Ordina per data modifica (più recente)
        pdf_files.sort(key=os.path.getmtime, reverse=True)
        latest_pdf = pdf_files[0]
        
        print(f"[OK] PDF trovato: {os.path.basename(latest_pdf)}")
        return latest_pdf
    
    def elabora_pdf(self, pdf_path):
        """
        Elabora PDF: parsing → calcolo materiali intelligente → route optimization
        """
        
        print("\n" + "="*70)
        print("ELABORAZIONE PDF")
        print("="*70)
        
        # Step 1: Parse PDF con GPT
        print("\n[STEP 1] Parsing PDF con GPT...")
        
        if not self.gpt_parser.is_available():
            print("[ERROR] GPT Parser non disponibile!")
            print("[ERROR] Verifica che Config/gpt_api_key.txt esista e sia valida")
            return None
        
        report = self.gpt_parser.generate_daily_report(pdf_path)
        
        if not report or not report.get('tasks'):
            print("[ERROR] Nessun task trovato nel PDF")
            print("[ERROR] Verifica che il PDF sia un report pulizie valido")
            return None
        
        print(f"[OK] Trovati {len(report['tasks'])} appartamenti")
        
        # Step 2: Ricalcola materiali con regole intelligenti + materiali extra da GPT
        print("\n[STEP 2] Calcolo materiali con regole intelligenti...")
        
        for task in report['tasks']:
            nome_apt = task['nome_proprieta']
            num_persone = task.get('num_persone', 2)
            
            # CASO SPECIALE: Appartamenti generici (senza DB)
            if task.get('appartamento_generico', False):
                print(f"  [GENERICO] {nome_apt}: Materiali minimi standard")
                # Materiali minimi per appartamento generico
                materiali_smart = {
                    'carta_igienica': 2,
                    'bustine_monouso_(bagnoschiuma/intimo/shampoo)': 4,
                    'tappetini_bagno': 1,
                    'asciugamani_grandi': 2,
                    'asciugamani_piccoli': 2,
                    'set_lenzuola_matrimoniali': 1,
                    'set_lenzuola_singole': 0,
                    'cialde_caffè': 4,
                    'sacchetti_spazzatura': 2,
                    'detersivo_piatti': 1,
                    'sgrassatore_universale': 1,
                    'sgrassatore_anticalcare': 1,
                    'lavapavimenti': 1,
                    'scottex/tovaglioli': 1,
                    'tipo_macchina_caffe': 'Nespresso'
                }
                
                task['materiali_necessari'] = materiali_smart
                continue
            
            # Carica database appartamenti (Database condiviso a livello superiore)
            appartamenti_file = os.path.join(os.path.dirname(self.base_dir), 'Database', 'appartamenti.xlsx')
            df_appartamenti = pd.read_excel(appartamenti_file)
            
            # Trova info appartamento da Excel
            apt_row = df_appartamenti[
                df_appartamenti['Ciao Booking Nome'] == nome_apt
            ]
            
            if not apt_row.empty:
                apt_info = apt_row.iloc[0].to_dict()
                
                # Calcola materiali dalle regole (senza materiali extra)
                materiali_smart = self.calcola_materiali_intelligente(apt_info, num_persone)
                
                # Assegna materiali al task
                task['materiali_necessari'] = materiali_smart
                
                # Conta solo articoli numerici (esclude tipo_macchina_caffe)
                num_articoli = sum(v for k, v in materiali_smart.items() if isinstance(v, (int, float)))
                print(f"  [OK] {nome_apt}: {num_persone} persone → {num_articoli} articoli")
        
        # Step 3: Ottimizza route
        print("\n[STEP 3] Ottimizzazione percorso...")
        
        if self.route_optimizer.api_key:
            # optimize_tasks_route ritorna (tasks_ordinati, route_info)
            tasks_ordinati, route_info = self.route_optimizer.optimize_tasks_route(report['tasks'])
            report['route_info'] = route_info
            report['tasks'] = tasks_ordinati  # Task già riordinati
            
            print(f"[OK] Route ottimizzata: {route_info['total_distance_km']:.1f} km, {route_info['total_duration_minutes']} min")
        else:
            print("[WARN] Google Maps API key mancante, skip route optimization")
        
        # Step 4: Calcola materiali totali e separa task speciali
        print("\n[STEP 4] Calcolo materiali totali...")
        
        tasks_generici = []
        tasks_non_identificati = []
        
        for task in report['tasks']:
            if task.get('appartamento_generico', False):
                tasks_generici.append(task)
            elif task.get('non_identificato', False):
                tasks_non_identificati.append(task)
        
        if tasks_generici:
            print(f"  [OK] Appartamenti generici: {len(tasks_generici)}")
        if tasks_non_identificati:
            print(f"  [OK] Non identificati: {len(tasks_non_identificati)}")
        
        # Calcola materiali totali (TUTTI)
        materiali_totali = {}
        for task in report['tasks']:
            for item, qty in task['materiali_necessari'].items():
                # Skip messaggi informativi (sono liste, non numeri)
                if item == '_messaggi_info':
                    continue
                # Gestisci tipo_macchina_caffe separatamente (è stringa, non numero)
                if item == 'tipo_macchina_caffe':
                    if item not in materiali_totali:
                        materiali_totali[item] = set()
                    materiali_totali[item].add(qty)
                # Solo articoli numerici
                elif isinstance(qty, (int, float)):
                    materiali_totali[item] = materiali_totali.get(item, 0) + qty
        
        # Converti set macchine caffè in stringa leggibile
        if 'tipo_macchina_caffe' in materiali_totali:
            macchine = materiali_totali['tipo_macchina_caffe']
            materiali_totali['tipo_macchina_caffe'] = ', '.join(sorted(macchine))
        
        report['materiali_totali'] = materiali_totali
        report['tasks_generici'] = tasks_generici
        report['tasks_non_identificati'] = tasks_non_identificati
        
        # Crea summary con contatori tipo_task e magazzini coinvolti
        magazzini_set = set()
        conteggi = {'check_in': 0, 'check_out': 0, 'cambio': 0, 'pulizia': 0}
        
        for task in report['tasks']:
            tipo = task.get('tipo_task', '').lower()
            # Debug: stampa tipo_task per vedere valori reali
            print(f"  [DEBUG] {task['nome_proprieta']}: tipo_task='{tipo}'")
            
            if tipo == 'check-in':
                conteggi['check_in'] += 1
            elif tipo == 'check-out':
                conteggi['check_out'] += 1
            elif 'cambio' in tipo:
                conteggi['cambio'] += 1
            elif 'pulizia' in tipo or 'ordinaria' in tipo:
                conteggi['pulizia'] += 1
            else:
                print(f"  [WARN] tipo_task non riconosciuto: '{tipo}'")
            
            # Raccogli magazzini
            magazzino = task.get('magazzino', '')
            if magazzino and magazzino.strip():
                magazzini_set.add(magazzino)
        
        report['summary'] = {
            'check_in': conteggi['check_in'],
            'check_out': conteggi['check_out'],
            'cambio': conteggi['cambio'],
            'pulizia': conteggi['pulizia'],
            'magazzini_coinvolti': sorted(list(magazzini_set))
        }
        report['totale_task'] = len(report['tasks'])
        
        # Conta solo articoli numerici
        num_articoli = sum(v for v in materiali_totali.values() if isinstance(v, (int, float)))
        print(f"[OK] Totali: {num_articoli} articoli, {len(materiali_totali)} tipologie")
        
        print("\n" + "="*70)
        
        return report
    
    def salva_report_txt(self, report):
        """Salva report in formato TXT leggibile nella cartella Output"""
        
        print("\n[FILE] Salvataggio report TXT...")
        
        # Crea cartella pdf_output se non esiste (a root del bot)
        output_dir = os.path.join(self.base_dir, 'pdf_output')
        os.makedirs(output_dir, exist_ok=True)
        
        # Nome file con data
        data_str = datetime.now().strftime('%Y-%m-%d')
        output_file = os.path.join(output_dir, f'report_giornaliero_{data_str}.txt')
        
        # Genera contenuto TXT
        with open(output_file, 'w', encoding='utf-8') as f:
            # Header
            f.write("═" * 79 + "\n")
            f.write(f"{'REPORT PULIZIE GIORNALIERO - ' + datetime.now().strftime('%d/%m/%Y'):^79}\n")
            f.write("═" * 79 + "\n\n")
            
            # Riepilogo generale
            f.write("📊 RIEPILOGO GENERALE\n")
            f.write("─" * 79 + "\n")
            f.write(f"Totale Task:          {len(report['tasks'])}\n")
            f.write(f"Check-In:             {report['summary']['check_in']}\n")
            f.write(f"Check-Out:            {report['summary']['check_out']}\n")
            f.write(f"Cambio Biancheria:    {report['summary']['cambio']}\n")
            f.write(f"Pulizie Ordinarie:    {report['summary']['pulizia']}\n\n")
            f.write(f"Magazzini Coinvolti:  {', '.join(report['summary']['magazzini_coinvolti'])}\n\n\n")
            
            # Materiali totali
            f.write("📦 MATERIALI NECESSARI TOTALI\n")
            f.write("─" * 79 + "\n")
            for materiale, qty in report['materiali_totali'].items():
                nome_mat = materiale.replace('_', ' ').title()
                if 'set' in materiale.lower() or 'lenzuola' in materiale.lower():
                    unita = 'set'
                else:
                    unita = 'pz'
                f.write(f"{nome_mat:<30} {qty:>3} {unita}\n")
            
            # Info percorso
            if report.get('route_info'):
                f.write("\n\n🗺️  PERCORSO OTTIMIZZATO\n")
                f.write("─" * 79 + "\n")
                route = report['route_info']
                f.write(f"Distanza Totale:     {route['total_distance_km']:.2f} km\n")
                ore = route['total_duration_minutes'] // 60
                minuti = route['total_duration_minutes'] % 60
                f.write(f"Durata Stimata:      {ore} ore e {minuti} minuti\n\n")
                f.write(f"Link Google Maps:\n{route.get('route_url', 'N/A')}\n")
            
            # Dettaglio task
            f.write("\n\n📋 DETTAGLIO TASK (ORDINE PERCORSO OTTIMIZZATO)\n")
            f.write("═" * 79 + "\n")
            
            for i, task in enumerate(report['tasks'], 1):
                f.write("\n┌" + "─" * 77 + "┐\n")
                f.write(f"│ {i}. {task['nome_proprieta']:<73} │\n")
                f.write("└" + "─" * 77 + "┘\n")
                f.write(f"   📍 {task['indirizzo']}\n")
                f.write(f"   🔑 {task['nome_ota']}\n")
                f.write(f"   🏠 {task['tipo_evento']} - {task['tipo_pulizia']}\n")
                f.write(f"   👥 {task['num_persone']} persone\n\n")
                
                # Struttura
                f.write("   🛏️  Struttura:\n")
                f.write(f"   • Camere Matrimoniali: {int(task.get('camere_matrimoniali', 0))}\n")
                f.write(f"   • Camere Singole: {int(task.get('camere_singole', 0))}\n")
                f.write(f"   • Bagni: {int(task.get('bagni', 0))}\n\n")
                
                # Materiali
                f.write("   📦 Materiali da portare:\n")
                for mat, qty in task['materiali_necessari'].items():
                    if qty > 0:
                        nome_mat = mat.replace('_', ' ').title()
                        if 'set' in mat.lower() or 'lenzuola' in mat.lower():
                            unita = 'set'
                        else:
                            unita = 'pz'
                        f.write(f"   • {nome_mat}: {qty} {unita}\n")
                
                # Note
                if task.get('note'):
                    f.write(f"\n   📝 Note: {task['note']}\n")
                
                f.write(f"   🏢 Magazzino: {task.get('magazzino', 'N/A')}\n")
                f.write("\n" + "─" * 79 + "\n")
            
            # Footer
            f.write("\n" + "═" * 79 + "\n")
            f.write(f"{'FINE REPORT':^79}\n")
            f.write("═" * 79 + "\n\n")
            f.write(f"Fonte dati: {report.get('pdf_source', 'N/A')}\n")
            f.write(f"Generato il: {datetime.now().strftime('%d/%m/%Y')}\n")
        
        print(f"[OK] Report salvato: {output_file}")
    
    def run(self):
        """Esegue workflow completo"""
        
        print("\n" + "="*70)
        print("MASTER PROCESSOR - MO.VE PROPERTY MANAGEMENT")
        print("="*70)
        
        # Step 1: Trova PDF
        pdf_path = self.trova_pdf_input()
        
        if not pdf_path:
            print("\n[ERROR] Nessun PDF da elaborare")
            print(f"[INFO] Carica PDF in: {self.input_dir}")
            return
        
        # Step 2: Elabora PDF
        report = self.elabora_pdf(pdf_path)
        
        if not report:
            print("\n[ERROR] Elaborazione fallita")
            return
        
        print("\n" + "="*70)
        print("✅ COMPLETATO")
        print("="*70)
        print(f"Appartamenti elaborati: {len(report['tasks'])}")
        print(f"Materiali totali: {sum(report['materiali_totali'].values())} articoli")
        
        if report.get('route_info'):
            print(f"Percorso: {report['route_info']['total_distance_km']:.1f} km")
            print(f"Durata: {report['route_info']['total_duration_minutes']} minuti")
        
        print("\n[INFO] Report generato con successo")


if __name__ == '__main__':
    processor = MasterProcessor()
    processor.run()
