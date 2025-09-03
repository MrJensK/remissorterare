#!/usr/bin/env python3
"""
AI-baserad verksamhetsidentifierare för Remissorterare
Använder OpenAI för intelligent verksamhetsidentifiering
"""

import os
import logging
import json
from typing import Dict, List, Tuple, Optional
from config import VERKSAMHETER
from ai_config import *

logger = logging.getLogger(__name__)

# Villkorlig OpenAI-import
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI-biblioteket är inte installerat. OpenAI-funktionalitet kommer inte att fungera.")

class AIVerksamhetsIdentifierare:
    """AI-baserad verksamhetsidentifierare med OpenAI"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or OPENAI_API_KEY
        self.client = None
        self.verksamheter = list(VERKSAMHETER.keys())
        
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI-biblioteket är inte tillgängligt")
            return
        
        if self.api_key and AI_ENABLED:
            try:
                self.client = OpenAI(
                    api_key=self.api_key,
                    timeout=AI_TIMEOUT
                )
                logger.info("OpenAI-klient initialiserad")
            except Exception as e:
                logger.error(f"Fel vid initialisering av OpenAI-klient: {e}")
                self.client = None
        else:
            if not AI_ENABLED:
                logger.warning("AI är inaktiverat i konfigurationen")
            else:
                logger.warning("Ingen OpenAI API-nyckel hittad. AI-identifiering kommer inte att fungera.")
    
    def identifiera_verksamhet(self, text: str) -> Tuple[str, float]:
        """
        Identifierar verksamhet med AI
        
        Args:
            text: Text att analysera
        
        Returns:
            Tuple med (verksamhet, sannolikhet)
        """
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI-biblioteket är inte tillgängligt")
            return "Okänd", 0.0
        
        if not self.client:
            logger.warning("OpenAI-klient inte tillgänglig")
            return "Okänd", 0.0
        
        try:
            # Skapa en intelligent prompt för AI:n
            prompt = self._skapa_prompt(text)
            
            # Logga prompt om aktiverat (endast för debugging)
            if AI_LOG_PROMPTS:
                logger.debug(f"AI-prompt: {prompt}")
            
            # Anropa OpenAI med retry-logik
            for attempt in range(AI_MAX_RETRIES):
                try:
                    response = self.client.chat.completions.create(
                        model=OPENAI_MODEL,
                        messages=[
                            {
                                "role": "system",
                                "content": "Du är en expert på svenska medicinska remisser. Din uppgift är att identifiera vilken medicinsk verksamhet en remiss ska skickas till baserat på innehållet. Analysera texten noggrant och identifiera mottagaren (INTE avsändaren)."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        temperature=OPENAI_TEMPERATURE,
                        max_tokens=OPENAI_MAX_TOKENS
                    )
                    
                    # Logga AI-svar om aktiverat
                    if AI_LOG_RESPONSES:
                        ai_svar = response.choices[0].message.content.strip()
                        logger.info(f"AI-svar: {ai_svar}")
                        logger.info(f"OpenAI fullständig response: {response}")
                    
                    break
                except Exception as e:
                    if attempt == AI_MAX_RETRIES - 1:
                        raise e
                    logger.warning(f"AI-anrop misslyckades, försök {attempt + 1}/{AI_MAX_RETRIES}: {e}")
                    continue
            
            # Parsa svaret
            ai_svar = response.choices[0].message.content.strip()
            
            # Extrahera verksamhet och sannolikhet från AI-svaret
            verksamhet, sannolikhet = self._parsa_ai_svar(ai_svar)
            
            return verksamhet, sannolikhet
            
        except Exception as e:
            logger.error(f"Fel vid AI-identifiering: {e}")
            return "Okänd", 0.0
    
    def _skapa_prompt(self, text: str) -> str:
        """Skapar en intelligent prompt för AI:n"""
        
        # Begränsa texten för att spara tokens
        text_preview = text[:AI_MAX_TEXT_LENGTH] + "..." if len(text) > AI_MAX_TEXT_LENGTH else text
        
        prompt = f"""
Analysera följande svenska medicinska remiss och identifiera vilken verksamhet den ska skickas till.

Tillgängliga verksamheter:
{', '.join(self.verksamheter)}

