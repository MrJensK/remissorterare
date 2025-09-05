# Remissorterare

Ett avancerat Python-program för automatisk hantering av inscannade remisser (PDF:er) med AI-driven verksamhetsidentifiering och förberedelse av data för import i andra system.

## 🚀 Funktioner

- **OCR-bearbetning**: Konverterar bildbaserade PDF:er till text med hjälp av Tesseract OCR
- **AI-driven analys**: Intelligent verksamhetsidentifiering med OpenAI eller lokala AI-modeller
- **Machine Learning**: Förbättrad verksamhetsidentifiering med TF-IDF och Random Forest
- **Web-baserat gränssnitt**: Modern drag-and-drop interface med realtidsstatus och statistik
- **Automatisk sortering**: Identifierar verksamhet med hög precision och kontextbaserad analys
- **Datautläsning**: Extraherar personnummer och remissdatum
- **Intelligent beslutslogik**: Sorterar remisser baserat på sannolikhetspoäng och AI-analys
- **Strukturerad output**: Skapar .dat-filer för import i Sälma
- **Realtidsuppdateringar**: WebSocket-baserad kommunikation
- **Statistik och rapportering**: Visar bearbetningsstatistik i realtid
- **Omdirigering av osäkra remisser**: Möjlighet att manuellt omfördela och träna modellen
- **Debug-verktyg**: Steg-för-steg analys av verksamhetsidentifiering
- **Lokal AI-stöd**: Kör AI-modeller direkt på din maskin utan internetanslutning
- **Remisshantering**: Komplett hantering av bearbetade remisser med omfördelning och radering
- **Verksamhetshantering**: Hantera verksamheter och nyckelord via webbgränssnitt
- **JSON-konfiguration**: Verksamheter lagras i extern JSON-fil för enkel hantering
- **Remissförhandsvisning**: Se innehållet i remisser direkt i webbläsaren
- **Ollama-modellval**: Välj mellan installerade Ollama-modeller direkt i gränssnittet
- **Dynamisk verksamhetsladdning**: Omdirigeringslistan uppdateras automatiskt från verksamheter.json
- **Klickbara filnamn**: Klicka på PDF-filnamn för att läsa innehåll i både osakert-listan och remisshantering
- **Förbättrad osakert-hantering**: Visar personnummer och remissdatum direkt i tabellen

## 🛠️ Installation

### Snabbinstallation (rekommenderat)

```bash
# Klona eller ladda ner projektet
cd remissorterare

# Gör installationsskriptet körbart
chmod +x install.sh

# Kör installationsskriptet
./install.sh
```

**Vad installationsskriptet gör automatiskt:**
- ✅ Installerar Python 3.12 via pyenv
- ✅ Installerar Tesseract OCR med svenska språkstöd
- ✅ Installerar Poppler för PDF-konvertering (macOS/Linux)
- ✅ Skapar virtuell Python-miljö
- ✅ Installerar alla Python-beroenden
- ✅ Installerar lokala AI-bibliotek
- ✅ Valfritt OpenAI-stöd
- ✅ Skapar mappstruktur och verksamhetsmappar
- ✅ Konfigurerar AI-inställningar
- ✅ Skapar verksamheter.json med alla verksamheter
- ✅ Testar installationen
- ✅ Skapar startskript
- ✅ Kontrollerar virtuell miljö vid körning

### Manuell installation

#### Förutsättningar

1. **Python 3.8 eller senare**
2. **Tesseract OCR** (krävs för textigenkänning)

#### Installera Tesseract

**macOS:**
```bash
brew install tesseract
brew install tesseract-lang  # För svenska språkstöd
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install tesseract-ocr
sudo apt install tesseract-ocr-swe  # Svenska språkstöd
sudo apt install poppler-utils      # PDF-konvertering
```

**macOS:**
```bash
brew install tesseract
brew install tesseract-lang  # För svenska språkstöd
brew install poppler         # PDF-konvertering
```

**Windows:**
Ladda ner från: https://github.com/UB-Mannheim/tesseract/wiki

