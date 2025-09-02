#!/usr/bin/env python3
"""
Testskript för Remissorterare
Verifierar att alla komponenter fungerar korrekt
"""

import os
import sys
import logging
from pathlib import Path
from unittest.mock import Mock, patch

# Lägg till projektmappen i Python-sökvägen
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from remiss_sorterare import RemissSorterare
from config import *

def test_konfiguration():
    """Testar att konfigurationen är korrekt"""
    print("🔧 Testar konfiguration...")
    
    # Kontrollera att alla nödvändiga konstanter finns
    assert hasattr(sys.modules['config'], 'SANNOLIKHET_TRÖSKEL')
    assert hasattr(sys.modules['config'], 'VERKSAMHETER')
    assert hasattr(sys.modules['config'], 'INPUT_MAPP')
    assert hasattr(sys.modules['config'], 'OUTPUT_MAPP')
    
    print(f"✅ Sannolikhetströskel: {SANNOLIKHET_TRÖSKEL}%")
    print(f"✅ Antal verksamheter: {len(VERKSAMHETER)}")
    print(f"✅ Input-mapp: {INPUT_MAPP}")
    print(f"✅ Output-mapp: {OUTPUT_MAPP}")
    
    return True

def test_mappskapande():
    """Testar att mappar skapas korrekt"""
    print("\n📁 Testar mappskapande...")
    
    # Skapa temporär sorterare
    sorterare = RemissSorterare("test_input", "test_output")
    
    # Kontrollera att mappar skapades
    assert sorterare.input_mapp.exists()
    assert sorterare.output_mapp.exists()
    assert sorterare.osakert_mapp.exists()
    
    # Kontrollera att verksamhetsmappar skapades
    for verksamhet in VERKSAMHETER.keys():
        verksamhet_mapp = sorterare.output_mapp / verksamhet
        assert verksamhet_mapp.exists()
    
    print("✅ Alla mappar skapades korrekt")
    
    # Rensa upp
    import shutil
    if sorterare.input_mapp.exists():
        shutil.rmtree(sorterare.input_mapp)
    if sorterare.output_mapp.exists():
        shutil.rmtree(sorterare.output_mapp)
    
    return True

def test_personnummer_identifiering():
    """Testar personnummer-identifiering"""
    print("\n🆔 Testar personnummer-identifiering...")
    
    sorterare = RemissSorterare()
    
    # Testfall
    test_cases = [
        ("Patient med personnummer 19850415-1234 har problem", "19850415-1234"),
        ("Födelsedatum: 1990-12-25, personnummer: 19901225-5678", "19901225-5678"),
        ("Inget personnummer här", None),
        ("Falskt nummer 12345-6789", None),
        ("Korrekt: 20000101-0001", "20000101-0001"),
    ]
    
    for text, expected in test_cases:
        result = sorterare.hitta_personnummer(text)
        if result == expected:
            print(f"✅ '{text[:30]}...' -> {result}")
        else:
            print(f"❌ '{text[:30]}...' -> {result} (förväntade {expected})")
            return False
    
    return True

def test_datum_identifiering():
    """Testar datum-identifiering"""
    print("\n📅 Testar datum-identifiering...")
    
    sorterare = RemissSorterare()
    
    # Testfall
    test_cases = [
        ("Remissdatum: 15/01/2024", "2024-01-15"),
        ("Datum: 2024-01-15", "2024-01-15"),
        ("Skapad: 15.01.24", "2024-01-15"),
        ("Inget datum här", None),
        ("Felaktigt datum: 32/13/2024", None),
    ]
    
    for text, expected in test_cases:
        result = sorterare.hitta_remissdatum(text)
        if result == expected:
            print(f"✅ '{text[:30]}...' -> {result}")
        else:
            print(f"❌ '{text[:30]}...' -> {result} (förväntade {expected})")
            return False
    
    return True

