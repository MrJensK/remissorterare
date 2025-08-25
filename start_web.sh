#!/bin/bash

# Startskript för Remissorterare Web App

echo "🚀 Startar Remissorterare Web App..."

# Aktivera virtuell miljö om den finns
if [ -d "venv" ]; then
    echo "Aktiverar virtuell miljö..."
    source venv/bin/activate
fi

# Kontrollera att alla beroenden är installerade
echo "Kontrollerar beroenden..."
python -c "import flask, flask_socketio, sklearn, joblib" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Vissa beroenden saknas. Kör 'pip install -r requirements.txt' först."
    exit 1
fi

# Skapa nödvändiga mappar
echo "Skapar mappar..."
mkdir -p uploads static/uploads models

# Starta web-appen
echo "✅ Startar web-server..."
echo "🌐 Öppna webbläsaren på: http://localhost:5000"
echo "⏹️  Tryck Ctrl+C för att stoppa servern"
echo ""

python web_app.py
