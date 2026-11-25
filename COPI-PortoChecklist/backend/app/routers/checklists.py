# app/routers/checklists.py
#
# PUT /api/v1/checklists/{checklist_id}
#
# O id é um UUID gerado pelo APP, então a mesma rota cria e edita
# (reenviar a mesma requisição não duplica nada).

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.erros import ErroNegocio
from app.models import (Checklist, Equipamento, Evento, Local, Resposta, Revisao, Template,
                        TemplateItem, Usuario)
from app.schemas import ChecklistIn, CorrecaoIn
from app.security import usuario_atual, exige_admin
from app.services.eventos import CAMPOS, calcular_diff
from app.services.impedimento import calcular_impedimento
from app.services.validacao import validar_checklist

router = APIRouter()

# Campos de controle: não entram no diff, mas são gravados e vão para o snapshot
CAMPOS_EXTRAS = ["usou_lote", "itens_marcados_lote", "itens_alterados_apos_lote",
                 "inicio_preenchimento_em", "finalizado_em", "duracao_segundos", "assinatura_operador"]


def itens_do_template(db: Session, template_id: str) -> list[dict]:
    t = db.get(Template, template_id)
    if not t:
        raise ErroNegocio(400, "VALIDACAO", "template_id inexistente")
    return [{"numero": i.numero, "critico": i.critico, "permite_na": i.permite_na} for i in t.itens]


def _conferir_referencias(db: Session, checklist_id: str, dados: dict) -> list[dict]:
    """Confere o que depende do banco: id é UUID; equipamento e local existem e estão ativos."""
    erros = []
    try:
        uuid.UUID(checklist_id)
    except ValueError:
        erros.append({"campo": "id", "mensagem": "Id do checklist deve ser um UUID válido."})
    eq = db.get(Equipamento, dados["equipamento_id"])
    if not eq or not eq.ativo:
        erros.append({"campo": "equipamento_id", "mensagem": "Equipamento não encontrado ou inativo."})
    loc = db.get(Local, dados["local_id"])
    if not loc or not loc.ativo:
        erros.append({"campo": "local_id", "mensagem": "Local não encontrado ou inativo."})
    return erros


def checklist_para_dict(c: Checklist) -> dict:
    """Mesma forma do corpo do PUT: serve para o diff e para o snapshot."""
    d = {campo: getattr(c, campo) for campo in CAMPOS + CAMPOS_EXTRAS}
    d["respostas"] = [{"item_numero": r.item_numero, "resposta": r.resposta, "origem": r.origem,
                       "observacao": r.observacao} for r in c.respostas]
    return d


