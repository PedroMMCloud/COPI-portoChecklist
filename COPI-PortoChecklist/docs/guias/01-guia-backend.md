# Guia 01 — Back-end passo a passo (BE-01 a BE-12)

> Leia antes: `00-entenda-o-sistema-e-como-trabalhar.md`. Contrato: `docs/00-contrato.md`.

## O que JÁ está pronto (e testado)
As regras de negócio estão em Python puro, **sem FastAPI e sem banco**, com 15 testes passando:
- `app/services/validacao.py` → `validar_checklist(dados, itens)` (RN01–RN04, RN06, RN17)
- `app/services/impedimento.py` → `calcular_impedimento(respostas, itens)` (RN05)
- `app/services/eventos.py` → `calcular_diff(antigo, novo)` (RN07/RN11)
- `tests/test_servicos.py` → testes com o caso da foto.

**Seu trabalho é "ligar os fios":** receber o JSON, chamar essas funções, gravar no banco e responder. Leia os 3 arquivos primeiro (são curtos) e rode `pytest`.

> ⚠️ Os trechos de código **FastAPI/SQLAlchemy** abaixo são **ponto de partida, ainda não executados**. Se der erro de importação ou de versão, copie o erro para a IA e peça a correção. Isso é normal.

## Mapa de arquivos que você vai criar
```
app/models.py            tabelas (BE-02)
app/erros.py             ErroNegocio (BE-03)
app/security.py          login/JWT/papéis (BE-03)
app/schemas.py           formato do JSON de entrada (BE-05)
app/routers/auth.py      POST /auth/login
app/routers/template.py  GET /template, /lookups, /equipamentos/{id}/ultimo-horimetro
app/routers/checklists.py PUT, GET, vistar, solicitar-correcao
scripts/seed.py          dados iniciais
tests/conftest.py        banco de teste (BE-11)
```
Ordem recomendada de trabalho: **BE-01 → 02 → 03 → 04 → 05 → 06 → 07/08 → 09 → 10 → 11 → 12**. Teste **cada rota no navegador** em `http://localhost:8000/docs` antes de passar à próxima.

---

## BE-01 — Rodar o ambiente local (D1, ~1h)
1. Instale **Python 3.12** (python.org). Confirme: `python --version`.
2. No terminal: `cd backend` e siga o `backend/README.md` (venv → `pip install -r requirements.txt` → `uvicorn ...`).
3. Abra `http://localhost:8000/api/v1/health` ⇒ `{"status":"ok",...}`.
4. Rode `pytest` ⇒ **15 passed** (+1 do health se o FastAPI estiver instalado).
**Pronto quando:** health responde, pytest verde, você consegue abrir `/docs`.
**Erros comuns:** *"python não reconhecido"* → reinstale marcando "Add to PATH". *PowerShell bloqueia o activate* → `Set-ExecutionPolicy -Scope Process Bypass`. *Porta 8000 ocupada* → `--port 8001`. *`ModuleNotFoundError: app`* → rode o pytest **dentro da pasta backend**.

---

## BE-02 — Modelos e seed (D2, ~3h)
**Objetivo:** criar as tabelas do contrato (§5) e popular os dados iniciais.

**Passos**
1. Crie `app/models.py` (modelo abaixo). Ele cobre as tabelas: `usuarios`, `locais`, `equipamentos`, `checklist_templates`, `checklist_template_itens`, `checklists`, `checklist_respostas`, `checklist_eventos`, `checklist_revisoes`.
2. Em `app/main.py`, crie as tabelas ao subir: `from app.db import Base, engine; import app.models; Base.metadata.create_all(engine)`. (Sem Alembic: SQLite + 3 dias. Para zerar o banco, apague `checklist.db`.)
3. Implemente `scripts/seed.py` lendo `settings.SEED_DIR` (modelo abaixo). Rode: `python -m scripts.seed`.
4. Rode **duas vezes**: não pode duplicar nada.

