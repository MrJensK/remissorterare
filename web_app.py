#!/usr/bin/env python3
"""
Web-baserat gränssnitt för Remissorterare
Flask-app med drag-and-drop, realtidsstatus och resultatvisning
"""

import os
import sys
import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit, join_room
import uuid

from remiss_sorterare import RemissSorterare
from ml_verksamhetsidentifierare import MLVerksamhetsIdentifierare
from config import *

# Kontrollera att virtuell miljö är aktiverad
def kontrollera_virtuell_miljo():
    """Kontrollerar att virtuell miljö är aktiverad innan appen startar"""
    venv_path = os.environ.get('VIRTUAL_ENV')
    if not venv_path:
        print("❌ FEL: Virtuell miljö är inte aktiverad!")
        print("")
        print("Aktivera den virtuella miljön först:")
        print("  source venv/bin/activate")
        print("")
        print("Eller använd startskriptet:")
        print("  ./start_web.sh")
        print("")
        exit(1)
    
    # Kontrollera att vi använder rätt Python
    # Hantera både vanliga venv och pyenv-venv
    python_path = os.path.realpath(sys.executable)
    venv_python = os.path.realpath(os.path.join(venv_path, 'bin', 'python'))
    
    # Kontrollera om vi använder rätt Python (antingen direkt eller via pyenv)
    python_ok = False
    
    # Fall 1: Direkt venv Python
    if python_path.startswith(venv_path):
        python_ok = True
    # Fall 2: Python via pyenv men med rätt venv aktiverad
    elif 'pyenv' in python_path and venv_path in os.environ.get('PATH', ''):
        # Kontrollera att venv/bin finns i PATH
        venv_bin_in_path = any(venv_path in p for p in os.environ.get('PATH', '').split(':'))
        if venv_bin_in_path:
            python_ok = True
    
    if not python_ok:
        print("❌ FEL: Fel Python-miljö aktiverad!")
        print(f"Använder: {python_path}")
        print(f"Förväntad: {venv_python}")
        print("")
        print("Aktivera den virtuella miljön först:")
        print("  source venv/bin/activate")
        print("")
        exit(1)
    
    print(f"✅ Virtuell miljö aktiverad: {venv_path}")
    print(f"✅ Python: {python_path}")

# Kör kontrollen direkt
kontrollera_virtuell_miljo()

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
                'meddelande': 'Startar bearbetning...',
                'timestamp': datetime.now().isoformat()
            }
            socketio.emit('status_update', bearbetnings_status[session_id], room=session_id)
            logger.info(f"Session {session_id}: Startar bearbetning av {fil_sokvag.name}")
            
            # Konvertera PDF till bilder
            bearbetnings_status[session_id].update({
                'progress': 20,
                'meddelande': 'Konverterar PDF till bilder...'
            })
            socketio.emit('status_update', bearbetnings_status[session_id], room=session_id)
            logger.info(f"Session {session_id}: Konverterar PDF till bilder")
            
            bilder = self.sorterare.pdf_till_bilder(fil_sokvag)
            if not bilder:
                raise Exception("Kunde inte konvertera PDF till bilder")
            
            # OCR-bearbetning
            bearbetnings_status[session_id].update({
                'progress': 40,
                'meddelande': 'Utför OCR-bearbetning...'
            })
            socketio.emit('status_update', bearbetnings_status[session_id], room=session_id)
            logger.info(f"Session {session_id}: Utför OCR-bearbetning")
            
            text = self.sorterare.extrahera_text_med_ocr(bilder)
            if not text.strip():
                raise Exception("Ingen text kunde extraheras från PDF")
            
            # Identifiera verksamhet
            bearbetnings_status[session_id].update({
                'progress': 60,
                'meddelande': 'Identifierar verksamhet...'
            })
            socketio.emit('status_update', bearbetnings_status[session_id], room=session_id)
            logger.info(f"Session {session_id}: Identifierar verksamhet")
            
            verksamhet, sannolikhet = self.sorterare.identifiera_verksamhet(text)
            logger.info(f"Session {session_id}: Verksamhet identifierad: {verksamhet} ({sannolikhet:.1f}%)")
            
            # Extrahera data
            bearbetnings_status[session_id].update({
                'progress': 80,
                'meddelande': 'Extraherar data...'
            })
            socketio.emit('status_update', bearbetnings_status[session_id], room=session_id)
            logger.info(f"Session {session_id}: Extraherar data")
            
            personnummer = self.sorterare.hitta_personnummer(text)
            remissdatum = self.sorterare.hitta_remissdatum(text)
            
            # Bestäm mål-mapp
            if sannolikhet >= SANNOLIKHET_TRÖSKEL:
                mål_mapp = self.sorterare.output_mapp / verksamhet
                status = "sorterad"
                logger.info(f"Session {session_id}: Remiss sorteras till {verksamhet}")
            else:
                mål_mapp = self.sorterare.osakert_mapp
                status = "osakert"
                logger.warning(f"Session {session_id}: Remiss flyttas till osakert (sannolikhet: {sannolikhet:.1f}%)")
            
            # Skapa mål-mapp om den inte finns
            mål_mapp.mkdir(parents=True, exist_ok=True)
            
            # Kopiera fil
            mål_fil = mål_mapp / fil_sokvag.name
            import shutil
            shutil.copy2(fil_sokvag, mål_fil)
            logger.info(f"Session {session_id}: PDF kopierad till {mål_fil}")
            
            # Skapa .dat-fil
            if personnummer and remissdatum:
                self.sorterare.skapa_dat_fil(
                    verksamhet, personnummer, remissdatum, 
                    fil_sokvag.name, mål_mapp
                )
                logger.info(f"Session {session_id}: .dat-fil skapad")
            
            # Slutför
            bearbetnings_status[session_id].update({
                'progress': 100,
                'meddelande': 'Bearbetning slutförd',
                'status': 'slutförd'
            })
            socketio.emit('status_update', bearbetnings_status[session_id], room=session_id)
            logger.info(f"Session {session_id}: Bearbetning slutförd")
            
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
            logger.error(f"Session {session_id}: Fel vid bearbetning av {fil_sokvag}: {e}")
            
            # Uppdatera status med fel
            bearbetnings_status[session_id].update({
                'status': 'fel',
                'meddelande': f'Fel: {str(e)}',
                'progress': 0
            })
            socketio.emit('status_update', bearbetnings_status[session_id], room=session_id)
            
            # Skicka felmeddelande till klienten
            socketio.emit('bearbetning_fel', {
                'filnamn': fil_sokvag.name,
                'fel': str(e)
            }, room=session_id)
            
            raise

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

