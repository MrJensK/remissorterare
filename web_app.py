#!/usr/bin/env python3
"""
Web-baserat gränssnitt för Remissorterare
Flask-app med drag-and-drop, realtidsstatus och resultatvisning
"""

import os
import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
import uuid

from remiss_sorterare import RemissSorterare
from ml_verksamhetsidentifierare import MLVerksamhetsIdentifierare
from config import *

# Konfigurera Flask-app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'remissorterare-secret-key-2024'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max

# Konfigurera SocketIO för realtidskommunikation
socketio = SocketIO(app, cors_allowed_origins="*")

# Skapa nödvändiga mappar
Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)
Path('static/uploads').mkdir(exist_ok=True)

# Globala variabler för att hålla koll på bearbetningsstatus
bearbetnings_status = {}
bearbetnings_resultat = {}

# Konfigurera logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebRemissSorterare:
    """Web-vänlig version av Remissorterare"""
    
    def __init__(self):
        self.sorterare = RemissSorterare()
        self.ml_identifierare = MLVerksamhetsIdentifierare()
    
    def bearbeta_fil_web(self, fil_sokvag: Path, session_id: str) -> Dict:
        """
        Bearbetar en fil och returnerar resultat för web-gränssnittet
        
        Args:
            fil_sokvag: Sökväg till filen
            session_id: Unikt ID för sessionen
            
        Returns:
            Dictionary med resultat
        """
        try:
            # Uppdatera status
            bearbetnings_status[session_id] = {
                'status': 'bearbetar',
                'fil': fil_sokvag.name,
                'progress': 0,
                'meddelande': 'Startar bearbetning...'
            }
            socketio.emit('status_update', bearbetnings_status[session_id], room=session_id)
            
            # Konvertera PDF till bilder
            bearbetnings_status[session_id]['progress'] = 20
            bearbetnings_status[session_id]['meddelande'] = 'Konverterar PDF till bilder...'
            socketio.emit('status_update', bearbetnings_status[session_id], room=session_id)
            
            bilder = self.sorterare.pdf_till_bilder(fil_sokvag)
            if not bilder:
                raise Exception("Kunde inte konvertera PDF till bilder")
            
            # OCR-bearbetning
            bearbetnings_status[session_id]['progress'] = 40
            bearbetnings_status[session_id]['meddelande'] = 'Utför OCR-bearbetning...'
            socketio.emit('status_update', bearbetnings_status[session_id], room=session_id)
            
            text = self.sorterare.extrahera_text_med_ocr(bilder)
            if not text.strip():
                raise Exception("Ingen text kunde extraheras från PDF")
            
            # Identifiera verksamhet
            bearbetnings_status[session_id]['progress'] = 60
            bearbetnings_status[session_id]['meddelande'] = 'Identifierar verksamhet...'
            socketio.emit('status_update', bearbetnings_status[session_id], room=session_id)
            
            verksamhet, sannolikhet = self.sorterare.identifiera_verksamhet(text)
            
            # Extrahera data
            bearbetnings_status[session_id]['progress'] = 80
            bearbetnings_status[session_id]['meddelande'] = 'Extraherar data...'
            socketio.emit('status_update', bearbetnings_status[session_id], room=session_id)
            
            personnummer = self.sorterare.hitta_personnummer(text)
            remissdatum = self.sorterare.hitta_remissdatum(text)
            
            # Bestäm mål-mapp
            if sannolikhet >= SANNOLIKHET_TRÖSKEL:
                mål_mapp = self.sorterare.output_mapp / verksamhet
                status = "sorterad"
            else:
                mål_mapp = self.sorterare.osakert_mapp
                status = "osakert"
            
            # Kopiera fil
            mål_fil = mål_mapp / fil_sokvag.name
            import shutil
            shutil.copy2(fil_sokvag, mål_fil)
            
            # Skapa .dat-fil
            if personnummer and remissdatum:
                self.sorterare.skapa_dat_fil(
                    verksamhet, personnummer, remissdatum, 
                    fil_sokvag.name, mål_mapp
                )
            
            # Slutför
            bearbetnings_status[session_id]['progress'] = 100
            bearbetnings_status[session_id]['meddelande'] = 'Bearbetning slutförd'
            socketio.emit('status_update', bearbetnings_status[session_id], room=session_id)
            
            # Skapa resultat
            resultat = {
                'filnamn': fil_sokvag.name,
                'verksamhet': verksamhet,
                'sannolikhet': round(sannolikhet, 1),
                'personnummer': personnummer,
                'remissdatum': remissdatum,
                'status': status,
                'mål_mapp': str(mål_mapp),
                'text_längd': len(text),
                'bearbetningstid': datetime.now().isoformat()
            }
            
            bearbetnings_resultat[session_id] = resultat
            socketio.emit('bearbetning_slutförd', resultat, room=session_id)
            
            return resultat
            
        except Exception as e:
            logger.error(f"Fel vid bearbetning av {fil_sokvag}: {e}")
            bearbetnings_status[session_id] = {
                'status': 'fel',
                'fil': fil_sokvag.name,
                'progress': 0,
                'meddelande': f'Fel: {str(e)}'
            }
            socketio.emit('status_update', bearbetnings_status[session_id], room=session_id)
            return {'error': str(e)}