#### Installera Ollama (rekommenderat)

**macOS:**
```bash
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Starta Ollama:**
```bash
ollama serve
```

**Installera standardmodell:**
```bash
ollama pull llama2:7b
```

#### Installera Python-beroenden

**Automatisk installation (rekommenderat):**
```bash
# Kör det kompletta installationsskriptet
./install.sh
```

**Manuell installation:**
```bash
# Grundläggande beroenden
pip install pytesseract pdf2image Pillow opencv-python numpy python-dateutil scikit-learn joblib Flask Flask-SocketIO Werkzeug

# Lokala AI-modeller (rekommenderat)
pip install transformers torch sentence-transformers

# OpenAI-stöd (valfritt)
pip install openai
```

## 🤖 AI-konfiguration

### Ollama-modeller (rekommenderat)

Programmet stöder nu **Ollama** - lokala stora språkmodeller som körs direkt på din maskin:

#### **Tillgängliga modeller:**
- **`llama2:7b`** (4.7GB): Snabb och effektiv, bra för svenska
- **`mistral:7b-instruct`** (4.1GB): Optimerad för instruktioner, utmärkt för svenska
- **`llama2:13b`** (8.5GB): Högre kvalitet, kräver mer minne (16GB RAM)
- **`llama2:70b`** (39GB): Högsta kvalitet, kräver mycket minne (32GB RAM)
- **`codellama:7b`** (4.7GB): Bra för strukturerad text
- **`qwen:7b`** (4.7GB): Modern modell med bra svenska stöd
- **`phi:2.7b`** (1.7GB): Liten men effektiv (4GB RAM)

#### **Rekommenderade modeller för svenska:**
1. **`mistral:7b-instruct`** - Bästa balansen mellan kvalitet och hastighet
2. **`llama2:7b`** - Bra standardmodell
3. **`llama2:13b`** - Om du har tillräckligt med RAM

#### **Installera Ollama:**
```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Starta Ollama
ollama serve
```

#### **Hantera modeller:**
```bash
# Lista tillgängliga modeller
python ollama_manager.py list

# Installera en modell
python ollama_manager.py install llama2:7b

# Testa en modell
python ollama_manager.py test mistral:7b-instruct

# Sätt standardmodell
python ollama_manager.py set-default mistral:7b-instruct
```

#### **Webbgränssnitt:**
Ollama-modellhantering är nu integrerat i huvudgränssnittet:
- Välj mellan installerade modeller direkt i AI-status
- Byt modell med ett klick
- Se status och prestanda

### Andra lokala AI-modeller

Programmet stöder även andra lokala AI-modeller:

- **Sentence Transformer**: Liten, snabb modell (117MB) - bra för svenska
- **Swedish BERT**: Svensk BERT-modell (438MB) - hög precision
- **Multilingual BERT**: Internationell modell (1.1GB) - stöder många språk

**Konfigurera för lokala AI:**
```python
# I ai_config.py
AI_TYPE = "lokal"
LOKAL_AI_MODEL = "ollama"  # eller "sentence_transformer", "swedish_bert", "multilingual_bert"
```

### OpenAI-integration (valfritt)

För att använda OpenAI:

1. **Sätt API-nyckel:**
   ```bash
   export OPENAI_API_KEY="sk-1234567890abcdef..."
   ```

2. **Konfigurera:**
   ```python
   # I ai_config.py
   AI_TYPE = "openai"
   OPENAI_MODEL = "gpt-3.5-turbo"
   ```

## 📁 Användning

### Grundläggande användning

1. **Mappstrukturen skapas automatiskt** av installationsskriptet:
   ```
   remissorterare/
   ├── input/          # Lägg PDF-filer här
   ├── output/         # Sorterade filer hamnar här
   │   ├── Ortopedi/
   │   ├── Kirurgi/
   │   ├── Kardiologi/
   │   ├── Gynekologi/
   │   └── osakert/    # Osäkra remisser
   ├── models/         # AI-modeller och cache
   └── remiss_sorterare.py
   ```

2. **Kör programmet**:

   **Kommando-rad version**:
   ```bash
   # Använd det automatiskt skapade startskriptet
   ./start.sh
   
   # Eller starta manuellt
   source venv/bin/activate
   python remiss_sorterare.py
   ```

   **Web-baserat gränssnitt**:
   ```bash
   # Använd det automatiskt skapade startskriptet
   ./start_web.sh
   
   # Eller starta manuellt
   source venv/bin/activate
   python web_app.py
   ```

### Ollama-modellhantering

#### **Webbgränssnitt:**
1. Starta webbapplikationen: `./start_web.sh`
2. Gå till "AI Status och Konfiguration" sektionen
3. Välj mellan installerade Ollama-modeller i dropdown-menyn
4. Klicka "Byt Modell" för att växla

#### **Kommandoradsverktyg:**
```bash
# Aktivera virtuell miljö
source venv/bin/activate

