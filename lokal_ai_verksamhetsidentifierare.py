#!/usr/bin/env python3
"""
Lokal AI-baserad verksamhetsidentifierare för Remissorterare
Använder lokala modeller för intelligent verksamhetsidentifiering
"""

import logging
import json
from typing import Dict, List, Tuple, Optional
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
from sentence_transformers import SentenceTransformer
import torch
import numpy as np
from config import VERKSAMHETER
from ai_config import *

logger = logging.getLogger(__name__)

class LokalAIVerksamhetsIdentifierare:
    """Lokal AI-baserad verksamhetsidentifierare"""
    
    def __init__(self, model_type: str = "sentence_transformer"):
        self.model_type = model_type
        self.model = None
        self.tokenizer = None
        self.verksamheter = list(VERKSAMHETER.keys())
        self.verksamhet_embeddings = {}
        
        # Modellalternativ
        self.model_options = {
            "sentence_transformer": {
                "name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                "description": "Liten svensk/engelsk modell (117MB)"
            },
            "swedish_bert": {
                "name": "KB/bert-base-swedish-cased",
                "description": "Svensk BERT-modell (438MB)"
            },
            "multilingual_bert": {
                "name": "bert-base-multilingual-cased",
                "description": "Multilingual BERT (1.1GB)"
            }
        }
        
        self.ladda_modell()
    
    def ladda_modell(self):
        """Laddar den valda AI-modellen"""
        try:
            if self.model_type == "sentence_transformer":
                logger.info(f"Laddar lokal AI-modell: {self.model_options[self.model_type]['name']}")
                self.model = SentenceTransformer(self.model_options[self.model_type]['name'])
                
                # Skapa embeddings för alla verksamheter
                self._skapa_verksamhet_embeddings()
                
            elif self.model_type in ["swedish_bert", "multilingual_bert"]:
                logger.info(f"Laddar lokal AI-modell: {self.model_options[self.model_type]['name']}")
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_options[self.model_type]['name'])
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    self.model_options[self.model_type]['name'],
                    num_labels=len(self.verksamheter)
                )
                
            logger.info("Lokal AI-modell laddad framgångsrikt")
            
        except Exception as e:
            logger.error(f"Fel vid laddning av lokal AI-modell: {e}")
            self.model = None
    
    def _skapa_verksamhet_embeddings(self):
        """Skapar embeddings för alla verksamheter"""
        try:
            # Skapa beskrivande texter för varje verksamhet
            verksamhet_texter = {}
            for verksamhet, nyckelord in VERKSAMHETER.items():
                # Kombinera verksamhetsnamn med nyckelord
                text = f"{verksamhet}. "
                text += f"Denna verksamhet hanterar: {', '.join(nyckelord[:5])}"
                verksamhet_texter[verksamhet] = text
            
            # Skapa embeddings
            texter = list(verksamhet_texter.values())
            embeddings = self.model.encode(texter)
            
            # Spara embeddings
            for i, verksamhet in enumerate(self.verksamheter):
                self.verksamhet_embeddings[verksamhet] = embeddings[i]
            
            logger.info(f"Skapade embeddings för {len(self.verksamheter)} verksamheter")
            
        except Exception as e:
            logger.error(f"Fel vid skapande av verksamhet-embeddings: {e}")
    
    def identifiera_verksamhet(self, text: str) -> Tuple[str, float]:
        """
        Identifierar verksamhet med lokal AI
        
        Args:
            text: Text att analysera
        
        Returns:
            Tuple med (verksamhet, sannolikhet)
        """
        if not self.model:
            logger.warning("Lokal AI-modell inte tillgänglig")
            return "Okänd", 0.0
        
        try:
            if self.model_type == "sentence_transformer":
                return self._identifiera_med_sentence_transformer(text)
            elif self.model_type in ["swedish_bert", "multilingual_bert"]:
                return self._identifiera_med_bert(text)
            else:
                logger.error(f"Okänd modelltyp: {self.model_type}")
                return "Okänd", 0.0
                
        except Exception as e:
            logger.error(f"Fel vid lokal AI-identifiering: {e}")
            return "Okänd", 0.0
    
    def _identifiera_med_sentence_transformer(self, text: str) -> Tuple[str, float]:
        """Identifierar verksamhet med Sentence Transformer"""
        try:
            # Skapa embedding för input-text
            text_embedding = self.model.encode([text])[0]
            
            # Beräkna likhet med alla verksamheter
            likheter = {}
            for verksamhet, verksamhet_embedding in self.verksamhet_embeddings.items():
                # Cosine similarity
                similarity = np.dot(text_embedding, verksamhet_embedding) / (
                    np.linalg.norm(text_embedding) * np.linalg.norm(verksamhet_embedding)
                )
                likheter[verksamhet] = similarity
            
            # Hitta bästa match
            bästa_verksamhet = max(likheter.items(), key=lambda x: x[1])
            verksamhet, likhet = bästa_verksamhet
            
            # Konvertera likhet till sannolikhet (0-100%)
            sannolikhet = max(0, min(100, (likhet + 1) * 50))  # Normalisera från [-1,1] till [0,100]
            
            logger.info(f"Lokal AI (Sentence Transformer): {verksamhet} (sannolikhet: {sannolikhet:.1f}%)")
            return verksamhet, sannolikhet
            
        except Exception as e:
            logger.error(f"Fel vid Sentence Transformer-identifiering: {e}")
            return "Okänd", 0.0
    
    def _identifiera_med_bert(self, text: str) -> Tuple[str, float]:
        """Identifierar verksamhet med BERT"""
        try:
            # Förbered text för BERT
            inputs = self.tokenizer(
                text,
                truncation=True,
                padding=True,
                max_length=512,
                return_tensors="pt"
            )
            
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
            
            logger.info(f"Lokal AI (BERT): {verksamhet} (sannolikhet: {sannolikhet:.1f}%)")
            return verksamhet, sannolikhet
            
        except Exception as e:
            logger.error(f"Fel vid BERT-identifiering: {e}")
            return "Okänd", 0.0
    
    def testa_modell(self) -> bool:
        """Testar om modellen fungerar"""
        if not self.model:
            return False
        
        try:
            test_text = "Test av lokal AI-modell"
            resultat = self.identifiera_verksamhet(test_text)
            return resultat[0] != "Okänd"
        except Exception as e:
            logger.error(f"Modelltest misslyckades: {e}")
            return False
    
    def få_modell_info(self) -> Dict:
        """Hämtar information om den laddade modellen"""
        if not self.model:
            return {"error": "Ingen modell laddad"}
        
        model_info = self.model_options.get(self.model_type, {})
        return {
            "typ": self.model_type,
            "namn": model_info.get("name", "Okänd"),
            "beskrivning": model_info.get("description", "Ingen beskrivning"),
            "status": "laddad",
            "verksamheter": len(self.verksamheter),
            "testad": self.testa_modell()
        }
    
    def byt_modell(self, ny_modell_typ: str) -> bool:
        """Bytar till en annan modell"""
        if ny_modell_typ not in self.model_options:
            logger.error(f"Okänd modelltyp: {ny_modell_typ}")
            return False
        
        try:
            logger.info(f"Bytter från {self.model_type} till {ny_modell_typ}")
            self.model_type = ny_modell_typ
            self.model = None
            self.tokenizer = None
            self.verksamhet_embeddings = {}
            
            self.ladda_modell()
            return self.model is not None
            
        except Exception as e:
            logger.error(f"Fel vid byte av modell: {e}")
            return False
    
    def få_tillgängliga_modeller(self) -> Dict:
        """Returnerar alla tillgängliga modeller"""
        return {
            "nuvarande": self.model_type,
            "tillgängliga": self.model_options
        }
