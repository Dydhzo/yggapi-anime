#!/usr/bin/env python3
"""
Script de lancement simple pour YGG API Anime Scraper
Usage: python start.py
"""

import sys
import os

# Ajouter le répertoire courant au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    try:
        # Vérifier que PostgreSQL est configuré
        from app.config import settings
        print(f"🔧 Configuration chargée:")
        print(f"   Base de données: {settings.db_name}@{settings.db_host}:{settings.db_port}")
        print(f"   Utilisateur: {settings.db_user}")
        print(f"   Intervalle de mise à jour: {settings.update_interval_seconds}s")
        print()
        
        # Lancer l'application
        print("🚀 Lancement de YGG API Anime Scraper...")
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
            log_level="info"
        )
        
    except Exception as e:
        print(f"❌ Erreur de lancement: {e}")
        print("\n💡 Vérifiez votre fichier .env et que PostgreSQL est démarré")
        sys.exit(1)