# Skapa global instans
web_sorterare = WebRemissSorterare()

@app.route('/')
def index():
    """Huvudsida"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Hanterar filuppladdning"""
    try:
        if 'files[]' not in request.files:
            return jsonify({'error': 'Inga filer valda'}), 400
        
        files = request.files.getlist('files[]')
        session_id = str(uuid.uuid4())
        
        # Skapa session-mapp
        session_mapp = Path(app.config['UPLOAD_FOLDER']) / session_id
        session_mapp.mkdir(exist_ok=True)
        
        uppladdade_filer = []
        
        for file in files:
            if file.filename == '':
                continue
            
            if file and file.filename.lower().endswith('.pdf'):
                filename = secure_filename(file.filename)
                file_path = session_mapp / filename
                file.save(file_path)
                uppladdade_filer.append(file_path)
        
        if not uppladdade_filer:
            return jsonify({'error': 'Inga giltiga PDF-filer hittades'}), 400
        
        # Starta bearbetning i bakgrund
        def bearbeta_filer():
            for fil_path in uppladdade_filer:
                web_sorterare.bearbeta_fil_web(fil_path, session_id)
                time.sleep(1)  # Kort paus mellan filer
        
        thread = threading.Thread(target=bearbeta_filer)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'session_id': session_id,
            'antal_filer': len(uppladdade_filer),
            'filnamn': [f.name for f in uppladdade_filer]
        })
        
    except Exception as e:
        logger.error(f"Fel vid uppladdning: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/status/<session_id>')
def get_status(session_id):
    """Hämtar bearbetningsstatus"""
    return jsonify(bearbetnings_status.get(session_id, {}))

@app.route('/resultat/<session_id>')
def get_resultat(session_id):
    """Hämtar bearbetningsresultat"""
    return jsonify(bearbetnings_resultat.get(session_id, {}))

@app.route('/statistik')
def get_statistik():
    """Hämtar statistik över bearbetade filer"""
    try:
        output_mapp = Path('output')
        statistik = {}
        
        for verksamhet_mapp in output_mapp.iterdir():
            if verksamhet_mapp.is_dir():
                pdf_filer = list(verksamhet_mapp.glob('*.pdf'))
                dat_filer = list(verksamhet_mapp.glob('*.dat'))
                statistik[verksamhet_mapp.name] = {
                    'pdf_filer': len(pdf_filer),
                    'dat_filer': len(dat_filer)
                }
        
        return jsonify(statistik)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/träna_ml', methods=['POST'])
def träna_ml():
    """Tränar ML-modellen"""
    try:
        accuracy = web_sorterare.ml_identifierare.träna_modell()
        return jsonify({
            'success': True,
            'accuracy': accuracy,
            'meddelande': f'ML-modell tränad med precision: {accuracy:.3f}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<path:filename>')
def download_file(filename):
    """Låter användare ladda ner bearbetade filer"""
    return send_from_directory('output', filename)

@socketio.on('connect')
def handle_connect():
    """Hanterar WebSocket-anslutning"""
    session_id = request.args.get('session_id')
    if session_id:
        socketio.emit('connected', {'session_id': session_id}, room=request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    """Hanterar WebSocket-avbrott"""
    pass

if __name__ == '__main__':
    # Träna ML-modellen vid start om den inte finns
    if not web_sorterare.ml_identifierare.trained:
        logger.info("Tränar ML-modell vid start...")
        try:
            web_sorterare.ml_identifierare.träna_modell()
        except Exception as e:
            logger.warning(f"Kunde inte träna ML-modell: {e}")
    
    # Starta Flask-app
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
