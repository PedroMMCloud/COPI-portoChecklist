"""
Testes da API PortData (Pytest + TestClient do FastAPI).

Instalação e execução (na pasta raiz do projeto):

    pip install pytest httpx
    pytest tests -v

Banco de dados de teste (exclusivo, nunca o de desenvolvimento):

    - Padrão: SQLite em memória, criado do zero para cada teste.
    - Opcional: PostgreSQL dedicado, informado em TEST_DATABASE_URL, por exemplo
          TEST_DATABASE_URL=postgresql+psycopg2://usuario:senha@localhost:5432/portdata_test pytest tests
      Por segurança, o nome do banco precisa conter "test" e a URL não pode ser a
      mesma de DATABASE_URL. As tabelas são recriadas e apagadas a cada teste.

A variável DATABASE_URL é redefinida NESTE processo para a URL de teste antes de
importar a aplicação, e a dependência get_db é substituída pela sessão de teste.
Assim, nenhum teste toca o banco de desenvolvimento.
"""

import os
import sys
from pathlib import Path

# --------------------------------------------------------------------------- #
# Configuração do ambiente (deve vir ANTES de importar a aplicação)
# --------------------------------------------------------------------------- #
RAIZ_PROJETO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_PROJETO))

import pytest  # noqa: E402
from sqlalchemy import create_engine, event, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "sqlite://")
_DATABASE_URL_ORIGINAL = os.environ.get("DATABASE_URL")


def _validar_url_de_teste(url: str) -> None:
    """Impede que os testes (que apagam tabelas) rodem em um banco que não seja de teste."""
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite":
        return
    if "test" not in (parsed.database or "").lower():
        raise RuntimeError(
            "TEST_DATABASE_URL deve apontar para um banco exclusivo de testes "
            "(o nome do banco precisa conter 'test')."
        )
    if url == _DATABASE_URL_ORIGINAL:
        raise RuntimeError("TEST_DATABASE_URL não pode ser igual a DATABASE_URL.")


_validar_url_de_teste(TEST_DATABASE_URL)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL  # database.py nunca vê a URL de desenvolvimento

from fastapi.testclient import TestClient  # noqa: E402

from app.services import services  # noqa: E402
from app.database.database import Base, get_db  # noqa: E402
from main import app  # noqa: E402
from app.models.models import TOTAL_ITENS  # noqa: E402
from app.schemas.schemas import CAMPOS_PARA_FINALIZADA, CAMPOS_PARA_PREENCHIDA  # noqa: E402

# SQLite não tem Decimal nativo; o aviso do SQLAlchemy é esperado e irrelevante aqui.
pytestmark = pytest.mark.filterwarnings("ignore:Dialect sqlite:sqlalchemy.exc.SAWarning")

requer_bloqueio_critico = pytest.mark.skipif(
    not services.BLOQUEAR_FINALIZACAO_COM_CRITICO_REPROVADO,
    reason="Regra desativada: item crítico NAO não bloqueia a finalização.",
)


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture()
def engine():
    """Banco de teste limpo para cada teste: tabelas criadas antes e apagadas depois."""
    if make_url(TEST_DATABASE_URL).get_backend_name() == "sqlite":
        eng = create_engine(
            TEST_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(eng, "connect")
        def _ativar_chaves_estrangeiras(dbapi_conn, _):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    else:
        eng = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)

    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture()
def client(engine):
    """TestClient usando o banco de teste no lugar do get_db da aplicação."""
    SessionTeste = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def _get_db_teste():
        db = SessionTeste()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db_teste
    # Sem "with": o lifespan da aplicação (create_all no banco configurado) não é executado.
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)


# --------------------------------------------------------------------------- #
# Dados e funções auxiliares
# --------------------------------------------------------------------------- #
def todas_respostas(valor="SIM"):
    return [{"numero_item": n, "resposta": valor} for n in range(1, TOTAL_ITENS + 1)]


