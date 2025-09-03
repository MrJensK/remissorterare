#!/bin/bash
# Startskript för webbgränssnittet

echo "🚀 Startar Remissorterare webbgränssnitt..."
echo "=========================================="

# Kontrollera att virtuell miljö finns
if [ ! -d "venv" ]; then
    echo "❌ FEL: Virtuell miljö 'venv' finns inte!"
    echo ""
    echo "Kör installationsskriptet först:"
    echo "  ./install.sh"
    echo ""
    exit 1
fi

# Aktivera virtuell miljö
echo "🔧 Aktiverar virtuell miljö..."
source venv/bin/activate

# Kontrollera att aktiveringen lyckades
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ FEL: Kunde inte aktivera virtuell miljö!"
    echo ""
    echo "Kontrollera att venv/bin/activate finns och är körbar."
    echo ""
    exit 1
fi

echo "✅ Virtuell miljö aktiverad: $VIRTUAL_ENV"
echo "✅ Python: $(which python)"
echo ""

# Kör webbapplikationen
echo "🌐 Startar webbgränssnittet..."
echo "Öppna http://localhost:8000 i din webbläsare"
echo "Tryck Ctrl+C för att stoppa"
echo ""

python web_app.py
