#!/bin/bash
# Arrête les services de développement

echo "🛑 Arrêt de l'environnement de développement..."
echo ""

# Stop backend (uvicorn)
BACKEND_PID=$(lsof -ti:8000)
if [ ! -z "$BACKEND_PID" ]; then
    echo "   Arrêt du backend (PID: $BACKEND_PID)..."
    kill $BACKEND_PID 2>/dev/null
    echo "   ✅ Backend arrêté"
else
    echo "   ℹ️  Backend non actif"
fi

# Stop frontend (Next.js dev)
FRONTEND_PID=$(lsof -ti:3000)
if [ ! -z "$FRONTEND_PID" ]; then
    echo "   Arrêt du frontend (PID: $FRONTEND_PID)..."
    kill $FRONTEND_PID 2>/dev/null
    echo "   ✅ Frontend arrêté"
else
    echo "   ℹ️  Frontend non actif"
fi

echo ""
echo "✨ Environnement de développement arrêté!"
echo ""
