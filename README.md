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

## Import de documents

Agent 4 BA peut exploiter des documents pour enrichir ses réponses. Vous pouvez
uploader un fichier sur un projet via l'API :

```bash
curl -F "file=@rapport.pdf" http://localhost:8000/projects/1/documents
```

Les textes sont découpés et vectorisés (via OpenAI) afin de permettre la
recherche sémantique. Une requête d'exemple :

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"query": "Que dit le rapport sur les ventes ?"}' \
  http://localhost:8000/projects/1/search
```

### Prérequis

- `OPENAI_API_KEY` doit être défini pour la génération des embeddings.
- Pour l'OCR d'images, installez Tesseract : `sudo apt-get install tesseract-ocr`.

### Limites (MVP)

- Types supportés : PDF et TXT (DOCX fonctionne, mais pas le format `.doc`).
- L'OCR d'images dépend de la qualité de l'image et de la présence de
  Tesseract. Sur Raspberry Pi, l'installation peut être lourde ; vous pouvez la
  reporter.
- Les fichiers supérieurs à ~5 Mo peuvent être tronqués ou résumés.

L'objectif est d'étendre progressivement à d'autres formats (DOCX, images) une
fois la base validée.

## Tests

L'ensemble de la suite de tests se lance avec :

```bash
poetry run pytest
```

=======

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

