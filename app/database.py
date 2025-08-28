from sqlalchemy import create_engine, Column, Integer, String, DateTime, BigInteger, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Créer le moteur de base de données
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=False
)

# Créer l'usine de sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Créer la classe de base pour les modèles
Base = declarative_base()

class AnimeSeriesModel(Base):
    __tablename__ = "anime_series"
    
    id = Column(BigInteger, primary_key=True, index=True)
    title = Column(String, nullable=False)
    seeders = Column(Integer, default=0)
    leechers = Column(Integer, default=0)
    downloads = Column(Integer, nullable=True)
    size = Column(BigInteger, nullable=False)
    slug = Column(String, nullable=True)
    category_id = Column(Integer, nullable=False)
    uploaded_at = Column(DateTime, nullable=False)
    link = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    hash = Column(String, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    scraped_at = Column(DateTime, nullable=False)
    
    def __repr__(self):
        return f"<AnimeSeries(id={self.id}, title={self.title[:50]})>"

class AnimeFilmModel(Base):
    __tablename__ = "anime_films"
    
    id = Column(BigInteger, primary_key=True, index=True)
    title = Column(String, nullable=False)
    seeders = Column(Integer, default=0)
    leechers = Column(Integer, default=0)
    downloads = Column(Integer, nullable=True)
    size = Column(BigInteger, nullable=False)
    slug = Column(String, nullable=True)
    category_id = Column(Integer, nullable=False)
    uploaded_at = Column(DateTime, nullable=False)
    link = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    hash = Column(String, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    scraped_at = Column(DateTime, nullable=False)
    
    def __repr__(self):
        return f"<AnimeFilm(id={self.id}, title={self.title[:50]})>"

class ScrapingState(Base):
    """Table pour suivre l'état du scraping et les derniers IDs connus"""
    __tablename__ = "scraping_state"
    
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, unique=True, nullable=False)  # 'series' ou 'films'
    last_known_id = Column(BigInteger, nullable=True)
    last_scrape_time = Column(DateTime, nullable=True)
    initial_scrape_completed = Column(Boolean, default=False)
    
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_database():
    """Initialiser les tables de la base de données"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Tables de base de données créées avec succès")
        
        # Initialiser l'état de scraping s'il n'existe pas
        db = SessionLocal()
        try:
            for category in ['series', 'films']:
                existing = db.query(ScrapingState).filter_by(category=category).first()
                if not existing:
                    state = ScrapingState(
                        category=category,
                        last_known_id=None,
                        initial_scrape_completed=False
                    )
                    db.add(state)
            db.commit()
            logger.info("État de scraping initialisé")
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de la base de données: {e}")
        raise