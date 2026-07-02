# K.IA — Konect Intelligence Artefact

> Assistant vocal personnel holographique propulsé par l'API Claude (Anthropic) ou OpenRouter.

![Status](https://img.shields.io/badge/status-en%20développement-blue?style=flat-square)
![Python](https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square)
![React](https://img.shields.io/badge/react-18-61dafb?style=flat-square)

---

## Aperçu

K.IA est un assistant IA local avec une interface holographique en temps réel. Il combine :

- Une **waveform animée** qui réagit à la voix de l'assistant
- Un **chat streamé** (les réponses apparaissent en temps réel)
- Un **micro vocal** (mode ponctuel ou mode Jarvis toujours actif)
- Une **webcam** que K.IA peut analyser pour commenter ce qu'il voit
- Des **outils intégrés** : météo, itinéraires, recherche web

---

## Structure du projet

```
K.IA/
├── backend/
│   ├── app.py              # Serveur Flask + SocketIO
│   ├── KIA_Online.py       # Moteur IA (Claude / OpenRouter)
│   ├── requirements.txt    # Dépendances Python
│   ├── .env                # Clés API (à créer, ne pas committer)
│   └── .env.example        # Modèle de configuration
│
└── frontend/
    ├── public/
    │   └── index.html
    ├── src/
    │   ├── App.js                      # Application principale
    │   ├── index.js
    │   └── components/
    │       ├── KIAWaveform.js          # Visualiseur holographique Canvas
    │       ├── ChatPanel.js            # Panneau de conversation
    │       └── WebcamPanel.js          # Capture webcam
    └── package.json
```

---

## Installation

### Prérequis

- Python 3.10+
- Node.js 18+
- Un compte [Anthropic](https://console.anthropic.com) (avec crédits) **ou** [OpenRouter](https://openrouter.ai) (gratuit)

---

### Backend

```bash
cd backend

# Créer et activer l'environnement virtuel
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac / Linux

# Installer les dépendances
pip install -r requirements.txt

# Configurer les clés API
cp .env.example .env
# Éditer .env avec tes clés (voir section Configuration)

# Lancer le serveur
python app.py
```

Le serveur démarre sur `http://localhost:5000`.

---

### Frontend

```bash
cd frontend

# Créer l'app React (première fois uniquement)
npx create-react-app .

# Installer Socket.IO
npm install socket.io-client

# Lancer
npm start
```

L'interface s'ouvre sur `http://localhost:3000`.

---

## Configuration `.env`

```env
# Fournisseur IA : "anthropic" ou "openrouter"
PROVIDER=openrouter

# Anthropic (avec crédits sur console.anthropic.com)
ANTHROPIC_API_KEY=sk-ant-...

# OpenRouter (gratuit sur openrouter.ai)
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=openrouter/free

# Google Maps (optionnel, pour les itinéraires)
MAPS_API_KEY=
```

### Modèles OpenRouter gratuits recommandés

| Modèle | Points forts |
|--------|-------------|
| `openrouter/free` | Sélection automatique (recommandé) |
| `meta-llama/llama-3.3-70b-instruct:free` | Polyvalent, bon en français |
| `deepseek/deepseek-v3:free` | Excellent raisonnement |
| `deepseek/deepseek-r1:free` | Meilleur pour les tâches complexes |

---

## Fonctionnalités

### Modes d'interaction

| Mode | Description |
|------|-------------|
| **Assistant** | Tu écris ou maintiens le bouton micro pour parler |
| **Jarvis** | Le micro est toujours actif, K.IA écoute en continu |

### Outils de K.IA

| Outil | Déclenchement |
|-------|--------------|
| Météo | "Quel temps fait-il à Paris ?" |
| Itinéraire | "Combien de temps pour aller à Lyon ?" *(nécessite MAPS_API_KEY)* |
| Recherche web | "Quelles sont les dernières nouvelles sur..." |
| Analyse webcam | Active la caméra, K.IA commente ce qu'il voit |

---

## Événements SocketIO

### Frontend → Backend

| Événement | Données | Description |
|-----------|---------|-------------|
| `send_text_message` | `{ message: string }` | Message texte |
| `send_transcribed_text` | `{ text: string }` | Transcription vocale |
| `send_video_frame` | `{ frame: string }` | Frame webcam (base64) |

### Backend → Frontend

| Événement | Données | Description |
|-----------|---------|-------------|
| `status` | `{ message: string }` | État : `thinking`, `speaking`, `idle`, `error` |
| `receive_text_chunk` | `{ text: string }` | Chunk de réponse streamée |
| `weather_update` | `{ city, temperature, ... }` | Données météo |
| `map_update` | `{ origin, destination, duration, ... }` | Données itinéraire |
| `search_results_update` | `{ query, results }` | Résultats de recherche |

---

## Développement

### Tester le backend sans frontend

```bash
# Dans un second terminal (venv activé)
pip install "python-socketio[client]"
python test_backend.py
```

### Diagnostic de connexion API

```bash
python diagnostic.py
```

---

## Roadmap

- [x] Backend Flask + SocketIO
- [x] Intégration API Claude (streaming)
- [x] Support OpenRouter (modèles gratuits)
- [x] Outils : météo, itinéraires, recherche web
- [x] Frontend React holographique
- [x] Waveform animée Canvas
- [x] Mode Assistant / Mode Jarvis
- [x] Webcam + analyse visuelle
- [ ] Synthèse vocale ElevenLabs (TTS)
- [ ] Widgets météo et carte visuels
- [ ] Historique de conversations persistant
- [ ] Déploiement (Electron / app desktop)

---

## Stack technique

| Couche | Technologies |
|--------|-------------|
| Backend | Python, Flask, Flask-SocketIO, Anthropic SDK |
| IA | Claude (Anthropic) / OpenRouter |
| Frontend | React 18, Canvas API, Web Speech API |
| Communication | SocketIO (WebSocket) |

---

## Licence

Projet personnel — usage libre pour apprentissage et expérimentation.
