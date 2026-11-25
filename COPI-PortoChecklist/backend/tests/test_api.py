"""Testes de integração da API (Pytest + FastAPI TestClient).

Endpoints reais usados (todos com prefixo /api/v1):
    GET  /health                           público
    POST /auth/login                       {matricula, pin} -> {access_token, usuario}
    GET  /template                         template ativo (id + 23 itens)
    GET  /lookups                          locais e equipamentos com seus IDs
    PUT  /checklists/{id}                  OPERADOR cria/edita (idempotente); 409 se VISTADO
    GET  /checklists                       lista (operador vê só os seus; admin vê todos)
    GET  /checklists/{id}                  detalhe (operador só abre os seus -> 403)
    POST /checklists/{id}/vistar           só ADMIN, só em ENVIADO

Login: fixtures headers_a / headers_b / headers_admin do conftest.py (usam a função auxiliar token).
Dados: usuários/locais/equipamentos vêm do seed (dados/seed) e o payload do checklist vem de
dados/fixtures/caso_foto.json, trocando os NOMES (equipamento, local) pelos IDs reais de
GET /lookups e GET /template, como manda o contrato (docs/00-contrato.md, seção 6).

Isolamento: o conftest.py recria e popula o teste.db antes de CADA teste; nenhum teste
depende de dados deixados por outro.
"""
API = "/api/v1"


# ---------------------------------------------------------------------------
# Funções auxiliares (as fixtures caso_foto, payload, headers_*, checklist_id vêm do conftest.py)
# ---------------------------------------------------------------------------
def url(checklist_id: str, sufixo: str = "") -> str:
    return f"{API}/checklists/{checklist_id}{sufixo}"


def enviar(client, headers, checklist_id, payload):
    """PUT /checklists/{id} que precisa dar certo (usado para montar o cenário do teste)."""
    r = client.put(url(checklist_id), json=payload, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------------------
# Cenário 1 - API inicializa e o acesso permitido responde 200
# ---------------------------------------------------------------------------
def test_01_api_inicia_e_acesso_permitido_retorna_200(client, headers_a, payload, checklist_id, caso_foto):
    r = client.get(f"{API}/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    # Acesso permitido: o operador dono envia o caso da foto (mesmo sendo "impedido")
    r = client.put(url(checklist_id), json=payload, headers=headers_a)
    assert r.status_code == 200
    esperado = caso_foto["esperado"]
    assert r.json() == {
        "id": checklist_id,
        "status": esperado["status_apos_envio"],  # ENVIADO
        "revisao": 1,
        "impedido": esperado["impedido"],  # True: itens críticos 1, 10 e 22 com "N"
        "editado": False,
    }


# ---------------------------------------------------------------------------
# Cenário 2 - operação não permitida ao perfil: 403
#   A API não devolve 403 por causa do flag "impedido". O 403 real do PUT é
#   "Somente o operador envia checklists": o ADMIN não pode criar/editar checklist.
# ---------------------------------------------------------------------------
def test_02_operacao_nao_permitida_ao_perfil_retorna_403(client, headers_admin, payload, checklist_id):
    r = client.put(url(checklist_id), json=payload, headers=headers_admin)

    assert r.status_code == 403
    assert r.json()["erro"]["codigo"] == "PERMISSAO"

    # nada foi gravado
    lista = client.get(f"{API}/checklists", headers=headers_admin)
    assert lista.status_code == 200
    assert lista.json()["itens"] == []


# ---------------------------------------------------------------------------
# Cenário 3 - mesmo ID enviado duas vezes
#   O contrato define o PUT como idempotente (RN11): reenviar é seguro. O comportamento
#   real é 200 nas duas vezes e UM único registro; 409 só existe para checklist VISTADO.
# ---------------------------------------------------------------------------
def test_03_mesmo_id_duas_vezes_nao_duplica_registro(client, headers_a, headers_admin, payload, checklist_id):
    primeiro = client.put(url(checklist_id), json=payload, headers=headers_a)
    segundo = client.put(url(checklist_id), json=payload, headers=headers_a)

    assert primeiro.status_code == 200
    assert segundo.status_code == 200
    assert segundo.json() == primeiro.json()
    assert segundo.json()["revisao"] == 1
    assert segundo.json()["editado"] is False

    lista = client.get(f"{API}/checklists", headers=headers_admin).json()
    assert [c["id"] for c in lista["itens"]] == [checklist_id]
    assert lista["contadores"]["pendentes"] == 1


# ---------------------------------------------------------------------------
# Cenário 4 - operador tentando vistar: 403
# ---------------------------------------------------------------------------
def test_04_operador_nao_pode_vistar_retorna_403(client, headers_a, payload, checklist_id):
    enviar(client, headers_a, checklist_id, payload)

    r = client.post(url(checklist_id, "/vistar"), headers=headers_a)

    assert r.status_code == 403
    assert r.json()["erro"]["codigo"] == "PERMISSAO"

    detalhe = client.get(url(checklist_id), headers=headers_a).json()
    assert detalhe["status"] == "ENVIADO"
    assert detalhe["vistado"] is None


# ---------------------------------------------------------------------------
# Cenário 5 - administrador vistando: 200
# ---------------------------------------------------------------------------
def test_05_admin_vista_checklist_retorna_200(client, headers_a, headers_admin, admin_demo, payload, checklist_id):
    enviar(client, headers_a, checklist_id, payload)

    r = client.post(url(checklist_id, "/vistar"), headers=headers_admin)

    assert r.status_code == 200
    assert r.json()["id"] == checklist_id
    assert r.json()["status"] == "VISTADO"

    detalhe = client.get(url(checklist_id), headers=headers_admin).json()
    assert detalhe["status"] == "VISTADO"
    assert detalhe["vistado"]["por"]["nome"] == admin_demo["nome"]
    assert detalhe["vistado"]["em"] is not None
    tipos = [e["tipo"] for e in detalhe["eventos"]]
    assert "CRIADO" in tipos and "VISTADO" in tipos


# ---------------------------------------------------------------------------
# Cenário 6 - administrador vistando de novo a mesma vistoria: 409
# ---------------------------------------------------------------------------
def test_06_admin_vistar_novamente_retorna_409(client, headers_a, headers_admin, payload, checklist_id):
    enviar(client, headers_a, checklist_id, payload)
    assert client.post(url(checklist_id, "/vistar"), headers=headers_admin).status_code == 200

    r = client.post(url(checklist_id, "/vistar"), headers=headers_admin)

    assert r.status_code == 409
    assert r.json()["erro"]["codigo"] == "ESTADO_INVALIDO"
    assert "VISTADO" in r.json()["erro"]["mensagem"]


# ---------------------------------------------------------------------------
# Cenário 7 - PUT depois de vistado: 409 (checklist travado)
# ---------------------------------------------------------------------------
def test_07_put_apos_vistado_retorna_409(client, headers_a, headers_admin, payload, checklist_id):
    enviar(client, headers_a, checklist_id, payload)
    assert client.post(url(checklist_id, "/vistar"), headers=headers_admin).status_code == 200

    # tenta alterar o horímetro final com um payload válido
    alterado = {**payload, "horimetro_final": payload["horimetro_final"] + 1}
    r = client.put(url(checklist_id), json=alterado, headers=headers_a)

    assert r.status_code == 409
    assert r.json()["erro"]["codigo"] == "TRAVADO"

    # o checklist continua exatamente como foi vistado
    detalhe = client.get(url(checklist_id), headers=headers_a).json()
    assert detalhe["horimetro_final"] == payload["horimetro_final"]
    assert detalhe["revisao"] == 1
    assert detalhe["editado"] is False


# ---------------------------------------------------------------------------
# Cenário 8 - operador A tentando ver o checklist do operador B: 403
# ---------------------------------------------------------------------------
def test_08_operador_nao_ve_checklist_de_outro_operador_retorna_403(
    client, headers_a, headers_b, payload, checklist_id
):
    enviar(client, headers_b, checklist_id, payload)  # o checklist pertence ao operador B

    r = client.get(url(checklist_id), headers=headers_a)

    assert r.status_code == 403
    assert r.json()["erro"]["codigo"] == "PERMISSAO"

    # controle: o dono (B) consegue abrir o próprio checklist
    assert client.get(url(checklist_id), headers=headers_b).status_code == 200