@router.put("/checklists/{checklist_id}")
def salvar_checklist(checklist_id: str, body: ChecklistIn,
                     db: Session = Depends(get_db), usuario=Depends(usuario_atual)):
    # 1. Só OPERADOR envia
    if usuario.papel != "OPERADOR":
        raise ErroNegocio(403, "PERMISSAO", "Somente o operador envia checklists")

    # 2. Validação (400 se houver erros)
    dados = body.model_dump()
    itens = itens_do_template(db, dados["template_id"])
    erros = _conferir_referencias(db, checklist_id, dados) + validar_checklist(dados, itens)
    if erros:
        raise ErroNegocio(400, "VALIDACAO", "Checklist inválido", erros)

    # 3. Impedido
    impedido = calcular_impedimento(dados["respostas"], itens)["impedido"]

    # 4. Já existe?
    c = db.get(Checklist, checklist_id)
    if c is None:                                           # --- criação ---
        c = Checklist(id=checklist_id, operador_id=usuario.id, status="ENVIADO", revisao=1, editado=False)
        _aplicar(c, dados, impedido)
        db.add(c)
        db.add(Evento(checklist_id=checklist_id, tipo="CRIADO", usuario_id=usuario.id))
    else:                                                   # --- edição / reenvio ---
        if c.operador_id != usuario.id:                     # (a)
            raise ErroNegocio(403, "PERMISSAO", "Este checklist é de outro operador")
        if c.status == "VISTADO":                           # (b)
            raise ErroNegocio(409, "TRAVADO", "Checklist já vistado: não pode ser alterado")
        antigo = checklist_para_dict(c)
        diff = calcular_diff(antigo, dados)
        if not diff:                                        # (c) reenvio idêntico
            if c.status == "CORRECAO_SOLICITADA" and dados["confirmacao_correcao"]:
                # o operador conferiu e manteve tudo: sai de "correção solicitada" sem nova revisão
                c.status = "ENVIADO"
                db.add(Evento(checklist_id=c.id, tipo="REENVIADO", usuario_id=usuario.id,
                              detalhe={"diff": [], "confirmacao_correcao": True}))
                db.commit()
            return _resumo(c)
        # (d) houve mudança: guarda a versão antiga e aplica a nova
        db.add(Revisao(checklist_id=c.id, revisao=c.revisao, snapshot=antigo))
        tipo = "REENVIADO" if c.status == "CORRECAO_SOLICITADA" else "EDITADO"
        db.add(Evento(checklist_id=c.id, tipo=tipo, usuario_id=usuario.id,
                      detalhe={"diff": diff, "confirmacao_correcao": dados["confirmacao_correcao"]}))
        c.revisao += 1
        c.editado = True
        c.status = "ENVIADO"
        _aplicar(c, dados, impedido)

    # 5. Commit e resposta
    db.commit()
    return _resumo(c)


def _aplicar(c: Checklist, dados: dict, impedido: bool) -> None:
    """Copia os dados recebidos para o checklist e recria as respostas."""
    for campo in CAMPOS + CAMPOS_EXTRAS + ["criado_no_dispositivo_em", "app_versao"]:
        setattr(c, campo, dados.get(campo))
    c.impedido = impedido
    c.respostas.clear()                                     # delete-orphan apaga as antigas
    for r in dados["respostas"]:
        c.respostas.append(Resposta(item_numero=r["item_numero"], resposta=r["resposta"],
                                    origem=r.get("origem", "MANUAL"), observacao=r.get("observacao")))


def _resumo(c: Checklist) -> dict:
    return {"id": c.id, "status": c.status, "revisao": c.revisao, "impedido": c.impedido, "editado": c.editado}

def _carregar(db: Session, checklist_id: str) -> Checklist:
    """Busca um checklist pelo ID ou retorna erro 404."""
    c = db.get(Checklist, checklist_id)

    if not c:
        raise ErroNegocio( 404, "NAO_ENCONTRADO", "Checklist não encontrado")
    return c

@router.post("/checklists/{checklist_id}/vistar")
def vistar(
    checklist_id: str,
    db: Session = Depends(get_db),
    admin=Depends(exige_admin)
):
    """Permite que um administrador realize a vistoria de um checklist."""

    # 1. Buscar o checklist
    c = _carregar(db, checklist_id)

    # 2. Verificar se está disponível para vistoria
    if c.status != "ENVIADO":
        raise ErroNegocio( 409, "ESTADO_INVALIDO", f"Não é possível vistar um checklist em {c.status}")

    # 3. Atualizar os dados da vistoria
    c.status = "VISTADO"
    c.vistado_por = admin.id
    c.vistado_em = datetime.now(timezone.utc)

    # 4. Registrar evento no histórico
    db.add(Evento(checklist_id=c.id, tipo="VISTADO", usuario_id=admin.id))

    # 5. Salvar alterações
    db.commit()

    # 6. Retornar resumo
    return _resumo(c)

