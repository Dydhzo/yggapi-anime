import httpx
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YggApiClient:
    def __init__(self):
        self.base_url = settings.ygg_api_base_url
        self.delay_seconds = settings.api_delay_seconds
        self.items_per_page = settings.items_per_page
        
    async def fetch_torrents_page(
        self, 
        category_id: int, 
        page: int = 1
    ) -> List[Dict[str, Any]]:
        """Récupérer une page de torrents depuis l'API YGG"""
        url = f"{self.base_url}/torrents"
        params = {
            "page": page,
            "category_id": category_id,
            "order_by": "uploaded_at",
            "per_page": str(self.items_per_page)
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"Page {page} récupérée pour la catégorie {category_id}: {len(data)} éléments")
                
                # Ajouter un délai entre les requêtes pour respecter l'API
                await asyncio.sleep(self.delay_seconds)
                
                return data
                
            except httpx.HTTPError as e:
                logger.error(f"Erreur HTTP lors de la récupération de la page {page} pour la catégorie {category_id}: {e}")
                return []
            except Exception as e:
                logger.error(f"Erreur lors de la récupération de la page {page} pour la catégorie {category_id}: {e}")
                return []
    
    async def fetch_torrent_details(self, torrent_id: int) -> Optional[Dict[str, Any]]:
        """Récupérer les informations détaillées d'un torrent"""
        url = f"{self.base_url}/torrent/{torrent_id}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                
                data = response.json()
                logger.debug(f"Détails récupérés pour le torrent {torrent_id}")
                
                # Ajouter un délai entre les requêtes
                await asyncio.sleep(self.delay_seconds)
                
                return data
                
            except httpx.HTTPError as e:
                logger.error(f"Erreur HTTP lors de la récupération des détails du torrent {torrent_id}: {e}")
                return None
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des détails du torrent {torrent_id}: {e}")
                return None
    
    async def fetch_all_torrents_with_details(
        self, 
        category_id: int, 
        stop_at_id: Optional[int] = None,
        is_initial: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Récupérer tous les torrents d'une catégorie avec leurs détails.
        Si stop_at_id est fourni, s'arrête quand cet ID est rencontré.
        Si is_initial est True, récupère toutes les pages. Sinon, s'arrête à stop_at_id.
        """
        all_torrents = []
        page = 1
        found_stop_id = False
        
        while True:
            # Récupérer la page
            torrents = await self.fetch_torrents_page(category_id, page)
            
            # Si page vide, on a atteint la fin
            if not torrents:
                logger.info(f"Fin des torrents atteinte à la page {page} pour la catégorie {category_id}")
                break
            
            # Traiter chaque torrent
            for torrent in torrents:
                # Vérifier si on doit s'arrêter (pour le mode mise à jour)
                if not is_initial and stop_at_id and torrent['id'] == stop_at_id:
                    found_stop_id = True
                    logger.info(f"ID d'arrêt {stop_at_id} trouvé, arrêt de la récupération")
                    break
                
                # Récupérer les informations détaillées du torrent
                details = await self.fetch_torrent_details(torrent['id'])
                
                if details:
                    # Fusionner les infos de base avec les détails
                    torrent_with_details = {**torrent, **details}
                    all_torrents.append(torrent_with_details)
                else:
                    # Si la récupération des détails a échoué, utiliser les infos de base avec des valeurs nulles
                    torrent['description'] = None
                    torrent['hash'] = None
                    torrent['updated_at'] = torrent.get('uploaded_at')
                    all_torrents.append(torrent)
            
            # Si on a trouvé l'ID d'arrêt, sortir de la boucle
            if found_stop_id:
                break
            
            # Passer à la page suivante
            page += 1
            
            # Logger le progrès toutes les 5 pages
            if page % 5 == 0:
                logger.info(f"Progrès: {len(all_torrents)} torrents récupérés jusqu'à présent (page {page})")
        
        logger.info(f"Total des torrents récupérés pour la catégorie {category_id}: {len(all_torrents)}")
        return all_torrents
    
    async def fetch_new_torrents(
        self, 
        category_id: int, 
        last_known_id: int
    ) -> List[Dict[str, Any]]:
        """Récupérer seulement les nouveaux torrents depuis last_known_id"""
        logger.info(f"Récupération des nouveaux torrents pour la catégorie {category_id} depuis l'ID {last_known_id}")
        return await self.fetch_all_torrents_with_details(
            category_id, 
            stop_at_id=last_known_id,
            is_initial=False
        )