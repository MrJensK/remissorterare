"""
Konfigurationsfil för Remissorterare
"""

# Tröskelvärden
SANNOLIKHET_TRÖSKEL = 90  # Minsta sannolikhet för att sortera till verksamhet

# OCR-inställningar
OCR_DPI = 300
OCR_SPRÅK = 'swe+eng'
OCR_PSM = '--psm 6'

# Verksamheter och nyckelord
VERKSAMHETER = {
    "Ortopedi": [
        "ortopedi", "ortopedisk", "led", "leder", "knä", "höft", "rygg", "ryggrad",
        "fraktur", "brott", "artros", "artrit", "reumatism", "reumatoid",
        "spondylit", "skolios", "hernia", "diskbråck", "menisk", "korsband",
        "tendinit", "bursit", "karpaltunnelsyndrom", "frozen shoulder"
    ],
    "Kirurgi": [
        "kirurgi", "kirurgisk", "operation", "operera", "kirurg", "snitt",
        "laparoskopi", "endoskopi", "biopsi", "tumör", "cancer", "malign",
        "benign", "appendicit", "gallsten", "hernia", "bråck", "polyp",
        "cholecystektomi", "appendektomi", "mastectomi", "prostatektomi"
    ],
    "Kardiologi": [
        "kardiologi", "kardiologisk", "hjärta", "hjärt", "kardiak", "arytmi",
        "fibrillering", "angina", "infarkt", "myokard", "ekg", "ekokardiografi",
        "stent", "bypass", "pacemaker", "defibrillator", "blodtryck", "hypertension",
        "hjärtsvikt", "kardiomyopati", "perikardit", "endokardit"
    ],
    "Neurologi": [
        "neurologi", "neurologisk", "hjärna", "hjärn", "nerv", "neurolog",
        "stroke", "cerebral", "epilepsi", "parkinson", "alzheimer", "demens",
        "migrän", "huvudvärk", "ms", "multipel skleros", "tumör", "cancer",
        "meningit", "encefalit", "neuropati", "radikulopati"
    ],
    "Gastroenterologi": [
        "gastroenterologi", "gastroenterologisk", "mage", "mag", "tarm", "lever",
        "galla", "bukspottkörtel", "ulcus", "sår", "kolit", "crohn", "celiaki",
        "reflux", "esofagit", "gastrit", "hepatit", "cirros", "pankreatit",
        "divertikulit", "irritable bowel", "ibs"
    ],
    "Endokrinologi": [
        "endokrinologi", "endokrinologisk", "diabetes", "socker", "glukos",
        "insulin", "sköldkörtel", "thyreoidea", "hypofys", "binjurar",
        "hormon", "kortisol", "testosteron", "östrogen", "progesteron",
        "hypothyreos", "hyperthyreos", "cushing", "addison", "acromegali"
    ],
    "Dermatologi": [
        "dermatologi", "dermatologisk", "hud", "hud", "eksem", "psoriasis",
        "akne", "vårtor", "födelsemärke", "melanom", "cancer", "allergi",
        "urticaria", "rosacea", "vitiligo", "alopeci", "basalcellscancer",
        "plattcellscancer", "keratos", "dermatit"
    ],
    "Urologi": [
        "urologi", "urologisk", "urin", "urinblåsa", "prostata", "njure",
        "ureter", "urinrör", "urininkontinens", "prostatit", "cystit",
        "sten", "tumör", "cancer", "impotens", "infertilitet", "pyelonefrit",
        "glomerulonefrit", "hydronefros", "vesikoureteral reflux"
    ],
    "Gynekologi": [
        "gynekologi", "gynekologisk", "gynekolog", "livmoder", "äggstockar",
        "menstruation", "menopaus", "endometrios", "myom", "cervix",
        "ovariell", "mammografi", "bröst", "graviditet", "förlossning"
    ],
    "Oftalmologi": [
        "oftalmologi", "oftalmologisk", "öga", "ögon", "syn", "katarakt",
        "glaukom", "retina", "makula", "diabetisk retinopati", "strabism",
        "amblyopi", "konjunktivit", "keratit", "uveit"
    ],
    "Otorinolaryngologi": [
        "otorinolaryngologi", "ent", "öra", "näsa", "hals", "tonsillit",
        "otit", "sinusit", "rinit", "laryngit", "faryngit", "hörsel",
        "yrsel", "tinnitus", "vertigo", "menieres"
    ]
}

# Mappnamn
INPUT_MAPP = "input"
OUTPUT_MAPP = "output"
OSAKERT_MAPP = "osakert"

# Loggningsinställningar
LOG_FIL = "remiss_sorterare.log"
LOG_NIVÅ = "INFO"
