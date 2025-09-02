#!/usr/bin/env python3
"""
Machine Learning-baserad verksamhetsidentifierare för Remissorterare
Använder TF-IDF och klassificerare för förbättrad precision
"""

import pickle
import logging
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sklearn.pipeline import Pipeline
import joblib

from config import VERKSAMHETER

logger = logging.getLogger(__name__)

class MLVerksamhetsIdentifierare:
    """Machine Learning-baserad verksamhetsidentifierare"""
    
    def __init__(self, model_path: str = "models/verksamhets_model.pkl"):
        self.model_path = Path(model_path)
        self.pipeline = None
        self.trained = False
        self.fallback_identifierare = None
        
        # Skapa models-mapp
        self.model_path.parent.mkdir(exist_ok=True)
        
        # Ladda befintlig modell om den finns
        self.ladda_modell()
    
    def skapa_pipeline(self):
        """Skapar ML-pipeline med TF-IDF och klassificerare"""
        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                max_features=2000,
                ngram_range=(1, 2),
                stop_words=None,  # Vi vill behålla svenska termer
                min_df=2,
                max_df=0.95
            )),
            ('classifier', RandomForestClassifier(
                n_estimators=100,
                random_state=42,
                n_jobs=-1
            ))
        ])
    
    def förbereda_träningsdata(self) -> Tuple[List[str], List[str]]:
        """
        Förbereder träningsdata baserat på nyckelord i config
        Skapar syntetiska texter för varje verksamhet
        """
        texter = []
        verksamheter = []
        
        for verksamhet, nyckelord in VERKSAMHETER.items():
            # Skapa flera varianter av texter för varje verksamhet
            for i in range(10):  # 10 texter per verksamhet
                # Kombinera nyckelord på olika sätt
                if i < 3:
                    # Kort text med få nyckelord
                    text = f"Remiss till {verksamhet.lower()}. {nyckelord[0]} och {nyckelord[1]}."
                elif i < 6:
                    # Medellång text
                    text = f"Patient remitteras till {verksamhet.lower()}. "
                    text += f"Diagnos: {nyckelord[0]}, {nyckelord[1]}, {nyckelord[2]}. "
                    text += f"Behandling: {nyckelord[3]}."
                else:
                    # Längre text med fler nyckelord
                    text = f"Remiss till {verksamhet.lower()}. "
                    text += f"Patient har {nyckelord[0]}, {nyckelord[1]}, {nyckelord[2]}. "
                    text += f"Symtom: {nyckelord[3]}, {nyckelord[4]}. "
                    text += f"Planerad behandling: {nyckelord[5]}."
                
                texter.append(text)
                verksamheter.append(verksamhet)
        
        return texter, verksamheter
    
    def träna_modell(self, custom_data: Optional[Tuple[List[str], List[str]]] = None):
        """
        Tränar ML-modellen
        
        Args:
            custom_data: Valfri egen träningsdata (texter, verksamheter)
        """
        logger.info("Startar träning av ML-modell...")
        
        # Skapa pipeline
        self.skapa_pipeline()
        
        # Förbereda träningsdata
        if custom_data:
            texter, verksamheter = custom_data
        else:
            texter, verksamheter = self.förbereda_träningsdata()
        
        logger.info(f"Träningsdata: {len(texter)} texter, {len(set(verksamheter))} verksamheter")
        
        # Dela data i träning och test
        X_train, X_test, y_train, y_test = train_test_split(
            texter, verksamheter, test_size=0.2, random_state=42, stratify=verksamheter
        )
        
        # Träna modellen
        self.pipeline.fit(X_train, y_train)
        
        # Utvärdera modellen
        y_pred = self.pipeline.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        logger.info(f"Modellträning slutförd. Precision: {accuracy:.3f}")
        logger.info(f"Klassifikationsrapport:\n{classification_report(y_test, y_pred)}")
        
        # Spara modellen
        self.spara_modell()
        self.trained = True
        
        return accuracy
    
    def träna_med_anpassad_data(self, texter: List[str], verksamheter: List[str]):
        """
        Tränar modellen med anpassad data (t.ex. från omfördelningsprocesser)
        
        Args:
            texter: Lista med texter att träna på
            verksamheter: Motsvarande verksamheter för texterna
        """
        if not texter or not verksamheter or len(texter) != len(verksamheter):
            logger.error("Ogiltig träningsdata")
            return
        
        logger.info(f"Tränar modell med {len(texter)} anpassade texter")
        
        try:
            # Skapa pipeline om den inte finns
            if self.pipeline is None:
                self.skapa_pipeline()
            
            # Kombinera befintlig träningsdata med ny data
            befintliga_texter, befintliga_verksamheter = self.förbereda_träningsdata()
            
            # Lägg till den nya datan
            alla_texter = befintliga_texter + texter
            alla_verksamheter = befintliga_verksamheter + verksamheter
            
            # Träna modellen
            self.pipeline.fit(alla_texter, alla_verksamheter)
            self.trained = True
            
            # Spara den uppdaterade modellen
            self.spara_modell()
            
            logger.info("Modell tränad och sparad med anpassad data")
            
        except Exception as e:
            logger.error(f"Fel vid träning med anpassad data: {e}")
            raise
    
    def identifiera_verksamhet(self, text: str) -> Tuple[str, float]:
        """
        Identifierar verksamhet med ML-modell
        
        Args:
            text: Text att analysera
            
        Returns:
            Tuple med (verksamhet, sannolikhet)
        """
        if not self.trained or self.pipeline is None:
            logger.warning("ML-modell inte tränad, använder fallback")
            return self.fallback_identifiering(text)
        
        try:
            # Förutsäg verksamhet
            prediction = self.pipeline.predict([text])[0]
            
            # Hämta sannolikheter för alla klasser
            probabilities = self.pipeline.predict_proba([text])[0]
            
            # Hitta index för förutsagd verksamhet
            classes = self.pipeline.classes_
            pred_index = list(classes).index(prediction)
            sannolikhet = probabilities[pred_index] * 100
            
            logger.info(f"ML-identifiering: {prediction} (sannolikhet: {sannolikhet:.1f}%)")
            
            return prediction, sannolikhet
            
        except Exception as e:
            logger.error(f"ML-identifiering misslyckades: {e}")
            return self.fallback_identifiering(text)
    
    def fallback_identifiering(self, text: str) -> Tuple[str, float]:
        """
        Fallback till original nyckelordsbaserad identifiering
        """
        if self.fallback_identifierare is None:
            # Importera original identifierare
            from remiss_sorterare import RemissSorterare
            temp_sorterare = RemissSorterare()
            self.fallback_identifierare = temp_sorterare.identifiera_verksamhet
        
        return self.fallback_identifierare(text)
    
    def spara_modell(self):
        """Sparar tränad modell"""
        try:
            joblib.dump(self.pipeline, self.model_path)
            logger.info(f"Modell sparad: {self.model_path}")
        except Exception as e:
            logger.error(f"Fel vid sparande av modell: {e}")
    
    def ladda_modell(self):
        """Laddar befintlig modell"""
        try:
            if self.model_path.exists():
                self.pipeline = joblib.load(self.model_path)
                self.trained = True
                logger.info(f"Modell laddad: {self.model_path}")
            else:
                logger.info("Ingen befintlig modell hittad")
        except Exception as e:
            logger.error(f"Fel vid laddning av modell: {e}")
            self.trained = False
    
    def utvärdera_texter(self, test_texter: List[str], true_verksamheter: List[str]):
        """
        Utvärderar modellen på testdata
        
        Args:
            test_texter: Lista med testtexter
            true_verksamheter: Lista med korrekta verksamheter
        """
        if not self.trained:
            logger.error("Modell inte tränad")
            return
        
        predictions = []
        for text in test_texter:
            pred, _ = self.identifiera_verksamhet(text)
            predictions.append(pred)
        
        accuracy = accuracy_score(true_verksamheter, predictions)
        logger.info(f"Utvärdering: Precision {accuracy:.3f}")
        logger.info(f"Detaljerad rapport:\n{classification_report(true_verksamheter, predictions)}")
        
        return accuracy


