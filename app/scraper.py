import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
from sqlalchemy.orm import Session
from dateutil import parser as date_parser

from app.database import (
    SessionLocal, AnimeSeriesModel, AnimeFilmModel, 
    ScrapingState, init_database
)
from app.ygg_api_client import YggApiClient
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YggScraper:
    def __init__(self):
        self.client = YggApiClient()
        self.series_category = settings.anime_series_category
        self.film_category = settings.anime_film_category
        
    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """Convertir une chaîne datetime en objet datetime"""
        if not date_str:
            return None
        try:
            return date_parser.parse(date_str)
        except Exception as e:
            logger.error(f"Erreur lors du parsing de la date {date_str}: {e}")
            return None
    
    def _save_torrents_to_db(
        self, 
        torrents: List[Dict[str, Any]], 
        category_type: str,
        db: Session
    ):
        """Sauvegarder les torrents en base de données"""
        Model = AnimeSeriesModel if category_type == 'series' else AnimeFilmModel
        
        saved_count = 0
        updated_count = 0
        
        for torrent_data in torrents:
            try:
                # Vérifier si le torrent existe déjà
                existing = db.query(Model).filter_by(id=torrent_data['id']).first()
                
                torrent_obj = {
                    'id': torrent_data['id'],
                    'title': torrent_data['title'],
                    'seeders': torrent_data['seeders'],
                    'leechers': torrent_data['leechers'],
                    'downloads': torrent_data.get('downloads'),
                    'size': torrent_data['size'],
                    'slug': torrent_data.get('slug', ''),
                    'category_id': torrent_data['category_id'],
                    'uploaded_at': self._parse_datetime(torrent_data['uploaded_at']),
                    'link': torrent_data['link'],
                    'description': torrent_data.get('description'),
                    'hash': torrent_data.get('hash'),
                    'updated_at': self._parse_datetime(torrent_data.get('updated_at')),
                    'scraped_at': datetime.now()
                }
                
                if existing:
                    # Mettre à jour le torrent existant
                    for key, value in torrent_obj.items():
                        setattr(existing, key, value)
                    updated_count += 1
                else:
                    # Créer un nouveau torrent
                    new_torrent = Model(**torrent_obj)
                    db.add(new_torrent)
                    saved_count += 1
                    
            except Exception as e:
                logger.error(f"Erreur lors de la sauvegarde du torrent {torrent_data.get('id')}: {e}")
                continue
        
        try:
            db.commit()
            logger.info(f"{saved_count} nouveaux torrents sauvegardés, {updated_count} torrents existants mis à jour pour {category_type}")
        except Exception as e:
            db.rollback()
            logger.error(f"Erreur lors du commit des torrents: {e}")
            raise
    
    def _get_last_known_id(self, category: str, db: Session) -> Optional[int]:
        """Obtenir le dernier ID de torrent connu pour une catégorie"""
        state = db.query(ScrapingState).filter_by(category=category).first()
        return state.last_known_id if state else None
    
    def _update_scraping_state(
        self, 
        category: str, 
        last_id: int, 
        db: Session,
        mark_initial_complete: bool = False
    ):
        """Mettre à jour l'état du scraping avec le dernier ID connu"""
        state = db.query(ScrapingState).filter_by(category=category).first()
        if state:
            state.last_known_id = last_id
            state.last_scrape_time = datetime.now()
            if mark_initial_complete:
                state.initial_scrape_completed = True
        else:
            state = ScrapingState(
                category=category,
                last_known_id=last_id,
                last_scrape_time=datetime.now(),
                initial_scrape_completed=mark_initial_complete
            )
            db.add(state)
        
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Erreur lors de la mise à jour de l'état du scraping: {e}")
    
    async def initial_scrape(self):
        """Effectuer le scraping initial complet de tous les torrents"""
        logger.info("Démarrage du scraping initial...")
        db = SessionLocal()
        
        try:
            # Vérifier si le scraping initial est déjà terminé
            series_state = db.query(ScrapingState).filter_by(category='series').first()
            films_state = db.query(ScrapingState).filter_by(category='films').first()
            
            # Scraper les séries anime si pas déjà fait
            if not series_state or not series_state.initial_scrape_completed:
                logger.info(f"Démarrage du scraping initial pour les séries anime (catégorie {self.series_category})")
                series_torrents = await self.client.fetch_all_torrents_with_details(
                    self.series_category,
                    is_initial=True
                )
                
                if series_torrents:
                    self._save_torrents_to_db(series_torrents, 'series', db)
                    # Obtenir l'ID le plus élevé (torrent le plus récent)
                    max_id = max(t['id'] for t in series_torrents)
                    self._update_scraping_state('series', max_id, db, mark_initial_complete=True)
                    logger.info(f"Scraping initial terminé pour les séries anime. Total: {len(series_torrents)} torrents")
            else:
                logger.info("Scraping initial déjà terminé pour les séries anime, ignorer...")
            
            # Scraper les films anime si pas déjà fait
            if not films_state or not films_state.initial_scrape_completed:
                logger.info(f"Démarrage du scraping initial pour les films anime (catégorie {self.film_category})")
                film_torrents = await self.client.fetch_all_torrents_with_details(
                    self.film_category,
                    is_initial=True
                )
                
                if film_torrents:
                    self._save_torrents_to_db(film_torrents, 'films', db)
                    # Obtenir l'ID le plus élevé (torrent le plus récent)
                    max_id = max(t['id'] for t in film_torrents)
                    self._update_scraping_state('films', max_id, db, mark_initial_complete=True)
                    logger.info(f"Scraping initial terminé pour les films anime. Total: {len(film_torrents)} torrents")
            else:
                logger.info("Scraping initial déjà terminé pour les films anime, ignorer...")
                
            logger.info("Processus de scraping initial terminé !")
            
        finally:
            db.close()
    
    async def update_scrape(self):
        """Effectuer le scraping de mise à jour pour obtenir les nouveaux torrents depuis la dernière vérification"""
        logger.info("Démarrage du scraping de mise à jour...")
        db = SessionLocal()
        
        try:
            # Mettre à jour les séries anime
            series_last_id = self._get_last_known_id('series', db)
            if series_last_id:
                logger.info(f"Récupération des nouvelles séries anime depuis l'ID {series_last_id}")
                new_series = await self.client.fetch_new_torrents(
                    self.series_category, 
                    series_last_id
                )
                
                if new_series:
                    self._save_torrents_to_db(new_series, 'series', db)
                    # Mettre à jour avec le nouvel ID le plus élevé
                    max_id = max(t['id'] for t in new_series)
                    if max_id > series_last_id:
                        self._update_scraping_state('series', max_id, db)
                    logger.info(f"{len(new_series)} nouveaux torrents de séries anime trouvés")
                else:
                    logger.info("Aucun nouveau torrent de série anime trouvé")
            
            # Mettre à jour les films anime
            films_last_id = self._get_last_known_id('films', db)
            if films_last_id:
                logger.info(f"Récupération des nouveaux films anime depuis l'ID {films_last_id}")
                new_films = await self.client.fetch_new_torrents(
                    self.film_category,
                    films_last_id
                )
                
                if new_films:
                    self._save_torrents_to_db(new_films, 'films', db)
                    # Mettre à jour avec le nouvel ID le plus élevé
                    max_id = max(t['id'] for t in new_films)
                    if max_id > films_last_id:
                        self._update_scraping_state('films', max_id, db)
                    logger.info(f"{len(new_films)} nouveaux torrents de films anime trouvés")
                else:
                    logger.info("Aucun nouveau torrent de film anime trouvé")
                    
            logger.info("Scraping de mise à jour terminé !")
            
        finally:
            db.close()
    
    async def run_once(self):
        """Exécuter le scraper une fois (pour test ou exécution manuelle)"""
        db = SessionLocal()
        try:
            # Vérifier si le scraping initial est nécessaire
            series_state = db.query(ScrapingState).filter_by(category='series').first()
            films_state = db.query(ScrapingState).filter_by(category='films').first()
            
            if (not series_state or not series_state.initial_scrape_completed or
                not films_state or not films_state.initial_scrape_completed):
                await self.initial_scrape()
            else:
                await self.update_scrape()
        finally:
            db.close()