```python
# app/models.py  (referência)
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def novo_id() -> str:
    return str(uuid.uuid4())


def agora() -> datetime:
    return datetime.now(timezone.utc)


class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=novo_id)
    matricula: Mapped[str] = mapped_column(String(20), unique=True)
    nome: Mapped[str] = mapped_column(String(120))
    papel: Mapped[str] = mapped_column(String(10))  # OPERADOR | ADMIN
    pin_hash: Mapped[str] = mapped_column(String(255))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


class Local(Base):
    __tablename__ = "locais"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=novo_id)
    nome: Mapped[str] = mapped_column(String(80), unique=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


class Equipamento(Base):
    __tablename__ = "equipamentos"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=novo_id)
    identificacao: Mapped[str] = mapped_column(String(80), unique=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


class Template(Base):
    __tablename__ = "checklist_templates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=novo_id)
    codigo: Mapped[str] = mapped_column(String(30))
    versao: Mapped[int] = mapped_column(Integer)
    data_versao: Mapped[str] = mapped_column(String(10))
    titulo: Mapped[str] = mapped_column(String(120))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    itens: Mapped[list["TemplateItem"]] = relationship(order_by="TemplateItem.numero")


class TemplateItem(Base):
    __tablename__ = "checklist_template_itens"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=novo_id)
    template_id: Mapped[str] = mapped_column(ForeignKey("checklist_templates.id"))
    numero: Mapped[int] = mapped_column(Integer)
    descricao: Mapped[str] = mapped_column(String(200))
    critico: Mapped[bool] = mapped_column(Boolean, default=False)
    permite_na: Mapped[bool] = mapped_column(Boolean, default=True)


class Checklist(Base):
    __tablename__ = "checklists"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID gerado no APP
    template_id: Mapped[str] = mapped_column(ForeignKey("checklist_templates.id"))
    operador_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id"))
    equipamento_id: Mapped[str] = mapped_column(ForeignKey("equipamentos.id"))
    local_id: Mapped[str] = mapped_column(ForeignKey("locais.id"))
    # Datas/horas vindas do app ficam como texto ISO (simples para a demo)
    data_turno: Mapped[str] = mapped_column(String(10))
    turno: Mapped[str] = mapped_column(String(10))
    navio: Mapped[str | None] = mapped_column(String(120), nullable=True)
    horimetro_inicial: Mapped[float] = mapped_column(Float)
    horimetro_final: Mapped[float | None] = mapped_column(Float, nullable=True)
    combustivel_pct: Mapped[int] = mapped_column(Integer)
    hora_entrada: Mapped[str] = mapped_column(String(5))
    hora_saida: Mapped[str | None] = mapped_column(String(5), nullable=True)
    observacao_geral: Mapped[str | None] = mapped_column(Text, nullable=True)
    assinatura_operador: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(25), default="ENVIADO")
    impedido: Mapped[bool] = mapped_column(Boolean, default=False)
    revisao: Mapped[int] = mapped_column(Integer, default=1)
    editado: Mapped[bool] = mapped_column(Boolean, default=False)
    usou_lote: Mapped[bool] = mapped_column(Boolean, default=False)
    itens_marcados_lote: Mapped[int] = mapped_column(Integer, default=0)
    itens_alterados_apos_lote: Mapped[int] = mapped_column(Integer, default=0)
    inicio_preenchimento_em: Mapped[str | None] = mapped_column(String(40), nullable=True)
    finalizado_em: Mapped[str | None] = mapped_column(String(40), nullable=True)
    duracao_segundos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    criado_no_dispositivo_em: Mapped[str | None] = mapped_column(String(40), nullable=True)
    app_versao: Mapped[str | None] = mapped_column(String(20), nullable=True)
    vistado_por: Mapped[str | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    vistado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recebido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    respostas: Mapped[list["Resposta"]] = relationship(
        cascade="all, delete-orphan", order_by="Resposta.item_numero"
    )


class Resposta(Base):
    __tablename__ = "checklist_respostas"
    checklist_id: Mapped[str] = mapped_column(ForeignKey("checklists.id"), primary_key=True)
    item_numero: Mapped[int] = mapped_column(Integer, primary_key=True)
    resposta: Mapped[str] = mapped_column(String(2))  # S | N | NA
    origem: Mapped[str] = mapped_column(String(6), default="MANUAL")  # LOTE | MANUAL
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)


class Evento(Base):
    __tablename__ = "checklist_eventos"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=novo_id)
    checklist_id: Mapped[str] = mapped_column(ForeignKey("checklists.id"))
    tipo: Mapped[str] = mapped_column(String(25))  # CRIADO, EDITADO, REENVIADO, CORRECAO_SOLICITADA, VISTADO
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id"))
    detalhe: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)


class Revisao(Base):
    __tablename__ = "checklist_revisoes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=novo_id)
    checklist_id: Mapped[str] = mapped_column(ForeignKey("checklists.id"))
    revisao: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSON)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
```
```python
# scripts/seed.py  (referência) — rode: python -m scripts.seed
import json
from pathlib import Path

from app.config import settings
from app.db import Base, SessionLocal, engine
import app.models as m
from app.security import hash_pin


def ler(nome):
    return json.loads((Path(settings.SEED_DIR) / nome).read_text(encoding="utf-8"))


def main():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    demo = ler("demo_usuarios_locais_equipamentos.json")
    for u in demo["usuarios"]:
        if not db.query(m.Usuario).filter_by(matricula=u["matricula"]).first():
            db.add(m.Usuario(matricula=u["matricula"], nome=u["nome"], papel=u["papel"], pin_hash=hash_pin(u["pin"])))
    for l in demo["locais"]:
        if not db.query(m.Local).filter_by(nome=l["nome"]).first():
            db.add(m.Local(nome=l["nome"]))
    for e in demo["equipamentos"]:
        if not db.query(m.Equipamento).filter_by(identificacao=e["identificacao"]).first():
            db.add(m.Equipamento(identificacao=e["identificacao"]))
    t = ler("checklist_template_for_opp_0017_v5.json")
    if not db.query(m.Template).filter_by(codigo=t["codigo"], versao=t["versao"]).first():
        tpl = m.Template(codigo=t["codigo"], versao=t["versao"], data_versao=t["data_versao"], titulo=t["titulo"])
        db.add(tpl)
        db.flush()
        for i in t["itens"]:
            db.add(m.TemplateItem(template_id=tpl.id, numero=i["numero"], descricao=i["descricao"],
                                  critico=i["critico"], permite_na=i["permite_na"]))
    db.commit()
    print("seed ok")


if __name__ == "__main__":
    main()
```
**Pronto quando:** `python -m scripts.seed` roda 2x sem erro; o banco tem 3 usuários, 2 locais, 3 equipamentos, 1 template com **23 itens**; o PIN no banco é um **hash** (nunca "1234").
**Erros comuns:** *`ModuleNotFoundError: app`* → use `python -m scripts.seed` dentro de `backend/`. *SEED_DIR não encontrado* → confira `.env` (`SEED_DIR=../dados/seed`).
**Prompt pronto:** *"Sou iniciante. Use este models.py (cole) e explique cada tabela em 1 linha. Depois escreva um seed idempotente que lê estes JSONs (cole). Use SQLAlchemy 2 e argon2 para hash do PIN."*

