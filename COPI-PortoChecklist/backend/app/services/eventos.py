# app/services/eventos.py
#
# Compara duas versões do checklist (a salva e a que chegou) para o histórico.
#
# O diff é uma LISTA de mudanças; lista vazia = nada mudou. Exemplo:
#   [{"campo": "turno", "de": "T_08_14", "para": "T_14_20"},
#    {"campo": "respostas[3]",
#     "de": {"resposta": "S", "observacao": None},
#     "para": {"resposta": "N", "observacao": "Rádio falhando"}}]

# Campos que contam como mudança de verdade.
# (Campos de controle - lote, tempos, assinatura, versão do app - não entram no diff.)
CAMPOS = [
    "template_id", "equipamento_id", "local_id", "data_turno", "turno", "navio",
    "horimetro_inicial", "horimetro_final", "combustivel_pct", "hora_entrada",
    "hora_saida", "observacao_geral",
]


def _resposta(r: dict | None) -> dict | None:
    """Reduz a resposta ao que importa; '' e None na observação contam como iguais."""
    if r is None:
        return None
    return {"resposta": r["resposta"], "observacao": r.get("observacao") or None}


def calcular_diff(antigo: dict, novo: dict) -> list[dict]:
    """antigo e novo têm a mesma forma do corpo do PUT (campos + lista 'respostas')."""
    diff: list[dict] = []

    for campo in CAMPOS:
        if antigo.get(campo) != novo.get(campo):
            diff.append({"campo": campo, "de": antigo.get(campo), "para": novo.get(campo)})

    antigas = {r["item_numero"]: _resposta(r) for r in antigo["respostas"]}
    novas = {r["item_numero"]: _resposta(r) for r in novo["respostas"]}
    for numero in sorted(antigas.keys() | novas.keys()):
        if antigas.get(numero) != novas.get(numero):
            diff.append({
                "campo": f"respostas[{numero}]",
                "de": antigas.get(numero),
                "para": novas.get(numero),
            })

    return diff