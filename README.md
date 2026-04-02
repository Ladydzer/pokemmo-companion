# PokeMMO Companion

App web + overlay OCR pour PokeMMO. Detecte automatiquement la route et l'adversaire en combat.

## Installation

### 1. Python 3.12+

```bash
pip install -r requirements.txt
```

### 2. Tesseract OCR (obligatoire pour l'overlay)

**Installer Tesseract :**

1. Telecharger depuis https://github.com/UB-Mannheim/tesseract/wiki
2. Installer dans `C:\Program Files\Tesseract-OCR\`
3. Cocher **Additional language data** > **French** pendant l'installation

**Ou installer la langue francaise manuellement :**

```bash
# Telecharger fra.traineddata (pour les noms Pokemon en francais)
curl -L -o "C:\Program Files\Tesseract-OCR\tessdata\fra.traineddata" ^
  https://github.com/tesseract-ocr/tessdata/raw/main/fra.traineddata
```

**Verifier l'installation :**

```bash
tesseract --list-langs
# Doit afficher : eng, fra
```

> **Note :** Sans `fra.traineddata`, l'OCR fonctionne avec `eng` en fallback, mais les accents francais (e, e, c, etc.) seront moins bien reconnus.

### 3. Lancer

```bash
python web.py
```

L'app web demarre sur http://127.0.0.1:8080. L'overlay OCR se lance via le bouton dans la sidebar.

## Configuration OCR

- **Studio OCR** : Options > Studio OCR > "Capturer depuis PokeMMO" pour calibrer les zones de detection
- **Config** : `~/.pokemmo-companion/config.json`
- **Zones** : `data/ocr_regions.json` (sauvegardees par le Studio)

## Hotkeys (overlay)

| Touche | Action |
|--------|--------|
| F9 | Masquer/afficher overlay |
| F10 | Mode etendu |
| F11 | Mode debug |
