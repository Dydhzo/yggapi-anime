import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.scraper import YggScraper
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TorrentScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.scraper = YggScraper()
        self.is_running = False
        
    async def scheduled_update(self):
        """Fonction appelée par le scheduler pour effectuer les mises à jour"""
        logger.info(f"Mise à jour programmée démarrée à {datetime.now()}")
        try:
            await self.scraper.update_scrape()
            logger.info(f"Mise à jour programmée terminée à {datetime.now()}")
        except Exception as e:
            logger.error(f"Erreur durant la mise à jour programmée: {e}")
    
    def start(self):
        """Démarrer le scheduler"""
        if not self.is_running:
            # Programmer la tâche de mise à jour
            self.scheduler.add_job(
                self.scheduled_update,
                IntervalTrigger(seconds=settings.update_interval_seconds),
                id='torrent_update',
                name='Tâche de Mise à Jour Torrents',
                replace_existing=True
            )
            
            self.scheduler.start()
            self.is_running = True
            logger.info(f"Scheduler démarré. Les mises à jour se feront toutes les {settings.update_interval_seconds} secondes")
    
    def stop(self):
        """Arrêter le scheduler"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Scheduler arrêté")
    
    def get_next_run_time(self):
        """Obtenir la prochaine heure d'exécution programmée"""
        job = self.scheduler.get_job('torrent_update')
        if job:
            return job.next_run_time
        return None