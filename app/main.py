import asyncio
import logging
import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Query, WebSocket, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.websockets import WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import init_database, get_db, AnimeSeriesModel, AnimeFilmModel, ScrapingState
from app.scraper import YggScraper
from app.scheduler import TorrentScheduler
from app.config import settings
from app.exporter import DatabaseExporter

# Lire la version depuis le fichier VERSION
def get_version():
    try:
        with open('VERSION', 'r') as f:
            return f.read().strip()
    except:
        return '1.0.0'

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Instance globale du scheduler
scheduler = TorrentScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gère le cycle de vie de l'application"""
    # Démarrage
    logger.info("Démarrage de YGG API Anime Scraper...")
    
    # Initialiser la base de données
    init_database()
    
    # Effectuer un scraping initial si nécessaire
    scraper = YggScraper()
    await scraper.run_once()
    
    # Démarrer le scheduler pour les mises à jour périodiques
    scheduler.start()
    
    logger.info("Application démarrée avec succès !")
    
    yield
    
    # Arrêt
    logger.info("Arrêt en cours...")
    scheduler.stop()
    logger.info("Arrêt de l'application terminé")

# Créer l'application FastAPI
app = FastAPI(
    title="YGG API Anime Scraper",
    description="Scraper pour torrents anime depuis YGG API avec interface web",
    version=get_version(),
    lifespan=lifespan
)

# Monter les fichiers statiques et templates
app.mount("/static", StaticFiles(directory="src/static"), name="static")
templates = Jinja2Templates(directory="src/templates")

# Gestionnaire de connexions WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connecté. Total connexions: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket déconnecté. Total connexions: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: Dict[str, Any]):
        message_str = json.dumps(message)
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception:
                disconnected.append(connection)
        
        # Supprimer les connexions déconnectées
        for connection in disconnected:
            if connection in self.active_connections:
                self.active_connections.remove(connection)

manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Page principale du dashboard"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "version": get_version()
    })

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Endpoint WebSocket pour les mises à jour temps réel"""
    await manager.connect(websocket)
    try:
        while True:
            # Maintenir la connexion active
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/api/info")
async def api_info():
    """Endpoint d'informations API"""
    return {
        "service": "YGG API Anime Scraper",
        "version": get_version(),
        "status": "running",
        "scheduler_active": scheduler.is_running,
        "next_update": scheduler.get_next_run_time().isoformat() if scheduler.get_next_run_time() else None
    }

@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Obtenir les statistiques de la base de données"""
    series_count = db.query(func.count(AnimeSeriesModel.id)).scalar()
    films_count = db.query(func.count(AnimeFilmModel.id)).scalar()
    
    series_state = db.query(ScrapingState).filter_by(category='series').first()
    films_state = db.query(ScrapingState).filter_by(category='films').first()
    
    return {
        "anime_series": {
            "total_count": series_count,
            "last_known_id": series_state.last_known_id if series_state else None,
            "last_scrape_time": series_state.last_scrape_time.isoformat() if series_state and series_state.last_scrape_time else None,
            "initial_scrape_completed": series_state.initial_scrape_completed if series_state else False
        },
        "anime_films": {
            "total_count": films_count,
            "last_known_id": films_state.last_known_id if films_state else None,
            "last_scrape_time": films_state.last_scrape_time.isoformat() if films_state and films_state.last_scrape_time else None,
            "initial_scrape_completed": films_state.initial_scrape_completed if films_state else False
        },
        "scheduler": {
            "is_running": scheduler.is_running,
            "next_run": scheduler.get_next_run_time().isoformat() if scheduler.get_next_run_time() else None,
            "update_interval_seconds": settings.update_interval_seconds
        }
    }

@app.get("/api/series")
async def get_series(
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Obtenir les torrents de séries anime"""
    torrents = db.query(AnimeSeriesModel)\
        .order_by(AnimeSeriesModel.uploaded_at.desc())\
        .limit(limit)\
        .offset(offset)\
        .all()
    
    total = db.query(func.count(AnimeSeriesModel.id)).scalar()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [
            {
                "id": t.id,
                "title": t.title,
                "seeders": t.seeders,
                "leechers": t.leechers,
                "downloads": t.downloads,
                "size": t.size,
                "uploaded_at": t.uploaded_at.isoformat() if t.uploaded_at else None,
                "link": t.link,
                "hash": t.hash
            } for t in torrents
        ]
    }

@app.get("/api/films")
async def get_films(
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Obtenir les torrents de films anime"""
    torrents = db.query(AnimeFilmModel)\
        .order_by(AnimeFilmModel.uploaded_at.desc())\
        .limit(limit)\
        .offset(offset)\
        .all()
    
    total = db.query(func.count(AnimeFilmModel.id)).scalar()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [
            {
                "id": t.id,
                "title": t.title,
                "seeders": t.seeders,
                "leechers": t.leechers,
                "downloads": t.downloads,
                "size": t.size,
                "uploaded_at": t.uploaded_at.isoformat() if t.uploaded_at else None,
                "link": t.link,
                "hash": t.hash
            } for t in torrents
        ]
    }

@app.post("/api/scrape/trigger")
async def trigger_scrape():
    """Déclencher manuellement une mise à jour de scraping"""
    try:
        scraper = YggScraper()
        await scraper.update_scrape()
        return {"message": "Scraping déclenché avec succès", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Erreur lors du déclenchement du scraping: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scrape/initial")
async def trigger_initial_scrape():
    """Déclencher manuellement le scraping initial complet (utiliser avec prudence !)"""
    try:
        scraper = YggScraper()
        await scraper.initial_scrape()
        return {"message": "Scraping initial déclenché avec succès", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Erreur lors du déclenchement du scraping initial: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scraping-state")
async def get_scraping_state(db: Session = Depends(get_db)):
    """Obtenir les informations d'état du scraping"""
    states = db.query(ScrapingState).all()
    return [
        {
            "id": state.id,
            "category": state.category,
            "last_known_id": state.last_known_id,
            "last_scrape_time": state.last_scrape_time,
            "initial_scrape_completed": state.initial_scrape_completed
        } for state in states
    ]

@app.get("/api/export/{format}")
async def export_database(format: str):
    """Exporter la base de données dans le format spécifié"""
    from fastapi.responses import Response
    
    if format not in ['sql', 'json', 'csv', 'all']:
        raise HTTPException(status_code=400, detail="Format invalide. Utiliser: sql, json, csv, ou all")
    
    try:
        exporter = DatabaseExporter()
        
        # Créer le fichier ZIP avec les exports
        zip_data = exporter.create_export_zip(format)
        
        # Générer le nom de fichier avec timestamp
        filename = f"ygg_anime_export_{format}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        
        return Response(
            content=zip_data,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de l'export de la base de données: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Endpoint de vérification de santé"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )