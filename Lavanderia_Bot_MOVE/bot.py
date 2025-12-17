"""
Bot Telegram per gestione report pulizie giornalieri
- Carica PDF pulizie
- Genera report PDF
- Crea LOG di controllo con tutti i match
- Mantiene storico input/output
"""

import os
import sys
import logging
import shutil
import pandas as pd
from datetime import datetime
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# PDF generation
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# Import dal nostro sistema
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'funzioni'))
from elabora_giro_giornaliero import MasterProcessor

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class TelegramBotPulizie:
    """Bot Telegram per gestione report pulizie"""
    
    def __init__(self, token: str):
        """
        Inizializza bot
        
        Args:
            token: Token bot Telegram
        """
        self.token = token
        self.base_dir = os.path.dirname(__file__)  # Root del bot
        
        # Cartelle storico
        self.pdf_input_dir = os.path.join(self.base_dir, 'pdf_input')
        self.pdf_output_dir = os.path.join(self.base_dir, 'pdf_output')
        self.logs_dir = os.path.join(self.base_dir, 'logs')
        
        # Crea cartelle se non esistono
        for dir_path in [self.pdf_input_dir, self.pdf_output_dir, self.logs_dir]:
            os.makedirs(dir_path, exist_ok=True)
        
        # Inizializza processore
        self.processor = MasterProcessor()
        
        logger.info("Bot inizializzato")
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler comando /start"""
        user = update.effective_user
        
        # Keyboard con pulsanti
        keyboard = [
            [KeyboardButton("📄 Carica PDF Pulizie")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        welcome_text = f"""
👋 Ciao {user.first_name}!

Sono il bot per la gestione dei report pulizie giornalieri.

📄 Clicca su **"Carica PDF Pulizie"** per iniziare!
        """
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler messaggi di testo"""
        text = update.message.text
        
        if text == "📄 Carica PDF Pulizie":
            await self.request_pdf(update, context)
        else:
            await update.message.reply_text(
                "❓ Non ho capito. Usa il pulsante 'Carica PDF Pulizie' per inviare un PDF."
            )
    
    async def request_pdf(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Richiede invio PDF"""
        await update.message.reply_text(
            "📤 **Invia il PDF delle pulizie**\n\n"
            "Carica il file PDF del report giornaliero.\n"
            "Inizierò subito l'elaborazione! ⚡"
        )
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler ricezione documenti (PDF)"""
        document = update.message.document
        
        # Verifica che sia un PDF
        if not document.file_name.endswith('.pdf'):
            await update.message.reply_text(
                "❌ **Errore:** Il file deve essere un PDF!\n"
                "Riprova con un file .pdf"
            )
            return
        
        try:
            # Messaggio di attesa
            status_msg = await update.message.reply_text(
                "⏳ **Elaborazione in corso...**\n\n"
                "📥 Download PDF...\n"
                "⚙️ Analisi appartamenti...\n"
                "🗺️ Ottimizzazione percorso...\n"
                "📊 Calcolo materiali..."
            )
            
            # Download PDF e salva in storico
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file = await context.bot.get_file(document.file_id)
            
            # Salva in pdf_input con timestamp
            input_filename = f"{timestamp}_{document.file_name}"
            pdf_input_path = os.path.join(self.pdf_input_dir, input_filename)
            await file.download_to_drive(pdf_input_path)
            
            logger.info(f"PDF ricevuto e salvato: {input_filename}")
            
            # Elabora PDF
            await status_msg.edit_text(
                "⏳ **Elaborazione in corso...**\n\n"
                "✅ Download completato\n"
                "⚙️ Analisi appartamenti in corso..."
            )
            
            report = self.processor.elabora_pdf(pdf_input_path)
            
            if not report:
                await status_msg.edit_text(
                    "❌ **Errore elaborazione**\n\n"
                    "Non sono riuscito ad elaborare il PDF.\n"
                    "Verifica che sia un report pulizie valido."
                )
                return
            
            # Genera file LOG (solo salvato, non inviato)
            await status_msg.edit_text(
                "⏳ **Elaborazione in corso...**\n\n"
                "✅ Download completato\n"
                "✅ Analisi completata\n"
                "📝 Generazione report PDF..."
            )
            
            self.generate_control_log(report, timestamp)
            
            # Genera report PDF
            pdf_output_path = os.path.join(self.pdf_output_dir, f"report_{timestamp}.pdf")
            self.generate_pdf_report(report, pdf_output_path)
            
            # Invia risultati
            await status_msg.edit_text(
                "✅ **Elaborazione completata!**\n\n"
                "📤 Invio report..."
            )
            
            # Invia solo il report PDF
            with open(pdf_output_path, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=f'report_pulizie_{datetime.now().strftime("%Y%m%d")}.pdf',
                    caption="📄 **Report Pulizie Giornaliero**"
                )
            
            # Riepilogo
            summary = report.get('summary', {})
            route_info = report.get('route_info', {})
            
            # Calcola totale materiali convertendo a int (salta campi non-materiali)
            tot_materiali = 0
            for mat_key, qty in report['materiali_totali'].items():
                if mat_key in ['flag_preparare_lenzuola', 'tipo_macchina_caffe']:
                    continue
                try:
                    tot_materiali += int(qty) if qty != '' else 0
                except (ValueError, TypeError):
                    continue
            
            summary_text = f"""
✅ **ELABORAZIONE COMPLETATA**

📊 **Riepilogo:**
• Appartamenti: {report.get('totale_task', len(report.get('tasks', [])))}
• Check-in: {summary.get('check_in', 0)}
• Check-out: {summary.get('check_out', 0)}
• Materiali totali: {tot_materiali} articoli

🗺️ **Percorso:**
• Distanza: {route_info.get('total_distance_km', 0):.1f} km
• Durata: {route_info.get('total_duration_minutes', 0)} minuti

🔗 **Google Maps:**
{route_info.get('route_url', 'N/A')}

💾 File salvati:
• PDF Input: pdf_input/{input_filename}
• TXT Estratto: pdf_input/pdf_to_txt_input/estratto_{timestamp}.txt
• PDF Output: pdf_output/report_{timestamp}.pdf
• Log Controllo: logs/log_{timestamp}.txt
            """
            
            await update.message.reply_text(summary_text)
            await status_msg.delete()
            
            logger.info(f"Elaborazione completata: {input_filename}")
            
        except Exception as e:
            logger.error(f"Errore elaborazione: {e}")
            import traceback
            traceback.print_exc()
            await update.message.reply_text(
                f"❌ **Errore durante l'elaborazione**\n\n"
                f"Dettagli: {str(e)}\n\n"
                f"Contatta l'amministratore se il problema persiste."
            )
    

    
    def generate_control_log(self, report: dict, timestamp: str) -> str:
        """
        Genera file LOG di controllo con tutti i match e calcoli
        Salvato solo localmente in logs/, non inviato in chat
        
        Args:
            report: Report generato dal processor
            timestamp: Timestamp unico per il file
            
        Returns:
            Path del file LOG
        """
        log_path = os.path.join(self.logs_dir, f'log_{timestamp}.txt')
        
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write("═" * 79 + "\n")
            f.write(f"{'FILE LOG DI CONTROLLO - ' + datetime.now().strftime('%d/%m/%Y %H:%M'):^79}\n")
            f.write("═" * 79 + "\n\n")
            
            f.write("📋 RIEPILOGO ELABORAZIONE\n")
            f.write("─" * 79 + "\n")
            f.write(f"PDF Fonte: {report.get('pdf_source', 'N/A')}\n")
            f.write(f"Data Elaborazione: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"Totale Appartamenti Trovati: {report.get('totale_task', len(report.get('tasks', [])))}\n")
            f.write(f"Check-in: {report.get('summary', {}).get('check_in', 0)}\n")
            f.write(f"Check-out: {report.get('summary', {}).get('check_out', 0)}\n\n\n")
            
            f.write("🏠 APPARTAMENTI RICONOSCIUTI E ANALIZZATI\n")
            f.write("═" * 79 + "\n\n")
            
            for i, task in enumerate(report['tasks'], 1):
                f.write(f"┌─ APPARTAMENTO {i:02d} " + "─" * 60 + "┐\n")
                f.write(f"│ Nome Proprietà: {task['nome_proprieta']:<64}│\n")
                f.write(f"│ Nome OTA: {task['nome_ota']:<70}│\n")
                f.write(f"│ Indirizzo: {task['indirizzo']:<67}│\n")
                f.write("├" + "─" * 77 + "┤\n")
                f.write(f"│ N. Persone: {task['num_persone']:<66}│\n")
                f.write(f"│ Magazzino: {task.get('magazzino', 'N/A'):<67}│\n")
                f.write("├" + "─" * 77 + "┤\n")
                f.write(f"│ 🛏️  STRUTTURA:                                                          │\n")
                f.write(f"│   • Camere Matrimoniali: {int(task.get('camere_matrimoniali', 0)):<47}│\n")
                f.write(f"│   • Camere Singole: {int(task.get('camere_singole', 0)):<52}│\n")
                f.write(f"│   • Bagni: {int(task.get('bagni', 0)):<63}│\n")
                f.write("├" + "─" * 77 + "┤\n")
                f.write(f"│ 📦 MATERIALI CALCOLATI:                                                 │\n")
                
                materiali = task.get('materiali_necessari', {})
                for mat_key, qty in materiali.items():
                    # Converti qty a intero (può essere stringa dall'Excel)
                    try:
                        qty_int = int(qty) if qty != '' else 0
                    except (ValueError, TypeError):
                        continue
                    
                    if qty_int > 0:
                        nome_mat = mat_key.replace('_', ' ').title()
                        f.write(f"│   • {nome_mat}: {qty_int} {('set' if 'lenzuola' in mat_key else 'pz'):<50}│\n")
                
                f.write("├" + "─" * 77 + "┤\n")
                if task.get('note'):
                    # Spezza note lunghe
                    note_lines = [task['note'][i:i+70] for i in range(0, len(task['note']), 70)]
                    f.write(f"│ 📝 NOTE:                                                                │\n")
                    for line in note_lines:
                        f.write(f"│   {line:<73}│\n")
                    f.write("├" + "─" * 77 + "┤\n")
                
                f.write(f"│ 🔍 CONTESTO RAW (per verifica):                                         │\n")
                context_lines = [task.get('raw_context', 'N/A')[i:i+70] for i in range(0, min(len(task.get('raw_context', '')), 140), 70)]
                for line in context_lines:
                    f.write(f"│   {line:<73}│\n")
                
                f.write("└" + "─" * 77 + "┘\n\n")
            
            # Sezione materiali totali
            f.write("\n" + "═" * 79 + "\n")
            f.write("📊 RIEPILOGO MATERIALI TOTALI\n")
            f.write("═" * 79 + "\n\n")
            
            for mat, qty in report['materiali_totali'].items():
                # Salta campi non-materiali
                if mat in ['flag_preparare_lenzuola', 'tipo_macchina_caffe']:
                    continue
                
                # Converti qty a intero (può essere stringa dall'Excel)
                try:
                    qty_int = int(qty) if qty != '' else 0
                except (ValueError, TypeError):
                    continue
                
                nome_mat = mat.replace('_', ' ').title()
                unita = 'set' if 'lenzuola' in mat else 'pz'
                f.write(f"{nome_mat:<50} {qty_int:>5} {unita}\n")
            
            # Sezione route
            if report.get('route_info'):
                f.write("\n\n" + "═" * 79 + "\n")
                f.write("🗺️  INFORMAZIONI PERCORSO\n")
                f.write("═" * 79 + "\n\n")
                route = report['route_info']
                f.write(f"Distanza Totale: {route['total_distance_km']:.2f} km\n")
                f.write(f"Durata Stimata: {route['total_duration_minutes']} minuti\n")
                f.write(f"Ordine Ottimizzato: {route.get('optimized_order', [])}\n\n")
                f.write(f"Link Google Maps:\n{route.get('route_url', 'N/A')}\n")
            
            # Footer
            f.write("\n\n" + "═" * 79 + "\n")
            f.write(f"{'FINE LOG DI CONTROLLO':^79}\n")
            f.write("═" * 79 + "\n")
            f.write(f"Generato automaticamente da Bot Telegram Pulizie\n")
            f.write(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
        
        logger.info(f"Log di controllo generato: {log_path}")
        return log_path
    
    def generate_pdf_report(self, report: dict, output_path: str):
        """
        Genera report PDF professionale
        
        Args:
            report: Report generato dal processor
            output_path: Path dove salvare il PDF
        """
        doc = SimpleDocTemplate(output_path, pagesize=A4,
                                rightMargin=2*cm, leftMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
        
        story = []
        styles = getSampleStyleSheet()
        
        # Stili custom
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=20,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2c5aa0'),
            spaceAfter=12,
            spaceBefore=16
        )
        
        # Header
        story.append(Paragraph("REPORT PULIZIE GIORNALIERO", title_style))
        story.append(Paragraph(f"Data: {datetime.now().strftime('%d/%m/%Y')}", styles['Normal']))
        story.append(Spacer(1, 0.5*cm))
        
        # Riepilogo generale
        story.append(Paragraph("📊 RIEPILOGO GENERALE", heading_style))
        
        summary_data = [
            ['Totale Appartamenti:', str(report.get('totale_task', len(report.get('tasks', []))))]
        ]
        
        summary_table = Table(summary_data, colWidths=[8*cm, 8*cm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.5*cm))
        
        # === SOMMARIO PER OPERATORE ===
        story.append(Paragraph("👤 SOMMARIO PER OPERATORE", heading_style))
        
        # Raggruppa task per operatore
        operatori_tasks = {}
        for task in report['tasks']:
            operatore = task.get('operatore', 'Non assegnato')
            if operatore not in operatori_tasks:
                operatori_tasks[operatore] = []
            operatori_tasks[operatore].append(task)
        
        # Ordina operatori alfabeticamente (ma "Non assegnato" alla fine)
        operatori_ordinati = sorted([op for op in operatori_tasks.keys() if op != 'Non assegnato'])
        if 'Non assegnato' in operatori_tasks:
            operatori_ordinati.append('Non assegnato')
        
        # Crea tabella sommario per ogni operatore
        for operatore in operatori_ordinati:
            tasks_operatore = operatori_tasks[operatore]
            num_immobili = len(tasks_operatore)
            
            # Header operatore con colore distintivo
            op_header_data = [[f"👤 {operatore} ({num_immobili} immobili)"]]
            op_header_table = Table(op_header_data, colWidths=[16*cm])
            op_header_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#673AB7')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ]))
            story.append(op_header_table)
            
            # Lista immobili per questo operatore
            for idx, task in enumerate(tasks_operatore, 1):
                nome_prop = task.get('nome_proprieta', 'N/A')
                indirizzo = task.get('indirizzo', 'N/A')
                tipo_evento = task.get('tipo_evento', 'N/A')
                num_persone = task.get('num_persone', 0)
                
                # Verifica se esterno
                pulizie_interne = task.get('pulizie_interne', True)
                is_esterno = str(pulizie_interne).lower() in ['falso', 'false', 'no', '0']
                badge_esterno = " 🔶" if is_esterno else ""
                
                immobile_data = [[f"  {idx}. {nome_prop}{badge_esterno} | {tipo_evento} | 👥 {num_persone} pers. | 📍 {indirizzo[:40]}..."]]
                immobile_table = Table(immobile_data, colWidths=[16*cm])
                immobile_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#EDE7F6')),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ]))
                story.append(immobile_table)
            
            story.append(Spacer(1, 0.3*cm))
        
        story.append(Spacer(1, 0.5*cm))
        
        # Percorso ottimizzato
        if report.get('route_info'):
            route = report['route_info']
            story.append(Paragraph("🗺️ PERCORSO OTTIMIZZATO", heading_style))
            
            route_data = [
                ['Distanza Totale:', f"{route.get('total_distance_km', 0):.2f} km"],
                ['Durata Stimata:', f"{route.get('total_duration_minutes', 0)} minuti"]
            ]
            
            route_table = Table(route_data, colWidths=[8*cm, 8*cm])
            route_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
            ]))
            story.append(route_table)
            story.append(Spacer(1, 0.3*cm))
            
            # Google Maps link (troncato se troppo lungo)
            maps_url = route.get('route_url', 'N/A')
            if len(maps_url) > 100:
                maps_url = maps_url[:100] + '...'
            story.append(Paragraph(f"<i>Link Google Maps: {maps_url}</i>", styles['Normal']))
            story.append(Spacer(1, 0.5*cm))
        
        # Materiali totali
        story.append(Paragraph("📦 MATERIALI NECESSARI TOTALI", heading_style))
        
        materiali_data = [['Materiale', 'Quantità']]
        for mat, qty in report['materiali_totali'].items():
            # Salta campi non-materiali
            if mat in ['flag_preparare_lenzuola', 'tipo_macchina_caffe']:
                continue
            
            # Converti qty a intero (può essere stringa dall'Excel)
            try:
                qty_int = int(qty) if qty != '' else 0
            except (ValueError, TypeError):
                continue
            
            nome = mat.replace('_', ' ').title()
            unita = 'set' if 'lenzuola' in mat else 'pz'
            materiali_data.append([nome, f"{qty_int} {unita}"])
        
        materiali_table = Table(materiali_data, colWidths=[12*cm, 4*cm])
        materiali_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4CAF50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(materiali_table)
        
        # Info lenzuola esterne
        if report.get('lenzuola_esterne'):
            lenz = report['lenzuola_esterne']
            story.append(Paragraph("ℹ️ INFO LENZUOLA TOTALI", heading_style))
            lenz_text = f"Set lenzuola TOTALI (tutte incluse, interne ed esterne): {lenz['set_lenzuola_matrimoniali']} matrimoniali, {lenz['set_lenzuola_singole']} singole"
            story.append(Paragraph(lenz_text, styles['Normal']))
            story.append(Spacer(1, 0.5*cm))
        
        # Nuova pagina per dettaglio task
        story.append(PageBreak())
        
        # LISTA UNICA APPARTAMENTI (tutti insieme, senza distinzioni)
        story.append(Paragraph("📋 LISTA APPARTAMENTI (ORDINE PERCORSO)", heading_style))
        story.append(Spacer(1, 0.3*cm))
        
        # Itera su TUTTI i task senza distinzioni
        for i, task in enumerate(report['tasks'], 1):
                # Box per ogni appartamento
                operatore = task.get('operatore', 'Non assegnato')
                destinazione = task.get('destinazione_riferimento', 'Abitazione/cantina')
                ha_cantina = task.get('ha_cantina', False)
                
                # Determina dove portare i materiali
                if destinazione == 'Abitazione/cantina':
                    luogo_materiali = "🔑 MATERIALI IN CANTINA" if ha_cantina else "⬆️ SALIRE IN APPARTAMENTO"
                else:
                    luogo_materiali = f"📦 PORTARE IN MAGAZZINO: {destinazione}"
                
                # Usa note come titolo SOLO se flag titolo_note=True
                note_task = task.get('note', '').strip()
                usa_note = task.get('titolo_note', False)
                titolo_task = note_task if (usa_note and note_task) else task['nome_proprieta']
                
                # Verifica se appartamento ha pulizie esterne (Pulizie Interne = Falso)
                pulizie_interne = task.get('pulizie_interne', True)  # Default True
                is_esterno = str(pulizie_interne).lower() in ['falso', 'false', 'no', '0']
                
                # Aggiungi badge ESTERNO se necessario
                if is_esterno:
                    titolo_task = f"{titolo_task} 🔶 ESTERNO"
                
                task_data = [
                    [f"#{i} - {titolo_task}"],
                    [f"👤 Operatore: {operatore}"],
                    [f"{luogo_materiali}"],
                    [f"🏠 {task['tipo_evento']} - {task['tipo_pulizia']}"],
                    [f"📍 {task['indirizzo']}"],
                    [f"👥 {task['num_persone']} persone | 🛏️ {int(task.get('camere_matrimoniali', 0))}M + {int(task.get('camere_singole', 0))}S | 🚿 {int(task.get('bagni', 0))} bagni"],
                ]
                
                # Colori diversi per appartamenti esterni
                if is_esterno:
                    header_color = colors.HexColor('#FF6F00')  # Arancione scuro
                    body_color = colors.HexColor('#FFE0B2')    # Arancione chiaro
                else:
                    header_color = colors.HexColor('#2196F3')  # Blu
                    body_color = colors.HexColor('#E3F2FD')    # Blu chiaro
                
                task_table = Table(task_data, colWidths=[16*cm])
                task_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, 0), header_color),
                    ('TEXTCOLOR', (0, 0), (0, 0), colors.whitesmoke),
                    ('BACKGROUND', (0, 1), (0, -1), body_color),
                    ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey)
                ]))
                story.append(task_table)
                
                # Materiali per questo task
                self._add_materiali_to_story(story, task, styles)
                
                # Note (se presenti) subito dopo i materiali
                note_complete = task.get('note_raw', '').strip() or task.get('note', '').strip()
                if note_complete:
                    note_box_data = [[Paragraph(f'<font size=8><b>📝 NOTE:</b> <i>{note_complete}</i></font>', styles['Normal'])]]
                    note_box = Table(note_box_data, colWidths=[16*cm])
                    note_box.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFFDE7')),
                        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#FBC02D')),
                        ('TOPPADDING', (0, 0), (-1, -1), 6),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                        ('LEFTPADDING', (0, 0), (-1, -1), 8),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                    ]))
                    story.append(note_box)
                
                story.append(Spacer(1, 0.4*cm))
        
        # Footer
        story.append(Spacer(1, 1*cm))
        story.append(Paragraph(f"<i>Report generato automaticamente - {datetime.now().strftime('%d/%m/%Y %H:%M')}</i>", 
                               styles['Normal']))
        
        # Build PDF
        doc.build(story)
        logger.info(f"Report PDF generato: {output_path}")
    
    def _add_materiali_to_story(self, story, task, styles):
        """Helper per aggiungere materiali nel PDF + messaggi informativi"""
        materiali = task.get('materiali_necessari', {})
        
        mat_list = []
        tipo_macchina = None
        messaggi_info = materiali.get('_messaggi_info', [])
        
        for mat, qty in materiali.items():
            # Salta campi speciali
            if mat in ['tipo_macchina_caffe', '_messaggi_info']:
                if mat == 'tipo_macchina_caffe':
                    tipo_macchina = qty
                continue
            
            try:
                qty_int = int(qty) if qty != '' else 0
            except (ValueError, TypeError):
                continue
            
            if qty_int > 0:
                nome = mat.replace('_', ' ').title()
                unita = 'set' if 'lenzuola' in mat else 'pz'
                mat_list.append(f"• {nome}: {qty_int} {unita}")
        
        if mat_list:
            mat_text = "<br/>".join(mat_list)
            
            # Aggiungi info macchina caffè
            if tipo_macchina and tipo_macchina != 'Non specificata':
                mat_text += f"<br/><b>☕ Macchina caffè: {tipo_macchina}</b>"
            
            story.append(Paragraph(f'<font size=8>📦 <b>Materiali:</b><br/>{mat_text}</font>', styles['Normal']))
        
        # MESSAGGI INFORMATIVI (se presenti)
        if messaggi_info:
            story.append(Spacer(1, 0.2*cm))
            msg_text = "<br/>".join(messaggi_info)
            story.append(Paragraph(f'<font size=8 color="#0066CC"><i>{msg_text}</i></font>', styles['Normal']))
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler errori globale"""
        logger.error(f"Update {update} ha causato errore {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ **Si è verificato un errore**\n\n"
                "Riprova o contatta l'amministratore."
            )
    
    def run(self):
        """Avvia il bot"""
        logger.info("Avvio bot Telegram...")
        
        # Crea application
        application = Application.builder().token(self.token).build()
        
        # Handler
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        application.add_handler(MessageHandler(filters.Document.PDF, self.handle_document))
        
        # Error handler
        application.add_error_handler(self.error_handler)
        
        logger.info("Bot avviato! In ascolto...")
        print("\n" + "="*60)
        print("🤖 BOT TELEGRAM PULIZIE - ATTIVO")
        print("="*60)
        print("✅ Bot in esecuzione")
        print("📱 Apri Telegram e cerca il tuo bot")
        print("⚡ Pronto a ricevere PDF!\n")
        print("Premi Ctrl+C per fermare il bot")
        print("="*60 + "\n")
        
        # Avvia polling
        application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Entry point"""
    # Leggi token da file Config
    base_dir = os.path.dirname(__file__)
    config_dir = os.path.join(base_dir, 'Config')
    token_file = os.path.join(config_dir, 'telegram_bot_token.txt')
    
    if not os.path.exists(token_file):
        print("❌ ERROR: File telegram_bot_token.txt non trovato!")
        print(f"📁 Crea il file: {token_file}")
        print("📝 Inserisci il token del bot Telegram (da @BotFather)")
        return
    
    with open(token_file, 'r', encoding='utf-8') as f:
        token = f.read().strip()
    
    if not token:
        print("❌ ERROR: Token vuoto in telegram_bot_token.txt")
        return
    
    # Avvia bot
    bot = TelegramBotPulizie(token)
    bot.run()


if __name__ == '__main__':
    main()