@router.post("/checklists/{checklist_id}/solicitar-correcao")
def solicitar_correcao(
    checklist_id: str,
    body: CorrecaoIn,
    db: Session = Depends(get_db),
    admin=Depends(exige_admin)
):
    """Permite que um administrador solicite correção de um checklist."""

    # 1. Validar o motivo
    motivo = body.motivo.strip()

    if not motivo:
        raise ErroNegocio(400, "VALIDACAO", "Informe o motivo da correção")

    # 2. Buscar o checklist
    c = _carregar(db, checklist_id)

    # 3. Verificar se pode receber solicitação de correção
    if c.status != "ENVIADO":
        raise ErroNegocio(409, "ESTADO_INVALIDO", f"Não é possível solicitar correção em {c.status}")

    # 4. Atualizar o status
    c.status = "CORRECAO_SOLICITADA"

    # 5. Registrar o evento e o motivo
    db.add(
        Evento( checklist_id=c.id, tipo="CORRECAO_SOLICITADA", usuario_id=admin.id, detalhe={"motivo": motivo}))

    # 6. Salvar alterações
    db.commit()

    # 7. Retornar resumo
    return _resumo(c)

# ---------------------------------------------------------------------------
# Consultas (GET)
# ---------------------------------------------------------------------------
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


def _detalhe(db, c: Checklist) -> dict:
    """Checklist completo: o resumo da lista + os mesmos campos do corpo do PUT."""
    itens = {i.numero: i for i in db.query(TemplateItem).filter_by(template_id=c.template_id)}
    vistador = db.get(Usuario, c.vistado_por) if c.vistado_por else None
    eventos = (
        db.query(Evento)
        .filter(Evento.checklist_id == c.id)
        .order_by(Evento.criado_em.asc())
        .all()
    )

    historico = []

    for evento in eventos:
        usuario_evento = db.get(Usuario, evento.usuario_id)

        historico.append({
            "tipo": evento.tipo,
            "usuario": usuario_evento.nome if usuario_evento else None,
            "detalhe": evento.detalhe,
            "criado_em": evento.criado_em.isoformat() if evento.criado_em else None
        })

    return {**_resumo_lista(db, c),
            "template_id": c.template_id, 
            "equipamento_id": c.equipamento_id, 
            "local_id": c.local_id,
            "data_turno": c.data_turno, 
            "turno": c.turno, "navio": c.navio,
            "eventos": historico,
            "horimetro_inicial": c.horimetro_inicial, 
            "horimetro_final": c.horimetro_final,
            "combustivel_pct": c.combustivel_pct,
            "hora_entrada": c.hora_entrada,
            "hora_saida": c.hora_saida,
            "observacao_geral": c.observacao_geral, 
            "assinatura_operador": c.assinatura_operador,
            "usou_lote": c.usou_lote, 
            "itens_marcados_lote": c.itens_marcados_lote,
            "itens_alterados_apos_lote": c.itens_alterados_apos_lote,
            "inicio_preenchimento_em": c.inicio_preenchimento_em, 
            "finalizado_em": c.finalizado_em,
            "duracao_segundos": c.duracao_segundos,
            "confirmacao_correcao": False,          # só faz sentido no PUT; aqui é sempre false
            "criado_no_dispositivo_em": c.criado_no_dispositivo_em, 
            "app_versao": c.app_versao,
            "vistado": ({"por": {"id": vistador.id, "nome": vistador.nome},
                         "em": c.vistado_em.isoformat() if c.vistado_em else None}
                        if vistador else None),
            "respostas": [{"item_numero": r.item_numero,
                           "descricao": itens[r.item_numero].descricao if r.item_numero in itens else None,
                           "critico": itens[r.item_numero].critico if r.item_numero in itens else None,
                           "resposta": r.resposta, "origem": r.origem, "observacao": r.observacao}
                          for r in c.respostas]}



@router.get("/checklists/{checklist_id}")
def obter(checklist_id: str, db: Session = Depends(get_db), usuario=Depends(usuario_atual)):
    c = db.get(Checklist, checklist_id)
    if c is None:
        raise ErroNegocio(404, "NAO_ENCONTRADO", "Checklist não encontrado")
    if usuario.papel == "OPERADOR" and c.operador_id != usuario.id:
        raise ErroNegocio(403, "PERMISSAO", "Este checklist é de outro operador")
    return _detalhe(db, c)