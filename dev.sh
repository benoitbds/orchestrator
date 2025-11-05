#!/bin/bash
# Script de développement - Lance backend et frontend en mode dev

echo "🚀 Démarrage de l'environnement de développement..."
echo ""

# Check if backend is already running
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "✅ Backend déjà en cours d'exécution sur le port 8000"
else
    echo "📦 Démarrage du backend..."
    cd /home/baq/Dev/orchestrator
    ./run_back.sh &
    BACKEND_PID=$!
    echo "   Backend PID: $BACKEND_PID"
    sleep 2
fi

# Check if frontend is already running
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null ; then
    echo "✅ Frontend déjà en cours d'exécution sur le port 3000"
else
    echo "🎨 Démarrage du frontend..."
    cd /home/baq/Dev/orchestrator/frontend
    pnpm run dev &
    FRONTEND_PID=$!
    echo "   Frontend PID: $FRONTEND_PID"
fi

echo ""
echo "✨ Environnement de développement prêt!"
echo ""
echo "📍 Accès:"
echo "   - Frontend dev:  http://localhost:3000"
echo "   - Backend API:   http://localhost:8000"
echo "   - API Docs:      http://localhost:8000/docs"
echo ""
echo "💡 Pour arrêter: ./stop_dev.sh"
echo ""