---

## BE-03 — Login, token e papéis (D2, ~3h)
**Passos**
1. Crie `app/erros.py` (erro padrão do contrato) e registre o handler em `main.py`.
2. Crie `app/security.py` (hash, token, dependências).
3. Crie `app/routers/auth.py` com `POST /auth/login` e registre em `main.py` (`app.include_router(auth.router, prefix="/api/v1")`).
4. Teste no `/docs`: login com 1001/1234 ⇒ copie o token ⇒ botão **Authorize**.

```python
# app/erros.py
class ErroNegocio(Exception):
    def __init__(self, status: int, codigo: str, mensagem: str, campos=None):
        self.status, self.codigo, self.mensagem, self.campos = status, codigo, mensagem, campos or []
```
```python
# em app/main.py
from fastapi.responses import JSONResponse
from app.erros import ErroNegocio

@app.exception_handler(ErroNegocio)
async def tratar_erro_negocio(request, exc: ErroNegocio):
    return JSONResponse(status_code=exc.status,
        content={"erro": {"codigo": exc.codigo, "mensagem": exc.mensagem, "campos": exc.campos}})
```
```python
# app/security.py
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.erros import ErroNegocio
from app.models import Usuario

_ph = PasswordHasher()
_bearer = HTTPBearer(auto_error=False)   # auto_error=False: nós devolvemos 401 no formato do contrato


def hash_pin(pin: str) -> str:
    return _ph.hash(pin)


def confere_pin(pin: str, hash_guardado: str) -> bool:
    try:
        return _ph.verify(hash_guardado, pin)
    except VerifyMismatchError:
        return False


def criar_token(u: Usuario) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRA_HORAS)
    return jwt.encode({"sub": u.id, "papel": u.papel, "exp": exp}, settings.JWT_SECRET, algorithm="HS256")


def usuario_atual(cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
                  db: Session = Depends(get_db)) -> Usuario:
    if cred is None:
        raise ErroNegocio(401, "NAO_AUTENTICADO", "Faça login")
    try:
        dados = jwt.decode(cred.credentials, settings.JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise ErroNegocio(401, "TOKEN_INVALIDO", "Sessão expirada, faça login novamente")
    u = db.get(Usuario, dados["sub"])
    if not u or not u.ativo:
        raise ErroNegocio(401, "TOKEN_INVALIDO", "Usuário inválido")
    return u


def exige_admin(u: Usuario = Depends(usuario_atual)) -> Usuario:
    if u.papel != "ADMIN":
        raise ErroNegocio(403, "PERMISSAO", "Apenas o administrador pode fazer isso")
    return u
```
```python
# app/routers/auth.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.erros import ErroNegocio
from app.models import Usuario
from app.security import confere_pin, criar_token

router = APIRouter()


class LoginIn(BaseModel):
    matricula: str
    pin: str


@router.post("/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.query(Usuario).filter_by(matricula=body.matricula, ativo=True).first()
    if not u or not confere_pin(body.pin, u.pin_hash):
        raise ErroNegocio(401, "CREDENCIAIS", "Matrícula ou PIN incorretos")
    return {"access_token": criar_token(u), "usuario": {"id": u.id, "nome": u.nome, "papel": u.papel}}
```
**Pronto quando:** PIN errado ⇒ 401 com mensagem; PIN certo ⇒ token; rota protegida sem token ⇒ 401; operador numa rota de admin ⇒ 403.
**Erros comuns:** *tabela não existe* → rode o seed antes. *`jwt` sem `encode`* → o pacote certo é **PyJWT** (`pip install pyjwt`), não `jwt`.
**Prompt pronto:** *"FastAPI + PyJWT. Revise este security.py (cole) e aponte falhas de segurança para um sistema simples de login por matrícula+PIN. Não mude a assinatura das funções."*

