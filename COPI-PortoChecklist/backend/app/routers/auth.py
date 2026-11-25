# app/routers/auth.py
#
# Rota de login. O app envia matrícula + PIN e recebe um token (JWT) para usar
# nas próximas requisições, no header:  Authorization: Bearer <access_token>
#
# Rota completa (com o prefixo registrado no main.py):  POST /api/v1/auth/login

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.erros import ErroNegocio
from app.models import Usuario
from app.security import confere_pin, criar_token

router = APIRouter()


class LoginIn(BaseModel):
    """Corpo esperado na requisição de login."""

    matricula: str
    pin: str


@router.post("/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    # Só considera usuários ativos (quem foi desativado não consegue entrar)
    u = db.scalars(select(Usuario).filter_by(matricula=body.matricula, ativo=True)).first()

    # Mesma mensagem para "usuário não existe" e "PIN errado", para não revelar
    # a quem tenta adivinhar quais matrículas estão cadastradas.
    if not u or not confere_pin(body.pin, u.pin_hash):
        raise ErroNegocio(401, "CREDENCIAIS", "Matrícula ou PIN incorretos")

    return {
        "access_token": criar_token(u),
        "usuario": {"id": u.id, "nome": u.nome, "papel": u.papel},
    }