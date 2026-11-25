# Rotas que o app consulta para montar a tela de checklist:
#   GET /api/v1/template                                      -> perguntas do checklist ativo
#   GET /api/v1/lookups                                       -> locais, equipamentos e turnos
#   GET /api/v1/equipamentos/{id}/ultimo-horimetro            -> último horímetro registrado
#
# Todas exigem login (header Authorization: Bearer <token>).
#
# Com os dados do seed, o resultado esperado é:
#   /template -> 23 itens, ordenados do 1 ao 23
#   /lookups  -> 2 locais (Cais 99, Cais 100) e 3 guindastes (GUINDASTE-280 a 282)

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.erros import ErroNegocio
from app.models import Checklist, Equipamento, Local, Template
from app.security import usuario_atual

router = APIRouter()
TURNOS = ["T_08_14", "T_14_20", "T_20_02", "T_02_08"]


@router.get("/template")
def template_ativo(db: Session = Depends(get_db), _=Depends(usuario_atual)):
    # Pega o template ativo de maior versão (o mais novo)
    t = db.scalars(
        select(Template).filter_by(ativo=True).order_by(Template.versao.desc())
    ).first()
    if not t:
        raise ErroNegocio(404, "SEM_TEMPLATE", "Nenhum template ativo")

    # t.itens já vem ordenado por número (order_by definido no relationship do models.py);
    # o sorted() abaixo é uma garantia extra para a ordem nunca depender do banco.
    itens = sorted(t.itens, key=lambda i: i.numero)

    return {
        "id": t.id,
        "codigo": t.codigo,
        "versao": t.versao,
        "titulo": t.titulo,
        "itens": [
            {
                "numero": i.numero,
                "descricao": i.descricao,
                "critico": i.critico,
                "permite_na": i.permite_na,
            }
            for i in itens
        ],
    }


@router.get("/lookups")
def lookups(db: Session = Depends(get_db), _=Depends(usuario_atual)):
    # Só itens ativos, em ordem alfabética (resultado sempre na mesma ordem)
    locais = db.scalars(select(Local).filter_by(ativo=True).order_by(Local.nome)).all()
    equipamentos = db.scalars(
        select(Equipamento).filter_by(ativo=True).order_by(Equipamento.identificacao)
    ).all()

    return {
        "locais": [{"id": l.id, "nome": l.nome} for l in locais],
        "equipamentos": [{"id": e.id, "identificacao": e.identificacao} for e in equipamentos],
        "turnos": TURNOS,
    }


@router.get("/equipamentos/{equipamento_id}/ultimo-horimetro")  # BE-10
def ultimo_horimetro(
    equipamento_id: str, db: Session = Depends(get_db), _=Depends(usuario_atual)
):
    # Último checklist recebido desse equipamento que tenha horímetro final preenchido
    c = db.scalars(
        select(Checklist)
        .where(
            Checklist.equipamento_id == equipamento_id,
            Checklist.horimetro_final.is_not(None),
        )
        .order_by(Checklist.recebido_em.desc())
    ).first()
    return {"horimetro_final": c.horimetro_final if c else None}