---

## BE-04 — Template e lookups (D2, ~1h)
```python
# app/routers/template.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.erros import ErroNegocio
from app.models import Checklist, Equipamento, Local, Template
from app.security import usuario_atual

router = APIRouter()
TURNOS = ["T_08_14", "T_14_20", "T_20_02", "T_02_08"]


@router.get("/template")
def template_ativo(db: Session = Depends(get_db), _=Depends(usuario_atual)):
    t = db.query(Template).filter_by(ativo=True).order_by(Template.versao.desc()).first()
    if not t:
        raise ErroNegocio(404, "SEM_TEMPLATE", "Nenhum template ativo")
    return {"id": t.id, "codigo": t.codigo, "versao": t.versao, "titulo": t.titulo,
            "itens": [{"numero": i.numero, "descricao": i.descricao, "critico": i.critico,
                       "permite_na": i.permite_na} for i in t.itens]}


@router.get("/lookups")
def lookups(db: Session = Depends(get_db), _=Depends(usuario_atual)):
    return {"locais": [{"id": l.id, "nome": l.nome} for l in db.query(Local).filter_by(ativo=True)],
            "equipamentos": [{"id": e.id, "identificacao": e.identificacao}
                             for e in db.query(Equipamento).filter_by(ativo=True)],
            "turnos": TURNOS}


@router.get("/equipamentos/{equipamento_id}/ultimo-horimetro")   # BE-10
def ultimo_horimetro(equipamento_id: str, db: Session = Depends(get_db), _=Depends(usuario_atual)):
    c = (db.query(Checklist)
         .filter(Checklist.equipamento_id == equipamento_id, Checklist.horimetro_final.isnot(None))
         .order_by(Checklist.recebido_em.desc()).first())
    return {"horimetro_final": c.horimetro_final if c else None}
```
**Pronto quando:** `/template` devolve 23 itens ordenados; `/lookups` devolve 2 locais e 3 guindastes. (BE-10 já está incluída acima: teste depois do BE-05.)

