# Ollama Setup Guide för Remissorterare

## 🚀 Vad är Ollama?

Ollama är en lokal AI-server som låter dig köra stora språkmodeller (LLMs) direkt på din maskin. Det är perfekt för Remissorterare eftersom det ger AI-funktionalitet utan att skicka data externt.

## 📦 Installation

### macOS
```bash
# Ladda ner och installera
curl -fsSL https://ollama.ai/install.sh | sh

# Starta Ollama
ollama serve
```

### Linux
```bash
# Ladda ner och installera
curl -fsSL https://ollama.ai/install.sh | sh

# Starta Ollama
ollama serve
```

### Windows
```bash
# Ladda ner från: https://ollama.ai/download
# Kör installeraren och följ instruktionerna
```

## 🤖 Ladda ner modeller

### Llama 2 (rekommenderad)
```bash
# Ladda ner Llama 2 7B (snabb och effektiv)
ollama pull llama2:7b

# Eller ladda ner Llama 2 13B (bättre kvalitet, långsammare)
ollama pull llama2:13b
```

### Andra modeller
```bash
# Mistral (bra svenska)
ollama pull mistral:7b

# Code Llama (bra för tekniska texter)
ollama pull codellama:7b

# Llama 2 Uncensored (mer flexibel)
ollama pull llama2-uncensored:7b
```

## ⚙️ Konfiguration

### 1. Starta Ollama-server
```bash
# I en terminal
ollama serve
```

### 2. Testa anslutning
```bash
# I en annan terminal
curl 

```

### 3. Konfigurera Remissorterare
Redigera `ai_config.py`:
```python
LOKAL_AI_MODEL = "ollama"  # Använd Ollama som standard
```

## 🔧 Felsökning

### Ollama startar inte
```bash
# Kontrollera att Ollama är installerat
which ollama

# Starta om Ollama
pkill ollama
ollama serve
```

### Modell laddas inte
```bash
# Kontrollera tillgängliga modeller
ollama list

# Ladda ner modell igen
ollama pull llama2:7b
```

### Anslutningsfel
```bash
# Kontrollera att Ollama körs
curl http://localhost:11434/api/tags

# Om det inte fungerar, starta om Ollama
ollama serve
```

## 📊 Prestanda

### Modellstorlekar
- **7B modeller**: ~4GB RAM, snabba
- **13B modeller**: ~8GB RAM, bättre kvalitet
- **30B+ modeller**: ~16GB+ RAM, högsta kvalitet

### Rekommendationer
- **4-8GB RAM**: Använd 7B modeller
- **8-16GB RAM**: Använd 13B modeller
- **16GB+ RAM**: Kan använda 30B+ modeller

## 🎯 Användning i Remissorterare

1. **Starta Ollama**: `ollama serve`
2. **Välj modell** i webbgränssnittet: "Ollama (Llama 2)"
3. **Testa AI-förslag** på remisser
4. **Få intelligenta förslag** på nya verksamheter

## 🔒 Säkerhet

- **All data körs lokalt** - inget skickas externt
- **Ingen internetanslutning** krävs efter nedladdning
- **Fullständig kontroll** över dina data
- **GDPR-kompatibel** för känslig medicinsk information

## 📚 Mer information

- [Ollama Documentation](https://ollama.ai/docs)
- [Modellbibliotek](https://ollama.ai/library)
- [Community](https://github.com/ollama/ollama/discussions)
