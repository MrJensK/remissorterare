# Bidrag till Remissorterare

Tack för ditt intresse för att bidra till Remissorterare! Detta dokument innehåller riktlinjer för hur du kan bidra till projektet.

## Hur du bidrar

### Rapportera buggar

1. Använd GitHub Issues för att rapportera buggar
2. Beskriv problemet så detaljerat som möjligt
3. Inkludera steg för att återskapa problemet
4. Ange din operativsystem och Python-version

### Föreslå förbättringar

1. Skapa en GitHub Issue för att diskutera förbättringen
2. Beskriv fördelen med förändringen
3. Inkludera exempel på användning om relevant

### Skicka kod

1. Forka projektet
2. Skapa en feature branch: `git checkout -b feature/ny-funktion`
3. Gör dina ändringar
4. Lägg till tester för nya funktioner
5. Commit dina ändringar: `git commit -m 'Lägg till ny funktion'`
6. Push till branchen: `git push origin feature/ny-funktion`
7. Skapa en Pull Request

## Utvecklingsmiljö

### Förutsättningar

- Python 3.8+
- Tesseract OCR
- Git

### Installation

```bash
# Klona projektet
git clone https://github.com/ditt-användarnamn/remissorterare.git
cd remissorterare

# Installera beroenden
pip install -r requirements.txt

# Kör tester
python test_remissorterare.py
```

## Kodstandard

### Python

- Följ PEP 8 för kodformatering
- Använd type hints där möjligt
- Skriv docstrings för alla funktioner
- Håll funktioner korta och fokuserade

### Commit-meddelanden

- Använd svenska för commit-meddelanden
- Beskriv vad som ändrats, inte hur
- Använd imperativ form: "Lägg till" inte "Lagt till"

### Tester

- Skriv tester för nya funktioner
- Kör alla tester innan du skickar en PR
- Se till att testtäckningen inte minskar

## Projektstruktur

```
remissorterare/
├── remiss_sorterare.py      # Huvudprogram
├── ml_verksamhetsidentifierare.py  # ML-komponent
├── web_app.py              # Webbgränssnitt
├── config.py               # Konfiguration
├── test_remissorterare.py  # Tester
├── requirements.txt        # Beroenden
├── README.md              # Dokumentation
└── static/                # Web-resurser
    ├── css/
    └── js/
```

## Säkerhet

- Rapportera säkerhetsproblem privat till projektägaren
- Inkludera inte känslig data i koden
- Följ säkerhetsriktlinjer för hantering av patientdata

## Licens

Genom att bidra till detta projekt godkänner du att dina bidrag licensieras under MIT-licensen.

## Kontakt

Om du har frågor om hur du kan bidra, skapa en GitHub Issue eller kontakta projektägaren.
