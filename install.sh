#!/bin/bash

# Installationsskript för Remissorterare
# Detta skript installerar alla nödvändiga beroenden och konfigurerar miljön

set -e  # Avsluta vid fel

echo "🚀 Startar installation av Remissorterare..."
echo "================================================"

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
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo "✅ Python-version: $python_version (OK)"
else
    echo "❌ Python $required_version eller senare krävs. Nuvarande: $python_version"
    exit 1
fi

# Installera Tesseract OCR
echo ""
echo "📦 Installerar Tesseract OCR..."

if [ "$OS" = "macos" ]; then
    if ! command -v brew &> /dev/null; then
        echo "❌ Homebrew är inte installerat. Installera först: https://brew.sh/"
        exit 1
    fi
    
    echo "Installerar Tesseract via Homebrew..."
    brew install tesseract
    brew install tesseract-lang
    
elif [ "$OS" = "linux" ]; then
    if command -v apt-get &> /dev/null; then
        echo "Installerar Tesseract via apt..."
        sudo apt-get update
        sudo apt-get install -y tesseract-ocr
        sudo apt-get install -y tesseract-ocr-swe
    elif command -v yum &> /dev/null; then
        echo "Installerar Tesseract via yum..."
        sudo yum install -y tesseract
        sudo yum install -y tesseract-langpack-swe
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

# Skapa virtuell miljö
echo ""
echo "🐍 Skapar virtuell Python-miljö..."

if [ ! -d "venv" ]; then
    python3 -m venv venv
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

# Installera Python-beroenden
echo ""
echo "📦 Installerar Python-beroenden..."
pip install -r requirements.txt

# Skapa mappstruktur
echo ""
echo "📁 Skapar mappstruktur..."
mkdir -p input output/osakert

# Skapa verksamhetsmappar från config
echo "Skapar verksamhetsmappar..."
python3 -c "
from config import VERKSAMHETER
import os
for verksamhet in VERKSAMHETER.keys():
    os.makedirs(f'output/{verksamhet}', exist_ok=True)
    print(f'✅ Skapade mapp: output/{verksamhet}')
"

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

# Slutrapport
echo ""
echo "🎉 Installation slutförd!"
echo "================================================"
echo ""
echo "📋 Nästa steg:"
echo "1. Lägg PDF-filer i 'input/' mappen"
echo "2. Kör './start.sh' för att bearbeta remisser"
echo "3. Kontrollera resultatet i 'output/' mappen"
echo "4. Konfigurera schemalagd körning med cron_exempel.txt"
echo ""
echo "📚 Dokumentation: README.md"
echo "🧪 Tester: python3 test_remissorterare.py"
echo "🔧 Konfiguration: config.py"
echo ""
echo "✅ Remissorteraren är redo att användas!"