def skapa_exempeldata():
    """Skapar exempeldata för träning"""
    exempel_texter = [
        "Patient med knäproblem och artros remitteras till ortopedi",
        "Hjärtproblem med arytmi kräver kardiologisk utredning",
        "Hudproblem med eksem behöver dermatologisk behandling",
        "Neurologiska symptom kräver neurologisk utredning",
        "Mageproblem och reflux till gastroenterologi",
        "Diabetes och insulinbehandling till endokrinologi",
        "Urinvägsproblem till urologi",
        "Gynekologiska problem till gynekologi",
        "Ögonproblem till oftalmologi",
        "Öra-näsa-hals problem till ENT"
    ]
    
    exempel_verksamheter = [
        "Ortopedi", "Kardiologi", "Dermatologi", "Neurologi",
        "Gastroenterologi", "Endokrinologi", "Urologi", "Gynekologi",
        "Oftalmologi", "Otorinolaryngologi"
    ]
    
    return exempel_texter, exempel_verksamheter


if __name__ == "__main__":
    # Testa ML-identifieraren
    logging.basicConfig(level=logging.INFO)
    
    identifierare = MLVerksamhetsIdentifierare()
    
    # Träna modellen
    accuracy = identifierare.träna_modell()
    print(f"Modellträning slutförd med precision: {accuracy:.3f}")
    
    # Testa identifiering
    test_texter = [
        "Patient med knäproblem och artros",
        "Hjärtproblem med arytmi",
        "Hudproblem med eksem",
        "Allmän text utan specifika termer"
    ]
    
    for text in test_texter:
        verksamhet, sannolikhet = identifierare.identifiera_verksamhet(text)
        print(f"'{text}' -> {verksamhet} ({sannolikhet:.1f}%)")
