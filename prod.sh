#!/bin/bash
# Script de production - Lance Docker Compose

echo "🚀 Démarrage de l'environnement de production (Docker)..."
echo ""

cd /home/baq/Dev/orchestrator

# Check if .env.docker exists
if [ ! -f .env.docker ]; then
    echo "⚠️  Fichier .env.docker manquant!"
    echo "   Copiez .env.docker.example vers .env.docker et configurez-le"
    echo ""
    echo "   cp .env.docker.example .env.docker"
    echo "   nano .env.docker"
    echo ""
    exit 1
fi

# Build and start
docker compose up -d --build

echo ""
echo "✨ Environnement de production démarré!"
echo ""
echo "📍 Accès:"
echo "   - Local:   http://localhost:9080"
echo "   - Distant: https://agent4ba.baq.ovh"
echo ""
echo "🔍 Commandes utiles:"
echo "   docker compose logs -f          # Voir les logs"
echo "   docker compose ps               # Voir les conteneurs"
echo "   docker compose down             # Arrêter tout"
echo "   docker compose restart <service> # Redémarrer un service"
echo ""
