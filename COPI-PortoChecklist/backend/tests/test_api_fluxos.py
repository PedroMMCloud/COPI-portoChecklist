"""Testes de integração dos fluxos do checklist: validação (400), edição e solicitar correção.

Complementa o test_api.py. Usa só endpoints reais (prefixo /api/v1):
    PUT  /checklists/{id}                       OPERADOR cria/edita
    GET  /checklists                            lista + contadores
    GET  /checklists/{id}                       detalhe (com eventos)
    POST /checklists/{id}/solicitar-correcao    só ADMIN, só em ENVIADO; body {"motivo": "..."}
    POST /checklists/{id}/vistar                só ADMIN

As fixtures (client, payload, headers_a, headers_admin, checklist_id...) vêm do conftest.py,
e cada teste começa com o teste.db recriado e populado pelo seed.
"""
import pytest
from sqlalchemy import select

import app.models as m
from app.db import SessionLocal

API = "/api/v1"
MOTIVO = "Horímetro final conferir"  # exemplo do próprio PRD (docs/01-PRD-PO-plano-3-dias.md)


def url(checklist_id: str, sufixo: str = "") -> str:
    return f"{API}/checklists/{checklist_id}{sufixo}"


def enviar(client, headers, checklist_id, corpo):
    """PUT /checklists/{id} que precisa dar certo (monta o cenário do teste)."""
    r = client.put(url(checklist_id), json=corpo, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def detalhe(client, headers, checklist_id) -> dict:
    r = client.get(url(checklist_id), headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def tipos_dos_eventos(det: dict) -> list[str]:
    return [e["tipo"] for e in det["eventos"]]


# ===========================================================================
# 1. Validação: dados inválidos => 400 VALIDACAO e nada é gravado
# ===========================================================================
def _sem_o_ultimo_item(p):
    p["respostas"] = p["respostas"][:-1]  # remove o item 23


def _horimetro_final_menor_que_o_inicial(p):
    p["horimetro_final"] = p["horimetro_inicial"] - 0.1


def _n_sem_observacao(p):
    item1 = next(r for r in p["respostas"] if r["item_numero"] == 1)
    item1["observacao"] = None


def _n_com_observacao_so_espacos(p):
    item1 = next(r for r in p["respostas"] if r["item_numero"] == 1)
    item1["observacao"] = "   "


CASOS_INVALIDOS = [
    pytest.param(_sem_o_ultimo_item, "respostas", "Faltam respostas", id="falta_um_item"),
    pytest.param(_horimetro_final_menor_que_o_inicial, "horimetro_final", "menor que o inicial",
                 id="horimetro_final_menor_que_inicial"),
    pytest.param(_n_sem_observacao, "respostas", "Item 1 com resposta 'N' exige observação",
                 id="RN02_N_sem_observacao"),
    pytest.param(_n_com_observacao_so_espacos, "respostas", "Item 1 com resposta 'N' exige observação",
                 id="RN02_N_com_observacao_em_branco"),
]


@pytest.mark.parametrize("alterar, campo, trecho_da_mensagem", CASOS_INVALIDOS)
def test_payload_invalido_retorna_400(
    client, headers_a, headers_admin, payload, checklist_id, alterar, campo, trecho_da_mensagem
):
    alterar(payload)

    r = client.put(url(checklist_id), json=payload, headers=headers_a)

    assert r.status_code == 400
    erro = r.json()["erro"]
    assert erro["codigo"] == "VALIDACAO"
    assert any(c["campo"] == campo and trecho_da_mensagem in c["mensagem"] for c in erro["campos"]), erro

    # nada foi gravado
    assert client.get(f"{API}/checklists", headers=headers_admin).json()["itens"] == []


def test_turno_20_02_com_saida_menor_que_entrada_e_aceito(client, headers_a, payload, checklist_id):
    """RN06: o turno T_20_02 cruza a meia-noite (entrada 20:00, saída 02:00)."""
    assert payload["turno"] == "T_20_02"
    assert payload["hora_saida"] < payload["hora_entrada"]

    r = client.put(url(checklist_id), json=payload, headers=headers_a)

    assert r.status_code == 200
    assert r.json()["status"] == "ENVIADO"


# ===========================================================================
# 2. Edição pelo operador: revisao, editado, snapshot e evento (RN07)
# ===========================================================================
def test_edicao_gera_revisao_2_snapshot_e_evento(client, headers_a, payload, checklist_id):
    horimetro_original = payload["horimetro_final"]
    enviar(client, headers_a, checklist_id, payload)

    editado = {**payload, "horimetro_final": 36471.0}
    r = client.put(url(checklist_id), json=editado, headers=headers_a)

    assert r.status_code == 200
    assert r.json() == {
        "id": checklist_id,
        "status": "ENVIADO",
        "revisao": 2,
        "impedido": True,
        "editado": True,
    }

    det = detalhe(client, headers_a, checklist_id)
    assert det["horimetro_final"] == 36471.0
    assert det["revisao"] == 2 and det["editado"] is True
    assert tipos_dos_eventos(det) == ["CRIADO", "EDITADO"]
    evento_editado = det["eventos"][1]
    assert evento_editado["detalhe"]["diff"] == [
        {"campo": "horimetro_final", "de": horimetro_original, "para": 36471.0}
    ]

    # snapshot da versão anterior (revisão 1) guardado no banco
    with SessionLocal() as db:
        snapshots = db.scalars(select(m.Revisao).filter_by(checklist_id=checklist_id)).all()
        assert len(snapshots) == 1
        assert snapshots[0].revisao == 1
        assert snapshots[0].snapshot["horimetro_final"] == horimetro_original


def test_edicao_de_resposta_aparece_no_diff(client, headers_a, payload, checklist_id):
    """Trocar o item 2 de S para N (com observação) vira uma entrada 'respostas[2]' no diff."""
    enviar(client, headers_a, checklist_id, payload)

    editado = {**payload, "respostas": [dict(r) for r in payload["respostas"]]}
    item2 = next(r for r in editado["respostas"] if r["item_numero"] == 2)
    item2.update(resposta="N", origem="MANUAL", observacao="Falha encontrada na revisão")

    r = client.put(url(checklist_id), json=editado, headers=headers_a)
    assert r.status_code == 200 and r.json()["revisao"] == 2

    det = detalhe(client, headers_a, checklist_id)
    assert det["eventos"][-1]["detalhe"]["diff"] == [
        {
            "campo": "respostas[2]",
            "de": {"resposta": "S", "observacao": None},
            "para": {"resposta": "N", "observacao": "Falha encontrada na revisão"},
        }
    ]


# ===========================================================================
# 3. Solicitar correção (admin) e reenvio (operador)
# ===========================================================================
def test_admin_solicita_correcao_com_motivo(client, headers_a, headers_admin, payload, checklist_id):
    enviar(client, headers_a, checklist_id, payload)

    r = client.post(url(checklist_id, "/solicitar-correcao"), json={"motivo": MOTIVO}, headers=headers_admin)

    assert r.status_code == 200
    assert r.json()["status"] == "CORRECAO_SOLICITADA"

    # o operador vê o motivo na lista e no detalhe, e o contador de correção sobe
    lista = client.get(f"{API}/checklists", headers=headers_a).json()
    assert lista["contadores"]["correcao"] == 1
    assert lista["itens"][0]["status"] == "CORRECAO_SOLICITADA"
    assert lista["itens"][0]["motivo_correcao"] == MOTIVO

    det = detalhe(client, headers_a, checklist_id)
    assert det["motivo_correcao"] == MOTIVO
    assert tipos_dos_eventos(det) == ["CRIADO", "CORRECAO_SOLICITADA"]
    assert det["eventos"][1]["detalhe"] == {"motivo": MOTIVO}


@pytest.mark.parametrize("motivo", ["", "   "])
def test_solicitar_correcao_sem_motivo_retorna_400(client, headers_a, headers_admin, payload, checklist_id, motivo):
    enviar(client, headers_a, checklist_id, payload)

    r = client.post(url(checklist_id, "/solicitar-correcao"), json={"motivo": motivo}, headers=headers_admin)

    assert r.status_code == 400
    assert r.json()["erro"]["codigo"] == "VALIDACAO"
    assert detalhe(client, headers_a, checklist_id)["status"] == "ENVIADO"


def test_operador_nao_solicita_correcao_retorna_403(client, headers_a, payload, checklist_id):
    enviar(client, headers_a, checklist_id, payload)

    r = client.post(url(checklist_id, "/solicitar-correcao"), json={"motivo": MOTIVO}, headers=headers_a)

    assert r.status_code == 403
    assert r.json()["erro"]["codigo"] == "PERMISSAO"
    assert detalhe(client, headers_a, checklist_id)["status"] == "ENVIADO"


def test_nao_solicita_correcao_de_checklist_vistado_retorna_409(client, headers_a, headers_admin, payload, checklist_id):
    """RN08: VISTADO é final, nem nova solicitação de correção é aceita."""
    enviar(client, headers_a, checklist_id, payload)
    assert client.post(url(checklist_id, "/vistar"), headers=headers_admin).status_code == 200

    r = client.post(url(checklist_id, "/solicitar-correcao"), json={"motivo": MOTIVO}, headers=headers_admin)

    assert r.status_code == 409
    assert r.json()["erro"]["codigo"] == "ESTADO_INVALIDO"


def test_reenvio_com_edicao_apos_correcao_volta_para_enviado(client, headers_a, headers_admin, payload, checklist_id):
    enviar(client, headers_a, checklist_id, payload)
    client.post(url(checklist_id, "/solicitar-correcao"), json={"motivo": MOTIVO}, headers=headers_admin)

    corrigido = {**payload, "horimetro_final": 36471.0, "confirmacao_correcao": True}
    r = client.put(url(checklist_id), json=corrigido, headers=headers_a)

    assert r.status_code == 200
    assert r.json() == {
        "id": checklist_id,
        "status": "ENVIADO",
        "revisao": 2,
        "impedido": True,
        "editado": True,
    }
    det = detalhe(client, headers_a, checklist_id)
    assert tipos_dos_eventos(det) == ["CRIADO", "CORRECAO_SOLICITADA", "REENVIADO"]
    assert det["eventos"][2]["detalhe"]["confirmacao_correcao"] is True


def test_reenvio_identico_com_confirmacao_volta_para_enviado_sem_nova_revisao(
    client, headers_a, headers_admin, payload, checklist_id
):
    """O operador conferiu e manteve tudo: sai de CORRECAO_SOLICITADA sem criar revisão (RN14)."""
    enviar(client, headers_a, checklist_id, payload)
    client.post(url(checklist_id, "/solicitar-correcao"), json={"motivo": MOTIVO}, headers=headers_admin)

    r = client.put(url(checklist_id), json={**payload, "confirmacao_correcao": True}, headers=headers_a)

    assert r.status_code == 200
    assert r.json() == {
        "id": checklist_id,
        "status": "ENVIADO",
        "revisao": 1,
        "impedido": True,
        "editado": False,
    }
    det = detalhe(client, headers_a, checklist_id)
    assert tipos_dos_eventos(det) == ["CRIADO", "CORRECAO_SOLICITADA", "REENVIADO"]
    assert det["eventos"][2]["detalhe"] == {"diff": [], "confirmacao_correcao": True}


def test_reenvio_identico_sem_confirmacao_mantem_correcao_solicitada(
    client, headers_a, headers_admin, payload, checklist_id
):
    enviar(client, headers_a, checklist_id, payload)
    client.post(url(checklist_id, "/solicitar-correcao"), json={"motivo": MOTIVO}, headers=headers_admin)

    r = client.put(url(checklist_id), json=payload, headers=headers_a)  # confirmacao_correcao=False

    assert r.status_code == 200
    assert r.json()["status"] == "CORRECAO_SOLICITADA"
    assert r.json()["revisao"] == 1
    assert tipos_dos_eventos(detalhe(client, headers_a, checklist_id)) == ["CRIADO", "CORRECAO_SOLICITADA"]