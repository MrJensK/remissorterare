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

@app.route('/api/lokal_ai_status')
def api_lokal_ai_status():
    """API för att kontrollera lokal AI-status"""
    try:
        from ai_config import AI_TYPE, LOKAL_AI_MODEL
        
        if AI_TYPE != "lokal":
            return jsonify({
                'success': False,
                'error': 'Lokal AI är inte aktiverat i konfigurationen'
            })
        
        web_sorterare = WebRemissSorterare()
        if hasattr(web_sorterare.sorterare.ai_identifierare, 'få_modell_info'):
            modell_info = web_sorterare.sorterare.ai_identifierare.få_modell_info()
        else:
            modell_info = {"error": "Lokal AI-identifierare stöder inte denna funktion"}
        
        return jsonify({
            'success': True,
            'ai_type': AI_TYPE,
            'modell': LOKAL_AI_MODEL,
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
                    'meddelande': f'Modell bytt till: {ny_modell}'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'Kunde inte byta till modell: {ny_modell}'
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

@app.route('/download/<path:filename>')
def download_file(filename):
    """Låter användare ladda ner bearbetade filer"""
    return send_from_directory('output', filename)

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
        socketio.join_room(session_id)
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
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
