# PokeMMO Companion

App web + overlay OCR pour PokeMMO. Détecte automatiquement la route et l'adversaire en combat.

## Installation

### 1. Python 3.12+

```bash
pip install -r requirements.txt
```

### 2. Tesseract OCR (obligatoire pour l'overlay)

**Installer Tesseract :**

1. Télécharger depuis https://github.com/UB-Mannheim/tesseract/wiki
2. Installer dans `C:\Program Files\Tesseract-OCR\`
3. Cocher **Additional language data** > **French** pendant l'installation

**Ou installer la langue française manuellement :**

```bash
# Télécharger fra.traineddata (pour les noms Pokémon en français)
curl -L -o "C:\Program Files\Tesseract-OCR\tessdata\fra.traineddata" ^
  https://github.com/tesseract-ocr/tessdata/raw/main/fra.traineddata
```

**Vérifier l'installation :**

```bash
tesseract --list-langs
# Doit afficher : eng, fra
```

> **Note :** Sans `fra.traineddata`, l'OCR fonctionne avec `eng` en fallback, mais les accents français (é, è, ç, etc.) seront moins bien reconnus.

### 3. Lancer

```bash
python web.py
```

L'app web démarre sur http://127.0.0.1:8080. L'overlay OCR se lance via le bouton dans la sidebar.

## Configuration OCR

- **Studio OCR** : Options > Studio OCR > "Capturer depuis PokeMMO" pour calibrer les zones de détection
- **Config** : `~/.pokemmo-companion/config.json`
- **Zones** : `data/ocr_regions.json` (sauvegardées par le Studio)

## Hotkeys (overlay)

| Touche | Action |
|--------|--------|
| F9 | Masquer/afficher overlay |
| F10 | Mode étendu |
| F11 | Mode debug |