def payload_basico(**extra):
    """Dados gerais completos, sem assinaturas e sem respostas (rascunho)."""
    dados = {
        "codigo_formulario": "FOR-001",
        "versao": "1.0",
        "local_atuacao": "Cais 1",
        "turno": "Diurno",
        "data": "2026-11-13",
        "navio": "MV Teste",
        "guindaste": "GM-01",
        "horimetro_inicial": 100.0,
        "horimetro_final": 108.5,
        "nivel_combustivel": 75.5,
        "hora_entrada": "07:00:00",
        "hora_saida": "19:00:00",
        "observacao_geral": "Inspeção de teste.",
        "nome_operador": "Operador Teste",
    }
    dados.update(extra)
    return dados


def payload_pronto(**extra):
    """Checklist pronta para finalizar: dados, assinaturas e os 23 itens como SIM."""
    dados = payload_basico(
        assinatura_operador="assinatura-operador",
        nome_lideranca="Liderança Teste",
        assinatura_lideranca="assinatura-lideranca",
        respostas=todas_respostas(),
    )
    dados.update(extra)
    return dados


def criar_checklist(client, payload) -> dict:
    resposta = client.post("/checklists", json=payload)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()["checklist"]


def escolher_item(checklist: dict, critico: bool) -> int:
    """Escolhe um item pelo atributo `critico` gravado, sem presumir quais são críticos."""
    candidatos = [r for r in checklist["respostas"] if r["critico"] is critico]
    if not candidatos:
        pytest.skip(f"Nenhum item com critico={critico} cadastrado no modelo.")
    return candidatos[0]["numero_item"]


def responder(client, checklist_id: int, numero_item: int, resposta: str, observacao=None):
    item = {"numero_item": numero_item, "resposta": resposta}
    if observacao is not None:
        item["observacao"] = observacao
    return client.put(f"/checklists/{checklist_id}", json={"respostas": [item]})


def contar(engine, tabela: str) -> int:
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM {tabela}")).scalar_one()


# --------------------------------------------------------------------------- #
# API funcionando
# --------------------------------------------------------------------------- #
def test_rota_raiz_responde(client):
    resposta = client.get("/")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert "PortData" in corpo["mensagem"]
    assert corpo["documentacao"] == {"swagger": "/docs", "redoc": "/redoc"}


def test_health_responde_ok(client):
    resposta = client.get("/health")
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "ok"


def test_documentacao_automatica_disponivel(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
    assert client.get("/openapi.json").status_code == 200


# --------------------------------------------------------------------------- #
# Criar, consultar e listar
# --------------------------------------------------------------------------- #
def test_criar_checklist(client):
    resposta = client.post("/checklists", json=payload_basico())

    assert resposta.status_code == 201
    corpo = resposta.json()
    checklist = corpo["checklist"]
    assert checklist["id"] >= 1
    assert resposta.headers["location"].endswith(f"/checklists/{checklist['id']}")
    assert checklist["status"] == "RASCUNHO"
    assert checklist["navio"] == "MV Teste"
    assert checklist["horimetro_inicial"] == pytest.approx(100.0)
    assert checklist["nivel_combustivel"] == pytest.approx(75.5)
    assert checklist["created_at"] and checklist["updated_at"]
    # Os 23 itens nascem com a checklist, ainda sem resposta.
    assert len(checklist["respostas"]) == TOTAL_ITENS
    assert all(r["resposta"] is None for r in checklist["respostas"])
    assert corpo["avaliacao"]["situacao"] == "COM_PENDENCIAS"


def test_criar_rascunho_sem_campos_preenchidos(client):
    resposta = client.post("/checklists", json={})

    assert resposta.status_code == 201
    checklist = resposta.json()["checklist"]
    assert checklist["status"] == "RASCUNHO"
    assert checklist["navio"] is None
    assert len(checklist["respostas"]) == TOTAL_ITENS


def test_nao_cria_checklist_ja_finalizada(client):
    resposta = client.post("/checklists", json=payload_pronto(status="FINALIZADA"))

    assert resposta.status_code == 409
    assert client.get("/checklists").json() == []


def test_consultar_checklist_por_id(client):
    criada = criar_checklist(client, payload_basico())

    resposta = client.get(f"/checklists/{criada['id']}")

    assert resposta.status_code == 200
    checklist = resposta.json()
    assert checklist["id"] == criada["id"]
    assert checklist["guindaste"] == "GM-01"
    assert [r["numero_item"] for r in checklist["respostas"]] == list(
        range(1, TOTAL_ITENS + 1)
    )
    assert all(r["checklist_id"] == criada["id"] for r in checklist["respostas"])


def test_consultar_checklist_inexistente_retorna_404(client):
    resposta = client.get("/checklists/999999")

    assert resposta.status_code == 404
    assert "999999" in resposta.json()["detail"]["mensagem"]


def test_listar_checklists_mais_recentes_primeiro(client):
    for data in ("2026-01-01", "2026-03-01", "2026-02-01"):
        criar_checklist(client, payload_basico(data=data))

    resposta = client.get("/checklists")

    assert resposta.status_code == 200
    assert [c["data"] for c in resposta.json()] == ["2026-03-01", "2026-02-01", "2026-01-01"]


def test_listar_checklists_vazio(client):
    resposta = client.get("/checklists")

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_listar_checklists_com_paginacao_e_filtro_de_status(client):
    for data in ("2026-01-01", "2026-02-01", "2026-03-01"):
        criar_checklist(client, payload_basico(data=data))

    assert len(client.get("/checklists", params={"limit": 2}).json()) == 2
    assert len(client.get("/checklists", params={"skip": 2, "limit": 2}).json()) == 1
    assert len(client.get("/checklists", params={"status": "RASCUNHO"}).json()) == 3
    assert client.get("/checklists", params={"status": "CANCELADA"}).json() == []


@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": 501}, {"skip": -1}, {"status": "INEXISTENTE"}],
)
def test_listar_checklists_com_parametros_invalidos(client, params):
    assert client.get("/checklists", params=params).status_code == 422


