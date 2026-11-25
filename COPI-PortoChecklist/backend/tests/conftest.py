"""Configuração global dos testes do back-end (Pytest + FastAPI TestClient).

O que este arquivo garante
--------------------------
1. Os testes SEMPRE usam o SQLite exclusivo ``backend/tests/teste.db``. A DATABASE_URL
   é definida aqui, sobrescrevendo qualquer valor do ambiente, e há uma checagem
   dupla (``_garantir_banco_de_teste``) que aborta tudo se o engine apontar para outro arquivo.
2. As variáveis de ambiente são definidas ANTES de qualquer ``import app...``, porque
   ``app/config.py`` lê o ambiente no momento da importação.
3. Funciona rodando ``pytest`` na raiz do projeto ou dentro de ``backend/``: todos os caminhos
   são absolutos e derivados da localização deste arquivo, nunca do diretório atual.
4. Antes de CADA teste as tabelas são apagadas, recriadas e populadas com o seed
   existente (``scripts/seed.py`` + ``dados/seed``), então nenhum teste enxerga dados de outro.

Uso nos testes
--------------
    def test_exemplo(client, auth_header, operador_demo):
        headers = auth_header(operador_demo["matricula"], operador_demo["pin"])
        resposta = client.get("/api/v1/lookups", headers=headers)
        assert resposta.status_code == 200

Ou, importando a função auxiliar diretamente:  ``from conftest import token``
e ``headers = token(client, "<matricula>", "<pin>")``.
"""
import json
import os
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# 1. Caminhos (absolutos; independem do diretório em que o pytest foi chamado)
# ---------------------------------------------------------------------------
TESTS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = TESTS_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
SEED_DIR = PROJECT_ROOT / "dados" / "seed"
TEST_DB_PATH = TESTS_DIR / "teste.db"
CASO_FOTO_PATH = PROJECT_ROOT / "dados" / "fixtures" / "caso_foto.json"
API = "/api/v1"

# Permite "import app" e "import scripts" mesmo quando o pytest roda fora de backend/
# (o pytest.ini de backend/ só adiciona o pythonpath quando é ele o arquivo de configuração).
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# ---------------------------------------------------------------------------
# 2. Variáveis de ambiente: SEMPRE antes de importar qualquer módulo de "app"
#    Atribuição direta (e não setdefault) de propósito: um DATABASE_URL já existente no
#    ambiente (dev/produção) nunca pode vazar para os testes.
# ---------------------------------------------------------------------------
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["SEED_DIR"] = str(SEED_DIR)
os.environ["JWT_SECRET"] = "segredo-somente-para-testes"
os.environ["JWT_EXPIRA_HORAS"] = "12"
os.environ["CORS_ORIGENS"] = "*"

# ---------------------------------------------------------------------------
# 3. Imports da aplicação (só depois do ambiente configurado)
# ---------------------------------------------------------------------------
from fastapi.testclient import TestClient  # noqa: E402

import app.models  # noqa: E402,F401  (registra todas as tabelas em Base.metadata)
from app.config import settings  # noqa: E402
from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from scripts import seed  # noqa: E402


# ---------------------------------------------------------------------------
# Proteção: nunca tocar em outro banco que não seja o de teste
# ---------------------------------------------------------------------------
def _garantir_banco_de_teste() -> None:
    """Aborta a execução se o engine do SQLAlchemy não aponta para ``teste.db``."""
    url = engine.url
    apontando_para_teste = (
        url.get_backend_name() == "sqlite"
        and bool(url.database)
        and Path(url.database).resolve() == TEST_DB_PATH.resolve()
    )
    if not apontando_para_teste or settings.DATABASE_URL != os.environ["DATABASE_URL"]:
        pytest.exit(
            "ABORTADO: o engine não está usando o banco de teste.\n"
            f"  esperado: {TEST_DB_PATH}\n"
            f"  atual:    {url.render_as_string(hide_password=True)}\n"
            "Algum módulo de 'app' foi importado antes do conftest.py definir a DATABASE_URL.",
            returncode=2,
        )


def _apagar_arquivos_do_banco() -> None:
    """Remove teste.db (e arquivos auxiliares do SQLite). Falhar aqui não é grave:
    as tabelas são recriadas a cada teste de qualquer forma."""
    engine.dispose()
    for sufixo in ("", "-journal", "-wal", "-shm"):
        try:
            Path(f"{TEST_DB_PATH}{sufixo}").unlink(missing_ok=True)
        except OSError:
            pass


