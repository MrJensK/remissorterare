# Remissorterare

Ett Python-program för automatisk hantering av inscannade remisser (PDF:er) och förberedelse av data för import i andra system.

## Funktioner

- **OCR-bearbetning**: Konverterar bildbaserade PDF:er till text med hjälp av Tesseract OCR
- **Machine Learning**: Förbättrad verksamhetsidentifiering med TF-IDF och Random Forest
- **Web-baserat gränssnitt**: Modern drag-and-drop interface med realtidsstatus
- **Automatisk sortering**: Identifierar verksamhet med högre precision
- **Datautläsning**: Extraherar personnummer och remissdatum
- **Intelligent beslutslogik**: Sorterar remisser baserat på sannolikhetspoäng
- **Strukturerad output**: Skapar .dat-filer för import i Sälma
- **Realtidsuppdateringar**: WebSocket-baserad kommunikation
- **Statistik och rapportering**: Visar bearbetningsstatistik i realtid

## Installation

### Förutsättningar

1. **Python 3.8 eller senare**
2. **Tesseract OCR** (krävs för textigenkänning)

### Installera Tesseract

#### macOS:
```bash
brew install tesseract
brew install tesseract-lang  # För svenska språkstöd
```

#### Ubuntu/Debian:
```bash
sudo apt update
sudo apt install tesseract-ocr
sudo apt install tesseract-ocr-swe  # Svenska språkstöd
```

#### Windows:
Ladda ner från: https://github.com/UB-Mannheim/tesseract/wiki

### Installera Python-beroenden

```bash
pip install -r requirements.txt
```

## Användning

### Grundläggande användning

1. **Skapa mappstruktur**:
   ```
   remissorterare/
   ├── input/          # Lägg PDF-filer här
   ├── output/         # Sorterade filer hamnar här
   │   ├── Ortopedi/
   │   ├── Kirurgi/
   │   ├── Kardiologi/
   │   └── osakert/    # Osäkra remisser
   └── remiss_sorterare.py
   ```

2. **Kör programmet**:

   **Kommando-rad version**:
   ```bash
   python remiss_sorterare.py
   ```

   **Web-baserat gränssnitt**:
   ```bash
   python web_app.py
   ```
   Öppna sedan webbläsaren på: http://localhost:5000

### Schemalagd körning

#### macOS/Linux (cron):
```bash
# Öppna crontab
crontab -e

# Lägg till för körning varje timme
0 * * * * cd /sökväg/till/remissorterare && python remiss_sorterare.py
```

#### Windows (Task Scheduler):
1. Öppna Task Scheduler
2. Skapa en ny uppgift
3. Ange sökväg till Python och skriptet
4. Sätt schemat efter behov

## Konfiguration

Redigera `config.py` för att anpassa:

- **Verksamheter och nyckelord**: Lägg till eller ändra verksamheter
- **Tröskelvärden**: Ändra sannolikhetströskel (standard: 90%)
- **OCR-inställningar**: Justera DPI och språk
- **Mappnamn**: Anpassa mappstruktur

## Machine Learning

Programmet använder nu Machine Learning för förbättrad verksamhetsidentifiering:

- **TF-IDF Vectorizer**: Extraherar viktiga termer från texten
- **Random Forest Classifier**: Klassificerar verksamhet med hög precision
- **Automatisk träning**: Modellen tränas automatiskt vid första körningen
- **Fallback-system**: Använder original nyckelordsmetod om ML misslyckas

### Träna ML-modellen manuellt:
```bash
python ml_verksamhetsidentifierare.py
```

### Via webbgränssnittet:
Klicka på "Träna ML"-knappen i övre högra hörnet.

### Exempel på konfiguration

```python
# Lägg till ny verksamhet
VERKSAMHETER["Onkologi"] = [
    "onkologi", "onkologisk", "cancer", "tumör", "malign",
    "kemoterapi", "strålbehandling", "immunterapi"
]

# Ändra tröskelvärde
SANNOLIKHET_TRÖSKEL = 85  # Lägre tröskel för mer känslig sortering
```

## Output-format

### .dat-filer

För varje bearbetad remiss skapas en .dat-fil med följande format:

```
Verksamhet: Ortopedi
Personnummer: 19850415-1234
Remissdatum: 2024-01-15
Skapad: 2024-01-15 14:30:25
```

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
└── osakert/
    └── ... (remisser med låg sannolikhet)
```

## Loggning

Programmet skapar detaljerade loggar i `remiss_sorterare.log`:

- Bearbetningsstatus för varje PDF
- OCR-resultat och extraherad text
- Identifierade verksamheter och sannolikheter
- ML-modellens prestanda och träning
- Fel och varningar

## Webbgränssnitt

Det nya webbgränssnittet erbjuder:

- **Drag-and-drop**: Enkel filuppladdning
- **Realtidsstatus**: Se bearbetningsförloppet live
- **Statistik**: Översikt över bearbetade filer
- **ML-träning**: Träna modellen direkt från gränssnittet
- **Responsivt design**: Fungerar på alla enheter

## Felsökning

### Vanliga problem

1. **Tesseract inte hittas**:
   - Kontrollera att Tesseract är installerat
   - Lägg till Tesseract i PATH-variabeln

2. **OCR ger dåliga resultat**:
   - Kontrollera bildkvalitet på PDF:erna
   - Justera DPI-inställning i config.py
   - Förbättra skanning av originaldokument

3. **Fel verksamhet identifieras**:
   - Granska nyckelord i config.py
   - Lägg till fler specifika termer
   - Justera tröskelvärde

### Debug-läge

Aktivera debug-loggning i `config.py`:

```python
LOG_NIVÅ = "DEBUG"
```

## Prestanda

- **Bearbetningstid**: ~30-60 sekunder per PDF (beroende på sidantal och bildkvalitet)
- **Minnesanvändning**: ~100-200 MB per PDF
- **Lagringsutrymme**: ~2-5x originalfilens storlek (temporära bilder)

## Säkerhet

- Programmet läser endast PDF-filer
- Inga data skickas externt
- Loggar innehåller inte känslig patientinformation
- Rekommendation: Kör i isolerad miljö för produktion

## Support

För frågor eller problem:
1. Kontrollera loggfilen för felmeddelanden
2. Verifiera att alla beroenden är korrekt installerade
3. Testa med en enkel PDF först

## Licens

Detta program är utvecklat för intern användning. Se till att följa relevanta riktlinjer för hantering av patientdata.
