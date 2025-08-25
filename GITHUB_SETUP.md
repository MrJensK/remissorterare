# Instruktioner för GitHub-uppladdning

## Steg 1: Skapa GitHub Repository

1. Gå till [GitHub.com](https://github.com) och logga in
2. Klicka på "New repository" (grön knapp)
3. Fyll i följande information:
   - **Repository name**: `remissorterare`
   - **Description**: `Automatisk hantering av inscannade remisser med Machine Learning och webbgränssnitt`
   - **Visibility**: Välj Public eller Private
   - **Initialize with**: Lämna alla kryssrutor tomma
4. Klicka "Create repository"

## Steg 2: Ladda upp koden

När du har skapat repository:t, kör följande kommandon i terminalen:

```bash
# Lägg till remote repository (ersätt USERNAME med ditt GitHub-användarnamn)
git remote add origin https://github.com/USERNAME/remissorterare.git

# Push koden till GitHub
git branch -M main
git push -u origin main
```

## Steg 3: Verifiera uppladdningen

1. Gå till din GitHub-repository
2. Kontrollera att alla filer är uppladdade
3. GitHub Actions kommer automatiskt att köra testerna

## Steg 4: Konfigurera GitHub Pages (valfritt)

För att visa README.md snyggt:

1. Gå till Settings > Pages
2. Under "Source", välj "Deploy from a branch"
3. Välj "main" branch och "/docs" folder
4. Klicka "Save"

## Steg 5: Skapa Releases (valfritt)

För att skapa en release:

1. Gå till "Releases" i din repository
2. Klicka "Create a new release"
3. Tag: `v1.0.0`
4. Title: `Remissorterare v1.0.0`
5. Description: Kopiera från README.md
6. Klicka "Publish release"

## Felsökning

### Om du får autentiseringsfel:
```bash
# Använd GitHub CLI (rekommenderat)
gh auth login
gh repo create remissorterare --public --source=. --remote=origin --push

# Eller använd Personal Access Token
git remote set-url origin https://TOKEN@github.com/USERNAME/remissorterare.git
```

### Om du vill ändra repository-namnet:
```bash
git remote set-url origin https://github.com/USERNAME/nytt-namn.git
```

## Nästa steg

Efter uppladdningen kan du:

1. **Dela projektet**: Dela länken till din repository
2. **Ta emot bidrag**: Andra kan nu fork:a och skicka Pull Requests
3. **Uppdatera dokumentation**: Lägg till mer information i README.md
4. **Skapa Issues**: Använd GitHub Issues för att spåra buggar och förbättringar

## Exempel på repository-URL

När du är klar kommer din repository att vara tillgänglig på:
`https://github.com/USERNAME/remissorterare`