def _recriar_banco() -> None:
    """Apaga e recria todas as tabelas e roda o seed existente (scripts/seed.py).

    O seed lê os JSONs de settings.SEED_DIR (= dados/seed) e usa o mesmo engine/SessionLocal
    da aplicação, ou seja, grava em teste.db.
    """
    _garantir_banco_de_teste()  # nunca rodar drop_all em outro banco
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    seed.main()


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------
def token(client: TestClient, matricula: str, pin: str) -> dict[str, str]:
    """Faz login (POST /api/v1/auth/login) e devolve ``{"Authorization": "Bearer <token>"}``."""
    resposta = client.post("/api/v1/auth/login", json={"matricula": matricula, "pin": pin})
    assert resposta.status_code == 200, (
        f"Login falhou para a matrícula {matricula!r}: {resposta.status_code} {resposta.text}"
    )
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def _banco_de_teste_da_sessao():
    """Início da sessão: confere o banco e parte de um teste.db novo; ao final, fecha as conexões.

    O arquivo teste.db é mantido depois da execução para facilitar inspeção
    (ele está coberto pelo '*.db' do .gitignore) e é recriado na sessão seguinte.
    """
    _garantir_banco_de_teste()
    _apagar_arquivos_do_banco()
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def _banco_limpo(_banco_de_teste_da_sessao):
    """Antes de cada teste: tabelas recriadas e populadas com o seed de demonstração."""
    _recriar_banco()
    yield


@pytest.fixture()
def recriar_banco():
    """Função que recria e popula o banco de novo (para testes que precisam "voltar ao zero")."""
    return _recriar_banco


@pytest.fixture()
def client(_banco_limpo):
    """TestClient da aplicação, falando com o banco de teste já populado."""
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_header(client):
    """Devolve uma função ``(matricula, pin) -> {"Authorization": "Bearer ..."}``."""

    def _auth_header(matricula: str, pin: str) -> dict[str, str]:
        return token(client, matricula, pin)

    return _auth_header


@pytest.fixture(scope="session")
def dados_demo() -> dict:
    """Conteúdo do JSON de demonstração (usuários, locais, equipamentos) lido de dados/seed."""
    return json.loads((SEED_DIR / seed.ARQ_DEMO).read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def operador_demo(dados_demo) -> dict:
    """Primeiro usuário OPERADOR do seed (dict com matricula, nome, papel e pin)."""
    return next(u for u in dados_demo["usuarios"] if u["papel"] == "OPERADOR")


@pytest.fixture(scope="session")
def admin_demo(dados_demo) -> dict:
    """Primeiro usuário ADMIN do seed (dict com matricula, nome, papel e pin)."""
    return next(u for u in dados_demo["usuarios"] if u["papel"] == "ADMIN")


# ---------------------------------------------------------------------------
# Fixtures compartilhadas pelos testes de API (test_api.py, test_api_fluxos.py)
# ---------------------------------------------------------------------------
# Chaves do caso_foto.json que existem só para leitura humana ou para o teste:
# o id vai na URL, o operador vem do token e "esperado" é o gabarito.
CHAVES_SO_DO_FIXTURE = {"descricao", "id", "operador_matricula", "equipamento", "local", "esperado"}


@pytest.fixture()
def caso_foto() -> dict:
    """Conteúdo de dados/fixtures/caso_foto.json (uma cópia nova a cada teste)."""
    return json.loads(CASO_FOTO_PATH.read_text(encoding="utf-8"))


@pytest.fixture()
def operador_a(dados_demo, caso_foto) -> dict:
    """Operador dono do caso da foto (matrícula indicada no próprio fixture)."""
    return next(u for u in dados_demo["usuarios"] if u["matricula"] == caso_foto["operador_matricula"])


@pytest.fixture()
def operador_b(dados_demo, operador_a) -> dict:
    """Outro operador do seed (papel OPERADOR, matrícula diferente da do operador A)."""
    return next(
        u for u in dados_demo["usuarios"]
        if u["papel"] == "OPERADOR" and u["matricula"] != operador_a["matricula"]
    )


@pytest.fixture()
def headers_a(auth_header, operador_a) -> dict:
    return auth_header(operador_a["matricula"], operador_a["pin"])


@pytest.fixture()
def headers_b(auth_header, operador_b) -> dict:
    return auth_header(operador_b["matricula"], operador_b["pin"])


@pytest.fixture()
def headers_admin(auth_header, admin_demo) -> dict:
    return auth_header(admin_demo["matricula"], admin_demo["pin"])


@pytest.fixture()
def payload(client, caso_foto, headers_a) -> dict:
    """Corpo do PUT montado a partir de caso_foto.json, com IDs reais de /template e /lookups."""
    r_template = client.get(f"{API}/template", headers=headers_a)
    assert r_template.status_code == 200
    r_lookups = client.get(f"{API}/lookups", headers=headers_a)
    assert r_lookups.status_code == 200

    equipamentos = {e["identificacao"]: e["id"] for e in r_lookups.json()["equipamentos"]}
    locais = {loc["nome"]: loc["id"] for loc in r_lookups.json()["locais"]}

    corpo = {k: v for k, v in caso_foto.items() if k not in CHAVES_SO_DO_FIXTURE}
    corpo["template_id"] = r_template.json()["id"]
    corpo["equipamento_id"] = equipamentos[caso_foto["equipamento"]]
    corpo["local_id"] = locais[caso_foto["local"]]
    return corpo


@pytest.fixture()
def checklist_id(caso_foto) -> str:
    return caso_foto["id"]