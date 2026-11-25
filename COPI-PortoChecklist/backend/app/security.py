# app/security.py
#
# Segurança da API, em três partes:
#   1. HASH   - guardar e conferir o PIN do usuário sem salvar o PIN em texto puro
#   2. TOKEN  - gerar o JWT que o app envia em toda requisição depois do login
#   3. DEPENDÊNCIAS - funções que as rotas usam para exigir login ou perfil ADMIN
#
# Dependências: pip install argon2-cffi pyjwt
# Precisa em settings: JWT_SECRET e JWT_EXPIRA_HORAS
#
# Exemplo de uso numa rota:
#
#     @router.get("/checklists")
#     def listar(usuario: Usuario = Depends(usuario_atual)): ...      # qualquer logado
#
#     @router.post("/locais")
#     def criar(admin: Usuario = Depends(exige_admin)): ...           # só ADMIN

from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.erros import ErroNegocio
from app.models import Usuario

_ph = PasswordHasher()
_bearer = HTTPBearer(auto_error=False)  # auto_error=False: nós devolvemos 401 no formato do contrato


# ---------------------------------------------------------------------------
# 1. HASH DO PIN
# ---------------------------------------------------------------------------
def hash_pin(pin: str) -> str:
    """Transforma o PIN em hash argon2 (é isso que vai para a coluna pin_hash)."""
    return _ph.hash(pin)


def confere_pin(pin: str, hash_guardado: str) -> bool:
    """Diz se o PIN digitado bate com o hash guardado no banco."""
    try:
        return _ph.verify(hash_guardado, pin)
    except (VerificationError, InvalidHashError):
        # VerifyMismatchError (PIN errado) é um tipo de VerificationError;
        # InvalidHashError cobre um pin_hash corrompido ou em outro formato.
        return False


# ---------------------------------------------------------------------------
# 2. TOKEN (JWT)
# ---------------------------------------------------------------------------
def criar_token(u: Usuario) -> str:
    """Gera o token de login: guarda id (sub), papel e a data de expiração."""
    exp = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRA_HORAS)
    return jwt.encode(
        {"sub": u.id, "papel": u.papel, "exp": exp},
        settings.JWT_SECRET,
        algorithm="HS256",
    )


# ---------------------------------------------------------------------------
# 3. DEPENDÊNCIAS DO FASTAPI
# ---------------------------------------------------------------------------
def usuario_atual(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    """Descobre quem está logado a partir do header 'Authorization: Bearer <token>'."""
    if cred is None:
        raise ErroNegocio(401, "NAO_AUTENTICADO", "Faça login")
    try:
        dados = jwt.decode(cred.credentials, settings.JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        # Cobre token malformado, assinatura errada e token expirado
        raise ErroNegocio(401, "TOKEN_INVALIDO", "Sessão expirada, faça login novamente")

    id_usuario = dados.get("sub")
    u = db.get(Usuario, id_usuario) if id_usuario else None
    if not u or not u.ativo:
        raise ErroNegocio(401, "TOKEN_INVALIDO", "Usuário inválido")
    return u


def exige_admin(u: Usuario = Depends(usuario_atual)) -> Usuario:
    """Igual a usuario_atual, mas só deixa passar quem é ADMIN."""
    if u.papel != "ADMIN":
        raise ErroNegocio(403, "PERMISSAO", "Apenas o administrador pode fazer isso")
    return u