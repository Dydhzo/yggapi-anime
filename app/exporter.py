import json
import csv
import io
import zipfile
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from app.database import SessionLocal, AnimeSeriesModel, AnimeFilmModel, ScrapingState

logger = logging.getLogger(__name__)

class DatabaseExporter:
    """Système d'export complet de la base de données"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def __del__(self):
        self.db.close()
    
    def export_to_sql(self) -> Dict[str, str]:
        """Export complet en SQL pour réimportation PostgreSQL"""
        sql_exports = {}
        
        try:
            # Exporter anime_series
            series_sql = self._generate_table_sql('anime_series', AnimeSeriesModel)
            sql_exports['anime_series.sql'] = series_sql
            
            # Exporter anime_films  
            films_sql = self._generate_table_sql('anime_films', AnimeFilmModel)
            sql_exports['anime_films.sql'] = films_sql
            
            # Exporter scraping_state
            state_sql = self._generate_table_sql('scraping_state', ScrapingState)
            sql_exports['scraping_state.sql'] = state_sql
            
            # Créer un fichier tout-en-un
            complete_sql = f"""-- Export Base de Données YGG Anime Scraper
-- Généré le: {datetime.now().isoformat()}
-- Total Séries: {self.db.query(AnimeSeriesModel).count()}
-- Total Films: {self.db.query(AnimeFilmModel).count()}

-- Supprimer les tables existantes
DROP TABLE IF EXISTS anime_series CASCADE;
DROP TABLE IF EXISTS anime_films CASCADE;
DROP TABLE IF EXISTS scraping_state CASCADE;

{series_sql}

{films_sql}

{state_sql}

-- Mettre à jour les séquences
SELECT setval('anime_series_id_seq', (SELECT MAX(id) FROM anime_series));
SELECT setval('anime_films_id_seq', (SELECT MAX(id) FROM anime_films));
SELECT setval('scraping_state_id_seq', (SELECT MAX(id) FROM scraping_state));

-- Vérifier l'import
SELECT 'Nombre de séries:', COUNT(*) FROM anime_series;
SELECT 'Nombre de films:', COUNT(*) FROM anime_films;
SELECT 'Entrées d\'état:', COUNT(*) FROM scraping_state;
"""
            sql_exports['complete_backup.sql'] = complete_sql
            
            logger.info("Export SQL terminé avec succès")
            return sql_exports
            
        except Exception as e:
            logger.error(f"Erreur durant l'export SQL: {e}")
            raise
    
    def _generate_table_sql(self, table_name: str, model_class) -> str:
        """Génère le SQL pour une table spécifique"""
        # Obtenir la structure de la table
        create_table_sql = f"""
