#!/usr/bin/env python3
"""
Remissorterare - Automatisk hantering av inscannade remisser

Programmet läser PDF-filer, utför OCR, extraherar relevant information
och sorterar remisserna till rätt verksamhetsmappar.
"""

import os
import sys
import re
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import cv2
import numpy as np
from dateutil import parser
from config import *
from ml_verksamhetsidentifierare import MLVerksamhetsIdentifierare
from ai_verksamhetsidentifierare import AIVerksamhetsIdentifierare
from lokal_ai_verksamhetsidentifierare import LokalAIVerksamhetsIdentifierare
from ai_config import *

# Kontrollera att virtuell miljö är aktiverad
def kontrollera_virtuell_miljo():
    """Kontrollerar att virtuell miljö är aktiverad innan programmet startar"""
    venv_path = os.environ.get('VIRTUAL_ENV')
    if not venv_path:
        print("❌ FEL: Virtuell miljö är inte aktiverad!")
        print("")
        print("Aktivera den virtuella miljön först:")
        print("  source venv/bin/activate")
        print("")
        print("Eller använd startskriptet:")
        print("  ./start.sh")
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

# Konfigurera logging
logging.basicConfig(
    level=getattr(logging, LOG_NIVÅ),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FIL),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RemissSorterare:
    """Huvudklass för remissortering"""
    
    def __init__(self):
        """Initierar RemissSorterare"""
        self.input_mapp = Path(INPUT_MAPP)
        self.output_mapp = Path(OUTPUT_MAPP)
        self.osakert_mapp = Path(OUTPUT_MAPP) / OSAKERT_MAPP
        
        # Skapa nödvändiga mappar
        self.output_mapp.mkdir(exist_ok=True)
        self.osakert_mapp.mkdir(exist_ok=True)
        
        # Skapa mappar för varje verksamhet
        for verksamhet in VERKSAMHETER.keys():
            (self.output_mapp / verksamhet).mkdir(exist_ok=True)
        
        # Initiera identifierare
        self.verksamheter = VERKSAMHETER
        self.ml_identifierare = MLVerksamhetsIdentifierare()
        
        # Initiera AI-identifierare baserat på konfiguration
        if AI_TYPE == "openai":
            self.ai_identifierare = AIVerksamhetsIdentifierare()
            logger.info("Använder OpenAI AI-identifierare")
        elif AI_TYPE == "lokal":
            self.ai_identifierare = LokalAIVerksamhetsIdentifierare(LOKAL_AI_MODEL)
            logger.info(f"Använder lokal AI-identifierare: {LOKAL_AI_MODEL}")
        else:
            self.ai_identifierare = None
            logger.warning("Ingen AI-identifierare konfigurerad")
        
        # Konfigurera OCR
        pytesseract.pytesseract.tesseract_cmd = 'tesseract'
        
        logger.info("RemissSorterare initialiserad")
    
    def _skapa_mappar(self):
        """Skapar nödvändiga mappar för programmet"""
        mappar = [
            self.input_mapp,
            self.output_mapp,
            self.osakert_mapp
        ]
        
        # Skapa verksamhetsmappar
        for verksamhet in self.verksamheter.keys():
            mappar.append(self.output_mapp / verksamhet)
        
        for mapp in mappar:
            mapp.mkdir(parents=True, exist_ok=True)
            logger.info(f"Skapade mapp: {mapp}")
    
    def pdf_till_bilder(self, pdf_sokvag: Path) -> List[Image.Image]:
        """
        Konverterar PDF till bilder för OCR
        
        Args:
            pdf_sokvag: Sökväg till PDF-filen
            
        Returns:
            Lista med PIL Image-objekt
        """
        try:
            logger.info(f"Konverterar PDF till bilder: {pdf_sokvag}")
            logger.info(f"PDF-storlek: {os.path.getsize(pdf_sokvag)} bytes")
            logger.info(f"OCR DPI: {OCR_DPI}")
            
            bilder = convert_from_path(pdf_sokvag, dpi=OCR_DPI)
            logger.info(f"Skapade {len(bilder)} bilder från PDF")
            
            # Logga information om varje bild
            for i, bild in enumerate(bilder):
                logger.info(f"Bild {i+1}: storlek {bild.size}, format {bild.mode}")
            
            return bilder
        except Exception as e:
            logger.error(f"Fel vid konvertering av PDF: {e}")
            return []
    
    def forbattra_bild_for_ocr(self, bild: Image.Image) -> Image.Image:
        """
        Förbättrar bildkvalitet för bättre OCR-resultat
        
        Args:
            bild: PIL Image-objekt
            
        Returns:
            Förbättrad PIL Image-objekt
        """
        # Konvertera till numpy array
        img_array = np.array(bild)
        
        # Konvertera till gråskala
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Använd adaptiv tröskling för bättre kontrast
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Lägg till lite morfologisk operation för att rensa brus
        kernel = np.ones((1, 1), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        # Konvertera tillbaka till PIL Image
        return Image.fromarray(cleaned)
    
    def extrahera_text_med_ocr(self, bilder: List[Image.Image]) -> str:
        """
        Utför OCR på bilder och extraherar text
        
        Args:
            bilder: Lista med PIL Image-objekt
            
        Returns:
            Extraherad text från alla bilder
        """
        all_text = ""
        
        for i, bild in enumerate(bilder):
            logger.info(f"Utför OCR på bild {i+1}/{len(bilder)}")
            
            # Förbättra bildkvalitet
            forbattrad_bild = self.forbattra_bild_for_ocr(bild)
            
            try:
                # Utför OCR med svenska språk
                logger.info(f"Utför OCR på bild {i+1} med språk: {OCR_SPRÅK}, PSM: {OCR_PSM}")
                text = pytesseract.image_to_string(
                    forbattrad_bild, 
                    lang=OCR_SPRÅK,
                    config=OCR_PSM
                )
                all_text += text + "\n"
                logger.info(f"Extraherade {len(text)} tecken från bild {i+1}")
                logger.debug(f"OCR-text från bild {i+1}: {text[:200]}...")
            except Exception as e:
                logger.error(f"OCR-fel på bild {i+1}: {e}")
        
        return all_text
    
    def hitta_personnummer(self, text: str) -> Optional[str]:
        """
        Hittar personnummer i texten
        Args:
            text: Text att söka i
        Returns:
            Personnummer eller None
        """
        # Matcha t.ex. '19850415-1234', '198504151234', '19 850415-1234', '20 990101-5678'
        regex = r'((?:19|20)[ ]?\d{6}-?\d{4})'
        match = re.search(regex, text)
        if match:
            # Ta bort eventuellt mellanslag mellan seklet och resten
            personnummer = match.group(1).replace(' ', '')
            logger.info(f"Hittade personnummer: {personnummer}")
            return personnummer
        logger.warning("Inget personnummer hittades")
        return None
    
    def hitta_remissdatum(self, text: str) -> Optional[str]:
        """
        Hittar remissdatum i texten
        
        Args:
            text: Text att söka i
            
        Returns:
            Datum i YYYY-MM-DD format eller None
        """
        # Olika datumformat att söka efter
        datum_patterns = [
            r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b',  # DD/MM/YYYY eller DD-MM-YYYY
            r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b',  # YYYY-MM-DD
            r'\b(\d{1,2})\.(\d{1,2})\.(\d{2,4})\b',  # DD.MM.YYYY
        ]
        
        for pattern in datum_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    if len(match[2]) == 2:  # År med 2 siffror
                        year = int(match[2])
                        if year < 50:
                            year += 2000
                        else:
                            year += 1900
                    else:
                        year = int(match[2])
                    
                    month = int(match[1])
                    day = int(match[0])
                    
                    # Validera datum
                    if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                        datum = f"{year:04d}-{month:02d}-{day:02d}"
                        logger.info(f"Hittade remissdatum: {datum}")
                        return datum
                except (ValueError, IndexError):
                    continue
        
        logger.warning("Inget giltigt remissdatum hittades")
        return None
    
    def identifiera_verksamhet(self, text: str) -> Tuple[str, float]:
        """
        Identifierar verksamhet med AI som primär metod och fallback till andra metoder
        
        Args:
            text: Text att analysera
        
        Returns:
            Tuple med (verksamhet, sannolikhet)
        """
        text_lower = text.lower()
        
        # 1. AI-baserad identifiering (primär metod)
        if self.ai_identifierare:
            try:
                verksamhet, sannolikhet = self.ai_identifierare.identifiera_verksamhet(text)
                if verksamhet != "Okänd" and sannolikhet > 70:
                    logger.info(f"AI-identifiering: {verksamhet} (sannolikhet: {sannolikhet:.1f}%)")
                    return verksamhet, sannolikhet
                else:
                    logger.info("AI-identifiering gav låg sannolikhet, använder fallback")
            except Exception as e:
                logger.warning(f"AI-identifiering misslyckades, använder fallback: {e}")
        
        # 2. Sök efter mottagare/remissadress (INTE avsändare)
        mottagarfraser = [
            "remiss till", "remitteras till", "mottagare:", "mottagande verksamhet:", 
            "mottagande avdelning:", "remissadress:", "till:", "för:", "till verksamhet:",
            "till avdelning:", "till klinik:", "till mottagare:", "till specialist:",
            "remitteras till", "skickas till", "överlämnas till", "överförs till"
        ]
        
        # Sök efter mottagare i hela texten
        for fras in mottagarfraser:
            idx = text_lower.find(fras)
            if idx != -1:
                # Ta ut text efter frasen (längre kontext)
                efter = text_lower[idx:idx+200]
                logger.info(f"Hittade mottagarfras: '{fras}' - analyserar: {efter[:100]}...")
                
                # Sök efter verksamheter i mottagartexten
                for verksamhet, nyckelord in self.verksamheter.items():
                    for nyckel in nyckelord:
                        if nyckel.lower() in efter:
                            logger.info(f"Mottagarmatch: {verksamhet} via '{fras}' och '{nyckel}'")
                            return verksamhet, 95.0
        
        # 3. Sök efter specifika mottagarkliniker/avdelningar
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
        
        for verksamhet, kliniker in mottagarkliniker.items():
            for klinik in kliniker:
                if klinik in text_lower:
                    logger.info(f"Klinikmatch: {verksamhet} via '{klinik}'")
                    return verksamhet, 90.0
        
        # 4. Försök med ML-identifierare
        try:
            verksamhet, sannolikhet = self.ml_identifierare.identifiera_verksamhet(text)
            if sannolikhet > 70:  # Högre tröskel för ML
                logger.info(f"ML-match: {verksamhet} (sannolikhet: {sannolikhet:.1f}%)")
                return verksamhet, sannolikhet
        except Exception as e:
            logger.warning(f"ML-identifiering misslyckades, använder fallback: {e}")
        
        # 5. Förbättrad fallback: Analysera hela texten med kontextbaserad poängsättning
        bästa_verksamhet = "Okänd"
        högsta_poäng = 0
        
        # Skapa en mer intelligent poängsättning
        for verksamhet, nyckelord in self.verksamheter.items():
            poäng = 0
            total_nyckelord = len(nyckelord)
            
            # Räkna förekomster av varje nyckelord
            for nyckel in nyckelord:
                antal = text_lower.count(nyckel.lower())
                if antal > 0:
                    # Ge högre poäng för fler förekomster
                    poäng += antal * 2
                    
                    # Ge extra poäng om nyckelordet finns nära mottagarfraser
                    for fras in mottagarfraser:
                        if fras in text_lower:
                            fras_idx = text_lower.find(fras)
                            nyckel_idx = text_lower.find(nyckel.lower())
                            if abs(fras_idx - nyckel_idx) < 100:  # Nära varandra
                                poäng += 10  # Öka från 5 till 10
                    
                    # Ge extra poäng för specifika gynekologiska termer
                    if verksamhet == "Gynekologi":
                        gynekologiska_termer = ["livmoder", "äggstockar", "menstruation", "menopaus", "endometrios", 
                                              "myom", "cervix", "ovariell", "mammografi", "bröst", "graviditet", 
                                              "förlossning", "uterus", "ovarium"]
                        for term in gynekologiska_termer:
                            if term in text_lower:
                                poäng += 15  # Extra poäng för specifika gynekologiska termer
                    
                    # Ge extra poäng för specifika kirurgiska termer
                    if verksamhet == "Kirurgi":
                        kirurgiska_termer = ["operation", "operera", "kirurgisk", "snitt", "laparoskopi", 
                                           "endoskopi", "biopsi", "appendicit", "gallsten", "hernia", 
                                           "bråck", "polyp", "cholecystektomi", "appendektomi"]
                        for term in kirurgiska_termer:
                            if term in text_lower:
                                poäng += 15  # Extra poäng för specifika kirurgiska termer
            
            # Normalisera poäng - använd en mer balanserad formel
            sannolikhet = min(100, (poäng / total_nyckelord) * 15)  # Minska från 20 till 15
            
            # Logga detaljerad information för debugging
            logger.debug(f"Verksamhet: {verksamhet}, Poäng: {poäng}, Sannolikhet: {sannolikhet:.1f}%")
            
            if sannolikhet > högsta_poäng:
                högsta_poäng = sannolikhet
                bästa_verksamhet = verksamhet
        
        logger.info(f"Fallback identifiering: {bästa_verksamhet} (sannolikhet: {högsta_poäng:.1f}%)")
        
        # Om sannolikheten är för låg, returnera "osakert"
        if högsta_poäng < 30:
            logger.info("Sannolikhet för låg, returnerar 'osakert'")
            return "osakert", högsta_poäng
        
        return bästa_verksamhet, högsta_poäng
    
    def skapa_dat_fil(self, verksamhet: str, personnummer: str, remissdatum: str, 
                     pdf_namn: str, mapp: Path):
        """
        Skapar .dat-fil med extraherad information
        
        Args:
            verksamhet: Identifierad verksamhet
            personnummer: Patientens personnummer
            remissdatum: Datum för remissen
            pdf_namn: Namn på PDF-filen
            mapp: Mapp att spara .dat-filen i
        """
        dat_namn = pdf_namn.replace('.pdf', '.dat')
        dat_sokvag = mapp / dat_namn
        
        try:
            with open(dat_sokvag, 'w', encoding='utf-8') as f:
                f.write(f"Verksamhet: {verksamhet}\n")
                f.write(f"Personnummer: {personnummer}\n")
                f.write(f"Remissdatum: {remissdatum}\n")
                f.write(f"Skapad: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            logger.info(f"Skapade .dat-fil: {dat_sokvag}")
        except Exception as e:
            logger.error(f"Fel vid skapande av .dat-fil: {e}")
    
    def bearbeta_pdf(self, pdf_sokvag: Path) -> bool:
        """
        Bearbetar en PDF-fil genom hela processen
        
        Args:
            pdf_sokvag: Sökväg till PDF-filen
            
        Returns:
            True om bearbetningen lyckades, False annars
        """
        try:
            logger.info(f"Börjar bearbeta: {pdf_sokvag}")
            
            # Konvertera PDF till bilder
            bilder = self.pdf_till_bilder(pdf_sokvag)
            if not bilder:
                return False
            
            # Extrahera text med OCR
            text = self.extrahera_text_med_ocr(bilder)
            if not text.strip():
                logger.warning("Ingen text extraherades från PDF")
                return False
            
            # Identifiera verksamhet
            verksamhet, sannolikhet = self.identifiera_verksamhet(text)
            
            # Extrahera personnummer och datum
            personnummer = self.hitta_personnummer(text)
            remissdatum = self.hitta_remissdatum(text)
            
            # Bestäm mål-mapp baserat på sannolikhet
            if sannolikhet >= SANNOLIKHET_TRÖSKEL:
                mål_mapp = self.output_mapp / verksamhet
                logger.info(f"Remiss sorteras till {verksamhet} (sannolikhet: {sannolikhet:.1f}%)")
            else:
                mål_mapp = self.osakert_mapp
                logger.warning(f"Remiss flyttas till osakert (sannolikhet: {sannolikhet:.1f}%)")
            
            # Kopiera PDF till mål-mapp
            pdf_namn = pdf_sokvag.name
            mål_pdf = mål_mapp / pdf_namn
            shutil.copy2(pdf_sokvag, mål_pdf)
            logger.info(f"Kopierade PDF till: {mål_pdf}")
            
            # Skapa .dat-fil
            if personnummer:
                self.skapa_dat_fil(verksamhet, personnummer, remissdatum or "Okänt", pdf_namn, mål_mapp)
            else:
                logger.warning("Kunde inte skapa .dat-fil - saknar personnummer")
            
            return True
            
        except Exception as e:
            logger.error(f"Fel vid bearbetning av {pdf_sokvag}: {e}")
            return False
    
    def bearbeta_alla_pdf(self):
        """Bearbetar alla PDF-filer i input-mappen"""
        if not self.input_mapp.exists():
            logger.error(f"Input-mapp finns inte: {self.input_mapp}")
            return
        
        pdf_filer = list(self.input_mapp.glob("*.pdf"))
        
        if not pdf_filer:
            logger.info("Inga PDF-filer hittades i input-mappen")
            return
        
        logger.info(f"Hittade {len(pdf_filer)} PDF-filer att bearbeta")
        lyckade = 0
        misslyckade = 0

        for pdf_fil in pdf_filer:
            if self.bearbeta_pdf(pdf_fil):
                lyckade += 1
            else:
                misslyckade += 1

        logger.info(f"Bearbetning slutförd: {lyckade} lyckade, {misslyckade} misslyckade")

    def omfördela_remiss(self, pdf_namn: str, ny_verksamhet: str) -> bool:
        """
        Omdirigerar en remiss från osakert till rätt verksamhet
        
        Args:
            pdf_namn: Namn på PDF-filen att omfördela
            ny_verksamhet: Verksamhet att flytta till
            
        Returns:
            True om omfördelningsprocessen lyckades, False annars
        """
        try:
            # Hitta PDF-filen i osakert-mappen
            osakert_pdf = self.osakert_mapp / pdf_namn
            if not osakert_pdf.exists():
                logger.error(f"PDF-fil hittades inte i osakert: {pdf_namn}")
                return False
            
            # Skapa mål-mapp för ny verksamhet
            mål_mapp = self.output_mapp / ny_verksamhet
            mål_mapp.mkdir(exist_ok=True)
            
            # Flytta PDF-filen
            mål_pdf = mål_mapp / pdf_namn
            shutil.move(str(osakert_pdf), str(mål_pdf))
            logger.info(f"Flyttade PDF från osakert till {ny_verksamhet}: {pdf_namn}")
            
            # Hitta och flytta motsvarande .dat-fil om den finns
            dat_namn = pdf_namn.replace('.pdf', '.dat')
            osakert_dat = self.osakert_mapp / dat_namn
            if osakert_dat.exists():
                mål_dat = mål_mapp / dat_namn
                shutil.move(str(osakert_dat), str(mål_dat))
                logger.info(f"Flyttade .dat-fil från osakert till {ny_verksamhet}: {dat_namn}")
            
            # Uppdatera .dat-filen med rätt verksamhet
            if mål_dat.exists():
                self.uppdatera_dat_fil_verksamhet(mål_dat, ny_verksamhet)
            
            return True
            
        except Exception as e:
            logger.error(f"Fel vid omfördelningsprocessen: {e}")
            return False
    
    def uppdatera_dat_fil_verksamhet(self, dat_sokvag: Path, ny_verksamhet: str):
        """
        Uppdaterar verksamheten i en .dat-fil
        
        Args:
            dat_sokvag: Sökväg till .dat-filen
            ny_verksamhet: Ny verksamhet att sätta
        """
        try:
            # Läs befintlig innehåll
            with open(dat_sokvag, 'r', encoding='utf-8') as f:
                rader = f.readlines()
            
            # Uppdatera verksamhetsraden
            for i, rad in enumerate(rader):
                if rad.startswith("Verksamhet:"):
                    rader[i] = f"Verksamhet: {ny_verksamhet}\n"
                    break
            
            # Skriv tillbaka uppdaterat innehåll
            with open(dat_sokvag, 'w', encoding='utf-8') as f:
                f.writelines(rader)
            
            logger.info(f"Uppdaterade verksamhet i {dat_sokvag} till: {ny_verksamhet}")
            
        except Exception as e:
            logger.error(f"Fel vid uppdatering av .dat-fil: {e}")
    
    def lista_osakert_remisser(self) -> List[Dict]:
        """
        Listar alla remisser i osakert-mappen med information
        
        Returns:
            Lista med dictionaries innehållande remissinformation
        """
        osakert_remisser = []
        
        if not self.osakert_mapp.exists():
            return osakert_remisser
        
        for pdf_fil in self.osakert_mapp.glob("*.pdf"):
            remiss_info = {
                "pdf_namn": pdf_fil.name,
                "storlek": pdf_fil.stat().st_size,
                "skapad": datetime.fromtimestamp(pdf_fil.stat().st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                "dat_fil": None
            }
            
            # Kolla om det finns motsvarande .dat-fil
            dat_fil = pdf_fil.with_suffix('.dat')
            if dat_fil.exists():
                try:
                    with open(dat_fil, 'r', encoding='utf-8') as f:
                        innehåll = f.read()
                        remiss_info["dat_fil"] = innehåll
                except Exception as e:
                    logger.warning(f"Kunde inte läsa .dat-fil: {e}")
            
            osakert_remisser.append(remiss_info)
        
        return osakert_remisser
    
    def träna_ml_med_omfördelningsdata(self, omfördelningsdata: List[Tuple[str, str]]):
        """
        Tränar ML-modellen med data från manuella omfördelningsprocesser
        
        Args:
            omfördelningsdata: Lista med (pdf_namn, rätt_verksamhet) tuples
        """
        try:
            logger.info(f"Tränar ML-modell med {len(omfördelningsdata)} omfördelningsdata")
            
            # Samla in text från omfördelningsdata
            texter = []
            verksamheter = []
            
            for pdf_namn, rätt_verksamhet in omfördelningsdata:
                # Hitta PDF-filen i rätt verksamhetsmapp
                verksamhets_mapp = self.output_mapp / rätt_verksamhet
                pdf_sokvag = verksamhets_mapp / pdf_namn
                
                if pdf_sokvag.exists():
                    # Bearbeta PDF för att få text
                    bilder = self.pdf_till_bilder(pdf_sokvag)
                    if bilder:
                        text = self.extrahera_text_med_ocr(bilder)
                        if text.strip():
                            texter.append(text)
                            verksamheter.append(rätt_verksamhet)
                            logger.info(f"Lade till träningsdata: {pdf_namn} -> {rätt_verksamhet}")
            
            # Träna ML-modellen med den nya datan
            if texter:
                self.ml_identifierare.träna_med_anpassad_data(texter, verksamheter)
                logger.info("ML-modell tränad med omfördelningsdata")
            else:
                logger.warning("Ingen text kunde extraheras från omfördelningsdata")
                
        except Exception as e:
            logger.error(f"Fel vid träning med omfördelningsdata: {e}")


def main():
    """Huvudfunktion"""
    logger.info("Startar Remissorterare")
    
    # Skapa sorterare och bearbeta filer
    sorterare = RemissSorterare()
    sorterare.bearbeta_alla_pdf()
    
    logger.info("Remissorterare slutförd")


if __name__ == "__main__":
    main()