# Lista tillgängliga modeller
python ollama_manager.py list

# Installera en modell
python ollama_manager.py install mistral:7b-instruct

# Testa en modell
python ollama_manager.py test llama2:7b

# Sätt standardmodell
python ollama_manager.py set-default mistral:7b-instruct
```

#### **Automatisk modellhantering:**
- Programmet kontrollerar automatiskt vilka modeller som är installerade
- Fallback till standardmodell om vald modell saknas
- Automatisk validering av modellkompatibilitet

### Remisshantering

#### **Komplett remisshantering:**
1. Starta webbapplikationen: `./start_web.sh`
2. Klicka på "Remisshantering" i huvudmenyn
3. Välj verksamhet för att se alla remisser
4. Klicka på remissnamn för att se innehåll
5. Omfördela remisser till andra verksamheter
6. Radera remisser som inte behövs

#### **Funktioner:**
- **Remisslista**: Se alla remisser med tidsangivelse och storlek
- **Förhandsvisning**: Klicka på remissnamn för att se fullständig text
- **Omfördelning**: Flytta remisser mellan verksamheter
- **Radering**: Ta bort remisser med bekräftelse
- **Sökning**: Filtrera remisser per verksamhet
- **Detaljer**: Se personnummer, remissdatum och .dat-fil innehåll
- **Klickbara filnamn**: PDF-ikon och klickbar länk för att läsa innehåll
- **Modal-funktionalitet**: Fullständig textvisning i popup-fönster

### Osakert-hantering

#### **Hantera osäkra remisser:**
1. Gå till "Omdirigering av osäkra remisser" sektionen på huvudsidan
2. Se alla remisser som behöver manuell granskning
3. Klicka på PDF-filnamn för att läsa fullständigt innehåll
4. Välj rätt verksamhet från uppdaterad lista (från verksamheter.json)
5. Omdirigera remisser med ett klick
6. Använd AI-förslag för att få hjälp med klassificering
7. Träna ML-modellen med omfördelningsdata

#### **Förbättringar:**
- **Dynamisk verksamhetsladdning**: Listan uppdateras automatiskt från verksamheter.json
- **Klickbara filnamn**: PDF-ikon och klickbar länk för att läsa innehåll
- **Förbättrad visning**: Visar personnummer och remissdatum direkt i tabellen
- **Modal-funktionalitet**: Fullständig textvisning i popup-fönster
- **AI-förslag**: Få förslag på verksamhet baserat på PDF-innehåll

### Verksamhetshantering

#### **Hantera verksamheter och nyckelord:**
1. Gå till "Verksamhetshantering" sektionen på huvudsidan
2. Lägg till nya verksamheter med nyckelord
3. Använd AI-förslag för att föreslå nyckelord
4. Ta bort verksamheter som inte behövs
5. Se antal filer per verksamhet

#### **JSON-konfiguration:**
- Verksamheter lagras i `verksamheter.json`
- Enkel att redigera och underhålla
- Automatisk laddning vid start
- Fallback till inbyggd konfiguration
- **Dynamisk uppdatering**: Ändringar i JSON-filen syns omedelbart i gränssnittet

### Schemalagd körning

#### macOS/Linux (cron):
```bash
# Öppna crontab
crontab -e