# --------------------------------------------------------------------------- #
# Atualizar
# --------------------------------------------------------------------------- #
def test_atualizar_checklist(client):
    criada = criar_checklist(client, payload_basico())

    resposta = client.put(
        f"/checklists/{criada['id']}",
        json={"turno": "Noturno", "nivel_combustivel": 50.0, "observacao_geral": "Atualizada"},
    )

    assert resposta.status_code == 200
    atualizada = resposta.json()["checklist"]
    assert atualizada["turno"] == "Noturno"
    assert atualizada["nivel_combustivel"] == pytest.approx(50.0)
    assert atualizada["observacao_geral"] == "Atualizada"
    # Campos não enviados permanecem como estavam.
    assert atualizada["local_atuacao"] == "Cais 1"
    assert atualizada["navio"] == "MV Teste"
    # A alteração foi gravada.
    assert client.get(f"/checklists/{criada['id']}").json()["turno"] == "Noturno"


def test_atualizar_checklist_inexistente_retorna_404(client):
    resposta = client.put("/checklists/999999", json={"turno": "Noturno"})

    assert resposta.status_code == 404


def test_nao_permite_definir_status_finalizada_pelo_update(client):
    criada = criar_checklist(client, payload_pronto())

    resposta = client.put(f"/checklists/{criada['id']}", json={"status": "FINALIZADA"})

    assert resposta.status_code == 409
    assert client.get(f"/checklists/{criada['id']}").json()["status"] == "RASCUNHO"


# --------------------------------------------------------------------------- #
# Respostas
# --------------------------------------------------------------------------- #
def test_armazenar_as_23_respostas(client):
    valores = ["SIM", "NAO", "NAO_APLICAVEL"]
    respostas = [
        {
            "numero_item": n,
            "resposta": valores[n % 3],
            "observacao": f"obs {n}" if n % 5 == 0 else None,
        }
        for n in range(1, TOTAL_ITENS + 1)
    ]

    criada = criar_checklist(client, payload_basico(respostas=respostas))
    gravadas = client.get(f"/checklists/{criada['id']}").json()["respostas"]

    assert [r["numero_item"] for r in gravadas] == list(range(1, TOTAL_ITENS + 1))
    for r in gravadas:
        n = r["numero_item"]
        assert r["resposta"] == valores[n % 3]
        assert r["observacao"] == (f"obs {n}" if n % 5 == 0 else None)
        assert r["descricao"]


