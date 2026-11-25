# app/services/validacao.py
#
# Regras de preenchimento do checklist. É uma função "pura": recebe dicionários e
# devolve a lista de erros, sem acessar o banco (por isso é fácil de testar).
#
#     erros = validar_checklist(dados, itens)
#     # erros == []  -> tudo certo
#     # erros == [{"campo": "turno", "mensagem": "..."}, ...]

from collections import Counter
from datetime import date, datetime

from app.routers.templates import TURNOS


def _hora_valida(valor: str) -> bool:
    """Aceita só o formato HH:MM (ex.: 08:30)."""
    try:
        datetime.strptime(valor, "%H:%M")
        return len(valor) == 5
    except ValueError:
        return False


def validar_checklist(dados: dict, itens: list[dict]) -> list[dict]:
    """dados = corpo do PUT (body.model_dump()); itens = itens do template
    no formato [{"numero", "critico", "permite_na"}, ...]."""
    erros: list[dict] = []

    def erro(campo: str, mensagem: str) -> None:
        erros.append({"campo": campo, "mensagem": mensagem})

    # Turno, data e horas
    if dados["turno"] not in TURNOS:
        erro("turno", f"Turno inválido. Use um destes: {', '.join(TURNOS)}.")
    try:
        if len(dados["data_turno"]) != 10:
            raise ValueError
        date.fromisoformat(dados["data_turno"])
    except ValueError:
        erro("data_turno", "Data inválida. Use o formato AAAA-MM-DD.")
    if not _hora_valida(dados["hora_entrada"]):
        erro("hora_entrada", "Hora inválida. Use o formato HH:MM.")
    if dados["hora_saida"] is not None and not _hora_valida(dados["hora_saida"]):
        erro("hora_saida", "Hora inválida. Use o formato HH:MM.")

    # Números
    if not 0 <= dados["combustivel_pct"] <= 100:
        erro("combustivel_pct", "Combustível deve estar entre 0 e 100.")
    if dados["horimetro_inicial"] < 0:
        erro("horimetro_inicial", "Horímetro inicial não pode ser negativo.")
    final = dados["horimetro_final"]
    if final is not None and final < dados["horimetro_inicial"]:
        erro("horimetro_final", "Horímetro final não pode ser menor que o inicial.")

    # Respostas
    por_numero = {i["numero"]: i for i in itens}
    enviados = [r["item_numero"] for r in dados["respostas"]]

    for numero, qtd in sorted(Counter(enviados).items()):
        if qtd > 1:
            erro("respostas", f"Item {numero} aparece mais de uma vez.")
    for numero in sorted(set(enviados) - set(por_numero)):
        erro("respostas", f"Item {numero} não existe neste template.")
    faltando = sorted(set(por_numero) - set(enviados))
    if faltando:
        erro("respostas", f"Faltam respostas para os itens: {', '.join(map(str, faltando))}.")
    for r in dados["respostas"]:
        item = por_numero.get(r["item_numero"])
        if item and r["resposta"] == "NA" and not item["permite_na"]:
            erro("respostas", f"Item {r['item_numero']} não aceita 'NA'.")
        # RN02: resposta "N" exige observação (texto vazio ou só espaços não vale)
        if r["resposta"] == "N" and not (r.get("observacao") or "").strip():
            erro("respostas", f"Item {r['item_numero']} com resposta 'N' exige observação.")

    return erros