def test_verksamhet_identifiering():
    """Testar verksamhetsidentifiering"""
    print("\n🏥 Testar verksamhetsidentifiering...")
    
    sorterare = RemissSorterare()
    
    # Testfall
    test_cases = [
        ("Patient med knäproblem och artros", ("Ortopedi", 100.0)),
        ("Hjärtproblem och arytmi", ("Kardiologi", 100.0)),
        ("Hudproblem med eksem", ("Dermatologi", 100.0)),
        ("Allmän text utan specifika termer", ("Okänd", 0.0)),
    ]
    
    for text, (expected_verksamhet, min_sannolikhet) in test_cases:
        verksamhet, sannolikhet = sorterare.identifiera_verksamhet(text)
        if verksamhet == expected_verksamhet and sannolikhet >= min_sannolikhet:
            print(f"✅ '{text[:30]}...' -> {verksamhet} ({sannolikhet:.1f}%)")
        else:
            print(f"❌ '{text[:30]}...' -> {verksamhet} ({sannolikhet:.1f}%) (förväntade {expected_verksamhet})")
            return False
    
    return True

def test_bildforbattring():
    """Testar bildförbättring (mock)"""
    print("\n🖼️ Testar bildförbättring...")
    
    sorterare = RemissSorterare()
    
    # Skapa en mock-bild
    from PIL import Image
    import numpy as np
    
    # Skapa en enkel testbild
    test_bild = Image.fromarray(np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8))
    
    try:
        forbattrad_bild = sorterare.forbattra_bild_for_ocr(test_bild)
        assert forbattrad_bild is not None
        print("✅ Bildförbättring fungerar")
        return True
    except Exception as e:
        print(f"❌ Bildförbättring misslyckades: {e}")
        return False

def test_dat_fil_skapande():
    """Testar .dat-filskapande"""
    print("\n📄 Testar .dat-filskapande...")
    
    sorterare = RemissSorterare("test_input", "test_output")
    
    # Skapa en test .dat-fil
    test_mapp = sorterare.output_mapp / "Ortopedi"
    test_mapp.mkdir(parents=True, exist_ok=True)
    
    try:
        sorterare.skapa_dat_fil(
            "Ortopedi",
            "19850415-1234",
            "2024-01-15",
            "test_remiss.pdf",
            test_mapp
        )
        
        # Kontrollera att filen skapades
        dat_fil = test_mapp / "test_remiss.dat"
        assert dat_fil.exists()
        
        # Kontrollera innehåll
        with open(dat_fil, 'r', encoding='utf-8') as f:
            innehåll = f.read()
            assert "Verksamhet: Ortopedi" in innehåll
            assert "Personnummer: 19850415-1234" in innehåll
            assert "Remissdatum: 2024-01-15" in innehåll
        
        print("✅ .dat-filskapande fungerar")
        
        # Rensa upp
        dat_fil.unlink()
        import shutil
        shutil.rmtree(sorterare.input_mapp)
        shutil.rmtree(sorterare.output_mapp)
        
        return True
    except Exception as e:
        print(f"❌ .dat-filskapande misslyckades: {e}")
        return False

def test_beroenden():
    """Testar att alla beroenden är installerade"""
    print("\n📦 Testar beroenden...")
    
    required_packages = [
        'pytesseract',
        'pdf2image',
        'PIL',
        'cv2',
        'numpy',
        'dateutil'
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} är installerat")
        except ImportError:
            print(f"❌ {package} saknas")
            return False
    
    return True

def main():
    """Kör alla tester"""
    print("🧪 Startar tester för Remissorterare\n")
    
    tests = [
        test_beroenden,
        test_konfiguration,
        test_mappskapande,
        test_personnummer_identifiering,
        test_datum_identifiering,
        test_verksamhet_identifiering,
        test_bildforbattring,
        test_dat_fil_skapande,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"❌ Testet {test.__name__} misslyckades")
        except Exception as e:
            print(f"❌ Testet {test.__name__} kraschade: {e}")
    
    print(f"\n📊 Testresultat: {passed}/{total} tester godkända")
    
    if passed == total:
        print("🎉 Alla tester godkända! Remissorteraren är redo att användas.")
        return True
    else:
        print("⚠️ Vissa tester misslyckades. Kontrollera installationen.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
