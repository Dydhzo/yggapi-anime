# 🎌 YGG API Anime Scraper

**Système de scraping automatique avec interface web moderne** pour récupérer les torrents d'anime (séries et films) depuis YGG API.

![Dashboard Preview](https://img.shields.io/badge/Interface-Moderne-blue?style=for-the-badge)
![Docker](https://img.shields.io/badge/Docker-Ready-green?style=for-the-badge)
![WebSocket](https://img.shields.io/badge/Real--time-WebSocket-orange?style=for-the-badge)

## ✨ Fonctionnalités

### 🤖 **Scraping Automatique**
- ✅ Scraping initial complet de tous les torrents anime existants
- ✅ Mise à jour automatique configurable (par défaut 1h)
- ✅ Récupération des détails complets (hash, description)
- ✅ Évite les doublons automatiquement
- ✅ Retry automatique en cas d'erreur API

### 💾 **Base de Données**
- ✅ PostgreSQL avec 2 tables séparées (séries/films)
- ✅ Tracking intelligent de l'état de synchronisation
- ✅ Stockage de tous les champs disponibles
- ✅ Migration automatique des schémas

### 🎨 **Interface Web Moderne**
- ✅ Dashboard responsive et moderne (dark theme)
- ✅ Statistiques en temps réel avec WebSocket
- ✅ Visualisation des 3 tables (séries, films, état)
- ✅ Contrôles manuels avec confirmations
- ✅ Progress tracking en temps réel
- ✅ Alertes et notifications

### 🐳 **Docker & Production**
- ✅ Configuration Docker complète
- ✅ Docker Compose pour dev et prod
- ✅ Prêt pour Docker Hub
- ✅ Scripts de déploiement automatisés

## 🚀 Installation Rapide

### Option 1: Docker (Recommandé)

```bash
# Cloner le projet
git clone https://github.com/votre-username/yggapi-anime
cd yggapi-anime

# Lancer avec Docker
docker-compose up -d
```

### Option 2: Installation manuelle

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Configurer PostgreSQL et .env
cp .env.example .env
# Modifier .env avec vos paramètres

# 3. Lancer
python -m app.main
```

## ⚙️ Configuration (.env)

```env
# Base de données PostgreSQL
DB_USER=postgres
DB_PASSWORD=votre_mot_de_passe
DB_HOST=localhost
DB_PORT=5432
DB_NAME=yggapi_anime

# Configuration du scraping
UPDATE_INTERVAL_SECONDS=3600    # 1h = 3600s
API_DELAY_SECONDS=1             # Délai entre requêtes
ITEMS_PER_PAGE=100              # 25, 50 ou 100

# Catégories YGG
ANIME_SERIES_CATEGORY=2179      # Séries d'animation
ANIME_FILM_CATEGORY=2178        # Films d'animation
```

## 🎯 Utilisation

### 🌐 **Interface Web**
Accédez à `http://localhost:8000` pour:

- **📊 Dashboard** - Vue d'ensemble avec statistiques
- **📺 Séries Anime** - Parcourir tous les torrents séries
- **🎬 Films Anime** - Parcourir tous les torrents films
- **⚙️ Contrôles** - Déclencher manuellement des vérifications
- **📈 État en temps réel** - WebSocket pour les mises à jour live

### 🔄 **Fonctionnement Automatique**

1. **Premier lancement**: Scraping initial complet (peut prendre plusieurs heures)
2. **Ensuite**: Vérification automatique toutes les heures
3. **Détection**: S'arrête automatiquement au dernier ID connu
4. **Enrichissement**: Récupère hash + description pour chaque torrent

### 🛠️ **Contrôles Manuels**

- **"Vérifier Maintenant"**: Force une vérification des nouveautés
- **"Scraping Initial"**: Re-scrape tout depuis le début (avec confirmation)
- **"Rafraîchir Stats"**: Met à jour les statistiques immédiatement
- **Protection**: Impossible de lancer plusieurs scraping simultanément

## 📊 Structure de la Base de Données

### Table `anime_series` (Séries)
```sql
id, title, seeders, leechers, downloads, size, slug, 
category_id, uploaded_at, link, description, hash, 
updated_at, scraped_at
```

### Table `anime_films` (Films)
```sql
-- Même structure que anime_series
```

### Table `scraping_state` (État)
```sql
id, category, last_known_id, last_scrape_time, 
initial_scrape_completed
```

## 🐳 Docker & Production

### Lancement Simple
```bash
docker-compose up -d
```

### Variables d'environnement Docker
```yaml
services:
  ygg-scraper:
    image: your-username/ygg-anime-scraper:latest
    environment:
      - DB_PASSWORD=your_secure_password
      - UPDATE_INTERVAL_SECONDS=3600
    ports:
      - "80:8000"  # Port 80 pour la production
```

## 📡 API Endpoints

### Interface Web
- `GET /` - Dashboard principal
- `WebSocket /ws` - Updates temps réel

### API REST
- `GET /api/stats` - Statistiques complètes
- `GET /api/series` - Liste des séries (avec pagination)
- `GET /api/films` - Liste des films (avec pagination)
- `GET /api/scraping-state` - État du scraping
- `POST /api/scrape/trigger` - Vérification manuelle
- `POST /api/scrape/initial` - Scraping initial complet
- `GET /health` - Health check
- `GET /api/export/{format}` - Export base (sql/json/csv/all)

## 🔧 Scripts Utiles

```bash
# Logs en temps réel
docker-compose logs -f yggapi-anime

# Redémarrer l'app
docker-compose restart yggapi-anime

# Accéder à la base PostgreSQL (externe)
psql -U postgres -h localhost yggapi_anime

# Backup de la base
pg_dump -U postgres -h localhost yggapi_anime > backup.sql
```

## 📈 Monitoring

### Logs
```bash
tail -f logs/scraper.log
```

### Métriques
- **Torrents totaux** dans le dashboard
- **Dernière synchronisation** par catégorie
- **Prochaine vérification** programmée
- **État des connexions** WebSocket

## 🚨 Dépannage

### Problèmes Courants

**❌ "Database connection failed"**
```bash
# Vérifier que PostgreSQL est démarré
psql -U postgres -h localhost -c "SELECT 1;"
```

**❌ "API rate limiting"**
```bash
# Augmenter le délai dans .env
API_DELAY_SECONDS=2
```

**❌ "WebSocket disconnected"**
- Le navigateur reconnecte automatiquement
- Fallback sur polling HTTP

### Remise à Zéro
```bash
# Supprimer toutes les données
docker-compose down -v
docker-compose up -d
```

## 📄 Licence

MIT License - Libre d'utilisation et modification.

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature
3. Commit vos changements
4. Push vers la branche
5. Créer une Pull Request

## 📞 Support

- **Issues**: Utilisez GitHub Issues
- **Logs**: Toujours joindre les logs en cas de problème
- **Configuration**: Vérifiez votre .env en premier

---

**⭐ Si ce projet vous aide, n'hésitez pas à mettre une étoile !**