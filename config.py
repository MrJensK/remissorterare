"""
Konfigurationsfil för Remissorterare
"""

# Tröskelvärden
SANNOLIKHET_TRÖSKEL = 70  # Minsta sannolikhet för att sortera till verksamhet

# OCR-inställningar
OCR_DPI = 300
OCR_SPRÅK = 'swe+eng'
OCR_PSM = '--psm 6'

# Verksamheter och nyckelord (laddas från JSON-fil)
import json
import os

def ladda_verksamheter():
    """Ladda verksamheter från JSON-fil"""
    try:
        json_fil = os.path.join(os.path.dirname(__file__), 'verksamheter.json')
        with open(json_fil, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Fallback om JSON-filen inte finns
        return {
            "Ortopedi": ["ortopedi", "ortopedisk", "led", "leder", "knä", "höft", "rygg", "ryggrad"],
            "Kirurgi": ["kirurgi", "kirurgisk", "operation", "operera", "kirurg", "snitt"],
            "Kardiologi": ["kardiologi", "kardiologisk", "hjärta", "hjärt", "kardiak", "arytmi"],
            "Neurologi": ["neurologi", "neurologisk", "hjärna", "hjärn", "nerv", "neurolog"],
            "Gastroenterologi": ["gastroenterologi", "gastroenterologisk", "mage", "mag", "tarm", "lever"],
            "Endokrinologi": ["endokrinologi", "endokrinologisk", "diabetes", "socker", "glukos", "insulin"],
            "Dermatologi": ["dermatologi", "dermatologisk", "hud", "eksem", "psoriasis", "akne"],
            "Urologi": ["urologi", "urologisk", "urin", "urinblåsa", "prostata", "njure"],
            "Gynekologi": ["gynekologi", "gynekologisk", "gynekolog", "livmoder", "äggstockar", "menstruation"],
            "Oftalmologi": ["oftalmologi", "oftalmologisk", "öga", "ögon", "syn", "katarakt"],
            "Otorinolaryngologi": ["otorinolaryngologi", "ent", "öra", "näsa", "hals", "tonsillit"]
        }
    except Exception as e:
        print(f"Fel vid laddning av verksamheter.json: {e}")
        return {}

VERKSAMHETER = ladda_verksamheter()

# Mappnamn
INPUT_MAPP = "input"
OUTPUT_MAPP = "output"
OSAKERT_MAPP = "osakert"

# Loggningsinställningar
LOG_FIL = "remiss_sorterare.log"
LOG_NIVÅ = "INFO"

# AI-inställningar
AI_ENABLED = True
AI_MODEL = "gpt-3.5-turbo"
AI_TEMPERATURE = 0.1
AI_MAX_TOKENS = 200
AI_CONFIDENCE_THRESHOLD = 70  # Minsta sannolikhet för att använda AI-resultat
