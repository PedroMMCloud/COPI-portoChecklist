"""
Execução:

    export DATABASE_URL="postgresql+psycopg2://usuario:senha@localhost:5432/portdata"
    uvicorn main:app --reload

Documentação:

    Swagger UI -> http://localhost:8000/docs
    ReDoc      -> http://localhost:8000/redoc
    OpenAPI    -> http://localhost:8000/openapi.json
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

import app.models.models # noqa: F401  (registra os modelos na Base antes de criar as tabelas)
from app.database.database import Base, engine
from app.checklist.checklist import checklists

API_TITULO = "PortData API"
API_VERSAO = "1.0.0"
API_DESCRICAO = """
API para gerenciamento de **checklists de inspeção portuária** de guindastes.

Principais recursos:

* Criação e edição de checklists, inclusive como **rascunho**.
* Registro dos **23 itens de inspeção** (SIM, NAO ou NAO_APLICAVEL), com identificação de itens críticos.
* **Verificação** de pendências, horímetros e reprovação em item crítico.
* **Finalização** da checklist somente quando todos os requisitos forem atendidos.
"""

TAGS_METADATA = [
    {
        "name": "Checklists",
        "description": "Criação, consulta, edição, verificação, finalização e exclusão de checklists.",
    },
    {
        "name": "Sistema",
        "description": "Rotas de verificação do funcionamento da aplicação.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    
    Base.metadata.create_all(bind=engine)
    yield
"""
    Na inicialização, cria as tabelas que ainda não existem.
    Em produção, prefira migrações com Alembic e remova esta linha.
"""


app = FastAPI(
    title=API_TITULO,
    description=API_DESCRICAO,
    version=API_VERSAO,
    openapi_tags=TAGS_METADATA,
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.include_router(checklists.router)



@app.get("/", tags=["Sistema"], summary="Verificar se o servidor está funcionando")
def raiz() -> dict:
    return {
        "mensagem": f"{API_TITULO} em funcionamento.",
        "versao": API_VERSAO,
        "documentacao": {"swagger": "/docs", "redoc": "/redoc"},
    }


@app.get("/health", tags=["Sistema"], summary="Verificar a disponibilidade da aplicação")
def health() -> dict:
    """Verificação básica de disponibilidade (não consulta o banco de dados)."""
    return {"status": "ok", "versao": API_VERSAO}