Instruktioner:
1. Titta på Mottagare (inte avsändare)
2. Sök efter fraser som "remiss till", "mottagare", "till verksamhet", etc.
3. Analysera innehållet för att förstå vad remissen handlar om
4. Välj den mest lämpliga verksamheten
5. Ge en kort motivering för ditt val

Remisstext:
{text_preview}

Svara i följande format:
Verksamhet: [verksamhetsnamn]
Sannolikhet: [0-100]%
Motivering: [kort förklaring av varför denna verksamhet valdes]
"""
        return prompt
    
    def _parsa_ai_svar(self, ai_svar: str) -> Tuple[str, float]:
        """Parsar AI:ns svar för att extrahera verksamhet och sannolikhet"""
        
        try:
            # Försök hitta verksamhet
            verksamhet = "Okänd"
            sannolikhet = 0.0
            
            # Sök efter verksamhet
            for line in ai_svar.split('\n'):
                if line.lower().startswith('verksamhet:'):
                    verksamhet = line.split(':', 1)[1].strip()
                    break
            
            # Sök efter sannolikhet
            for line in ai_svar.split('\n'):
                if line.lower().startswith('sannolikhet:'):
                    try:
                        sannolikhet_text = line.split(':', 1)[1].strip()
                        sannolikhet = float(sannolikhet_text.replace('%', ''))
                        break
                    except (ValueError, IndexError):
                        pass
            
            # Validera verksamhet
            if verksamhet not in self.verksamheter:
                logger.warning(f"AI returnerade okänd verksamhet: {verksamhet}")
                # Försök hitta närmaste match
                verksamhet = self._hitta_närmaste_verksamhet(verksamhet)
            
            # Validera sannolikhet
            if not (0 <= sannolikhet <= 100):
                sannolikhet = 75.0  # Standardvärde om AI inte gav en giltig sannolikhet
            elif sannolikhet == 0.0 and verksamhet != "Okänd":
                # Om AI identifierade en verksamhet men gav 0% sannolikhet, 
                # betyder det att AI:n är osäker - sätt till 50% istället
                sannolikhet = 50.0
                logger.info(f"AI gav 0% sannolikhet för '{verksamhet}' - sätter till 50% (osäker)")
            
            logger.info(f"AI identifierade: {verksamhet} med {sannolikhet}% sannolikhet")
            return verksamhet, sannolikhet
            
        except Exception as e:
            logger.error(f"Fel vid parsning av AI-svar: {e}")
            return "Okänd", 0.0
    
    def _hitta_närmaste_verksamhet(self, okänd_verksamhet: str) -> str:
        """Hittar närmaste matchande verksamhet baserat på likhet"""
        import difflib
        
        # Använd difflib för att hitta närmaste match
        matches = difflib.get_close_matches(okänd_verksamhet.lower(), 
                                          [v.lower() for v in self.verksamheter], 
                                          n=1, cutoff=0.6)
        
        if matches:
            # Hitta original-verksamheten med rätt skiftläge
            for verksamhet in self.verksamheter:
                if verksamhet.lower() == matches[0]:
                    logger.info(f"Korrigerade '{okänd_verksamhet}' till '{verksamhet}'")
                    return verksamhet
        
        # Fallback till första verksamheten
        logger.warning(f"Kunde inte hitta match för '{okänd_verksamhet}', använder fallback")
        return self.verksamheter[0] if self.verksamheter else "Okänd"
    
    def testa_anslutning(self) -> bool:
        """Testar anslutningen till OpenAI"""
        if not OPENAI_AVAILABLE:
            return False
        
        if not self.client:
            return False
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=10
            )
            return True
        except Exception as e:
            logger.error(f"OpenAI-anslutningstest misslyckades: {e}")
            return False
    
    def få_användningsstatistik(self) -> Dict:
        """Hämtar användningsstatistik från OpenAI"""
        if not OPENAI_AVAILABLE:
            return {"error": "OpenAI-biblioteket är inte installerat"}
        
        if not self.client:
            return {"error": "Ingen OpenAI-klient"}
        
        try:
            # Detta kräver en OpenAI API-nyckel med rätt behörigheter
            # För nu returnerar vi bara grundläggande info
            return {
                "status": "ansluten",
                "modell": "gpt-3.5-turbo",
                "användning": "tillgänglig"
            }
        except Exception as e:
            logger.error(f"Fel vid hämtning av användningsstatistik: {e}")
            return {"error": str(e)}