---

## BE-05 — `PUT /checklists/{id}` (D2–D3, a tarefa mais importante, ~6h)
**Como pensar (receita do endpoint):**
1. Só `OPERADOR` envia. 2. Valide com `validar_checklist` ⇒ 400 se houver erros. 3. Calcule `impedido`. 4. O checklist **já existe**?
   - **Não:** crie (status `ENVIADO`, revisão 1) + evento `CRIADO`.
   - **Sim:** (a) só o dono edita (403); (b) se `VISTADO` ⇒ 409; (c) `calcular_diff`: **diff vazio ⇒ responda 200 sem mudar nada**; (d) senão guarde **snapshot** da versão antiga, `revisao + 1`, `editado = True`, apague e recrie as respostas; evento `EDITADO` (ou `REENVIADO` se estava em `CORRECAO_SOLICITADA`) com o diff; status volta a `ENVIADO`.
5. `commit` e responda `{id, status, revisao, impedido, editado}`.

**Passo 1 — schema de entrada**
```python
# app/schemas.py
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class RespostaIn(BaseModel):
    item_numero: int
    resposta: Literal["S", "N", "NA"]
    origem: Literal["LOTE", "MANUAL"] = "MANUAL"
    observacao: str | None = None


class ChecklistIn(BaseModel):
    template_id: str
    equipamento_id: str
    local_id: str
    data_turno: str
    turno: str
    navio: str | None = None
    horimetro_inicial: float
    horimetro_final: float | None = None
    combustivel_pct: int
    hora_entrada: str
    hora_saida: str | None = None
    observacao_geral: str | None = None
    assinatura_operador: str | None = None
    usou_lote: bool = False
    itens_marcados_lote: int = 0
    itens_alterados_apos_lote: int = 0
    inicio_preenchimento_em: str | None = None
    finalizado_em: str | None = None
    duracao_segundos: int | None = None
    confirmacao_correcao: bool = False
    criado_no_dispositivo_em: str | None = None
    app_versao: str | None = None
    respostas: list[RespostaIn]
```
**Passo 2 — a rota (referência)**
```python
# app/routers/checklists.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.erros import ErroNegocio
from app.models import Checklist, Evento, Resposta, Revisao, Template
from app.schemas import ChecklistIn
from app.security import usuario_atual
from app.services.eventos import CAMPOS, calcular_diff
from app.services.impedimento import calcular_impedimento
from app.services.validacao import validar_checklist

router = APIRouter()
CAMPOS_EXTRAS = ["usou_lote", "itens_marcados_lote", "itens_alterados_apos_lote",
                 "inicio_preenchimento_em", "finalizado_em", "duracao_segundos", "assinatura_operador"]


def itens_do_template(db: Session, template_id: str) -> list[dict]:
    t = db.get(Template, template_id)
    if not t:
        raise ErroNegocio(400, "VALIDACAO", "template_id inexistente")
    return [{"numero": i.numero, "critico": i.critico, "permite_na": i.permite_na} for i in t.itens]


def checklist_para_dict(c: Checklist) -> dict:
    """Mesma forma do corpo do PUT: serve para o diff e para o snapshot."""
    d = {campo: getattr(c, campo) for campo in CAMPOS + CAMPOS_EXTRAS}
    d["respostas"] = [{"item_numero": r.item_numero, "resposta": r.resposta, "origem": r.origem,
                       "observacao": r.observacao} for r in c.respostas]
    return d


@router.put("/checklists/{checklist_id}")
def salvar_checklist(checklist_id: str, body: ChecklistIn,
                     db: Session = Depends(get_db), usuario=Depends(usuario_atual)):
    if usuario.papel != "OPERADOR":
        raise ErroNegocio(403, "PERMISSAO", "Somente o operador envia checklists")

    dados = body.model_dump()
    itens = itens_do_template(db, dados["template_id"])
    erros = validar_checklist(dados, itens)
    if erros:
        raise ErroNegocio(400, "VALIDACAO", "Checklist inválido", erros)
    impedido = calcular_impedimento(dados["respostas"], itens)["impedido"]

    c = db.get(Checklist, checklist_id)
    if c is None:                                           # --- criação ---
        c = Checklist(id=checklist_id, operador_id=usuario.id, status="ENVIADO", revisao=1, editado=False)
        _aplicar(c, dados, impedido)
        db.add(c)
        db.add(Evento(checklist_id=checklist_id, tipo="CRIADO", usuario_id=usuario.id))
    else:                                                   # --- edição / reenvio ---
        if c.operador_id != usuario.id:
            raise ErroNegocio(403, "PERMISSAO", "Este checklist é de outro operador")
        if c.status == "VISTADO":
            raise ErroNegocio(409, "TRAVADO", "Checklist já vistado: não pode ser alterado")
        antigo = checklist_para_dict(c)
        diff = calcular_diff(antigo, dados)
        if not diff:                                        # reenvio idêntico (RN11)
            if c.status == "CORRECAO_SOLICITADA" and dados["confirmacao_correcao"]:
                # o operador conferiu e manteve tudo: sai de "correção solicitada" sem nova revisão
                c.status = "ENVIADO"
                db.add(Evento(checklist_id=c.id, tipo="REENVIADO", usuario_id=usuario.id,
                              detalhe={"diff": [], "confirmacao_correcao": True}))
                db.commit()
            return _resumo(c)
        db.add(Revisao(checklist_id=c.id, revisao=c.revisao, snapshot=antigo))
        tipo = "REENVIADO" if c.status == "CORRECAO_SOLICITADA" else "EDITADO"
        db.add(Evento(checklist_id=c.id, tipo=tipo, usuario_id=usuario.id,
                      detalhe={"diff": diff, "confirmacao_correcao": dados["confirmacao_correcao"]}))
        c.revisao += 1
        c.editado = True
        c.status = "ENVIADO"
        _aplicar(c, dados, impedido)
    db.commit()
    return _resumo(c)


def _aplicar(c: Checklist, dados: dict, impedido: bool) -> None:
    for campo in CAMPOS + CAMPOS_EXTRAS + ["template_id", "criado_no_dispositivo_em", "app_versao"]:
        setattr(c, campo, dados.get(campo))
    c.impedido = impedido
    c.respostas.clear()                                     # delete-orphan apaga as antigas
    for r in dados["respostas"]:
        c.respostas.append(Resposta(item_numero=r["item_numero"], resposta=r["resposta"],
                                    origem=r.get("origem", "MANUAL"), observacao=r.get("observacao")))


def _resumo(c: Checklist) -> dict:
    return {"id": c.id, "status": c.status, "revisao": c.revisao, "impedido": c.impedido, "editado": c.editado}
```
**Como testar no `/docs`** (login primeiro, **Authorize**): copie o `respostas` e demais campos de `dados/fixtures/caso_foto.json`, troque `equipamento_id`/`local_id`/`template_id` pelos IDs de `/lookups` e `/template`, adicione `assinatura_operador`. Esperado: 200, `impedido: true`, `revisao: 1`. Envie de novo igual ⇒ continua `revisao: 1`. Mude o `horimetro_final` e envie ⇒ `revisao: 2`, `editado: true`.
**Pronto quando:** os cenários 1–5, 8–11 do PRD (`02-backend.md`, "Testes mínimos") funcionam.
**Erros comuns:** *`CAMPOS` com `usou_lote` etc. dão `KeyError`* → confira que o schema tem todos os campos. *422 em vez de 400* → o formato do JSON está errado (FastAPI valida tipos antes das nossas regras). *Respostas duplicadas* → faltou o `c.respostas.clear()`.
**Prompt pronto:** *"Estou implementando PUT /checklists/{id} em FastAPI + SQLAlchemy 2. As regras de negócio já existem em services/ (cole as assinaturas). Revise esta rota (cole) comparando com esta receita (cole os 5 passos). Aponte bugs, sem reescrever tudo."*

