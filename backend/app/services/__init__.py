# EuroGoal Predictor - Data Services
from app.services.football_data import FootballDataClient
from app.services.scraper import UnderstatScraper
from app.services.sync import DataSyncService

__all__ = ["FootballDataClient", "UnderstatScraper", "DataSyncService"]
