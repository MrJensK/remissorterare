#!/usr/bin/env python3
"""
Ollama-modellhanterare för Remissorterare
Använd för att lista, installera och byta mellan olika Ollama-modeller
"""

import sys
import argparse
import requests
import json
from ollama_config import *
from lokal_ai_verksamhetsidentifierare import LokalAIVerksamhetsIdentifierare

def list_models():
    """Listar alla tillgängliga modeller"""
    print("🔍 Tillgängliga Ollama-modeller:")
    print("=" * 60)
    
    for model_name in OLLAMA_MODELS:
        info = OLLAMA_MODELS[model_name]
        print(f"\n📦 {model_name}")
        print(f"   Beskrivning: {info['description']}")
        print(f"   Storlek: {info['size']}")
        print(f"   Språk: {info['language']}")
        print(f"   Prestanda: {info['performance']}")
        print(f"   Minne: {info['memory']}")
    
    print(f"\n💡 Rekommenderade för svenska: {', '.join(RECOMMENDED_FOR_SWEDISH)}")

def check_installed_models():
    """Kontrollerar vilka modeller som är installerade"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print("✅ Installerade Ollama-modeller:")
            print("=" * 40)
            
            if models:
                for model in models:
                    print(f"📦 {model['name']}")
            else:
                print("❌ Inga modeller installerade")
                print("💡 Installera en modell med: python ollama_manager.py install <modellnamn>")
        else:
            print("❌ Kan inte ansluta till Ollama")
            print("💡 Starta Ollama med: ollama serve")
    except requests.exceptions.RequestException:
        print("❌ Ollama är inte igång")
        print("💡 Starta Ollama med: ollama serve")

def install_model(model_name):
    """Installerar en specifik modell"""
    if not validate_model_name(model_name):
        print(f"❌ Ogiltig modellnamn: {model_name}")
        print(f"💡 Tillgängliga modeller: {', '.join(list_available_models())}")
        return False
    
    print(f"🚀 Installerar {model_name}...")
    print("💡 Detta kan ta flera minuter beroende på modellstorlek")
    
    try:
        # Använd ollama pull kommandot
        import subprocess
        result = subprocess.run(["ollama", "pull", model_name], 
                              capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ {model_name} installerades framgångsrikt!")
            return True
        else:
            print(f"❌ Fel vid installation: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Installationen tog för lång tid (timeout)")
        return False
    except FileNotFoundError:
        print("❌ Ollama är inte installerat eller inte i PATH")
        print("💡 Installera Ollama från: https://ollama.ai/")
        return False
    except Exception as e:
        print(f"❌ Oväntat fel: {e}")
        return False

def test_model(model_name):
    """Testar en specifik modell"""
    if not validate_model_name(model_name):
        print(f"❌ Ogiltig modellnamn: {model_name}")
        return False
    
    print(f"🧪 Testar modell: {model_name}")
    
    try:
        # Skapa en test-instans
        identifierare = LokalAIVerksamhetsIdentifierare("ollama")
        
        # Byt till den valda modellen
        if identifierare.byt_ollama_modell(model_name):
            print(f"✅ Modell {model_name} laddades framgångsrikt")
            
            # Testa med en enkel prompt
            test_text = "Remiss till gynekologiska kliniken för utredning av cysta"
            print(f"📝 Testar med text: {test_text}")
            
            verksamhet, sannolikhet = identifierare.identifiera_verksamhet(test_text)
            print(f"🎯 Resultat: {verksamhet} ({sannolikhet:.1f}%)")
            
            return True
        else:
            print(f"❌ Kunde inte ladda modell {model_name}")
            return False
            
    except Exception as e:
        print(f"❌ Fel vid testning: {e}")
        return False

def set_default_model(model_name):
    """Sätter en modell som standard"""
    if not validate_model_name(model_name):
        print(f"❌ Ogiltig modellnamn: {model_name}")
        return False
    
    try:
        # Uppdatera ollama_config.py
        with open("ollama_config.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Ersätt DEFAULT_OLLAMA_MODEL
        old_line = f'DEFAULT_OLLAMA_MODEL = "{DEFAULT_OLLAMA_MODEL}"'
        new_line = f'DEFAULT_OLLAMA_MODEL = "{model_name}"'
        
        if old_line in content:
            content = content.replace(old_line, new_line)
            
            with open("ollama_config.py", "w", encoding="utf-8") as f:
                f.write(content)
            
            print(f"✅ {model_name} är nu standardmodell")
            print("💡 Starta om Remissorterare för att använda den nya standardmodellen")
            return True
        else:
            print("❌ Kunde inte hitta DEFAULT_OLLAMA_MODEL i konfigurationen")
            return False
            
    except Exception as e:
        print(f"❌ Fel vid uppdatering av konfiguration: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Ollama-modellhanterare för Remissorterare")
    parser.add_argument("command", choices=["list", "installed", "install", "test", "set-default"],
                       help="Kommando att köra")
    parser.add_argument("model", nargs="?", help="Modellnamn (krävs för install, test, set-default)")
    
    args = parser.parse_args()
    
    if args.command in ["install", "test", "set-default"] and not args.model:
        print(f"❌ Modellnamn krävs för kommandot '{args.command}'")
        print(f"💡 Exempel: python ollama_manager.py {args.command} llama2:7b")
        return
    
    if args.command == "list":
        list_models()
    elif args.command == "installed":
        check_installed_models()
    elif args.command == "install":
        install_model(args.model)
    elif args.command == "test":
        test_model(args.model)
    elif args.command == "set-default":
        set_default_model(args.model)

if __name__ == "__main__":
    main()
