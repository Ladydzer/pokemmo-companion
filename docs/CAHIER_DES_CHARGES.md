# PokeMMO Companion — Cahier des Charges

**Version** : 1.1
**Date** : 31 mars 2026
**Auteur** : Orchestrateur (synthèse des recherches ScoutBot + DevBot + recherche interne + brainstorm)

---

## 1. Vision du Projet

### 1.1 Résumé
Application Windows desktop qui se superpose au jeu PokeMMO en overlay transparent pour fournir des informations en temps réel : localisation, spawns, guide de progression, counters en combat, et outils avancés de breeding/shiny hunting.

### 1.2 Proposition de Valeur
**Gap identifié** : Aucun outil existant ne combine toutes ces fonctionnalités en une seule app. Les outils actuels sont fragmentés :
- 3s-PokeMMO-Tool (Electron, 20★) → route tracking + Pokédex mais pas d'overlay combat
- Archetype Counter (71★) → encounter tracker uniquement
- PokeMMO-Companion (Rust) → overlay basique sans données
- ChansEgg → breeding uniquement

**Notre app** = le premier **all-in-one** avec overlay temps réel.

### 1.3 Killer Feature — Intelligence Contextuelle (décision brainstorm)
L'app détecte automatiquement le contexte du joueur et pousse l'information pertinente :
- **Overworld** → spawns de la zone, guide de progression, spots recommandés
- **Combat** → type counters, suggestions de moves, faiblesses ×2/×4
- **PC** → analyse IVs, suggestions de breeding
- **Marché** → estimation de prix (si données disponibles)

L'app est un **assistant passif** : elle INFORME mais ne JOUE PAS. Zéro injection, zéro input automatisé.

### 1.4 Tracking de Progression — Mode Coach GPS (décision brainstorm)
1. **Setup initial** (30 sec) : région, nombre de badges, étape story
2. **Auto-tracking passif** : OCR victoire gym, changement de route détecté
3. **Inférence par position** : chaque route a un champ `min_badges` en DB → si tu es Route 8 Kanto = 3+ badges → on recommande le gym 4

### 1.5 Contraintes Critiques
- **Anti-cheat** : PokeMMO n'a PAS d'anti-cheat kernel-level, mais interdit l'injection mémoire/DLL et l'automatisation d'input. **Lecture d'écran externe = SAFE** (confirmé par la communauté et les outils existants sur les forums officiels).
- **Performance** : Le pipeline doit rester < 60ms et < 3% CPU pour ne pas impacter le jeu.
- **5 régions** : Kanto, Johto, Hoenn, Sinnoh, Unova — toutes doivent être supportées.
- **Mécanique Gen 5** : PokeMMO utilise les mécaniques de la Génération 5 pour toutes les régions.

---

## 2. Stack Technique

### 2.1 Décision finale (consensus DevBot + ScoutBot + recherche)

| Composant | Technologie | Justification |
|-----------|-------------|---------------|
| **Langage** | Python 3.11+ | Meilleur écosystème OCR/CV, prototypage rapide, PyInstaller pour distribution |
| **Screen Capture** | BetterCam | 240+ FPS, numpy arrays, < 5ms/capture, supérieur à MSS/Win32 BitBlt |
| **OCR** | Tesseract 5 | PokeMMO utilise NotoSans (font propre = OCR facile). EasyOCR/PaddleOCR trop lourds |
| **Computer Vision** | OpenCV | Template matching pour détecter état du jeu (combat, map, menu) |
| **UI/Overlay** | PyQt6 | Fenêtre transparente click-through (WS_EX_TRANSPARENT + WS_EX_TOPMOST), léger |
| **Base de données** | SQLite | Données offline, pas de serveur nécessaire, rapide |
| **Distribution** | PyInstaller | .exe standalone 30-50 MB |

### 2.2 Architecture

```
[PokeMMO Game Window]
        │
        │ BetterCam (screen capture, no injection)
        ▼
[Capture Engine] ─── capture screenshots à intervalle régulier
        │
        │ numpy arrays
        ▼
[Detection Engine]
  ├── Route Detector (OCR zone nom de route)
  ├── Battle Detector (template matching + OCR nom Pokémon)
  ├── Menu Detector (état : overworld, combat, PC, etc.)
  └── Text Extractor (OCR générique)
        │
        │ événements (route_changed, battle_started, etc.)
        ▼
[Data Engine]
  ├── Pokédex (649 Pokémon, Gen 1-5)
  ├── Spawn Tables (par route, par région)
  ├── Type Chart (18 types, faiblesses/résistances)
  ├── Move Database (moves, PP, power, accuracy)
  ├── Evolution Chains
  └── Progression Guide (par région)
        │
        │ données contextuelles
        ▼
[Overlay UI (PyQt6)]
  ├── Route Info Panel (spawns, taux, niveaux)
  ├── Battle Assistant (type counters, suggestions)
  ├── Progression Guide (prochaine étape)
  ├── Encounter Counter (shiny tracker)
  ├── Team Analyzer
  └── Quick Tools (IV calc, type chart, etc.)
```

