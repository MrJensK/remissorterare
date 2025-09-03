#!/usr/bin/env python3
"""
Konfiguration för Ollama-modeller i Remissorterare
"""

# Tillgängliga Ollama-modeller
OLLAMA_MODELS = {
    "llama2:7b": {
        "name": "llama2:7b",
        "description": "Llama 2 (7B) - Snabb och effektiv, bra för svenska",
        "size": "4.7GB",
        "language": "Svenska/Engelska",
        "performance": "Bra",
        "memory": "8GB RAM"
    },
    "llama2:13b": {
        "name": "llama2:13b", 
        "description": "Llama 2 (13B) - Bättre kvalitet, kräver mer minne",
        "size": "8.5GB",
        "language": "Svenska/Engelska",
        "performance": "Mycket bra",
        "memory": "16GB RAM"
    },
    "llama2:70b": {
        "name": "llama2:70b",
        "description": "Llama 2 (70B) - Högsta kvalitet, kräver mycket minne",
        "size": "39GB",
        "language": "Svenska/Engelska", 
        "performance": "Utmärkt",
        "memory": "32GB RAM"
    },
    "mistral:7b": {
        "name": "mistral:7b",
        "description": "Mistral (7B) - Modern och effektiv, bra för svenska",
        "size": "4.1GB",
        "language": "Svenska/Engelska",
        "performance": "Mycket bra",
        "memory": "8GB RAM"
    },
    "mistral:7b-instruct": {
        "name": "mistral:7b-instruct",
        "description": "Mistral (7B) Instruct - Optimerad för instruktioner",
        "size": "4.1GB", 
        "language": "Svenska/Engelska",
        "performance": "Utmärkt",
        "memory": "8GB RAM"
    },
    "codellama:7b": {
        "name": "codellama:7b",
        "description": "Code Llama (7B) - Bra för strukturerad text",
        "size": "4.7GB",
        "language": "Svenska/Engelska",
        "performance": "Bra",
        "memory": "8GB RAM"
    },
    "qwen:7b": {
        "name": "qwen:7b", 
        "description": "Qwen (7B) - Modern kinesisk modell, bra för svenska",
        "size": "4.7GB",
        "language": "Svenska/Engelska/Kinesiska",
        "performance": "Bra",
        "memory": "8GB RAM"
    },
    "phi:2.7b": {
        "name": "phi:2.7b",
        "description": "Phi-2 (2.7B) - Liten men effektiv",
        "size": "1.7GB",
        "language": "Svenska/Engelska",
        "performance": "Bra",
        "memory": "4GB RAM"
    }
}

# Standardmodell
DEFAULT_OLLAMA_MODEL = "llama2:7b"

# Modeller som rekommenderas för svenska
RECOMMENDED_FOR_SWEDISH = [
    "llama2:7b",
    "mistral:7b-instruct", 
    "llama2:13b"
]

def get_model_info(model_name: str) -> dict:
    """Hämtar information om en specifik modell"""
    return OLLAMA_MODELS.get(model_name, {})

def list_available_models() -> list:
    """Listar alla tillgängliga modeller"""
    return list(OLLAMA_MODELS.keys())

def get_recommended_models() -> list:
    """Hämtar rekommenderade modeller för svenska"""
    return RECOMMENDED_FOR_SWEDISH

def validate_model_name(model_name: str) -> bool:
    """Validerar om en modellnamn är giltigt"""
    return model_name in OLLAMA_MODELS
