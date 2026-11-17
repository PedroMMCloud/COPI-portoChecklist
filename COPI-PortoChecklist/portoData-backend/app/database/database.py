"""Configuração da conexão com o PostgreSQL usando SQLAlchemy 2.x.

Uso nos demais módulos:
    from database import Base, engine, SessionLocal, get_db

Você precisa de um driver PostgreSQL instalado, por exemplo
pip install sqlalchemy psycopg2-binary. A URL deve seguir o 
formato postgresql+psycopg2://usuario:senha@localhost:5432/meu_banco.

Para criar as tabelas a partir dos modelos, importe os modelos 
e rode Base.metadata.create_all(bind=engine). Em projetos 
maiores, o mais comum é usar o Alembic para as migrações.
"""

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Opcional: carrega variáveis de um arquivo .env, se python-dotenv estiver instalado.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Exemplo de URL: postgresql+psycopg2://usuario:senha@localhost:5432/meu_banco
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "A variável de ambiente DATABASE_URL não está definida. "
        "Exemplo: postgresql+psycopg2://usuario:senha@localhost:5432/meu_banco"
    )

# Mecanismo de conexão com o banco.
# pool_pre_ping=True testa a conexão antes de usá-la, evitando erros com conexões expiradas.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

# Fábrica de sessões para comunicação com o banco.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Classe-base para todos os modelos ORM."""


def get_db() -> Generator[Session, None, None]:
    """
    Fornece uma sessão do banco para cada requisição e garante seu fechamento.

    Exemplo com FastAPI:

        @app.get("/itens")
        def listar(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()