### 2.3 Pipeline Performance Cible

| Étape | Temps cible | Méthode |
|-------|-------------|---------|
| Screen capture | < 5ms | BetterCam région spécifique |
| Pre-processing | < 5ms | OpenCV threshold/crop |
| OCR | < 30ms | Tesseract PSM optimisé |
| Data lookup | < 5ms | SQLite indexed |
| UI update | < 15ms | PyQt6 signal/slot |
| **Total** | **< 60ms** | **~16 FPS de refresh** |

---

## 3. UX Overlay — 3 Modes (décision brainstorm)

### Mode Compact (par défaut)
- Widget 200×80px, semi-transparent, ancré en coin
- Nom de route + 3 spawns principaux (icônes, pas texte)
- En combat : type adverse + icône weakness
- Hotkey **F9** toggle visible/invisible

### Mode Étendu (F10)
- Panneau latéral ~300px depuis le côté droit
- Liste complète spawns avec taux, type chart, suggestions moves
- Infos breeding/EV yields, guide de progression

### Mode Notification (toujours actif)
- Toasts contextuels en haut à droite, auto-dismiss 5s
- Alertes : nouveau gym dispo, shiny détecté (permanent + son), EV spot
- "SHINY DÉTECTÉ !!!" = reste affiché + alerte sonore

### Smart Fade
- Overlay plus transparent quand le joueur est en action (mouvement détecté via changements d'écran)
- Redevient visible quand le joueur s'arrête
- "Le joueur oublie qu'il est là jusqu'à ce qu'il en ait besoin"

### Implémentation PyQt6
- `QWidget` frameless + `WA_TranslucentBackground` + `WindowStaysOnTopHint`
- Click-through : `WS_EX_TRANSPARENT` via Win32 `SetWindowLong`
- Zone de grip (barre en haut) non click-through pour drag & drop
- Transition compact↔étendu : `QPropertyAnimation` sur geometry
- Hotkeys globaux : librairie `keyboard` (fonctionne même quand le jeu a le focus)
- Warning si fullscreen exclusif détecté → recommander mode fenêtré/borderless

---

## 4. Fonctionnalités Détaillées

### 3.1 MVP (Itération 1) — Core Features

#### F1 : Détection de localisation en temps réel
- OCR du nom de route/ville affiché en haut de l'écran
- Détection du changement de zone
- Affichage dans l'overlay : nom de la zone actuelle
- **Source** : OCR sur la zone supérieure de la fenêtre PokeMMO

#### F2 : Spawns de la zone courante
- Quand la route change → afficher la liste des Pokémon qui spawn ici
- Pour chaque Pokémon : nom, taux d'apparition (%), niveaux, méthode (herbe, surf, pêche, horde)
- Données séparées par région (Kanto/Johto/Hoenn/Sinnoh/Unova)
- **Source** : PokeMMOZone/PokeMMO-Data + PokeMMO-Tools/pokemmo-data

#### F3 : Détection de combat
- Template matching pour détecter l'entrée en combat (transition d'écran)
- OCR du nom du Pokémon adverse
- Détection automatique si c'est un wild, trainer, ou horde
- **Source** : OpenCV template matching + Tesseract OCR

#### F4 : Assistant de combat — Type Counter
- Quand un combat est détecté : afficher les types du Pokémon adverse
- Calculer et afficher : faiblesses (×2, ×4), résistances (×0.5, ×0.25), immunités (×0)
- Suggérer les meilleurs types d'attaque à utiliser
- Afficher les types d'attaque à éviter
- **Source** : Type chart Gen 5 (18 types)

#### F5 : Overlay transparent
- Fenêtre transparente par-dessus PokeMMO
- Click-through (les clics passent au jeu en dessous)
- Position configurable (coin, côté, etc.)
- Toggle show/hide avec hotkey global (ex: F9)
- Opacité réglable
- **Source** : PyQt6 + Win32 flags

### 3.2 Itération 2 — Enhanced Features

#### F6 : Guide de progression
- Basé sur la localisation actuelle, suggérer ce que le joueur devrait faire
- Walkthrough étape par étape pour chaque région
- Indication du prochain badge/objectif
- Pokémon recommandés à capturer dans la zone
- Niveaux recommandés pour chaque étape

