#!/usr/bin/env python3
"""
Remissorterare - Automatisk hantering av inscannade remisser

Programmet läser PDF-filer, utför OCR, extraherar relevant information
och sorterar remisserna till rätt verksamhetsmappar.
"""

import os
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
    
    def __init__(self, input_mapp: str = INPUT_MAPP, output_mapp: str = OUTPUT_MAPP):
        """
        Initierar remissorteraren
        
        Args:
            input_mapp: Mapp med inkommande PDF-filer
            output_mapp: Rotmapp för sorterade filer
        """
        self.input_mapp = Path(input_mapp)
        self.output_mapp = Path(output_mapp)
        self.osakert_mapp = self.output_mapp / OSAKERT_MAPP
        
        # Verksamheter och nyckelord från config
        self.verksamheter = VERKSAMHETER
        
        # Skapa nödvändiga mappar
        self._skapa_mappar()
        
        # ML-identifierare
        self.ml_identifierare = MLVerksamhetsIdentifierare()
    
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
            bilder = convert_from_path(pdf_sokvag, dpi=OCR_DPI)
            logger.info(f"Skapade {len(bilder)} bilder från PDF")
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
                text = pytesseract.image_to_string(
                    forbattrad_bild, 
                    lang=OCR_SPRÅK,
                    config=OCR_PSM
                )
                all_text += text + "\n"
                logger.info(f"Extraherade {len(text)} tecken från bild {i+1}")
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
        # Mönster för svenska personnummer (ÅÅÅÅMMDD-XXXX)
        pattern = r'\b(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])-\d{4}\b'
        match = re.search(pattern, text)
        
        if match:
            personnummer = match.group()
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
        Identifierar verksamhet med ML-modell eller fallback till nyckelord
        
        Args:
            text: Text att analysera
            
        Returns:
            Tuple med (verksamhet, sannolikhet)
        """
        # Försök med ML-identifierare först
        try:
            verksamhet, sannolikhet = self.ml_identifierare.identifiera_verksamhet(text)
            return verksamhet, sannolikhet
        except Exception as e:
            logger.warning(f"ML-identifiering misslyckades, använder fallback: {e}")
        
        # Fallback till original nyckelordsbaserad metod
        text_lower = text.lower()
        bästa_verksamhet = "Okänd"
        högsta_poäng = 0
        
        for verksamhet, nyckelord in self.verksamheter.items():
            poäng = 0
            total_nyckelord = len(nyckelord)
            
            for nyckel in nyckelord:
                if nyckel.lower() in text_lower:
                    poäng += 1
            
            # Beräkna sannolikhet som procent
            sannolikhet = (poäng / total_nyckelord) * 100
            
            if sannolikhet > högsta_poäng:
                högsta_poäng = sannolikhet
                bästa_verksamhet = verksamhet
        
        logger.info(f"Fallback identifiering: {bästa_verksamhet} (sannolikhet: {högsta_poäng:.1f}%)")
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
            if personnummer and remissdatum:
                self.skapa_dat_fil(verksamhet, personnummer, remissdatum, pdf_namn, mål_mapp)
            else:
                logger.warning("Kunde inte skapa .dat-fil - saknar personnummer eller datum")
            
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


def main():
    """Huvudfunktion"""
    logger.info("Startar Remissorterare")
    
    # Skapa sorterare och bearbeta filer
    sorterare = RemissSorterare()
    sorterare.bearbeta_alla_pdf()
    
    logger.info("Remissorterare slutförd")


if __name__ == "__main__":
    main()