def test_atualizar_respostas_altera_apenas_os_itens_enviados(client):
    valores = ["SIM", "NAO", "NAO_APLICAVEL"]
    respostas = [
        {"numero_item": n, "resposta": valores[n % 3], "observacao": f"obs {n}" if n % 5 == 0 else None}
        for n in range(1, TOTAL_ITENS + 1)
    ]
    criada = criar_checklist(client, payload_basico(respostas=respostas))

    resposta = client.put(
        f"/checklists/{criada['id']}",
        json={
            "respostas": [
                {"numero_item": 5, "resposta": "NAO", "observacao": "ajuste"},
                {"numero_item": 10, "resposta": "SIM"},  # observação não enviada
            ]
        },
    )

    assert resposta.status_code == 200
    por_item = {r["numero_item"]: r for r in resposta.json()["checklist"]["respostas"]}
    assert len(por_item) == TOTAL_ITENS
    assert (por_item[5]["resposta"], por_item[5]["observacao"]) == ("NAO", "ajuste")
    assert (por_item[10]["resposta"], por_item[10]["observacao"]) == ("SIM", "obs 10")
    assert por_item[6]["resposta"] == valores[6 % 3]  # intacto


@pytest.mark.parametrize("valor", ["TALVEZ", "SIMM", "N/A", 123])
def test_rejeita_resposta_com_valor_invalido(client, valor):
    item = {"numero_item": 1, "resposta": valor}

    assert client.post("/checklists", json=payload_basico(respostas=[item])).status_code == 422
    assert client.get("/checklists").json() == []  # nada foi gravado

    criada = criar_checklist(client, payload_basico())
    resposta = client.put(f"/checklists/{criada['id']}", json={"respostas": [item]})
    assert resposta.status_code == 422
    primeira = client.get(f"/checklists/{criada['id']}").json()["respostas"][0]
    assert primeira["resposta"] is None


@pytest.mark.parametrize("numero_item", [-1, 0, TOTAL_ITENS + 1])
def test_rejeita_numero_de_item_fora_do_intervalo(client, numero_item):
    item = {"numero_item": numero_item, "resposta": "SIM"}

    resposta = client.post("/checklists", json=payload_basico(respostas=[item]))

    assert resposta.status_code == 422


def test_rejeita_item_repetido_na_mesma_requisicao(client):
    itens = [
        {"numero_item": 3, "resposta": "SIM"},
        {"numero_item": 3, "resposta": "NAO"},
    ]

    resposta = client.post("/checklists", json=payload_basico(respostas=itens))

    assert resposta.status_code == 422


# --------------------------------------------------------------------------- #
# Horímetro e combustível
# --------------------------------------------------------------------------- #
def test_horimetro_final_igual_ao_inicial_e_valido(client):
    resposta = client.post(
        "/checklists", json=payload_basico(horimetro_inicial=100.0, horimetro_final=100.0)
    )

    assert resposta.status_code == 201


def test_rejeita_horimetro_final_menor_que_o_inicial_na_criacao(client):
    resposta = client.post(
        "/checklists", json=payload_basico(horimetro_inicial=100.0, horimetro_final=90.0)
    )

    assert resposta.status_code == 422
    assert client.get("/checklists").json() == []


def test_rejeita_horimetro_final_menor_que_o_inicial_na_atualizacao(client):
    criada = criar_checklist(client, payload_basico(horimetro_inicial=100.0, horimetro_final=108.5))

    # O payload sozinho é válido; a inconsistência só aparece junto do valor já gravado.
    resposta = client.put(f"/checklists/{criada['id']}", json={"horimetro_final": 50.0})

    assert resposta.status_code == 422
    assert "horímetro final" in resposta.json()["detail"]["mensagem"].lower()
    gravada = client.get(f"/checklists/{criada['id']}").json()
    assert gravada["horimetro_final"] == pytest.approx(108.5)


@pytest.mark.parametrize("campo", ["horimetro_inicial", "horimetro_final"])
def test_rejeita_horimetro_negativo(client, campo):
    resposta = client.post("/checklists", json=payload_basico(**{campo: -1.0}))

    assert resposta.status_code == 422


