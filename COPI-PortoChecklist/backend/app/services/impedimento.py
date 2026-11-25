# app/services/impedimento.py
#
# Decide se o equipamento está IMPEDIDO de operar.
# Regra: impedido = existe item CRÍTICO respondido com "N" (não conforme).

def calcular_impedimento(respostas: list[dict], itens: list[dict]) -> dict:
    """respostas = [{"item_numero", "resposta", ...}]; itens = [{"numero", "critico", ...}].

    Devolve {"impedido": bool, "itens_criticos_nao_conformes": [números dos itens]}.
    """
    criticos = {i["numero"] for i in itens if i["critico"]}
    nao_conformes = sorted(
        r["item_numero"] for r in respostas
        if r["item_numero"] in criticos and r["resposta"] == "N"
    )
    return {"impedido": bool(nao_conformes), "itens_criticos_nao_conformes": nao_conformes}