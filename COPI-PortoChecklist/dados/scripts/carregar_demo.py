"""Carrega 3 checklists de demonstração na API (BE-12 / DA-02).

    python dados/scripts/carregar_demo.py http://localhost:8000/api/v1
    python dados/scripts/carregar_demo.py http://192.168.0.15:8000/api/v1

Pré-requisitos: servidor no ar e o seed já rodado (usuários, locais, equipamentos e template).
Usa só a biblioteca padrão do Python (não precisa de venv nem de pip install).

Os 3 checklists, enviados como o operador do caso da foto (matrícula/PIN de dados/seed):
  1. SEM PROBLEMAS  - GUINDASTE-281, 23 respostas "S"
  2. COM CRÍTICO    - o próprio caso da foto (GUINDASTE-280, itens 1, 10 e 22 com "N" => impedido)
  3. EDITADO        - GUINDASTE-282, enviado e depois corrigido (revisao 2, selo "Editado")

Pode rodar de novo: os IDs são fixos e um checklist que já existe na API é pulado
(nunca reenvia nem duplica). Para recomeçar a demo do zero: apague backend/checklist.db e rode o seed.
"""
import copy
import json
import sys
import uuid
from pathlib import Path
from urllib import error, request

DADOS = Path(__file__).resolve().parents[1]  # pasta dados/
CASO_FOTO = DADOS / "fixtures" / "caso_foto.json"
SEED_DEMO = DADOS / "seed" / "demo_usuarios_locais_equipamentos.json"

URL_PADRAO = "http://localhost:8000/api/v1"
# IDs fixos (UUID v5): o mesmo nome gera sempre o mesmo UUID, o que torna o script reexecutável
_NS = uuid.UUID("6f1d9c52-3a7b-4e0a-9d51-0c5a7b2e4f10")
CHAVES_SO_DO_FIXTURE = {"descricao", "id", "operador_matricula", "equipamento", "local", "esperado"}


class ErroApi(Exception):
    pass


def chamar(metodo: str, url: str, corpo: dict | None = None, token: str | None = None):
    """Requisição JSON. Devolve (status, json). Só levanta ErroApi se não houver resposta da API."""
    dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8") if corpo is not None else None
    req = request.Request(url, data=dados, method=metodo)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8") or "null")
    except error.HTTPError as e:
        texto = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(texto)
        except ValueError:
            return e.code, {"texto": texto}
    except error.URLError as e:
        raise ErroApi(f"Não consegui falar com {url}: {e.reason}. O servidor está no ar?") from e


def exigir(status: int, resposta, esperado: int, o_que: str):
    if status != esperado:
        raise ErroApi(f"{o_que}: HTTP {status} (esperado {esperado}) -> {json.dumps(resposta, ensure_ascii=False)}")
    return resposta


def montar_checklists(caso: dict, template_id: str, equipamentos: dict, locais: dict) -> list[dict]:
    """Monta os 3 payloads a partir do caso da foto, trocando nomes por IDs de /lookups e /template."""

    def base(equipamento: str, local: str) -> dict:
        p = {k: v for k, v in caso.items() if k not in CHAVES_SO_DO_FIXTURE}
        p.update(template_id=template_id, equipamento_id=equipamentos[equipamento], local_id=locais[local])
        return p

    def sem_problemas(p: dict) -> dict:
        p["respostas"] = [{"item_numero": r["item_numero"], "resposta": "S", "origem": "LOTE"}
                          for r in p["respostas"]]
        p.update(observacao_geral=None, usou_lote=True, itens_marcados_lote=len(p["respostas"]),
                 itens_alterados_apos_lote=0)
        return p

    # 1. sem problemas
    ok = sem_problemas(base("GUINDASTE-281", "Cais 100"))
    ok.update(turno="T_08_14", hora_entrada="08:00", hora_saida="14:00", horimetro_inicial=1200.0,
              horimetro_final=1206.0, combustivel_pct=80, inicio_preenchimento_em="2026-11-03T11:02:10Z",
              finalizado_em="2026-11-03T11:02:40Z", duracao_segundos=30)

    # 2. com crítico = o caso da foto, sem alterações
    critico = base(caso["equipamento"], caso["local"])

    # 3. editado: enviado como abaixo e depois corrigido (horímetro final)
    editado = sem_problemas(base("GUINDASTE-282", "Cais 99"))
    editado.update(turno="T_14_20", hora_entrada="14:00", hora_saida="20:00", horimetro_inicial=2300.0,
                   horimetro_final=2305.5, combustivel_pct=60, inicio_preenchimento_em="2026-11-03T17:02:10Z",
                   finalizado_em="2026-11-03T17:02:40Z", duracao_segundos=30)
    editado_depois = copy.deepcopy(editado)
    editado_depois["horimetro_final"] = 2306.0

    def novo_id(nome: str) -> str:
        return str(uuid.uuid5(_NS, nome))

    return [
        {"nome": "sem problemas", "id": novo_id("demo-sem-problemas"), "envios": [ok]},
        {"nome": "com crítico", "id": novo_id("demo-com-critico"), "envios": [critico]},
        {"nome": "editado", "id": novo_id("demo-editado"), "envios": [editado, editado_depois]},
    ]


def main(base_url: str) -> int:
    base_url = base_url.rstrip("/")
    caso = json.loads(CASO_FOTO.read_text(encoding="utf-8"))
    demo = json.loads(SEED_DEMO.read_text(encoding="utf-8"))
    operador = next(u for u in demo["usuarios"] if u["matricula"] == caso["operador_matricula"])

    st, r = chamar("GET", f"{base_url}/health")
    exigir(st, r, 200, "Health")
    print(f"API ok em {base_url} (versão {r.get('versao')})")

    st, r = chamar("POST", f"{base_url}/auth/login", {"matricula": operador["matricula"], "pin": operador["pin"]})
    token = exigir(st, r, 200, f"Login da matrícula {operador['matricula']} (rodou o seed?)")["access_token"]

    st, tpl = chamar("GET", f"{base_url}/template", token=token)
    exigir(st, tpl, 200, "Template")
    st, lk = chamar("GET", f"{base_url}/lookups", token=token)
    exigir(st, lk, 200, "Lookups")
    equipamentos = {e["identificacao"]: e["id"] for e in lk["equipamentos"]}
    locais = {x["nome"]: x["id"] for x in lk["locais"]}

    resultado = []
    for item in montar_checklists(caso, tpl["id"], equipamentos, locais):
        url = f"{base_url}/checklists/{item['id']}"
        st, _ = chamar("GET", url, token=token)
        if st == 200:
            print(f"  - {item['nome']}: já existe, pulado")
            continue
        for envio in item["envios"]:
            st, r = chamar("PUT", url, envio, token)
            exigir(st, r, 200, f"Envio do checklist '{item['nome']}'")
        resultado.append((item["nome"], r))
        print(f"  + {item['nome']}: status={r['status']} revisao={r['revisao']} "
              f"impedido={r['impedido']} editado={r['editado']}")

    print(f"Concluído: {len(resultado)} criado(s). O admin já pode ver a lista.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else URL_PADRAO))
    except ErroApi as e:
        print(f"ERRO: {e}", file=sys.stderr)
        sys.exit(1)