@pytest.mark.parametrize("percentual", [-0.1, 100.5])
def test_rejeita_nivel_de_combustivel_fora_de_0_a_100(client, percentual):
    resposta = client.post("/checklists", json=payload_basico(nivel_combustivel=percentual))

    assert resposta.status_code == 422


# --------------------------------------------------------------------------- #
# Itens críticos
# --------------------------------------------------------------------------- #
@requer_bloqueio_critico
def test_identifica_item_critico_respondido_nao(client):
    criada = criar_checklist(client, payload_pronto())
    critico = escolher_item(criada, critico=True)

    resposta = responder(client, criada["id"], critico, "NAO", "Falha encontrada")

    assert resposta.status_code == 200
    avaliacao = resposta.json()["avaliacao"]
    assert avaliacao["situacao"] == "REPROVADA_ITEM_CRITICO"
    assert avaliacao["pode_finalizar"] is False
    assert avaliacao["pendencias"] == []
    assert len(avaliacao["bloqueios"]) == 1
    assert f"Item {critico}" in avaliacao["bloqueios"][0]
    assert "Falha encontrada" in avaliacao["bloqueios"][0]

    verificacao = client.post(f"/checklists/{criada['id']}/verificar")
    assert verificacao.status_code == 200
    assert verificacao.json()["situacao"] == "REPROVADA_ITEM_CRITICO"


@requer_bloqueio_critico
def test_item_critico_reprovado_bloqueia_a_finalizacao(client):
    criada = criar_checklist(client, payload_pronto())
    critico = escolher_item(criada, critico=True)
    responder(client, criada["id"], critico, "NAO")

    resposta = client.post(f"/checklists/{criada['id']}/finalizar")

    assert resposta.status_code == 409
    detalhe = resposta.json()["detail"]
    assert "crítico" in detalhe["mensagem"].lower()
    assert len(detalhe["bloqueios"]) == 1
    assert client.get(f"/checklists/{criada['id']}").json()["status"] == "RASCUNHO"

    # Corrigido o item, a finalização passa.
    responder(client, criada["id"], critico, "SIM")
    assert client.post(f"/checklists/{criada['id']}/finalizar").status_code == 200


def test_item_nao_critico_respondido_nao_gera_apenas_alerta(client):
    criada = criar_checklist(client, payload_pronto())
    comum = escolher_item(criada, critico=False)

    resposta = responder(client, criada["id"], comum, "NAO")

    assert resposta.status_code == 200
    avaliacao = resposta.json()["avaliacao"]
    assert avaliacao["situacao"] == "PREENCHIDA"
    assert avaliacao["bloqueios"] == []
    assert len(avaliacao["alertas"]) == 1
    assert f"Item {comum}" in avaliacao["alertas"][0]
    assert client.post(f"/checklists/{criada['id']}/finalizar").status_code == 200


# --------------------------------------------------------------------------- #
# Verificação e finalização
# --------------------------------------------------------------------------- #
def test_verificar_checklist_com_pendencias(client):
    criada = criar_checklist(client, payload_basico())

    resposta = client.post(f"/checklists/{criada['id']}/verificar")

    assert resposta.status_code == 200
    avaliacao = resposta.json()
    assert avaliacao["situacao"] == "COM_PENDENCIAS"
    assert avaliacao["pode_finalizar"] is False
    assert any("itens sem resposta" in p for p in avaliacao["pendencias"])


def test_verificar_checklist_inexistente_retorna_404(client):
    assert client.post("/checklists/999999/verificar").status_code == 404


def test_verificar_checklist_preenchida_e_pronta(client):
    criada = criar_checklist(client, payload_pronto())

    avaliacao = client.post(f"/checklists/{criada['id']}/verificar").json()

    assert avaliacao["situacao"] == "PREENCHIDA"
    assert avaliacao["pode_finalizar"] is True
    assert avaliacao["pendencias"] == [] and avaliacao["bloqueios"] == []