---

## BE-06 — Listagem e detalhe (D3, ~4h)
**Passos:** (1) `GET /checklists` com filtros `status`, `equipamento_id`, `local_id`, `impedido`; (2) operador só vê os seus (RN13); (3) ordene **impedidos primeiro**; (4) calcule os **contadores** sobre todos os registros visíveis (antes de filtrar por status); (5) `GET /checklists/{id}` com respostas, metadados e eventos (formato no contrato §6).
```python
# trecho (adicione em app/routers/checklists.py)
from datetime import datetime, timezone
from app.models import Equipamento, Local, TemplateItem, Usuario


def _resumo_lista(db, c: Checklist) -> dict:
    op = db.get(Usuario, c.operador_id)
    motivo = None
    if c.status == "CORRECAO_SOLICITADA":
        ev = (db.query(Evento).filter_by(checklist_id=c.id, tipo="CORRECAO_SOLICITADA")
              .order_by(Evento.criado_em.desc()).first())
        motivo = (ev.detalhe or {}).get("motivo") if ev else None
    return {"id": c.id, "status": c.status, "impedido": c.impedido, "editado": c.editado,
            "revisao": c.revisao, "usou_lote": c.usou_lote,
            "operador": {"id": op.id, "nome": op.nome},
            "equipamento": db.get(Equipamento, c.equipamento_id).identificacao,
            "local": db.get(Local, c.local_id).nome, "turno": c.turno, "data_turno": c.data_turno,
            "recebido_em": c.recebido_em.isoformat(), "motivo_correcao": motivo}


@router.get("/checklists")
def listar(status: str | None = None, equipamento_id: str | None = None, local_id: str | None = None,
           impedido: bool | None = None, db: Session = Depends(get_db), usuario=Depends(usuario_atual)):
    base = db.query(Checklist)
    if usuario.papel == "OPERADOR":
        base = base.filter(Checklist.operador_id == usuario.id)
    todos = base.all()
    hoje = datetime.now(timezone.utc).date()
    contadores = {
        "pendentes": sum(c.status == "ENVIADO" for c in todos),
        "impedidos": sum(c.impedido and c.status != "VISTADO" for c in todos),
        "correcao": sum(c.status == "CORRECAO_SOLICITADA" for c in todos),
        "vistados_hoje": sum(c.status == "VISTADO" and c.vistado_em and c.vistado_em.date() == hoje for c in todos),
    }
    q = base
    if status: q = q.filter(Checklist.status == status)
    if equipamento_id: q = q.filter(Checklist.equipamento_id == equipamento_id)
    if local_id: q = q.filter(Checklist.local_id == local_id)
    if impedido is not None: q = q.filter(Checklist.impedido == impedido)
    q = q.order_by(Checklist.impedido.desc(), Checklist.recebido_em.desc())
    return {"contadores": contadores, "itens": [_resumo_lista(db, c) for c in q.all()]}
```
O **detalhe** segue o mesmo padrão: junte `TemplateItem` (para `descricao` e `critico` de cada resposta) e liste `Evento` em ordem de data. Operador só abre os seus (404/403 caso contrário).
**Pronto quando:** como operador (João) você só vê os seus; como admin vê todos; os contadores batem com o que está no banco; o detalhe traz 23 respostas com descrição.
**Prompt pronto:** *"Complete o GET /checklists/{id} seguindo este formato JSON (cole o trecho do contrato §6) e estes modelos (cole). Mantenha o estilo do trecho _resumo_lista."*