# Lägg till för körning varje timme
0 * * * * cd /sökväg/till/remissorterare && ./venv/bin/python run_scheduled.py

# Eller använd startskriptet
0 * * * * cd /sökväg/till/remissorterare && ./start.sh
```

#### Windows (Task Scheduler):
1. Öppna Task Scheduler
2. Skapa en ny uppgift
3. Ange sökväg till Python och skriptet
4. Sätt schemat efter behov

## ⚙️ Konfiguration

### Huvudkonfiguration

Redigera `config.py` för att anpassa:

- **Tröskelvärden**: Ändra sannolikhetströskel (standard: 70% för AI, 90% för fallback)
- **OCR-inställningar**: Justera DPI och språk
- **Mappnamn**: Anpassa mappstruktur

### Verksamhetskonfiguration

Verksamheter och nyckelord lagras nu i `verksamheter.json`:

```json
{
  "Ortopedi": [
    "ortopedi", "ortopedisk", "led", "leder", "knä", "höft", "rygg", "ryggrad",
    "fraktur", "brott", "artros", "artrit", "reumatism", "reumatoid"
  ],
  "Kirurgi": [
    "kirurgi", "kirurgisk", "operation", "operera", "kirurg", "snitt",
    "laparoskopi", "endoskopi", "biopsi", "tumör", "cancer", "malign"
  ]
}
```

**Fördelar med JSON-konfiguration:**
- ✅ Enkel att redigera och underhålla
- ✅ Kan hanteras via webbgränssnittet
- ✅ Automatisk laddning vid start
- ✅ Fallback till inbyggd konfiguration

### AI-konfiguration

Redigera `ai_config.py` för AI-inställningar:

#### **Ollama-konfiguration:**
```python
# I ai_config.py
AI_TYPE = "lokal"
LOKAL_AI_MODEL = "ollama"

# I ollama_config.py kan du ändra standardmodell
DEFAULT_OLLAMA_MODEL = "mistral:7b-instruct"  # Ändra till önskad modell
```

```python
# AI-typ
AI_TYPE = "lokal"  # "lokal" eller "openai"

# Lokala AI-modeller
LOKAL_AI_MODEL = "sentence_transformer"
LOKAL_AI_DOWNLOAD_MODELS = True