@pytest.mark.parametrize("campo", CAMPOS_PARA_PREENCHIDA + CAMPOS_PARA_FINALIZADA)
def test_nao_finaliza_com_campo_obrigatorio_ausente(client, campo):
    criada = criar_checklist(client, payload_pronto(**{campo: None}))

    resposta = client.post(f"/checklists/{criada['id']}/finalizar")

    assert resposta.status_code == 422
    pendencias = resposta.json()["detail"]["pendencias"]
    assert any(p.endswith(f": {campo}") for p in pendencias), pendencias
    assert client.get(f"/checklists/{criada['id']}").json()["status"] == "RASCUNHO"


def test_nao_finaliza_com_itens_sem_resposta(client):
    respostas = todas_respostas()[:20]  # faltam os itens 21, 22 e 23
    criada = criar_checklist(client, payload_pronto(respostas=respostas))

    resposta = client.post(f"/checklists/{criada['id']}/finalizar")

    assert resposta.status_code == 422
    pendencias = resposta.json()["detail"]["pendencias"]
    assert any("itens sem resposta: 21, 22, 23" in p for p in pendencias), pendencias


def test_finalizar_checklist_completa(client):
    criada = criar_checklist(client, payload_pronto())

    resposta = client.post(f"/checklists/{criada['id']}/finalizar")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["checklist"]["status"] == "FINALIZADA"
    assert corpo["avaliacao"]["situacao"] == "FINALIZADA"
    assert client.get(f"/checklists/{criada['id']}").json()["status"] == "FINALIZADA"


def test_finalizar_checklist_inexistente_retorna_404(client):
    assert client.post("/checklists/999999/finalizar").status_code == 404


# --------------------------------------------------------------------------- #
# Checklist finalizada é imutável
# --------------------------------------------------------------------------- #
def test_nao_permite_alterar_checklist_finalizada(client):
    criada = criar_checklist(client, payload_pronto())
    client.post(f"/checklists/{criada['id']}/finalizar")
    url = f"/checklists/{criada['id']}"

    tentativas = [
        client.put(url, json={"turno": "Noturno"}),
        client.put(url, json={"respostas": [{"numero_item": 1, "resposta": "NAO"}]}),
        client.put(url, json={"status": "RASCUNHO"}),
    ]

    for tentativa in tentativas:
        assert tentativa.status_code == 409
        assert "finalizada" in tentativa.json()["detail"]["mensagem"].lower()

    # Nenhuma alteração silenciosa: os dados continuam exatamente como estavam.
    atual = client.get(url).json()
    assert atual["status"] == "FINALIZADA"
    assert atual["turno"] == "Diurno"
    assert atual["respostas"][0]["resposta"] == "SIM"


def test_nao_permite_finalizar_novamente_nem_excluir_checklist_finalizada(client, engine):
    criada = criar_checklist(client, payload_pronto())
    client.post(f"/checklists/{criada['id']}/finalizar")

    assert client.post(f"/checklists/{criada['id']}/finalizar").status_code == 409
    assert client.delete(f"/checklists/{criada['id']}").status_code == 409
    assert client.get(f"/checklists/{criada['id']}").status_code == 200
    assert contar(engine, "checklist_respostas") == TOTAL_ITENS


# --------------------------------------------------------------------------- #
# Exclusão
# --------------------------------------------------------------------------- #
def test_excluir_rascunho(client, engine):
    criada = criar_checklist(client, payload_basico())
    assert contar(engine, "checklists") == 1
    assert contar(engine, "checklist_respostas") == TOTAL_ITENS

    resposta = client.delete(f"/checklists/{criada['id']}")

    assert resposta.status_code == 204
    assert resposta.content == b""
    assert client.get(f"/checklists/{criada['id']}").status_code == 404
    assert contar(engine, "checklists") == 0
    assert contar(engine, "checklist_respostas") == 0  # respostas removidas junto


def test_excluir_checklist_inexistente_retorna_404(client):
    assert client.delete("/checklists/999999").status_code == 404


def test_nao_exclui_checklist_preenchida(client):
    criada = criar_checklist(client, payload_pronto(status="PREENCHIDA"))
    assert criada["status"] == "PREENCHIDA"

    resposta = client.delete(f"/checklists/{criada['id']}")

    assert resposta.status_code == 409
    assert client.get(f"/checklists/{criada['id']}").status_code == 200