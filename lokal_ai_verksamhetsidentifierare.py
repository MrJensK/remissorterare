#!/usr/bin/env python3
"""
Modern lokal AI-baserad verksamhetsidentifierare för Remissorterare
Stöder flera AI-modeller: Ollama, BERT, Sentence Transformers, och andra
"""

import logging
import json
import requests
from typing import Dict, List, Tuple, Optional
import numpy as np
from config import VERKSAMHETER
from ollama_config import *

logger = logging.getLogger(__name__)

class LokalAIVerksamhetsIdentifierare:
    """Modern lokal AI-baserad verksamhetsidentifierare med stöd för flera modelltyper"""
    
    def __init__(self, model_type: str = "ollama"):
        self.model_type = model_type
        self.model = None
        self.tokenizer = None
        self.verksamheter = list(VERKSAMHETER.keys())
        self.verksamhet_embeddings = {}
        
        # Modellalternativ med moderna AI-lösningar
        self.model_options = {
            "ollama": {
                "name": DEFAULT_OLLAMA_MODEL,  # Använd standard från ollama_config
                "description": "Ollama med konfigurerbar modell",
                "url": "http://localhost:11434/api/generate",
                "requires_setup": True
            },
            "sentence_transformer": {
                "name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                "description": "Sentence Transformer - Liten svensk/engelsk modell (117MB)",
                "requires_setup": False
            },
            "swedish_bert": {
                "name": "KB/bert-base-swedish-cased",
                "description": "Svensk BERT - Högsta precision för svenska (438MB)",
                "requires_setup": False
            },
            "multilingual_bert": {
                "name": "bert-base-multilingual-cased",
                "description": "Multilingual BERT - Stöder många språk (1.1GB)",
                "requires_setup": False
            },
            "openai_local": {
                "name": "local",
                "description": "Lokal OpenAI-kompatibel server",
                "url": "http://localhost:1234/v1/chat/completions",
                "requires_setup": True
            },
            "huggingface_inference": {
                "name": "microsoft/DialoGPT-medium",
                "description": "Hugging Face Inference API",
                "requires_setup": False
            }
        }
        
        self.ladda_modell()
    
    def byt_ollama_modell(self, model_name: str) -> bool:
        """Byter Ollama-modell till en ny modell"""
        try:
            if not validate_model_name(model_name):
                logger.error(f"Ogiltig modellnamn: {model_name}")
                logger.info(f"Tillgängliga modeller: {', '.join(list_available_models())}")
                return False
            
            # Uppdatera modellnamnet
            self.model_options["ollama"]["name"] = model_name
            logger.info(f"Bytt till Ollama-modell: {model_name}")
            
            # Ladda om modellen
            return self._ladda_ollama_modell()
            
        except Exception as e:
            logger.error(f"Fel vid byte av Ollama-modell: {e}")
            return False
    
    def hämta_tillgängliga_ollama_modeller(self) -> list:
        """Hämtar lista över tillgängliga Ollama-modeller"""
        return list_available_models()
    
    def hämta_rekommenderade_modeller(self) -> list:
        """Hämtar rekommenderade modeller för svenska"""
        return get_recommended_models()
    
    def hämta_modell_info(self, model_name: str) -> dict:
        """Hämtar information om en specifik modell"""
        return get_model_info(model_name)
    
    def ladda_modell(self):
        """Laddar den valda AI-modellen"""
        try:
            if self.model_type == "ollama":
                return self._ladda_ollama_modell()
            elif self.model_type == "sentence_transformer":
                return self._ladda_sentence_transformer()
            elif self.model_type in ["swedish_bert", "multilingual_bert"]:
                return self._ladda_bert_modell()
            elif self.model_type == "openai_local":
                return self._ladda_openai_local()
            elif self.model_type == "huggingface_inference":
                return self._ladda_huggingface_inference()
            else:
                logger.error(f"Okänd modelltyp: {self.model_type}")
                return False
                
        except Exception as e:
            logger.error(f"Fel vid laddning av modell {self.model_type}: {e}")
            return False
    
    def _ladda_ollama_modell(self):
        """Laddar Ollama-modell"""
        try:
            # Testa anslutning till Ollama
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                # Kontrollera vilken modell som är vald
                vald_modell = self.model_options["ollama"]["name"]
                logger.info(f"Ollama-anslutning fungerar, vald modell: {vald_modell}")
                
                # Kontrollera om modellen finns installerad
                try:
                    model_response = requests.get(f"http://localhost:11434/api/show", 
                                               json={"name": vald_modell}, timeout=5)
                    if model_response.status_code == 200:
                        logger.info(f"Modell {vald_modell} är installerad och redo")
                        self.model = "ollama"
                        return True
                    else:
                        logger.warning(f"Modell {vald_modell} är inte installerad")
                        logger.info(f"Installera med: ollama pull {vald_modell}")
                        # Använd standardmodellen istället
                        self.model_options["ollama"]["name"] = DEFAULT_OLLAMA_MODEL
                        logger.info(f"Använder standardmodell: {DEFAULT_OLLAMA_MODEL}")
                        self.model = "ollama"
                        return True
                except Exception as e:
                    logger.warning(f"Kunde inte kontrollera modell {vald_modell}: {e}")
                    self.model = "ollama"
                    return True
            else:
                logger.error(f"Ollama svarade med status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Kan inte ansluta till Ollama: {e}")
            logger.info("Kontrollera att Ollama körs: ollama serve")
            return False
    
    def _ladda_sentence_transformer(self):
        """Laddar Sentence Transformer-modell"""
        try:
            from sentence_transformers import SentenceTransformer
            
            logger.info(f"Laddar Sentence Transformer: {self.model_options[self.model_type]['name']}")
            self.model = SentenceTransformer(self.model_options[self.model_type]['name'])
            
            # Skapa embeddings för verksamheter
            self._skapa_verksamhet_embeddings()
            
            logger.info("Sentence Transformer laddad framgångsrikt")
            return True
            
        except ImportError:
            logger.error("Sentence Transformers inte installerat. Kör: pip install sentence-transformers")
            return False
        except Exception as e:
            logger.error(f"Fel vid laddning av Sentence Transformer: {e}")
            return False
    
    def _ladda_bert_modell(self):
        """Laddar BERT-modell med modern hantering"""
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            import torch
            
            logger.info(f"Laddar BERT-modell: {self.model_options[self.model_type]['name']}")
            
            # Ladda tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_options[self.model_type]['name']
            )
            
            # Ladda modell med modern konfiguration
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.model_options[self.model_type]['name'],
                num_labels=len(self.verksamheter),
                torch_dtype=torch.float32,
                low_cpu_mem_usage=True
            )
            
            # Flytta till rätt enhet
            if torch.cuda.is_available():
                self.model = self.model.cuda()
                logger.info("BERT-modell flyttad till GPU")
            else:
                self.model = self.model.cpu()
                logger.info("BERT-modell körs på CPU")
            
            logger.info("BERT-modell laddad framgångsrikt")
            return True
            
        except ImportError:
            logger.error("Transformers inte installerat. Kör: pip install transformers torch")
            return False
        except Exception as e:
            logger.error(f"Fel vid laddning av BERT-modell: {e}")
            return False
    
    def _ladda_openai_local(self):
        """Laddar lokal OpenAI-kompatibel server"""
        try:
            # Testa anslutning till lokal server
            response = requests.get("http://localhost:1234/v1/models", timeout=5)
            if response.status_code == 200:
                logger.info("Lokal OpenAI-server fungerar")
                self.model = "openai_local"
                return True
            else:
                logger.error(f"Lokal OpenAI-server svarade med status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Kan inte ansluta till lokal OpenAI-server: {e}")
            return False
    
    def _ladda_huggingface_inference(self):
        """Laddar Hugging Face Inference API"""
        try:
            # För nu, sätt modellen som tillgänglig
            # Implementera senare med riktig Hugging Face API
            logger.info("Hugging Face Inference API konfigurerad")
            self.model = "huggingface_inference"
            return True
        except Exception as e:
            logger.error(f"Fel vid laddning av Hugging Face Inference: {e}")
            return False
    
    def _skapa_verksamhet_embeddings(self):
        """Skapar embeddings för verksamheter (endast för Sentence Transformer)"""
        try:
            if not self.model or not hasattr(self.model, 'encode'):
                return
            
            self.verksamhet_embeddings = {}
            
            for verksamhet, nyckelord in VERKSAMHETER.items():
                # Skapa beskrivande text
                text = f"{verksamhet}. Denna verksamhet hanterar: {', '.join(nyckelord[:5])}"
                
                try:
                    embedding = self.model.encode([text])[0]
                    self.verksamhet_embeddings[verksamhet] = embedding
                except Exception as e:
                    logger.warning(f"Kunde inte skapa embedding för {verksamhet}: {e}")
                    continue
            
            logger.info(f"Skapade embeddings för {len(self.verksamhet_embeddings)} verksamheter")
            
        except Exception as e:
            logger.error(f"Fel vid skapande av embeddings: {e}")
            self.verksamhet_embeddings = {}
    
    def identifiera_verksamhet(self, text: str) -> Tuple[str, float]:
        """
        Identifierar verksamhet med vald AI-modell
        
        Args:
            text: Text att analysera
        
        Returns:
            Tuple med (verksamhet, sannolikhet)
        """
        try:
            if self.model_type == "ollama":
                return self._identifiera_med_ollama(text)
            elif self.model_type == "sentence_transformer":
                return self._identifiera_med_sentence_transformer(text)
            elif self.model_type in ["swedish_bert", "multilingual_bert"]:
                return self._identifiera_med_bert(text)
            elif self.model_type == "openai_local":
                return self._identifiera_med_openai_local(text)
            elif self.model_type == "huggingface_inference":
                return self._identifiera_med_huggingface(text)
            else:
                logger.error(f"Okänd modelltyp: {self.model_type}")
                return "Okänd", 0.0
                
        except Exception as e:
            logger.error(f"Fel vid AI-identifiering med {self.model_type}: {e}")
            return "Okänd", 0.0
    
    def _identifiera_med_ollama(self, text: str) -> Tuple[str, float]:
        """Identifierar verksamhet med Ollama"""
        try:
            prompt = self._skapa_ollama_prompt(text)
            
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model_options["ollama"]["name"],
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result.get('response', '').strip()
                
                # Logga rå output från AI:n för debugging
                logger.info(f"Ollama rå output: {ai_response}")
                logger.info(f"Ollama fullständig response: {result}")
                
                # Parsa AI-svar
                verksamhet, sannolikhet = self._parsa_ai_svar(ai_response)
                
                logger.info(f"Ollama identifierade: {verksamhet} ({sannolikhet:.1f}%)")
                return verksamhet, sannolikhet
            else:
                logger.error(f"Ollama API-fel: {response.status_code}")
                return "Okänd", 0.0
                
        except Exception as e:
            logger.error(f"Fel vid Ollama-anrop: {e}")
            return "Okänd", 0.0
    
    def _identifiera_med_sentence_transformer(self, text: str) -> Tuple[str, float]:
        """Identifierar verksamhet med Sentence Transformer"""
        try:
            if not self.model or not hasattr(self.model, 'encode'):
                return "Okänd", 0.0
            
            # Skapa embedding för input-text
            text_embedding = self.model.encode([text])[0]
            
            # Beräkna likhet med verksamheter
            likheter = {}
            for verksamhet, verksamhet_embedding in self.verksamhet_embeddings.items():
                try:
                    similarity = np.dot(text_embedding, verksamhet_embedding) / (
                        np.linalg.norm(text_embedding) * np.linalg.norm(verksamhet_embedding)
                    )
                    likheter[verksamhet] = similarity
                except Exception as e:
                    logger.warning(f"Fel vid likhetsberäkning för {verksamhet}: {e}")
                    likheter[verksamhet] = 0.0
            
            if likheter:
                bästa_verksamhet = max(likheter.items(), key=lambda x: x[1])
                verksamhet, likhet = bästa_verksamhet
                sannolikhet = max(0, min(100, (likhet + 1) * 50))
                
                logger.info(f"Sentence Transformer: {verksamhet} ({sannolikhet:.1f}%)")
                return verksamhet, sannolikhet
            else:
                return "Okänd", 0.0
                
        except Exception as e:
            logger.error(f"Fel vid Sentence Transformer: {e}")
            return "Okänd", 0.0
    
    def _identifiera_med_bert(self, text: str) -> Tuple[str, float]:
        """Identifierar verksamhet med BERT"""
        try:
            if not self.model or not self.tokenizer:
                return "Okänd", 0.0
            
            # Förbered text för BERT
            inputs = self.tokenizer(
                text,
                truncation=True,
                padding=True,
                max_length=512,
                return_tensors="pt"
            )
            
            # Flytta inputs till samma enhet som modellen
            device = next(self.model.parameters()).device
            inputs = {k: v.to(device) for k, v in inputs.items()}
            
            # Gör prediktion
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=1)
            
            # Hitta bästa match
            best_idx = torch.argmax(probabilities, dim=1).item()
            best_probability = probabilities[0][best_idx].item()
            
            verksamhet = self.verksamheter[best_idx]
            sannolikhet = best_probability * 100
            
            logger.info(f"BERT identifierade: {verksamhet} ({sannolikhet:.1f}%)")
            return verksamhet, sannolikhet
            
        except Exception as e:
            logger.error(f"Fel vid BERT-identifiering: {e}")
            return "Okänd", 0.0
    
    def _identifiera_med_openai_local(self, text: str) -> Tuple[str, float]:
        """Identifierar verksamhet med lokal OpenAI-server"""
        try:
            prompt = self._skapa_openai_prompt(text)
            
            response = requests.post(
                "http://localhost:1234/v1/chat/completions",
                json={
                    "model": "local",
                    "messages": [
                        {"role": "system", "content": "Du är en expert på svenska medicinska remisser."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 200
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content'].strip()
                
                verksamhet, sannolikhet = self._parsa_ai_svar(ai_response)
                
                logger.info(f"Lokal OpenAI identifierade: {verksamhet} ({sannolikhet:.1f}%)")
                return verksamhet, sannolikhet
            else:
                logger.error(f"Lokal OpenAI API-fel: {response.status_code}")
                return "Okänd", 0.0
                
        except Exception as e:
            logger.error(f"Fel vid lokal OpenAI-anrop: {e}")
            return "Okänd", 0.0
    
    def _identifiera_med_huggingface(self, text: str) -> Tuple[str, float]:
        """Identifierar verksamhet med Hugging Face Inference API"""
        try:
            # Implementera senare med riktig Hugging Face API
            logger.info("Hugging Face Inference API inte implementerat än")
            return "Okänd", 0.0
        except Exception as e:
            logger.error(f"Fel vid Hugging Face Inference: {e}")
            return "Okänd", 0.0
    
    def _skapa_ollama_prompt(self, text: str) -> str:
        """Skapar prompt för Ollama"""
        return f"""Du är en expert på svenska medicinska remisser. Din uppgift är att identifiera vilken medicinsk verksamhet en remiss ska skickas till.

Tillgängliga verksamheter: {', '.join(self.verksamheter)}

VIKTIGA REGLER:
1. Titta ALLTID på MOTTAGAREN (inte avsändaren)
2. Sök efter fraser som "remiss till", "mottagare:", "till verksamhet:", "till klinik:", etc.
3. Analysera innehållet noggrant för att förstå vad remissen handlar om
4. Välj den mest lämpliga verksamheten baserat på innehållet
5. Sätt sannolikheten till MINST 70% om du är säker på din identifiering
6. Sätt sannolikheten till 0% ENDAST om du verkligen inte kan identifiera verksamheten

Remisstext:
{text[:1000]}

Svara EXAKT i följande format:
Verksamhet: [verksamhetsnamn]
Sannolikhet: [70-100]% (om säker) eller 0% (om osäker)
Motivering: [kort förklaring av varför denna verksamhet valdes]"""
    
    def _skapa_openai_prompt(self, text: str) -> str:
        """Skapar prompt för OpenAI-kompatibel server"""
        return f"""Analysera följande svenska medicinska remiss och identifiera vilken verksamhet den ska skickas till.

Tillgängliga verksamheter: {', '.join(self.verksamheter)}

Instruktioner:
1. Titta på MOTTAGAREN (inte avsändaren)
2. Sök efter fraser som "remiss till", "mottagare:", "till verksamhet:", etc.
3. Analysera innehållet för att förstå vad remissen handlar om
4. Välj den mest lämpliga verksamheten
5. Ge en kort motivering för ditt val

Remisstext:
{text[:1000]}

Svara i följande format:
Verksamhet: [verksamhetsnamn]
Sannolikhet: [0-100]%
Motivering: [kort förklaring]"""
    
    def _parsa_ai_svar(self, ai_response: str) -> Tuple[str, float]:
        """Parsar AI-svar för att extrahera verksamhet och sannolikhet"""
        try:
            verksamhet = "Okänd"
            sannolikhet = 0.0
            
            # Sök efter verksamhet
            for line in ai_response.split('\n'):
                if line.lower().startswith('verksamhet:'):
                    verksamhet = line.split(':', 1)[1].strip()
                    break
            
            # Sök efter sannolikhet
            for line in ai_response.split('\n'):
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
                sannolikhet = 75.0  # Standardvärde om AI gav ogiltig sannolikhet
            elif sannolikhet == 0.0 and verksamhet != "Okänd":
                # Om AI identifierade en verksamhet men gav 0% sannolikhet, 
                # betyder det att AI:n är osäker - sätt till 50% istället
                sannolikhet = 50.0
                logger.info(f"AI gav 0% sannolikhet för '{verksamhet}' - sätter till 50% (osäker)")
            
            return verksamhet, sannolikhet
            
        except Exception as e:
            logger.error(f"Fel vid parsning av AI-svar: {e}")
            return "Okänd", 0.0
    
    def _hitta_närmaste_verksamhet(self, okänd_verksamhet: str) -> str:
        """Hittar närmaste matchande verksamhet baserat på likhet"""
        import difflib
        
        matches = difflib.get_close_matches(
            okänd_verksamhet.lower(),
            [v.lower() for v in self.verksamheter],
            n=1, cutoff=0.6
        )
        
        if matches:
            for verksamhet in self.verksamheter:
                if verksamhet.lower() == matches[0]:
                    logger.info(f"Korrigerade '{okänd_verksamhet}' till '{verksamhet}'")
                    return verksamhet
        
        # Fallback till första verksamheten
        logger.warning(f"Kunde inte hitta match för '{okänd_verksamhet}', använder fallback")
        return self.verksamheter[0] if self.verksamheter else "Okänd"
    
    def testa_modell(self) -> bool:
        """Testar om modellen fungerar"""
        try:
            test_text = "Test av lokal AI-modell"
            resultat = self.identifiera_verksamhet(test_text)
            return resultat[0] != "Okänd"
        except Exception as e:
            logger.error(f"Modelltest misslyckades: {e}")
            return False
    
    def få_modell_info(self) -> Dict:
        """Hämtar information om den laddade modellen"""
        model_info = self.model_options.get(self.model_type, {})
        return {
            "typ": self.model_type,
            "namn": model_info.get("name", "Okänd"),
            "beskrivning": model_info.get("description", "Ingen beskrivning"),
            "status": "laddad" if self.model else "fel",
            "verksamheter": len(self.verksamheter),
            "testad": self.testa_modell(),
            "kräver_setup": model_info.get("requires_setup", False)
        }
    
    def byt_modell(self, ny_modell_typ: str) -> bool:
        """Bytar till en annan modell"""
        if ny_modell_typ not in self.model_options:
            logger.error(f"Okänd modelltyp: {ny_modell_typ}")
            return False
        
        try:
            logger.info(f"Bytter från {self.model_type} till {ny_modell_typ}")
            
            # Spara gamla modellen temporärt
            gammal_model = self.model
            gammal_model_type = self.model_type
            
            # Rensa gamla modeller
            self.model = None
            self.tokenizer = None
            if hasattr(self, 'verksamhet_embeddings'):
                self.verksamhet_embeddings = {}
            
            # Uppdatera modelltyp
            self.model_type = ny_modell_typ
            
            # Försök ladda ny modell
            if self.ladda_modell():
                logger.info(f"Modell bytt framgångsrikt till {ny_modell_typ}")
                return True
            else:
                # Återställ gamla modellen om ny misslyckades
                logger.warning(f"Kunde inte ladda {ny_modell_typ}, återställer {gammal_model_type}")
                self.model_type = gammal_model_type
                self.model = gammal_model
                return False
            
        except Exception as e:
            logger.error(f"Fel vid byte av modell: {e}")
            # Återställ gamla modellen
            self.model_type = gammal_model_type
            self.model = gammal_model
            return False
    
    def få_tillgängliga_modeller(self) -> Dict:
        """Returnerar alla tillgängliga modeller"""
        return {
            "nuvarande": self.model_type,
            "tillgängliga": self.model_options
        }
    
    def få_användningsstatistik(self) -> Dict:
        """Hämtar användningsstatistik för lokal AI"""
        try:
            model_info = self.få_modell_info()
            
            if self.model_type == "ollama":
                return {
                    "status": "ansluten" if self.model else "ej ansluten",
                    "modell": "ollama",
                    "modellnamn": self.model_options["ollama"]["name"],
                    "användning": "tillgänglig" if self.model else "ej tillgänglig",
                    "kräver_setup": True
                }
            elif self.model_type == "sentence_transformer":
                return {
                    "status": "laddad" if self.model else "ej laddad",
                    "modell": "sentence_transformer",
                    "modellnamn": self.model_options["sentence_transformer"]["name"],
                    "användning": "tillgänglig" if self.model else "ej tillgänglig",
                    "kräver_setup": False
                }
            elif self.model_type in ["swedish_bert", "multilingual_bert"]:
                return {
                    "status": "laddad" if self.model else "ej laddad",
                    "modell": self.model_type,
                    "modellnamn": self.model_options[self.model_type]["name"],
                    "användning": "tillgänglig" if self.model else "ej tillgänglig",
                    "kräver_setup": False
                }
            elif self.model_type == "openai_local":
                return {
                    "status": "ansluten" if self.model else "ej ansluten",
                    "modell": "openai_local",
                    "modellnamn": "local",
                    "användning": "tillgänglig" if self.model else "ej tillgänglig",
                    "kräver_setup": True
                }
            else:
                return {
                    "status": "okänd",
                    "modell": self.model_type,
                    "modellnamn": "okänd",
                    "användning": "ej tillgänglig",
                    "kräver_setup": False
                }
                
        except Exception as e:
            logger.error(f"Fel vid hämtning av användningsstatistik: {e}")
            return {
                "status": "fel",
                "modell": self.model_type,
                "modellnamn": "okänd",
                "användning": "ej tillgänglig",
                "error": str(e)
            }
