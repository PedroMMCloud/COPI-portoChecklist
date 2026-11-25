"""Testes da própria infraestrutura de testes (conftest.py).

Usam apenas endpoints e dados que existem no projeto: POST /api/v1/auth/login,
GET /api/v1/lookups e os usuários/locais/equipamentos de dados/seed.
"""
import os
from pathlib import Path

from sqlalchemy import func, select

import app.models as m
from app.config import settings
from app.db import SessionLocal, engine
from scripts import seed

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_DB_PATH = BACKEND_DIR / "tests" / "teste.db"


def test_usa_somente_o_banco_de_teste():
    assert settings.DATABASE_URL == os.environ["DATABASE_URL"]
    assert Path(engine.url.database).resolve() == TEST_DB_PATH.resolve()
    assert Path(engine.url.database).name == "teste.db"
    # nunca o banco de desenvolvimento da demo
    assert Path(engine.url.database).resolve() != (BACKEND_DIR / "checklist.db").resolve()


def test_seed_populou_o_banco(dados_demo):
    template = seed.ler(seed.ARQ_TEMPLATE)
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(m.Usuario)) == len(dados_demo["usuarios"])
        assert db.scalar(select(func.count()).select_from(m.Local)) == len(dados_demo["locais"])
        assert db.scalar(select(func.count()).select_from(m.Equipamento)) == len(
            dados_demo["equipamentos"]
        )
        assert db.scalar(select(func.count()).select_from(m.Template)) == 1
        assert db.scalar(select(func.count()).select_from(m.TemplateItem)) == len(template["itens"])


def test_login_gera_cabecalho_bearer_valido(client, auth_header, operador_demo, dados_demo):
    headers = auth_header(operador_demo["matricula"], operador_demo["pin"])
    assert headers["Authorization"].startswith("Bearer ")

    r = client.get("/api/v1/lookups", headers=headers)
    assert r.status_code == 200
    assert len(r.json()["locais"]) == len(dados_demo["locais"])
    assert len(r.json()["equipamentos"]) == len(dados_demo["equipamentos"])


def test_login_do_admin(auth_header, admin_demo):
    assert auth_header(admin_demo["matricula"], admin_demo["pin"])["Authorization"].startswith(
        "Bearer "
    )


def test_rota_protegida_exige_token(client):
    r = client.get("/api/v1/lookups")
    assert r.status_code == 401
    assert r.json()["erro"]["codigo"] == "NAO_AUTENTICADO"


def test_login_com_pin_errado_e_rejeitado(client, operador_demo):
    r = client.post(
        "/api/v1/auth/login",
        json={"matricula": operador_demo["matricula"], "pin": operador_demo["pin"] + "x"},
    )
    assert r.status_code == 401
    assert r.json()["erro"]["codigo"] == "CREDENCIAIS"


def test_recriar_banco_descarta_dados_criados_no_teste(recriar_banco):
    with SessionLocal() as db:
        db.add(m.Local(nome="Local criado só neste teste"))
        db.commit()
        assert db.scalars(select(m.Local).filter_by(nome="Local criado só neste teste")).first()

    recriar_banco()  # é o que acontece automaticamente antes de cada teste

    with SessionLocal() as db:
        assert db.scalars(select(m.Local).filter_by(nome="Local criado só neste teste")).first() is None