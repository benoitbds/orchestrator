# Workflow Développement & Production

## 🎯 Deux Environnements Séparés

### Développement (Hot Reload)
- **Ports:** 3000 (frontend), 8000 (backend)
- **Base de données:** SQLite locale `orchestrator.db`
- **Avantages:** Hot reload, debugging facile, rapide

### Production (Docker)
- **Port:** 9080 (local) ou 443/80 (distant via agent4ba.baq.ovh)
- **Base de données:** SQLite dans volume Docker
- **Avantages:** Isolation, identique à la prod distante

---

## 🚀 Commandes Rapides

### Développement

```bash
# Démarrer l'environnement de dev
./dev.sh

# Accéder au site
open http://localhost:3000

# Arrêter l'environnement de dev
./stop_dev.sh
```

### Production (Docker)

```bash
# Démarrer la production
./prod.sh

# Accéder au site
open http://localhost:9080

# Voir les logs
docker compose logs -f

# Redémarrer un service
docker compose restart app
docker compose restart frontend

# Arrêter tout
docker compose down
```

---

## 📋 Workflow Typique

### 1. Développer une nouvelle fonctionnalité

```bash
# 1. Mode développement
./dev.sh

# 2. Travailler sur le code
#    - Backend: fichiers Python dans api/, orchestrator/, agents/
#    - Frontend: fichiers dans frontend/src/

# 3. Tester en temps réel sur http://localhost:3000

# 4. Quand satisfait, commiter
git add .
git commit -m "feat: nouvelle fonctionnalité"
```

### 2. Tester en environnement Docker (avant mise en prod)

```bash
# 1. Arrêter le dev
./stop_dev.sh

# 2. Lancer Docker
./prod.sh

# 3. Tester sur http://localhost:9080
#    (C'est exactement comme ce que verra l'utilisateur distant)

# 4. Vérifier les logs
docker compose logs -f
```

### 3. Déployer en production

```bash
# 1. Push les changements
git push origin main

# 2. Sur le serveur de prod (si différent)
git pull
docker compose down
docker compose up -d --build

# 3. Vérifier que https://agent4ba.baq.ovh fonctionne
```

---

## 🔧 Configuration des environnements

### Développement
- **Frontend:** `.env.local` avec `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`
- **Backend:** `.env` avec les variables locales

### Production (Docker)
- **Frontend:** `.env.production` avec auto-détection des URLs
- **Backend:** `.env` monté dans le conteneur

---

## 🐛 Debugging

### Backend ne démarre pas
```bash
# Vérifier les ports
lsof -i :8000
lsof -i :6379

# Logs du backend en dev
tail -f orchestrator.log

# Logs Docker
docker compose logs app -f
```

### Frontend ne se connecte pas au backend
```bash
# Vérifier la config
cat frontend/.env.local

# Vérifier dans le navigateur (Console)
# L'URL API devrait être visible dans les requêtes réseau
```

### WebSocket ne fonctionne pas
```bash
# Vérifier les logs Caddy
docker compose logs reverse -f

# Vérifier que le backend supporte WebSocket
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" http://localhost:8000/ws/langgraph/test
```

---

## 📊 Architecture

```
┌─────────────────────────────────────────────────┐
│              DÉVELOPPEMENT                       │
│  Frontend (3000) ←→ Backend (8000) ←→ SQLite    │
│      Next.js           FastAPI                   │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│           PRODUCTION (Docker)                    │
│                                                  │
│   Browser → Caddy (9080) → Frontend (3000)      │
│                  ↓                               │
│              Backend (8000) ←→ Redis (6379)     │
│                  ↓                               │
│               SQLite                             │
└─────────────────────────────────────────────────┘
```

---

## 🔄 Mise à jour des dépendances

### Backend
```bash
cd /home/baq/Dev/orchestrator
poetry update
poetry lock
```

### Frontend
```bash
cd frontend
pnpm update
pnpm install
```

---

## ✅ Checklist avant déploiement

- [ ] Tests passent : `poetry run pytest`
- [ ] Frontend build : `cd frontend && pnpm run build`
- [ ] Docker build : `docker compose build`
- [ ] Test local Docker : `http://localhost:9080`
- [ ] Variables d'environnement à jour
- [ ] Git commit et push
- [ ] Backup de la base de données