-- Table: {table_name}
CREATE TABLE IF NOT EXISTS {table_name} (
"""
        
        # Ajouter les colonnes basées sur le modèle
        columns = []
        for column in model_class.__table__.columns:
            col_type = str(column.type)
            nullable = "" if column.nullable else " NOT NULL"
            primary = " PRIMARY KEY" if column.primary_key else ""
            columns.append(f"    {column.name} {col_type}{nullable}{primary}")
        
        create_table_sql += ",\n".join(columns)
        create_table_sql += "\n);\n\n"
        
        # Récupérer toutes les données
        records = self.db.query(model_class).all()
        
        # Générer les instructions INSERT
        if records:
            create_table_sql += f"-- Données pour {table_name}\n"
            for record in records:
                values = []
                for column in model_class.__table__.columns:
                    value = getattr(record, column.name)
                    if value is None:
                        values.append("NULL")
                    elif isinstance(value, str):
                        # Échapper les apostrophes
                        escaped = value.replace("'", "''")
                        values.append(f"'{escaped}'")
                    elif isinstance(value, datetime):
                        values.append(f"'{value.isoformat()}'")
                    else:
                        values.append(str(value))
                
                insert_sql = f"INSERT INTO {table_name} VALUES ({', '.join(values)});\n"
                create_table_sql += insert_sql
        
        return create_table_sql
    
    def export_to_json(self) -> Dict[str, str]:
        """Export en JSON pour portabilité"""
        json_exports = {}
        
        try:
            # Export series
            series = self.db.query(AnimeSeriesModel).all()
            series_data = []
            for s in series:
                series_data.append({
                    'id': s.id,
                    'title': s.title,
                    'seeders': s.seeders,
                    'leechers': s.leechers,
                    'downloads': s.downloads,
                    'size': s.size,
                    'slug': s.slug,
                    'category_id': s.category_id,
                    'uploaded_at': s.uploaded_at.isoformat() if s.uploaded_at else None,
                    'link': s.link,
                    'description': s.description,
                    'hash': s.hash,
                    'updated_at': s.updated_at.isoformat() if s.updated_at else None,
                    'scraped_at': s.scraped_at.isoformat() if s.scraped_at else None
                })
            json_exports['anime_series.json'] = json.dumps(series_data, indent=2, ensure_ascii=False)
            
            # Export films
            films = self.db.query(AnimeFilmModel).all()
            films_data = []
            for f in films:
                films_data.append({
                    'id': f.id,
                    'title': f.title,
                    'seeders': f.seeders,
                    'leechers': f.leechers,
                    'downloads': f.downloads,
                    'size': f.size,
                    'slug': f.slug,
                    'category_id': f.category_id,
                    'uploaded_at': f.uploaded_at.isoformat() if f.uploaded_at else None,
                    'link': f.link,
                    'description': f.description,
                    'hash': f.hash,
                    'updated_at': f.updated_at.isoformat() if f.updated_at else None,
                    'scraped_at': f.scraped_at.isoformat() if f.scraped_at else None
                })
            json_exports['anime_films.json'] = json.dumps(films_data, indent=2, ensure_ascii=False)
            
            # Export state
            states = self.db.query(ScrapingState).all()
            states_data = []
            for state in states:
                states_data.append({
                    'id': state.id,
                    'category': state.category,
                    'last_known_id': state.last_known_id,
                    'last_scrape_time': state.last_scrape_time.isoformat() if state.last_scrape_time else None,
                    'initial_scrape_completed': state.initial_scrape_completed
                })
            json_exports['scraping_state.json'] = json.dumps(states_data, indent=2, ensure_ascii=False)
            
            # Metadata
            metadata = {
                'export_date': datetime.now().isoformat(),
                'total_series': len(series_data),
                'total_films': len(films_data),
                'database_version': '1.0',
                'exporter_version': '1.0'
            }
            json_exports['metadata.json'] = json.dumps(metadata, indent=2)
            
            logger.info("Export JSON terminé avec succès")
            return json_exports
            
        except Exception as e:
            logger.error(f"Erreur durant l'export JSON: {e}")
            raise
    
    def export_to_csv(self) -> Dict[str, str]:
        """Export en CSV pour Excel/LibreOffice"""
        csv_exports = {}
        
        try:
            # Export series
            series = self.db.query(AnimeSeriesModel).all()
            series_csv = io.StringIO()
            if series:
                writer = csv.DictWriter(series_csv, fieldnames=[
                    'id', 'title', 'seeders', 'leechers', 'downloads', 'size',
                    'category_id', 'uploaded_at', 'link', 'hash', 'scraped_at'
                ])
                writer.writeheader()
                for s in series:
                    writer.writerow({
                        'id': s.id,
                        'title': s.title,
                        'seeders': s.seeders,
                        'leechers': s.leechers,
                        'downloads': s.downloads,
                        'size': s.size,
                        'category_id': s.category_id,
                        'uploaded_at': s.uploaded_at.isoformat() if s.uploaded_at else '',
                        'link': s.link,
                        'hash': s.hash or '',
                        'scraped_at': s.scraped_at.isoformat() if s.scraped_at else ''
                    })
            csv_exports['anime_series.csv'] = series_csv.getvalue()
            
            # Export films
            films = self.db.query(AnimeFilmModel).all()
            films_csv = io.StringIO()
            if films:
                writer = csv.DictWriter(films_csv, fieldnames=[
                    'id', 'title', 'seeders', 'leechers', 'downloads', 'size',
                    'category_id', 'uploaded_at', 'link', 'hash', 'scraped_at'
                ])
                writer.writeheader()
                for f in films:
                    writer.writerow({
                        'id': f.id,
                        'title': f.title,
                        'seeders': f.seeders,
                        'leechers': f.leechers,
                        'downloads': f.downloads,
                        'size': f.size,
                        'category_id': f.category_id,
                        'uploaded_at': f.uploaded_at.isoformat() if f.uploaded_at else '',
                        'link': f.link,
                        'hash': f.hash or '',
                        'scraped_at': f.scraped_at.isoformat() if f.scraped_at else ''
                    })
            csv_exports['anime_films.csv'] = films_csv.getvalue()
            
            logger.info("Export CSV terminé avec succès")
            return csv_exports
            
        except Exception as e:
            logger.error(f"Erreur durant l'export CSV: {e}")
            raise
    
    def create_export_zip(self, export_format: str = 'all') -> bytes:
        """Crée un ZIP avec tous les exports"""
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add README
            readme = f"""YGG Anime Scraper - Database Export
====================================
Date d'Export: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Format: {export_format.upper()}

Contenu:
--------"""
            
            if export_format in ['sql', 'all']:
                sql_exports = self.export_to_sql()
                for filename, content in sql_exports.items():
                    zip_file.writestr(f"sql/{filename}", content)
                readme += "\n- Fichiers SQL pour import PostgreSQL"
                
            if export_format in ['json', 'all']:
                json_exports = self.export_to_json()
                for filename, content in json_exports.items():
                    zip_file.writestr(f"json/{filename}", content)
                readme += "\n- Fichiers JSON pour traitement de données"
                
            if export_format in ['csv', 'all']:
                csv_exports = self.export_to_csv()
                for filename, content in csv_exports.items():
                    zip_file.writestr(f"csv/{filename}", content)
                readme += "\n- Fichiers CSV pour Excel/LibreOffice"
            
            readme += """

Comment Importer:
-----------------
SQL (PostgreSQL):
  psql -U postgres yggapi_anime < sql/complete_backup.sql

JSON (Python):
  import json
  with open('json/anime_series.json') as f:
      data = json.load(f)

CSV (Excel):
  Open csv/anime_series.csv directly in Excel

For support: github.com/your-repo
"""
            
            zip_file.writestr("README.txt", readme)
        
        zip_buffer.seek(0)
        return zip_buffer.read()