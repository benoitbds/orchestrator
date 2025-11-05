# 🚀 Quick Start Guide

## Installation initiale

```bash
# 1. Backend
poetry install --with dev

# 2. Frontend
cd frontend
pnpm install
```

## 🎯 Utilisation

### Mode Développement (Recommandé pour coder)

```bash
./dev.sh
```

**Accès:** http://localhost:3000

**Avantages:**
- ✅ Hot reload frontend et backend
- ✅ Debugging facile
- ✅ Modifications visibles instantanément
- ✅ Logs visibles dans le terminal

**Arrêter:**
```bash
./stop_dev.sh
```

---

### Mode Production (Docker)

```bash
./prod.sh
```

**Accès:** 
- Local: http://localhost:9080
- Distant: https://agent4ba.baq.ovh

**Avantages:**
- ✅ Environnement identique à la production
- ✅ Isolation complète
- ✅ Tester avant le déploiement réel

**Arrêter:**
```bash
docker compose down
```

---

## 📝 Workflow quotidien

### 1. Développer
```bash
./dev.sh
# Travailler sur le code
# Tester sur http://localhost:3000
./stop_dev.sh
```

### 2. Valider
```bash
./prod.sh
# Tester sur http://localhost:9080
# Vérifier que tout fonctionne comme en production
```

### 3. Déployer
```bash
git add .
git commit -m "feat: ma nouvelle fonctionnalité"
git push
```

---

## 🔧 Commandes utiles

### Développement
```bash
# Backend seul
./run_back.sh

# Frontend seul
cd frontend && pnpm run dev

# Tests backend
poetry run pytest

# Linting
poetry run ruff check
cd frontend && pnpm run lint
```

### Production (Docker)
```bash
# Voir les logs
docker compose logs -f

# Logs d'un service spécifique
docker compose logs -f app
docker compose logs -f frontend
docker compose logs -f reverse

# Redémarrer un service
docker compose restart app

# Reconstruire après changements
docker compose up -d --build
```

---

## 🐛 Problèmes fréquents

### Port déjà utilisé
```bash
# Trouver quel process utilise le port 8000
lsof -i :8000

# Arrêter le dev avant de lancer Docker
./stop_dev.sh
```

### Docker ne build pas
```bash
# Nettoyer et reconstruire
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

### Frontend ne se connecte pas au backend
```bash
# Vérifier la config dev
cat frontend/.env.local

# Devrait contenir:
# NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## 📚 Documentation complète

Voir [WORKFLOW.md](./WORKFLOW.md) pour plus de détails sur :
- Architecture
- Debugging avancé
- Mise à jour des dépendances
- Checklist déploiement