@app.route('/api/statistik')
def api_statistik():
    """API för att hämta statistik över bearbetade filer"""
    try:
        output_mapp = Path('output')
        statistik = {}
        
        if output_mapp.exists():
            for verksamhet_mapp in output_mapp.iterdir():
                if verksamhet_mapp.is_dir():
                    pdf_filer = list(verksamhet_mapp.glob('*.pdf'))
                    dat_filer = list(verksamhet_mapp.glob('*.dat'))
                    statistik[verksamhet_mapp.name] = {
                        'pdf_filer': len(pdf_filer),
                        'dat_filer': len(dat_filer)
                    }
        
        return jsonify({
            'success': True,
            'statistik': statistik
        })
    except Exception as e:
        logger.error(f"Fel vid hämtning av statistik: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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

@app.route('/api/osakert_remisser')
def api_osakert_remisser():
    """API för att lista alla remisser i osakert-mappen"""
    try:
        web_sorterare = WebRemissSorterare()
        osakert_remisser = web_sorterare.sorterare.lista_osakert_remisser()
        return jsonify({
            'success': True,
            'remisser': osakert_remisser
        })
    except Exception as e:
        logger.error(f"Fel vid hämtning av osakert-remisser: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/omfördela_remiss', methods=['POST'])
def api_omfördela_remiss():
    """API för att omfördela en remiss från osakert till rätt verksamhet"""
    try:
        data = request.get_json()
        pdf_namn = data.get('pdf_namn')
        ny_verksamhet = data.get('ny_verksamhet')
        
        if not pdf_namn or not ny_verksamhet:
            return jsonify({
                'success': False,
                'error': 'Saknar pdf_namn eller ny_verksamhet'
            }), 400
        
        web_sorterare = WebRemissSorterare()
        resultat = web_sorterare.sorterare.omfördela_remiss(pdf_namn, ny_verksamhet)
        
        if resultat:
            return jsonify({
                'success': True,
                'meddelande': f'Remiss {pdf_namn} omfördela till {ny_verksamhet}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Kunde inte omfördela remissen'
            }), 500
            
    except Exception as e:
        logger.error(f"Fel vid omfördelningsprocessen: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/träna_ml_med_omfördelningsdata', methods=['POST'])
def api_träna_ml_med_omfördelningsdata():
    """API för att träna ML-modellen med data från omfördelningsprocesser"""
    try:
        data = request.get_json()
        omfördelningsdata = data.get('omfördelningsdata', [])
        
        if not omfördelningsdata:
            return jsonify({
                'success': False,
                'error': 'Ingen omfördelningsdata tillhandahållen'
            }), 400
        
        web_sorterare = WebRemissSorterare()
        web_sorterare.sorterare.träna_ml_med_omfördelningsdata(omfördelningsdata)
        
        return jsonify({
            'success': True,
            'meddelande': f'ML-modell tränad med {len(omfördelningsdata)} omfördelningsdata'
        })
        
    except Exception as e:
        logger.error(f"Fel vid ML-träning med omfördelningsdata: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/analysera_text', methods=['POST'])
def api_analysera_text():
    """API för att analysera text och identifiera verksamhet"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({
                'success': False,
                'error': 'Ingen text tillhandahållen'
            }), 400
        
        web_sorterare = WebRemissSorterare()
        verksamhet, sannolikhet = web_sorterare.sorterare.identifiera_verksamhet(text)
        
        return jsonify({
            'success': True,
            'verksamhet': verksamhet,
            'sannolikhet': sannolikhet,
            'analyserad_text': text[:500] + "..." if len(text) > 500 else text
        })
        
    except Exception as e:
        logger.error(f"Fel vid textanalys: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/debug_verksamhetsidentifiering', methods=['POST'])
def api_debug_verksamhetsidentifiering():
    """API för att debugga verksamhetsidentifieringen steg för steg"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({
                'success': False,
                'error': 'Ingen text tillhandahållen'
            }), 400
        
        text_lower = text.lower()
        debug_info = {
            'text_längd': len(text),
            'text_preview': text[:200] + "..." if len(text) > 200 else text,
            'analys_steg': []
        }
        
        # Steg 1: Sök efter mottagarfraser
        mottagarfraser = [
            "remiss till", "remitteras till", "mottagare:", "mottagande verksamhet:", 
            "mottagande avdelning:", "remissadress:", "till:", "för:", "till verksamhet:",
            "till avdelning:", "till klinik:", "till mottagare:", "till specialist:",
            "remitteras till", "skickas till", "överlämnas till", "överförs till"
        ]
        
        mottagar_match = None
        for fras in mottagarfraser:
            idx = text_lower.find(fras)
            if idx != -1:
                efter = text_lower[idx:idx+200]
                mottagar_match = {
                    'fras': fras,
                    'kontext': efter[:100] + "...",
                    'position': idx
                }
                break
        
        debug_info['analys_steg'].append({
            'steg': 'Mottagarfraser',
            'resultat': mottagar_match,
            'status': 'hittad' if mottagar_match else 'ej hittad'
        })
        
        # Steg 2: Sök efter specifika mottagarkliniker/avdelningar
        mottagarkliniker = {
            "Ortopedi": ["ortopedklinik", "ortopedkliniken", "ortopedavdelning", "ortopedavdelningen"],
            "Kirurgi": ["kirurgklinik", "kirurgkliniken", "kirurgavdelning", "kirurgavdelningen"],
            "Kardiologi": ["kardioklinik", "kardiokliniken", "kardioavdelning", "kardioavdelningen"],
            "Neurologi": ["neurologklinik", "neurologkliniken", "neurologavdelning", "neurologavdelningen"],
            "Gastroenterologi": ["gastroklinik", "gastrokliniken", "gastroavdelning", "gastroavdelningen"],
            "Endokrinologi": ["endokrinklinik", "endokrinkliniken", "endokrinavdelning", "endokrinavdelningen"],
            "Dermatologi": ["dermaklinik", "dermakliniken", "dermaavdelning", "dermaavdelningen"],
            "Urologi": ["uroklinik", "urokliniken", "uroavdelning", "uroavdelningen"],
            "Gynekologi": ["gynekoklinik", "gynekokliniken", "gynekoavdelning", "gynekoavdelningen"],
            "Oftalmologi": ["ögonklinik", "ögonkliniken", "ögonavdelning", "ögonavdelningen"],
            "Otorinolaryngologi": ["ent-klinik", "ent-kliniken", "ent-avdelning", "ent-avdelningen"]
        }
        
        klinik_match = None
        for verksamhet, kliniker in mottagarkliniker.items():
            for klinik in kliniker:
                if klinik in text_lower:
                    klinik_match = {
                        'verksamhet': verksamhet,
                        'klinik': klinik,
                        'position': text_lower.find(klinik)
                    }
                    break
            if klinik_match:
                break
        
        debug_info['analys_steg'].append({
            'steg': 'Mottagarkliniker',
            'resultat': klinik_match,
            'status': 'hittad' if klinik_match else 'ej hittad'
        })
        
        # Steg 3: Sök efter specifika nyckelord per verksamhet
        from config import VERKSAMHETER
        nyckelord_analys = {}
        
        for verksamhet, nyckelord in VERKSAMHETER.items():
            hittade_nyckelord = []
            for nyckel in nyckelord:
                if nyckel.lower() in text_lower:
                    antal = text_lower.count(nyckel.lower())
                    hittade_nyckelord.append({
                        'nyckel': nyckel,
                        'antal': antal,
                        'positioner': [i for i in range(len(text_lower)) if text_lower.startswith(nyckel.lower(), i)]
                    })
            
            if hittade_nyckelord:
                nyckelord_analys[verksamhet] = hittade_nyckelord
        
        debug_info['analys_steg'].append({
            'steg': 'Nyckelordsanalys',
            'resultat': nyckelord_analys,
            'status': 'hittade' if nyckelord_analys else 'ej hittade'
        })
        
        # Steg 4: Beräkna poäng per verksamhet
        poäng_per_verksamhet = {}
        for verksamhet, nyckelord in VERKSAMHETER.items():
            poäng = 0
            total_nyckelord = len(nyckelord)
            
            if verksamhet in nyckelord_analys:
                for hittad in nyckelord_analys[verksamhet]:
                    poäng += hittad['antal'] * 2
                    
                    # Extra poäng för kontext
                    if mottagar_match:
                        for pos in hittad['positioner']:
                            if abs(mottagar_match['position'] - pos) < 100:
                                poäng += 10
                    
                    # Extra poäng för specifika termer
                    if verksamhet == "Gynekologi":
                        gynekologiska_termer = ["livmoder", "äggstockar", "menstruation", "menopaus", "endometrios"]
                        for term in gynekologiska_termer:
                            if term in text_lower:
                                poäng += 15
                    
                    if verksamhet == "Kirurgi":
                        kirurgiska_termer = ["operation", "operera", "kirurgisk", "snitt", "laparoskopi"]
                        for term in kirurgiska_termer:
                            if term in text_lower:
                                poäng += 15
            
            sannolikhet = min(100, (poäng / total_nyckelord) * 15) if total_nyckelord > 0 else 0
            poäng_per_verksamhet[verksamhet] = {
                'poäng': poäng,
                'sannolikhet': round(sannolikhet, 1)
            }
        
        debug_info['analys_steg'].append({
            'steg': 'Poängberäkning',
            'resultat': poäng_per_verksamhet,
            'status': 'beräknad'
        })
        
        # Steg 5: Slutresultat
        bästa_verksamhet = max(poäng_per_verksamhet.items(), key=lambda x: x[1]['sannolikhet']) if poäng_per_verksamhet else ("Okänd", 0)
        
        debug_info['slutresultat'] = {
            'verksamhet': bästa_verksamhet[0],
            'sannolikhet': bästa_verksamhet[1]['sannolikhet']
        }
        
        return jsonify({
            'success': True,
            'debug_info': debug_info
        })
        
    except Exception as e:
        logger.error(f"Fel vid debug-analys: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/ai_status')
def api_ai_status():
    """API för att kontrollera AI-status"""
    try:
        web_sorterare = WebRemissSorterare()
        ai_status = web_sorterare.sorterare.ai_identifierare.få_användningsstatistik()
        
        return jsonify({
            'success': True,
            'ai_status': ai_status
        })
    except Exception as e:
        logger.error(f"Fel vid hämtning av AI-status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/testa_ai', methods=['POST'])
def api_testa_ai():
    """API för att testa AI-identifieraren"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({
                'success': False,
                'error': 'Ingen text tillhandahållen'
            }), 400
        
        web_sorterare = WebRemissSorterare()
        ai_resultat = web_sorterare.sorterare.ai_identifierare.identifiera_verksamhet(text)
        
        return jsonify({
            'success': True,
            'ai_resultat': {
                'verksamhet': ai_resultat[0],
                'sannolikhet': ai_resultat[1]
            }
        })
        
    except Exception as e:
        logger.error(f"Fel vid AI-test: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def läs_ai_config_från_fil():
    """Läs AI-konfiguration direkt från filen för att få senaste värden"""
    try:
        import os
        config_file = 'ai_config.py'
        if not os.path.exists(config_file):
            return None, None, None
        
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extrahera AI_TYPE
        import re
        ai_type_match = re.search(r'AI_TYPE\s*=\s*["\']([^"\']*)["\']', content)
        ai_type = ai_type_match.group(1) if ai_type_match else None
        
        # Extrahera LOKAL_AI_MODEL
        lokal_ai_model_match = re.search(r'LOKAL_AI_MODEL\s*=\s*["\']([^"\']*)["\']', content)
        lokal_ai_model = lokal_ai_model_match.group(1) if lokal_ai_model_match else None
        
        # Extrahera OLLAMA_MODEL
        ollama_model_match = re.search(r'OLLAMA_MODEL\s*=\s*["\']([^"\']*)["\']', content)
        ollama_model = ollama_model_match.group(1) if ollama_model_match else None
        
        return ai_type, lokal_ai_model, ollama_model
    except Exception as e:
        logger.error(f"Fel vid läsning av AI-konfiguration: {e}")
        return None, None, None

@app.route('/api/lokal_ai_status')
def api_lokal_ai_status():
    """API för att kontrollera lokal AI-status"""
    try:
        # Läs konfiguration direkt från filen för att få senaste värden
        ai_type, lokal_ai_model, ollama_model = läs_ai_config_från_fil()
        
        if not ai_type or ai_type != "lokal":
            return jsonify({
                'success': False,
                'error': 'Lokal AI är inte aktiverat i konfigurationen'
            })
        
        web_sorterare = WebRemissSorterare()
        if hasattr(web_sorterare.sorterare.ai_identifierare, 'få_modell_info'):
            modell_info = web_sorterare.sorterare.ai_identifierare.få_modell_info()
            # Uppdatera modellnamnet med den senaste konfigurationen
            if lokal_ai_model == "ollama" and ollama_model:
                modell_info["namn"] = ollama_model
        else:
            modell_info = {"error": "Lokal AI-identifierare stöder inte denna funktion"}
        
        return jsonify({
            'success': True,
            'ai_type': ai_type,
            'modell': lokal_ai_model,
            'modell_info': modell_info
        })
        
    except Exception as e:
        logger.error(f"Fel vid hämtning av lokal AI-status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/lokal_ai_modeller')
def api_lokal_ai_modeller():
    """API för att lista tillgängliga lokala AI-modeller"""
    try:
        from ai_config import AI_TYPE
        
        if AI_TYPE != "lokal":
            return jsonify({
                'success': False,
                'error': 'Lokal AI är inte aktiverat i konfigurationen'
            })
        
        web_sorterare = WebRemissSorterare()
        if hasattr(web_sorterare.sorterare.ai_identifierare, 'få_tillgängliga_modeller'):
            modeller = web_sorterare.sorterare.ai_identifierare.få_tillgängliga_modeller()
        else:
            modeller = {"error": "Lokal AI-identifierare stöder inte denna funktion"}
        
        return jsonify({
            'success': True,
            'modeller': modeller
        })
        
    except Exception as e:
        logger.error(f"Fel vid hämtning av lokala AI-modeller: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/byt_lokal_ai_modell', methods=['POST'])
def api_byt_lokal_ai_modell():
    """API för att byta lokal AI-modell"""
    try:
        data = request.get_json()
        ny_modell = data.get('modell', '')
        
        if not ny_modell:
            return jsonify({
                'success': False,
                'error': 'Ingen modell angiven'
            }), 400
        
        from ai_config import AI_TYPE
        
        if AI_TYPE != "lokal":
            return jsonify({
                'success': False,
                'error': 'Lokal AI är inte aktiverat i konfigurationen'
            })
        
        web_sorterare = WebRemissSorterare()
        if hasattr(web_sorterare.sorterare.ai_identifierare, 'byt_modell'):
            resultat = web_sorterare.sorterare.ai_identifierare.byt_modell(ny_modell)
            
            if resultat:
                return jsonify({
                    'success': True,
                    'meddelande': f'Modell bytt till: {ny_modell}',
                    'ny_modell': ny_modell
                })
            else:
                # Hämta aktuell modell efter misslyckat byte
                aktuell_modell = web_sorterare.sorterare.ai_identifierare.model_type
                return jsonify({
                    'success': False,
                    'error': f'Kunde inte byta till modell: {ny_modell}',
                    'ny_modell': aktuell_modell
                }), 500
        else:
            return jsonify({
                'success': False,
                'error': 'Lokal AI-identifierare stöder inte byte av modell'
            }), 500
        
    except Exception as e:
        logger.error(f"Fel vid byte av lokal AI-modell: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/ollama_installerade')
def api_ollama_installerade():
    """API för att hämta installerade Ollama-modeller"""
    try:
        import requests
        
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return jsonify({
                'success': True,
                'modeller': [model['name'] for model in models]
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Kan inte ansluta till Ollama'
            }), 500
            
    except requests.exceptions.RequestException:
        return jsonify({
            'success': False,
            'modeller': []
        })
    except Exception as e:
        logger.error(f"Fel vid kontroll av installerade Ollama-modeller: {e}")
        return jsonify({
            'success': False,
            'modeller': []
        })

@app.route('/api/byt_ollama_modell', methods=['POST'])
def api_byt_ollama_modell():
    """API för att byta Ollama-modell"""
    try:
        data = request.get_json()
        ny_modell = data.get('modell', '')
        
        if not ny_modell:
            return jsonify({
                'success': False,
                'error': 'Ingen modell angiven'
            }), 400
        
        # Uppdatera ai_config.py
        import os
        config_file = 'ai_config.py'
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Ersätt OLLAMA_MODEL-värdet
            import re
            pattern = r'OLLAMA_MODEL\s*=\s*["\'][^"\']*["\']'
            replacement = f'OLLAMA_MODEL = "{ny_modell}"'
            new_content = re.sub(pattern, replacement, content)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
        
        # Ladda om AI-identifieraren med den nya modellen
        try:
            # Skapa en ny WebRemissSorterare-instans för att ladda om AI-identifieraren
            global web_sorterare
            web_sorterare = WebRemissSorterare()
            logger.info(f"AI-identifierare laddad om med modell: {ny_modell}")
        except Exception as e:
            logger.error(f"Fel vid omladdning av AI-identifierare: {e}")
            # Fortsätt ändå eftersom konfigurationen är uppdaterad
        
        return jsonify({
            'success': True,
            'meddelande': f'Ollama-modell bytt till: {ny_modell}',
            'ny_modell': ny_modell
        })
        
    except Exception as e:
        logger.error(f"Fel vid byte av Ollama-modell: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/download/<path:filename>')
def download_file(filename):
    """Låter användare ladda ner bearbetade filer"""
    return send_from_directory('output', filename)

@app.route('/api/verksamheter', methods=['GET'])
def api_verksamheter():
    """API för att hämta alla verksamheter"""
    try:
        from config import VERKSAMHETER
        return jsonify({
            'success': True,
            'verksamheter': VERKSAMHETER
        })
    except Exception as e:
        logger.error(f"Fel vid hämtning av verksamheter: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/lägg_till_verksamhet', methods=['POST'])
def api_lägg_till_verksamhet():
    """API för att lägga till en ny verksamhet"""
    try:
        data = request.get_json()
        verksamhet_namn = data.get('namn', '').strip()
        nyckelord = data.get('nyckelord', [])
        
        if not verksamhet_namn:
            return jsonify({
                'success': False,
                'error': 'Verksamhetsnamn krävs'
            }), 400
        
        if not nyckelord:
            return jsonify({
                'success': False,
                'error': 'Minst ett nyckelord krävs'
            }), 400
        
        # Importera config dynamiskt
        import config
        import importlib
        
        # Lägg till verksamheten i config
        if verksamhet_namn not in config.VERKSAMHETER:
            config.VERKSAMHETER[verksamhet_namn] = nyckelord
            
            # Skapa output-mapp för den nya verksamheten
            output_mapp = Path(f'output/{verksamhet_namn}')
            output_mapp.mkdir(exist_ok=True)
            
            # Uppdatera ML-identifieraren om den finns
            try:
                web_sorterare = WebRemissSorterare()
                if hasattr(web_sorterare.sorterare, 'ml_identifierare'):
                    # Träna om ML-modellen med den nya verksamheten
                    web_sorterare.ml_identifierare.träna_modell()
                    logger.info(f"ML-modell tränad om med ny verksamhet: {verksamhet_namn}")
            except Exception as e:
                logger.warning(f"Kunde inte träna om ML-modellen: {e}")
            
            logger.info(f"Ny verksamhet tillagd: {verksamhet_namn} med {len(nyckelord)} nyckelord")
            
            return jsonify({
                'success': True,
                'meddelande': f'Verksamhet "{verksamhet_namn}" tillagd framgångsrikt',
                'verksamhet': {
                    'namn': verksamhet_namn,
                    'nyckelord': nyckelord
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Verksamhet "{verksamhet_namn}" finns redan'
            }), 400
            
    except Exception as e:
        logger.error(f"Fel vid tillägg av verksamhet: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/ta_bort_verksamhet', methods=['POST'])
def api_ta_bort_verksamhet():
    """API för att ta bort en verksamhet"""
    try:
        data = request.get_json()
        verksamhet_namn = data.get('namn', '').strip()
        
        if not verksamhet_namn:
            return jsonify({
                'success': False,
                'error': 'Verksamhetsnamn krävs'
            }), 400
        
        import config
        
        if verksamhet_namn in config.VERKSAMHETER:
            # Ta bort från config
            del config.VERKSAMHETER[verksamhet_namn]
            
            # Flytta alla filer från den verksamheten till "osakert"
            verksamhet_mapp = Path(f'output/{verksamhet_namn}')
            osakert_mapp = Path('output/osakert')
            
            if verksamhet_mapp.exists():
                for fil in verksamhet_mapp.iterdir():
                    if fil.is_file():
                        # Flytta till osakert
                        ny_sökväg = osakert_mapp / fil.name
                        fil.rename(ny_sökväg)
                        logger.info(f"Flyttade {fil.name} till osakert")
                
                # Ta bort den tomma mappen
                verksamhet_mapp.rmdir()
            
            logger.info(f"Verksamhet borttagen: {verksamhet_namn}")
            
            return jsonify({
                'success': True,
                'meddelande': f'Verksamhet "{verksamhet_namn}" borttagen framgångsrikt'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Verksamhet "{verksamhet_namn}" finns inte'
            }), 400
            
    except Exception as e:
        logger.error(f"Fel vid borttagning av verksamhet: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/verksamhet_fil_antal')
def api_verksamhet_fil_antal():
    """API för att räkna antal filer per verksamhet"""
    try:
        verksamhet = request.args.get('verksamhet', '')
        
        if not verksamhet:
            return jsonify({
                'success': False,
                'error': 'Verksamhetsnamn krävs'
            }), 400
        
        verksamhet_mapp = Path(f'output/{verksamhet}')
        
        if not verksamhet_mapp.exists():
            return jsonify({
                'success': True,
                'antal': 0
            })
        
        # Räkna PDF-filer
        pdf_filer = list(verksamhet_mapp.glob('*.pdf'))
        
        return jsonify({
            'success': True,
            'antal': len(pdf_filer)
        })
        
    except Exception as e:
        logger.error(f"Fel vid räkning av filer för verksamhet {verksamhet}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/ai_förslag_verksamhet', methods=['POST'])
def api_ai_förslag_verksamhet():
    """API för att få AI-förslag på nya verksamheter baserat på text"""
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        pdf_namn = data.get('pdf_namn', '')  # Ny parameter för PDF-filnamn
        
        if not text:
            return jsonify({
                'success': False,
                'error': 'Text krävs för analys'
            }), 400
        
        from config import VERKSAMHETER
        
        # Använd lokal AI för att analysera texten
        web_sorterare = WebRemissSorterare()
        
        if hasattr(web_sorterare.sorterare, 'ai_identifierare') and web_sorterare.sorterare.ai_identifierare:
            # Få AI:s analys
            verksamhet, sannolikhet = web_sorterare.sorterare.ai_identifierare.identifiera_verksamhet(text)
            
            # Kontrollera om AI föreslår en verksamhet som inte finns
            if verksamhet not in VERKSAMHETER and verksamhet != "Okänd":
                # Skapa förslag baserat på textanalys
                förslag = skapa_verksamhets_förslag(text, verksamhet)
                
                return jsonify({
                    'success': True,
                    'ai_verksamhet': verksamhet,
                    'sannolikhet': sannolikhet,
                    'förslag': förslag,
                    'meddelande': f'AI föreslår ny verksamhet: {verksamhet}',
                    'pdf_namn': pdf_namn
                })
            else:
                return jsonify({
                    'success': True,
                    'ai_verksamhet': verksamhet,
                    'sannolikhet': sannolikhet,
                    'förslag': None,
                    'meddelande': f'AI identifierade befintlig verksamhet: {verksamhet}',
                    'pdf_namn': pdf_namn
                })
        else:
            return jsonify({
                'success': False,
                'error': 'AI-identifierare inte tillgänglig'
            }), 500
            
    except Exception as e:
        logger.error(f"Fel vid AI-förslag på verksamhet: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/ai_förslag_från_pdf', methods=['POST'])
def api_ai_förslag_från_pdf():
    """API för att få AI-förslag på nya verksamheter baserat på uppladdad PDF"""
    try:
        data = request.get_json()
        pdf_namn = data.get('pdf_namn', '').strip()
        
        if not pdf_namn:
            return jsonify({
                'success': False,
                'error': 'PDF-filnamn krävs'
            }), 400
        
        from config import VERKSAMHETER
        
        # Hitta PDF-filen i osakert-mappen
        pdf_sökväg = Path(f'output/osakert/{pdf_namn}')
        
        if not pdf_sökväg.exists():
            return jsonify({
                'success': False,
                'error': f'PDF-fil {pdf_namn} hittades inte'
            }), 404
        
        # Använd RemissSorterare för att extrahera text från PDF
        web_sorterare = WebRemissSorterare()
        
        try:
            # Konvertera PDF till bilder
            bilder = web_sorterare.sorterare.pdf_till_bilder(pdf_sökväg)
            if not bilder:
                return jsonify({
                    'success': False,
                    'error': 'Kunde inte konvertera PDF till bilder'
                }), 500
            
            # Extrahera text med OCR
            text = web_sorterare.sorterare.extrahera_text_med_ocr(bilder)
            if not text.strip():
                return jsonify({
                    'success': False,
                    'error': 'Ingen text kunde extraheras från PDF'
                }), 500
            
            # Använd AI för att analysera texten
            if hasattr(web_sorterare.sorterare, 'ai_identifierare') and web_sorterare.sorterare.ai_identifierare:
                verksamhet, sannolikhet = web_sorterare.sorterare.ai_identifierare.identifiera_verksamhet(text)
                
                # Kontrollera om AI föreslår en verksamhet som inte finns
                if verksamhet not in VERKSAMHETER and verksamhet != "Okänd":
                    # Skapa förslag baserat på textanalys
                    förslag = skapa_verksamhets_förslag(text, verksamhet)
                    
                    return jsonify({
                        'success': True,
                        'ai_verksamhet': verksamhet,
                        'sannolikhet': sannolikhet,
                        'förslag': förslag,
                        'meddelande': f'AI föreslår ny verksamhet: {verksamhet}',
                        'pdf_namn': pdf_namn,
                        'extraherad_text': text[:500] + "..." if len(text) > 500 else text  # Visa första 500 tecken
                    })
                else:
                    return jsonify({
                        'success': True,
                        'ai_verksamhet': verksamhet,
                        'sannolikhet': sannolikhet,
                        'förslag': None,
                        'meddelande': f'AI identifierade befintlig verksamhet: {verksamhet}',
                        'pdf_namn': pdf_namn,
                        'extraherad_text': text[:500] + "..." if len(text) > 500 else text
                    })
            else:
                return jsonify({
                    'success': False,
                    'error': 'AI-identifierare inte tillgänglig'
                }), 500
                
        except Exception as e:
            logger.error(f"Fel vid bearbetning av PDF {pdf_namn}: {e}")
            return jsonify({
                'success': False,
                'error': f'Fel vid bearbetning av PDF: {str(e)}'
            }), 500
            
    except Exception as e:
        logger.error(f"Fel vid AI-förslag från PDF: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def skapa_verksamhets_förslag(text: str, föreslagen_verksamhet: str) -> dict:
    """Skapar förslag på ny verksamhet baserat på text och AI-analys"""
    try:
        # Extrahera relevanta termer från texten
        text_lower = text.lower()
        
        # Sök efter medicinska termer som kan indikera verksamhet
        medicinska_termer = []
        
        # Vanliga medicinska suffix
        suffix_list = ['ologi', 'iatri', 'ologi', 'ologi', 'ologi']
        
        # Sök efter termer som slutar med medicinska suffix
        import re
        for suffix in suffix_list:
            pattern = r'\b\w+' + suffix + r'\b'
            matches = re.findall(pattern, text_lower)
            medicinska_termer.extend(matches)
        
        # Sök efter specifika medicinska områden
        områden = {
            'hud': ['hud', 'dermatologi', 'eksem', 'psoriasis', 'melanom', 'akne'],
            'ögon': ['öga', 'ögon', 'syn', 'katarakt', 'glaukom', 'oftalmologi'],
            'öron': ['öra', 'hörsel', 'tinnitus', 'otologi', 'otorinolaryngologi'],
            'hjärta': ['hjärta', 'kardiologi', 'arytmi', 'infarkt', 'hjärtfel'],
            'hjärna': ['hjärna', 'neurologi', 'stroke', 'epilepsi', 'parkinson'],
            'mage': ['mage', 'gastroenterologi', 'ulcus', 'kolit', 'lever'],
            'lungor': ['lunga', 'pneumologi', 'astma', 'kronisk', 'bronkit'],
            'ben': ['ben', 'ortopedi', 'fraktur', 'led', 'artros'],
            'urin': ['urin', 'urologi', 'prostata', 'njure', 'urinblåsa'],
            'gynekologi': ['livmoder', 'äggstockar', 'menstruation', 'gynekologi']
        }
        
        # Hitta matchande områden
        matchande_områden = []
        for område, termer in områden.items():
            if any(term in text_lower for term in termer):
                matchande_områden.append(område)
        
        # Skapa förslag på nyckelord
        föreslagna_nyckelord = []
        
        # Lägg till termer från matchande områden
        for område in matchande_områden:
            föreslagna_nyckelord.extend(områden[område][:3])  # Ta första 3 termerna
        
        # Lägg till unika termer från texten
        unika_termer = set()
        for term in medicinska_termer:
            if term not in föreslagna_nyckelord:
                unika_termer.add(term)
        
        föreslagna_nyckelord.extend(list(unika_termer)[:5])  # Max 5 extra termer
        
        # Ta bort duplicerade och begränsa längden
        föreslagna_nyckelord = list(dict.fromkeys(föreslagna_nyckelord))[:8]
        
        return {
            'namn': föreslagen_verksamhet,
            'nyckelord': föreslagna_nyckelord,
            'motivering': f'AI identifierade {föreslagen_verksamhet} baserat på textanalys',
            'matchande_områden': matchande_områden,
            'medicinska_termer': medicinska_termer
        }
        
    except Exception as e:
        logger.error(f"Fel vid skapande av verksamhetsförslag: {e}")
        return {
            'namn': föreslagen_verksamhet,
            'nyckelord': ['medicinsk', 'specialist', 'remiss'],
            'motivering': f'AI föreslår {föreslagen_verksamhet}',
            'matchande_områden': [],
            'medicinska_termer': []
        }

# SocketIO-händelser
@socketio.on('connect')
def handle_connect():
    """Hanterar klientanslutning"""
    session_id = request.sid
    logger.info(f"Klient ansluten: {session_id}")
    
    # Skapa rum för klienten
    socketio.emit('connected', {'session_id': session_id}, room=session_id)

@socketio.on('join_session')
def handle_join_session(data):
    """Hanterar att klienten ansluter till en session"""
    session_id = data.get('session_id')
    if session_id:
        join_room(session_id)
        logger.info(f"Klient ansluten till session: {session_id}")
        
        # Skicka befintlig status om den finns
        if session_id in bearbetnings_status:
            socketio.emit('status_update', bearbetnings_status[session_id], room=session_id)

@socketio.on('disconnect')
def handle_disconnect():
    """Hanterar klientfrånkoppling"""
    session_id = request.sid
    logger.info(f"Klient frånkopplad: {session_id}")
    
    # Rensa upp session-data om det behövs
    # (Behåll data för att kunna visa resultat senare)

if __name__ == '__main__':
    # Träna ML-modellen vid start om den inte finns
    if not web_sorterare.ml_identifierare.trained:
        logger.info("Tränar ML-modell vid start...")
        try:
            web_sorterare.ml_identifierare.träna_modell()
        except Exception as e:
            logger.warning(f"Kunde inte träna ML-modell: {e}")
    
    # Starta Flask-app
    socketio.run(app, debug=True, host='0.0.0.0', port=8000)
