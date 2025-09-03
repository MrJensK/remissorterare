#!/usr/bin/env python3
"""
AI-konfiguration för Remissorterare
"""

import os
from typing import Optional

# AI-inställningar
AI_ENABLED = True
AI_TYPE = "lokal"  # "openai" eller "lokal"
AI_MODEL = "gpt-3.5-turbo"
AI_TEMPERATURE = 0.1
AI_MAX_TOKENS = 200
AI_CONFIDENCE_THRESHOLD = 70  # Minsta sannolikhet för att använda AI-resultat

# Lokala AI-modeller
LOKAL_AI_ENABLED = True
LOKAL_AI_MODEL = "ollama"  # "ollama", "sentence_transformer", "swedish_bert", "multilingual_bert", "openai_local"
LOKAL_AI_DOWNLOAD_MODELS = True  # Sätt till True för AI-modeller
LOKAL_AI_CACHE_DIR = "models/local_ai"  # Cache-mapp för lokala modeller

# OpenAI-inställningar (endast om AI_TYPE = "openai")
OPENAI_API_KEY: Optional[str] = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL: str = "gpt-3.5-turbo"
OPENAI_TEMPERATURE: float = 0.1
OPENAI_MAX_TOKENS: int = 200

# Fallback-inställningar
USE_ML_FALLBACK: bool = True
USE_RULE_BASED_FALLBACK: bool = True

# Loggningsinställningar för AI
AI_LOG_LEVEL: str = "INFO"
AI_LOG_PROMPTS: bool = False  # Logga inte prompts av säkerhetsskäl
AI_LOG_RESPONSES: bool = True  # Logga AI-svar för debugging

# Kostnadsoptimering
AI_MAX_TEXT_LENGTH: int = 1000  # Begränsa textlängd för att spara tokens
AI_CACHE_ENABLED: bool = True  # Aktivera caching av AI-svar
AI_CACHE_TTL: int = 3600  # Cache TTL i sekunder (1 timme)

# Säkerhetsinställningar
AI_CONTENT_FILTER: bool = True  # Aktivera OpenAI:s innehållsfilter
AI_MAX_RETRIES: int = 3  # Max antal försök vid fel
AI_TIMEOUT: int = 30  # Timeout i sekunder
