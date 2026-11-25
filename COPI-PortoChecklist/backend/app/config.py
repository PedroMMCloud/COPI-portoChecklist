"""Configuração lida de variáveis de ambiente (.env). Nada de segredo no código."""
import os
from pathlib import Path


class Settings:
    # SQLite na demo (arquivo local ./checklist.db); trocar por postgresql+psycopg://... depois, sem mudar os modelos.
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./checklist.db")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "troque-esta-chave-na-demo")
    JWT_EXPIRA_HORAS: int = int(os.getenv("JWT_EXPIRA_HORAS", "12"))
    BASE_DIR = Path(__file__).resolve().parents[2]
    # Pasta dos seeds: local = ../dados/seed ; no Docker = /dados/seed
    SEED_DIR: str = os.getenv("SEED_DIR", str(BASE_DIR / "dados" / "seed"))
    CORS_ORIGENS: str = os.getenv("CORS_ORIGENS", "*")

settings = Settings()