#### F7 : Encounter Counter / Shiny Tracker
- Compteur d'encounters incrémenté automatiquement à chaque combat
- Probabilité de shiny estimée (base 1/30,000 dans PokeMMO)
- Streak tracker pour les chaînes
- Historique des sessions de hunt
- Sweet Scent horde tracking (méthode #1 de shiny hunting)

#### F8 : Pokédex intégré
- Base de données complète des 649 Pokémon (Gen 1-5)
- Stats, types, abilities, moves apprises par niveau
- Localisations par région dans PokeMMO
- Évolutions et conditions d'évolution
- Recherche rapide par nom/numéro/type

#### F9 : Team Analyzer
- Afficher l'analyse de la team actuelle (détectée via OCR du menu)
- Couverture de types de l'équipe
- Faiblesses communes
- Suggestions d'amélioration
- Matchup contre les champions d'arène de la région courante

### 3.3 Itération 3 — Pro Features

#### F10 : IV Calculator
- Estimation des IVs basée sur les stats visibles (OCR)
- Formule Gen 5 : `Stat = ((2×Base + IV + EV/4) × Level / 100 + 5) × Nature`
- Support des natures (+10%/-10%)
- Export des résultats

#### F11 : Breeding Assistant
- Calculateur d'héritage d'IVs
- Egg moves compatibility
- Chaînes de breeding optimales
- Nature inheritance (Everstone)
- Ability inheritance

#### F12 : EV Training Guide
- EV yield par Pokémon
- Meilleurs spots d'EV training par stat et par région
- Tracker d'EVs accumulés
- Power items / Pokérus calculator

#### F13 : GTL Price Checker (si faisable)
- Prix du marché des Pokémon/items (données communautaires)
- Alertes de prix intéressants
- Note : pas d'API officielle GTL, données limitées

#### F14 : Horde Encounter Optimizer
- Meilleurs spots de horde par région
- Pokémon disponibles en horde avec taux
- Sweet Scent PP tracker
- Estimation du temps pour trouver un shiny en horde

### 3.4 Itération 4 — Polish & UX

#### F15 : Thèmes et personnalisation
- Thèmes sombre/clair
- Position de l'overlay configurable par drag
- Modules activables/désactivables
- Raccourcis clavier personnalisables

#### F16 : Système de profils
- Sauvegarde de la progression par personnage
- Multiple profils supportés
- Import/export de données

#### F17 : Notifications
- Alerte quand un Pokémon rare apparaît
- Alerte quand un shiny est détecté (couleur différente)
- Son configurable

---

## 4. Données Requises

### 4.1 Sources de données

| Source | Données | Format | Utilisation |
|--------|---------|--------|-------------|
| **PokeAPI** (dump offline) | 649 Pokémon, stats, types, moves, abilities, evolutions | JSON | Pokédex, type chart, moves |
| **PokeMMOZone/PokeMMO-Data** | Spawns par route, egg moves, rarities, PVP tiers | JSON (16 fichiers) | Spawns, breeding |
| **PokeMMO-Tools/pokemmo-data** | Pokédex multi-région, monsters, moves, items | JSON | Données cross-région |
| **Showdown data** | Type chart, learnsets, competitive data | JSON/TS | Type counters, moves |
| **Veekun** | Base relationnelle complète | CSV/SQLite | Backup/référence |

### 4.2 Base de données locale (SQLite)

Tables principales :
- `pokemon` (id, name, types, base_stats, abilities, gen)
- `moves` (id, name, type, power, accuracy, pp, category, effect)
- `pokemon_moves` (pokemon_id, move_id, method, level)
- `routes` (id, name, region, game_area)
- `spawns` (route_id, pokemon_id, method, rate, level_min, level_max)
- `type_effectiveness` (attacking_type, defending_type, multiplier)
- `evolutions` (from_pokemon_id, to_pokemon_id, method, condition)
- `progression` (region, step, description, location, recommended_level)
- `ev_yields` (pokemon_id, hp, atk, def, spa, spd, spe)

---

## 5. Structure du Projet

```
C:\agents\pokemmo-companion\
├── docs/
│   └── CAHIER_DES_CHARGES.md    ← ce fichier
├── data/
│   ├── pokemon.db               ← SQLite compilée
│   ├── raw/                     ← données brutes (JSON/CSV)
│   └── sprites/                 ← sprites Pokémon (optionnel)
├── src/
│   ├── main.py                  ← point d'entrée
│   ├── capture/
│   │   ├── screen_capture.py    ← BetterCam wrapper
│   │   └── region_detector.py   ← ROI (regions of interest) du jeu
│   ├── detection/
│   │   ├── route_detector.py    ← OCR nom de route
│   │   ├── battle_detector.py   ← détection combat + OCR adversaire
│   │   ├── state_machine.py     ← état du jeu (overworld/combat/menu)
│   │   └── ocr_engine.py        ← wrapper Tesseract
│   ├── data/
│   │   ├── database.py          ← accès SQLite
│   │   ├── pokedex.py           ← requêtes Pokédex
│   │   ├── type_chart.py        ← calculs de types
│   │   ├── spawn_data.py        ← données de spawn
│   │   └── progression.py       ← guide de progression
│   ├── ui/
│   │   ├── overlay.py           ← fenêtre overlay principale
│   │   ├── widgets/
│   │   │   ├── route_panel.py   ← panel info route
│   │   │   ├── battle_panel.py  ← panel assistant combat
│   │   │   ├── encounter_counter.py
│   │   │   ├── pokedex_widget.py
│   │   │   └── team_analyzer.py
│   │   ├── themes.py
│   │   └── hotkeys.py           ← raccourcis globaux
│   └── utils/
│       ├── config.py            ← configuration
│       ├── logger.py
│       └── constants.py
├── tests/
│   ├── test_ocr.py
│   ├── test_detection.py
│   └── test_type_chart.py
├── scripts/
│   ├── build_database.py        ← compile les données en SQLite
│   └── download_data.py         ← télécharge les données brutes
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## 6. Plan d'Itérations

### Itération 1 — MVP (semaine 1)
**Objectif** : App fonctionnelle qui détecte la route et affiche les spawns
1. Setup projet (pyproject.toml, venv, dépendances)
2. Build database SQLite (données Pokémon + spawns 5 régions)
3. Screen capture engine (BetterCam + détection fenêtre PokeMMO)
4. OCR engine (Tesseract, détection nom de route)
5. Overlay basique PyQt6 (transparent, click-through, toggle hotkey)
6. Route panel (affichage spawns de la zone courante)
7. Tests + validation

### Itération 2 — Battle Assistant (semaine 2)
**Objectif** : Détection de combat + counters en temps réel
1. Battle detector (template matching transition combat)
2. OCR nom Pokémon adverse
3. Type counter engine (faiblesses, résistances, suggestions)
4. Battle panel overlay
5. Encounter counter (auto-incrémenté)
6. Shiny tracker basique
7. Tests + validation

### Itération 3 — Guide & Pokédex (semaine 3)
**Objectif** : Guide de progression + Pokédex intégré
1. Progression data (walkthrough par région)
2. Guide panel (prochaine étape basée sur localisation)
3. Pokédex widget (recherche, stats, moves)
4. Team analyzer basique
5. Améliorations OCR (précision, edge cases)
6. Tests + validation

### Itération 4 — Pro Tools (semaine 4)
**Objectif** : IV calc, breeding, EV training, polish
1. IV calculator
2. Breeding assistant
3. EV training guide
4. Horde encounter optimizer
5. Thèmes + personnalisation UI
6. Notifications (rare Pokémon, shiny)
7. Build .exe (PyInstaller)
8. Tests finaux + polish

---

## 7. Référence Compétitive

| Outil | Stars | Ce qu'il fait | Ce qu'il manque |
|-------|-------|---------------|-----------------|
| 3s-PokeMMO-Tool | 20 | Route OCR, Pokédex, team builder, horde search | Pas d'overlay combat, lourd (Electron), pas de guide progression |
| Archetype | 107 | UI overhaul du jeu | Juste cosmétique, pas de données |
| Archetype Counter | 71 | Encounter tracker OCR | Que le compteur, pas de spawns/counters |
| PokeMMO-Companion | 3 | Overlay basique, notes | Pas de détection, pas de données Pokémon |
| ChansEgg | Nouveau | Breeding planner | Que le breeding, pas d'overlay |

**Notre avantage** : Premier all-in-one avec overlay temps réel + détection contextuelle + données complètes.

---

## 8. Risques et Mitigations

| Risque | Impact | Mitigation |
|--------|--------|------------|
| OCR imprécis sur certaines résolutions | Élevé | Template matching en backup, support multi-résolution, mod OCR optimizer |
| PokeMMO update change l'UI | Moyen | Architecture modulaire, ROI configurables, mise à jour rapide |
| Performance overlay impact le jeu | Moyen | Pipeline optimisé < 60ms, capture à intervalle (pas en continu), mode eco |
| Données de spawn obsolètes | Faible | Sources multiples, mise à jour via scripts, contribution communautaire |
| Anti-cheat futur | Faible | Pure lecture d'écran (aucune injection), overlay externe, pas d'input |

---

## 9. Nom du Projet

**Proposition** : `PokeMMO Companion` ou `PokeLens` ou `PokeOverlay`
→ À valider avec ladyd_

---

*Document généré par l'Orchestrateur — synthèse des recherches ScoutBot, DevBot et recherche interne.*