---

## BE-07 e BE-08 — Vistar e solicitar correção (D3, ~2h)
```python
from pydantic import BaseModel
from app.security import exige_admin


class CorrecaoIn(BaseModel):
    motivo: str


def _carregar(db, checklist_id):
    c = db.get(Checklist, checklist_id)
    if not c:
        raise ErroNegocio(404, "NAO_ENCONTRADO", "Checklist não encontrado")
    return c


@router.post("/checklists/{checklist_id}/vistar")
def vistar(checklist_id: str, db: Session = Depends(get_db), admin=Depends(exige_admin)):
    c = _carregar(db, checklist_id)
    if c.status != "ENVIADO":
        raise ErroNegocio(409, "ESTADO_INVALIDO", f"Não é possível vistar um checklist em {c.status}")
    c.status, c.vistado_por, c.vistado_em = "VISTADO", admin.id, datetime.now(timezone.utc)
    db.add(Evento(checklist_id=c.id, tipo="VISTADO", usuario_id=admin.id))
    db.commit()
    return _resumo(c)


@router.post("/checklists/{checklist_id}/solicitar-correcao")
def solicitar_correcao(checklist_id: str, body: CorrecaoIn, db: Session = Depends(get_db),
                       admin=Depends(exige_admin)):
    if not body.motivo.strip():
        raise ErroNegocio(400, "VALIDACAO", "Informe o motivo da correção")
    c = _carregar(db, checklist_id)
    if c.status != "ENVIADO":
        raise ErroNegocio(409, "ESTADO_INVALIDO", f"Não é possível solicitar correção em {c.status}")
    c.status = "CORRECAO_SOLICITADA"
    db.add(Evento(checklist_id=c.id, tipo="CORRECAO_SOLICITADA", usuario_id=admin.id,
                  detalhe={"motivo": body.motivo.strip()}))
    db.commit()
    return _resumo(c)
```
**Pronto quando:** operador chamando `vistar` ⇒ 403; vistar 2x ⇒ 409; solicitar correção sem motivo ⇒ 400; depois do vistar, `PUT` do operador ⇒ 409.

