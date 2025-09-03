#!/bin/bash

# Installationsskript för Remissorterare
# Detta skript installerar alla nödvändiga beroenden och konfigurerar miljön

set -e  # Avsluta vid fel

echo "🚀 Startar installation av Remissorterare med AI-stöd..."
echo "========================================================"

# Kontrollera operativsystem
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
else
    echo "❌ Operativsystemet stöds inte: $OSTYPE"
    exit 1
fi

echo "✅ Operativsystem: $OS"

# Kontrollera Python-version

# Installera och använd pyenv för att säkra Python 3.12
if ! command -v pyenv &> /dev/null; then
    echo "📦 Installerar pyenv..."
    curl https://pyenv.run | bash
    export PATH="$HOME/.pyenv/bin:$PATH"
    eval "$(pyenv init -)"
    eval "$(pyenv virtualenv-init -)"
fi

export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

required_version="3.12.0"
    if ! pyenv versions | grep -q "$required_version"; then
        echo "📦 Installerar byggberoenden för Python..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y make build-essential libssl-dev zlib1g-dev \
                libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
                libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev \
                python3-openssl git
        fi
        echo "📦 Installerar Python $required_version via pyenv..."
        pyenv install $required_version
    fi
pyenv local $required_version
echo "✅ Python-version: $(python --version) (pyenv)"

# Installera Tesseract OCR och Poppler
echo ""
echo "📦 Installerar Tesseract OCR och Poppler..."

if [ "$OS" = "macos" ]; then
    if ! command -v brew &> /dev/null; then
        echo "❌ Homebrew är inte installerat. Installera först: https://brew.sh/"
        exit 1
    fi
    
    echo "Installerar Tesseract via Homebrew..."
    brew install tesseract
    brew install tesseract-lang
    
    echo "Installerar Poppler via Homebrew..."
    brew install poppler
    
elif [ "$OS" = "linux" ]; then
    if command -v apt-get &> /dev/null; then
        echo "Installerar Tesseract via apt..."
        sudo apt-get update
        sudo apt-get install -y tesseract-ocr
        sudo apt-get install -y tesseract-ocr-swe
        
        echo "Installerar Poppler via apt..."
        sudo apt-get install -y poppler-utils
    elif command -v yum &> /dev/null; then
        echo "Installerar Tesseract via yum..."
        sudo yum install -y tesseract
        sudo yum install -y tesseract-langpack-swe
        
        echo "Installerar Poppler via yum..."
        sudo yum install -y poppler-utils
    else
        echo "❌ Pakethanterare (apt eller yum) hittades inte"
        exit 1
    fi
fi

# Verifiera Tesseract-installation
if command -v tesseract &> /dev/null; then
    tesseract_version=$(tesseract --version | head -n1)
    echo "✅ Tesseract installerat: $tesseract_version"
else
    echo "❌ Tesseract kunde inte installeras"
    exit 1
fi

# Verifiera Poppler-installation
if command -v pdftoppm &> /dev/null; then
    poppler_version=$(pdftoppm -v 2>&1 | head -n1)
    echo "✅ Poppler installerat: $poppler_version"
else
    echo "❌ Poppler kunde inte installeras"
    exit 1
fi

# Skapa virtuell miljö
echo ""
echo "🐍 Skapar virtuell Python-miljö med Python $required_version..."
if [ ! -d "venv" ]; then
    python -m venv venv
    echo "✅ Virtuell miljö skapad"
else
    echo "✅ Virtuell miljö finns redan"
fi

# Aktivera virtuell miljö
echo "Aktiverar virtuell miljö..."
source venv/bin/activate

# Uppgradera pip
echo "Uppgraderar pip..."
pip install --upgrade pip

# Installera grundläggande Python-beroenden
echo ""
echo "📦 Installerar grundläggande Python-beroenden..."
pip install pytesseract pdf2image Pillow opencv-python numpy python-dateutil scikit-learn joblib Flask Flask-SocketIO Werkzeug

# Installera AI-bibliotek
echo ""
echo "🤖 Installerar AI-bibliotek för lokala modeller..."
pip install transformers torch sentence-transformers

# Installera OpenAI (valfritt)
echo ""
echo "🔑 OpenAI-stöd (valfritt)..."
read -p "Vill du installera OpenAI-stöd? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔑 Installerar OpenAI-stöd..."
    pip install openai
    echo "✅ OpenAI installerat"
else
    echo "ℹ️  Hoppar över OpenAI-installation"
fi

# Skapa mappstruktur
echo ""
echo "📁 Skapar mappstruktur..."
mkdir -p input output/osakert models/local_ai

# Skapa verksamhetsmappar från config
echo "Skapar verksamhetsmappar..."
python3 -c "
from config import VERKSAMHETER
import os
for verksamhet in VERKSAMHETER.keys():
    os.makedirs(f'output/{verksamhet}', exist_ok=True)
    print(f'✅ Skapade mapp: output/{verksamhet}')
"

# Konfigurera AI-inställningar
echo ""
echo "⚙️  Konfigurerar AI-inställningar..."

# Skapa ai_config.py om den inte finns
if [ ! -f "ai_config.py" ]; then
    echo "Skapar ai_config.py..."
    cat > ai_config.py << 'EOF'
#!/usr/bin/env python3
"""
AI-konfiguration för Remissorterare
"""

import os
from typing import Optional

# AI-inställningar
AI_ENABLED = True
AI_TYPE = "lokal"  # "openai" eller "lokal"
AI_MODEL = "gpt-3.5-turbo" # Default for OpenAI
AI_TEMPERATURE = 0.1
AI_MAX_TOKENS = 200
AI_CONFIDENCE_THRESHOLD = 70  # Minsta sannolikhet för att använda AI-resultat