# OpenAI (endast om AI_TYPE = "openai")
OPENAI_MODEL = "gpt-3.5-turbo"
OPENAI_TEMPERATURE = 0.1
AI_CONFIDENCE_THRESHOLD = 70
```

## 🧠 AI och Machine Learning

### AI-driven verksamhetsidentifiering

Programmet använder nu AI som primär metod för verksamhetsidentifiering:

1. **AI-analys** (70%+ sannolikhet): Använder OpenAI eller lokala modeller
2. **ML-fallback**: Machine Learning med TF-IDF och Random Forest
3. **Regelbaserad fallback**: Förbättrad nyckelordsanalys med kontextbaserad poängsättning
4. **Osäker klassificering**: Returnerar "osakert" vid låg sannolikhet

### Lokala AI-modeller

**Fördelar:**
- ✅ Ingen internetanslutning krävs
- ✅ Inga API-kostnader
- ✅ Datasäkerhet - allt körs lokalt
- ✅ Snabbare svar - ingen nätverksfördröjning
- ✅ Alltid tillgänglig

**Modeller:**
- **Sentence Transformer**: Snabb, effektiv för svenska text
- **Swedish BERT**: Högsta precision för svenska
- **Multilingual BERT**: Stöder många språk

### Machine Learning

- **TF-IDF Vectorizer**: Extraherar viktiga termer från texten
- **Random Forest Classifier**: Klassificerar verksamhet med hög precision
- **Automatisk träning**: Modellen tränas automatiskt vid första körningen
- **Fallback-system**: Använder AI om ML misslyckas

### Träna ML-modellen

**Via webbgränssnittet:**
1. Ladda upp remisser som hamnat i "osakert"
2. Klicka på "Omdirigera" för varje remiss
3. Välj rätt verksamhet
4. Klicka på "Träna ML med omfördelningsdata"

**Manuellt:**
```bash
python ml_verksamhetsidentifierare.py
```

## 🔄 Omdirigering av osäkra remisser

### Ny funktionalitet

Programmet stöder nu manuell omfördelnings av remisser som hamnat i "osakert":

1. **Lista osäkra remisser**: Se alla remisser som behöver omfördelnings
2. **Omdirigera**: Flytta remisser till rätt verksamhet
3. **Träna modellen**: Använd omfördelningsdata för att förbättra ML-modellen
4. **Automatisk uppdatering**: .dat-filer uppdateras automatiskt

### API-endpoints

- `GET /api/osakert_remisser` - Lista alla osäkra remisser
- `POST /api/omfördela_remiss` - Omdirigera en remiss
- `POST /api/träna_ml_med_omfördelningsdata` - Träna ML-modellen

## 🎯 Förbättrad verksamhetsidentifiering

### Kontextbaserad analys

- **Mottagarfraser**: Söker efter "remiss till", "mottagare:", etc.
- **Viktad poängsättning**: Nyckelord nära mottagarfraser får extra poäng
- **Specifika termer**: Separata nyckelord för gynekologi, kirurgi, etc.
- **Avsändarfiltrering**: Undviker att identifiera avsändaren istället för mottagaren

### Debug-verktyg

- **Steg-för-steg analys**: Se hur varje steg i identifieringen fungerar
- **Poängsättning**: Visa detaljerad poängsättning för varje metod
- **AI-analys**: Se AI:ns resonemang och sannolikhet

## 📊 Webbgränssnitt

Det nya webbgränssnittet erbjuder:

- **Drag-and-drop**: Enkel filuppladdning
- **Realtidsstatus**: Se bearbetningsförloppet live med WebSocket
- **Statistik**: Översikt över bearbetade filer per verksamhet
- **AI-status**: Kontrollera AI-modellernas status och konfiguration
- **Ollama-modellval**: Välj mellan installerade Ollama-modeller direkt i gränssnittet
- **Omdirigering**: Hantera osäkra remisser direkt från gränssnittet
- **Textanalys**: Testa verksamhetsidentifiering med valfri text
- **Debug-analys**: Steg-för-steg analys av identifieringsprocessen
- **ML-träning**: Träna modellen direkt från gränssnittet
- **Remisshantering**: Komplett hantering av bearbetade remisser
- **Verksamhetshantering**: Hantera verksamheter och nyckelord
- **Remissförhandsvisning**: Se innehållet i remisser direkt
- **Osakert-hantering**: Förbättrad hantering av osäkra remisser
- **Dynamisk verksamhetsladdning**: Automatisk uppdatering från verksamheter.json
- **Klickbara filnamn**: PDF-ikon och klickbar länk för att läsa innehåll
- **Modal-funktionalitet**: Fullständig textvisning i popup-fönster
- **Responsivt design**: Fungerar på alla enheter

### Starta webbgränssnittet

```bash
# Använd det automatiskt skapade startskriptet
./start_web.sh

# Eller starta manuellt
source venv/bin/activate
python web_app.py
```

Öppna sedan webbläsaren på: http://localhost:5000

## 📤 Output-format

### .dat-filer

För varje bearbetad remiss skapas en .dat-fil med följande format:

```
Verksamhet: Ortopedi
Personnummer: 19850415-1234
Remissdatum: 2024-01-15
Skapad: 2024-01-15 14:30:25
```

**Förbättringar:**
- ✅ .dat-filer skapas även om remissdatum saknas
- ✅ Personnummer är endast krav för .dat-filskapande
- ✅ Automatisk uppdatering vid omfördelning
- ✅ Synkronisering med PDF-filer

### Mappstruktur

```
output/
├── Ortopedi/
│   ├── remiss1.pdf
│   ├── remiss1.dat
│   ├── remiss2.pdf
│   └── remiss2.dat
├── Kirurgi/
│   └── ...
├── Gynekologi/
│   └── ...
└── osakert/
    └── ... (remisser med låg sannolikhet)
