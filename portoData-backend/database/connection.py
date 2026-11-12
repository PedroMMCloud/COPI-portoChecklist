"""
Módulo de conexão com o PostgreSQL.

Responsabilidades:
- Criar o mecanismo de conexão (engine) com o banco de dados.
- Configurar a fábrica de sessões (SessionLocal).
- Definir a classe base dos modelos ORM (Base).
- Disponibilizar uma sessão por requisição (get_db).
- Encerrar as conexões do engine quando necessário (close_connection).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import (
    DeclarativeBase, sessionmaker
)

from app.core.config import settings


# Mecanismo de conexão com o PostgreSQL.
# pool_pre_ping=True testa a conexão antes de usá-la, evitando erros
# causados por conexões que foram encerradas pelo servidor.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True
)


# Fábrica de sessões vinculada ao engine.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


class Base(DeclarativeBase):
    """Classe base para todos os modelos ORM."""
    pass


def get_db():
    """
    Disponibiliza uma sessão do banco de dados para cada requisição.

    A sessão é sempre fechada ao final, mesmo em caso de erro.
    Uso típico com FastAPI:

        @router.get("/itens")
        def listar(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


def close_connection():
    """
    Encerra todas as conexões do pool do engine.

    Deve ser chamada quando a aplicação for finalizada
    (por exemplo, no evento de shutdown/lifespan do FastAPI).
    """
    engine.dispose()