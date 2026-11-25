"""Ponto de entrada da API. Rode: uvicorn app.main:app --reload  (docs em /docs)."""
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.erros import ErroNegocio, tratar_erro_negocio, tratar_erro_validacao
from app.routers import auth, checklists, templates

app = FastAPI(title="Checklist Guindaste API", version="0.1.0")


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGENS.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Handlers de erro: garantem que toda falha da API sai no formato padrão do contrato
app.add_exception_handler(ErroNegocio, tratar_erro_negocio)
app.add_exception_handler(RequestValidationError, tratar_erro_validacao)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(templates.router, prefix="/api/v1")
app.include_router(checklists.router, prefix="/api/v1")

@app.get("/api/v1/health")
def health():
    return {"status": "ok", "versao": app.version}