# Lokala AI-modeller
LOKAL_AI_ENABLED = True
LOKAL_AI_MODEL = "sentence_transformer"  # "sentence_transformer", "swedish_bert", "multilingual_bert"
LOKAL_AI_DOWNLOAD_MODELS = True  # Ladda ner modeller automatiskt
LOKAL_AI_CACHE_DIR = "models/local_ai"  # Cache-mapp för lokala modeller

# OpenAI-inställningar (endast om AI_TYPE = "openai")
OPENAI_API_KEY: Optional[str] = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL: str = "gpt-3.5-turbo"
OPENAI_TEMPERATURE: float = 0.1
OPENAI_MAX_TOKENS: int = 200

# Fallback-inställningar
USE_ML_FALLBACK: bool = True
USE_RULE_BASED_FALLBACK: bool = True

# Loggningsinställningar för AI
AI_LOG_LEVEL: str = "INFO"
AI_LOG_PROMPTS: bool = False  # Logga inte prompts av säkerhetsskäl
AI_LOG_RESPONSES: bool = True  # Logga AI-svar för debugging

# Kostnadsoptimering
AI_MAX_TEXT_LENGTH: int = 1000  # Begränsa textlängd för att spara tokens
AI_CACHE_ENABLED: bool = True  # Aktivera caching av AI-svar
AI_CACHE_TTL: int = 3600  # Cache TTL i sekunder (1 timme)

# Säkerhetsinställningar
AI_CONTENT_FILTER: bool = True  # Aktivera OpenAI:s innehållsfilter
AI_MAX_RETRIES: int = 3  # Max antal försök vid fel
AI_TIMEOUT: int = 30  # Timeout i sekunder
EOF
    echo "✅ ai_config.py skapad"
else
    echo "✅ ai_config.py finns redan"
fi

# Gör skript körbara
echo ""
echo "🔧 Gör skript körbara..."
chmod +x remiss_sorterare.py
chmod +x test_remissorterare.py
chmod +x run_scheduled.py

# Kör tester
echo ""
echo "🧪 Kör tester för att verifiera installationen..."
if python3 test_remissorterare.py; then
    echo "✅ Alla tester godkända!"
else
    echo "⚠️ Vissa tester misslyckades. Kontrollera installationen."
fi

# Testa AI-installation
echo ""
echo "🤖 Testar AI-installation..."
python3 -c "
try:
    from transformers import pipeline
    from sentence_transformers import SentenceTransformer
    import torch
    print('✅ Lokala AI-bibliotek fungerar')
except ImportError as e:
    print(f'❌ Problem med lokala AI-bibliotek: {e}')

try:
    import openai
    print('✅ OpenAI-bibliotek fungerar')
except ImportError:
    print('ℹ️  OpenAI-bibliotek inte installerat (valfritt)')
"

# Skapa exempel på schemalagd körning
echo ""
echo "📅 Skapar exempel för schemalagd körning..."

cat > cron_exempel.txt << 'EOF'
# Exempel på cron-konfiguration för körning varje timme:
# 0 * * * * cd /sökväg/till/remissorterare && ./venv/bin/python run_scheduled.py

# För körning var 15:e minut:
# */15 * * * * cd /sökväg/till/remissorterare && ./venv/bin/python run_scheduled.py

# För körning varje dag kl 08:00:
# 0 8 * * * cd /sökväg/till/remissorterare && ./venv/bin/python run_scheduled.py
EOF

echo "✅ Exempel skapat: cron_exempel.txt"

# Skapa startskript
echo ""
echo "🚀 Skapar startskript..."

cat > start.sh << 'EOF'
#!/bin/bash
# Startskript för Remissorterare

# Aktivera virtuell miljö
source venv/bin/activate

# Kör remissorteraren
python remiss_sorterare.py
EOF

chmod +x start.sh
echo "✅ Startskript skapat: start.sh"

# Skapa webbstartskript
echo ""
echo "🌐 Skapar webbstartskript..."

cat > start_web.sh << 'EOF'
#!/bin/bash
# Startskript för webbgränssnittet

# Aktivera virtuell miljö
source venv/bin/activate

# Kör webbapplikationen
python web_app.py
EOF

chmod +x start_web.sh
echo "✅ Webbstartskript skapat: start_web.sh"

# Slutrapport
echo ""
echo "🎉 Installation slutförd!"
echo "========================================================"
echo ""
echo "📋 Nästa steg:"
echo "1. Lägg PDF-filer i 'input/' mappen"
echo "2. Kör './start.sh' för att bearbeta remisser"
echo "3. Kör './start_web.sh' för webbgränssnittet"
echo "4. Kontrollera resultatet i 'output/' mappen"
echo "5. Konfigurera schemalagd körning med cron_exempel.txt"
echo ""
echo "🤖 AI-funktioner:"
echo "- Lokala AI-modeller är installerade och konfigurerade"
echo "- Standardmodell: Sentence Transformer (snabb och effektiv)"
echo "- Byt modell via webbgränssnittet eller ai_config.py"
echo "- Första nedladdningen av AI-modeller sker automatiskt"
echo ""
echo "📚 Dokumentation: README.md"
echo "🧪 Tester: python3 test_remissorterare.py"
echo "🔧 Konfiguration: config.py och ai_config.py"
echo "🌐 Webbgränssnitt: http://localhost:5000"
echo ""
echo "✅ Remissorteraren med AI-stöd är redo att användas!"
echo ""
echo "💡 Tips:"
echo "- Använd webbgränssnittet för enklare hantering"
echo "- Lokala AI-modeller fungerar offline efter första nedladdningen"
echo "- Debug-verktygen hjälper vid felsökning av verksamhetsidentifiering"
