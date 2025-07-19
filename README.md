# Orchestrator

MVP agentique sur Raspberry Pi.

## Installation

1. Installez [Poetry](https://python-poetry.org/) puis récupérez les dépendances :

```bash
pip install poetry
poetry install --with dev
```

2. Configurez vos variables d'environnement (ou créez un fichier `.env`) :

```bash
export OPENAI_API_KEY=<votre-clé-OpenAI>
```

## Lancement de l'API FastAPI

```bash
poetry run uvicorn api.main:app --reload
```

## Frontend Next.js

```bash
cd frontend
npm install    # ou pnpm install
npm run dev
```

L'application sera alors disponible sur `http://localhost:3000`.

## Ligne de commande

Vous pouvez exécuter la boucle principale sans serveur :

```bash
poetry run python orchestrator/core_loop.py "Votre objectif"
```

## Tests

L'ensemble de la suite de tests se lance avec :

```bash
poetry run pytest
```