## BE-09 — Eventos, snapshot e trava (D4, ~2h)
Já nasceram no BE-05. Aqui você **fecha as pontas**: (1) o detalhe lista `eventos` em ordem com nome de quem fez; (2) confirme que **cada edição** gera 1 `Revisao` e 1 `Evento` com diff; (3) escreva os testes 9 e 8 do PRD (edição ⇒ revisão 2 / PUT após VISTADO ⇒ 409).

## BE-10 — Último horímetro
Já incluída em BE-04. **Pronto quando:** antes de qualquer checklist ⇒ `{"horimetro_final": null}`; depois do fixture ⇒ `36470.8`.

---

## BE-11 — Testes de API (D3, ~3h)
Os 15 testes de regras já passam. Agora teste a API de ponta a ponta com um **banco de teste separado**.
```python
# tests/conftest.py   (carregado pelo pytest ANTES dos testes)
import os
os.environ["DATABASE_URL"] = "sqlite:///./teste.db"
os.environ["SEED_DIR"] = "../dados/seed"

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    from scripts.seed import main as seed
    seed()
    return TestClient(app)


def token(client, matricula, pin):
    r = client.post("/api/v1/auth/login", json={"matricula": matricula, "pin": pin})
    return {"Authorization": "Bearer " + r.json()["access_token"]}
```
Escreva em `tests/test_api.py` os cenários do PRD (§7): fixture ⇒ 200 e `impedido`; mesmo `id` 2x; operador tenta vistar ⇒ 403; admin vista ⇒ 200 e de novo ⇒ 409; PUT após VISTADO ⇒ 409; operador A não lê o do B.
**Pronto quando:** `pytest` verde. **Prompt pronto:** *"Escreva testes pytest com TestClient (FastAPI) para estes cenários (cole a lista), usando este conftest (cole). Monte o payload a partir de dados/fixtures/caso_foto.json trocando nomes por IDs de /lookups e /template."*

## BE-12 — Servidor acessível pelos 2 aparelhos (D4, ~2h)
1. Rode: `uvicorn app.main:app --host 0.0.0.0 --port 8000` (o `0.0.0.0` é essencial).
2. Descubra o IP do notebook (`ipconfig`) e **libere a porta 8000** no firewall.
3. No celular (mesma rede), abra `http://IP:8000/api/v1/health`. Tem que responder.
4. Rode o seed e `python dados/scripts/carregar_demo.py http://IP:8000/api/v1` (carrega 3 checklists de exemplo).
5. Plano B: túnel `ngrok http 8000` (ou cloudflared) e use a URL HTTPS gerada. Docker é opcional.
**Pronto quando:** os dois celulares abrem `/health` e o admin vê os 3 checklists demo na lista.