```

## 📝 Loggning

Programmet skapar detaljerade loggar i `remiss_sorterare.log`:

- Bearbetningsstatus för varje PDF
- OCR-resultat och extraherad text
- AI-analysresultat och sannolikheter
- ML-modellens prestanda och träning
- Omdirigeringar och ML-träning
- Fel och varningar

## 🔧 Felsökning

### Vanliga problem

1. **Tesseract inte hittas**:
   - Kontrollera att Tesseract är installerat
   - Lägg till Tesseract i PATH-variabeln
   - **Lösning**: Kör `./install.sh` igen för att installera Tesseract

2. **OCR ger dåliga resultat**:
   - Kontrollera bildkvalitet på PDF:erna
   - Justera DPI-inställning i config.py
   - Förbättra skanning av originaldokument

3. **Fel verksamhet identifieras**:
   - Använd debug-analys för att se steg-för-steg
   - Kontrollera AI-konfigurationen
   - Lägg till fler specifika termer i config.py
   - Justera tröskelvärden

4. **AI-modeller laddas inte**:
   - Kontrollera internetanslutning (för första nedladdningen)
   - Verifiera att rätt AI-typ är vald i ai_config.py
   - Kontrollera att alla AI-bibliotek är installerade
   - **Lösning**: Kör `./install.sh` igen för att installera AI-bibliotek

5. **Installationsproblem**:
   - **Lösning**: Kör `./install.sh` för att installera allt automatiskt
   - Kontrollera att du har Python 3.8+ installerat
   - För Linux: Kontrollera att du har sudo-rättigheter

### Debug-läge

Aktivera debug-loggning i `config.py`:

```python
LOG_NIVÅ = "DEBUG"
```

### AI-debug

Använd debug-verktygen i webbgränssnittet:
1. Klicka på "Debug Analys" för steg-för-steg analys
2. Kontrollera AI-status för att se modellernas tillstånd
3. Testa AI med valfri text

## ⚡ Prestanda

- **Bearbetningstid**: ~30-60 sekunder per PDF (beroende på sidantal och bildkvalitet)
- **Minnesanvändning**: ~100-200 MB per PDF
- **AI-modeller**: 
  - Sentence Transformer: ~117MB
  - Swedish BERT: ~438MB
  - Multilingual BERT: ~1.1GB
  - Ollama-modeller: 1.7GB - 39GB (beroende på modell)
- **Lagringsutrymme**: ~2-5x originalfilens storlek (temporära bilder)
- **Minneskrav för Ollama**: 4GB - 32GB RAM (beroende på modell)

## 🔒 Säkerhet

- Programmet läser endast PDF-filer
- **Lokala AI-modeller**: Inga data skickas externt
- **OpenAI**: Data skickas till OpenAI (se deras sekretesspolicy)
- Loggar innehåller inte känslig patientinformation
- Rekommendation: Kör i isolerad miljö för produktion

## 🆘 Support

### Felsökning

1. **Kontrollera loggfilen** för felmeddelanden
2. **Verifiera AI-konfiguration** i ai_config.py
3. **Testa med en enkel PDF** först
4. **Använd debug-verktygen** i webbgränssnittet
5. **Kör installationsskriptet igen** om du har problem: `./install.sh`

### Vanliga frågor

**Q: Varför fungerar inte AI-identifiering?**
A: Kontrollera att rätt AI_TYPE är vald i ai_config.py och att alla beroenden är installerade.

**Q: Hur byter jag mellan olika AI-modeller?**
A: Använd "AI Status och Konfiguration" sektionen i webbgränssnittet för att välja mellan installerade Ollama-modeller.

**Q: Hur installerar jag Ollama-modeller?**
A: Använd `ollama pull <modellnamn>` i terminalen eller installera via Ollama:s webbgränssnitt.

**Q: Vilken Ollama-modell ska jag välja?**
A: Börja med `mistral:7b-instruct` för bästa balans mellan kvalitet och hastighet.

**Q: Ollama startar inte - vad gör jag?**
A: Kör `ollama serve` i en terminal och håll den igång, eller starta som tjänst.

**Q: Kan jag använda programmet utan internet?**
A: Ja, med lokala AI-modeller fungerar allt offline efter första nedladdningen.

**Q: Hur installerar jag allt enkelt?**
A: Kör bara `./install.sh` - det installerar allt automatiskt inklusive AI-stöd.

**Q: Vad gör installationsskriptet?**
A: Det installerar Python 3.12, Tesseract OCR, alla Python-beroenden, AI-bibliotek, skapar mappstruktur och konfigurerar allt automatiskt.

**Q: Hur hanterar jag remisser efter bearbetning?**
A: Använd "Remisshantering" i huvudmenyn för att se, omfördela eller radera remisser.

**Q: Hur ändrar jag verksamheter och nyckelord?**
A: Använd "Verksamhetshantering" sektionen på huvudsidan eller redigera `verksamheter.json` direkt.

**Q: Varför skapas inte .dat-filer?**
A: .dat-filer skapas endast om personnummer hittas. Kontrollera att personnumret är läsbart i PDF:en.

**Q: Hur ser jag innehållet i en remiss?**
A: Klicka på remissnamnet i remisshanteringssidan eller osakert-listan för att se fullständig text och information.

**Q: Varför uppdateras inte verksamhetslistan i osakert-omdirigering?**
A: Verksamhetslistan hämtas nu dynamiskt från verksamheter.json. Kontrollera att filen är korrekt formaterad och att webbservern har startats om efter ändringar.

**Q: Kan jag klicka på filnamn för att läsa PDF-innehåll?**
A: Ja, både i remisshantering och osakert-listan kan du klicka på PDF-filnamnet för att se fullständigt innehåll i en popup.

**Q: Hur fungerar dynamisk verksamhetsladdning?**
A: Omdirigeringslistan hämtar verksamheter från /api/verksamheter som läser från verksamheter.json. Ändringar syns omedelbart utan omstart.

## 📄 Licens

Detta program är utvecklat för intern användning. Se till att följa relevanta riktlinjer för hantering av patientdata.

## 🔄 Uppdateringar

### Senaste versionen innehåller:

- ✅ AI-driven verksamhetsidentifiering
- ✅ Stöd för lokala AI-modeller
- ✅ **Ollama-integration** med stöd för 8+ modeller
- ✅ **Ollama-modellval** direkt i webbgränssnittet
- ✅ **Automatisk modellvalidering** och fallback
- ✅ **Förbättrad PDF-konvertering** med Poppler-stöd
- ✅ **Virtuell miljökontroll** för säker körning
- ✅ **Komplett remisshantering** med omfördelning och radering
- ✅ **Verksamhetshantering** via webbgränssnitt
- ✅ **JSON-konfiguration** för verksamheter
- ✅ **Remissförhandsvisning** med fullständig text
- ✅ **Förbättrade .dat-filer** som skapas även utan remissdatum
- ✅ **Dynamisk verksamhetsladdning** i osakert-omdirigering
- ✅ **Klickbara filnamn** för att läsa PDF-innehåll
- ✅ **Förbättrad osakert-hantering** med personnummer och remissdatum
- ✅ **Modal-funktionalitet** för fullständig textvisning
- ✅ Omdirigering av osäkra remisser
- ✅ Förbättrad kontextbaserad analys
- ✅ Debug-verktyg för felsökning
- ✅ Webbgränssnitt med realtidsstatus
- ✅ ML-träning med omfördelningsdata
- ✅ Stöd för fler verksamheter (Gynekologi, etc.)
- ✅ Komplett installationsskript med AI-stöd
- ✅ Automatisk AI-konfiguration
- ✅ Webbstartskript för enklare användning
