"""
Endpoints de gerenciamento de checklists portuárias (FastAPI).

Registro na aplicação (main.py):

    from fastapi import FastAPI
    from routers import checklists

    app = FastAPI(title="PortData")
    app.include_router(checklists.router)

Os endpoints não contêm regras de negócio: validam a entrada (schemas), chamam
services.py (regras) ou crud.py (leitura, listagem e exclusão, que não possuem
regra adicional) e traduzem as exceções em respostas HTTP:

    ChecklistNaoEncontradaError  -> 404
    OperacaoNaoPermitidaError    -> 409  (inclui checklist finalizada e item crítico reprovado)
    DadosInvalidosError          -> 422  (inclui pendências e horímetro inválido)
"""

from contextlib import contextmanager
from typing import Iterator, Optional

from fastapi import (
    APIRouter, Depends, HTTPException, Path,
    Query, Request, Response,
)
from fastapi import status as http_status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from crud import (
    LIMITE_MAXIMO_LISTAGEM,
    ChecklistNaoEncontradaError,
    DadosInvalidosError,
    OperacaoNaoPermitidaError,
    delete_checklist,
    get_checklist,
    get_checklists,
)
from database import get_db
from schemas import ChecklistCreate, ChecklistResponse, ChecklistUpdate, StatusChecklist
from services import (
    SituacaoChecklist,
    create_checklist_service,
    evaluate_checklist,
    finalize_checklist,
    update_checklist_service,
)

router = APIRouter(prefix="/checklists", tags=["Checklists"])


# --------------------------------------------------------------------------- #
# Schemas de resposta específicos destas rotas
# --------------------------------------------------------------------------- #
class AvaliacaoResponse(BaseModel):
    """Situação da checklist segundo as regras de negócio (services.Avaliacao)."""

    model_config = ConfigDict(from_attributes=True)

    situacao: SituacaoChecklist
    mensagem: str
    pode_finalizar: bool
    pendencias: list[str]
    pendencias_finalizacao: list[str]
    bloqueios: list[str]
    alertas: list[str]


class ChecklistComAvaliacaoResponse(BaseModel):
    """Checklist gravada junto com a avaliação de sua situação."""

    model_config = ConfigDict(from_attributes=True)

    checklist: ChecklistResponse
    avaliacao: AvaliacaoResponse


class ErroResponse(BaseModel):
    """Corpo de erro das regras de negócio: `detail.mensagem` e, quando houver, detalhes."""

    detail: dict


# --------------------------------------------------------------------------- #
# Tradução de erros
# --------------------------------------------------------------------------- #
def _detalhe(exc: Exception) -> dict:
    detalhe: dict = {"mensagem": str(exc)}
    for atributo in ("pendencias", "bloqueios", "erros"):
        valor = getattr(exc, atributo, None)
        if valor:
            detalhe[atributo] = valor
    return detalhe


@contextmanager
def _traduzir_erros() -> Iterator[None]:
    """Converte as exceções do CRUD/services em HTTPException."""
    try:
        yield
    except ChecklistNaoEncontradaError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail=_detalhe(exc)
        ) from exc
    except OperacaoNaoPermitidaError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT, detail=_detalhe(exc)
        ) from exc
    except DadosInvalidosError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail=_detalhe(exc)
        ) from exc


def _com_avaliacao(resultado) -> ChecklistComAvaliacaoResponse:
    """Converte o ResultadoChecklist dos services no schema de resposta."""
    return ChecklistComAvaliacaoResponse.model_validate(resultado, from_attributes=True)


_NAO_ENCONTRADA = {
    http_status.HTTP_404_NOT_FOUND: {
        "model": ErroResponse,
        "description": "Checklist não encontrada.",
    }
}
_CONFLITO = {
    http_status.HTTP_409_CONFLICT: {
        "model": ErroResponse,
        "description": "Operação não permitida pelas regras de negócio.",
    }
}
_INVALIDA = {
    http_status.HTTP_422_UNPROCESSABLE_ENTITY: {
        "description": "Dados inválidos ou checklist com pendências.",
    }
}

ChecklistId = Path(..., ge=1, description="Identificador da checklist.")


# --------------------------------------------------------------------------- #
# Rotas
# --------------------------------------------------------------------------- #
@router.post(
    "",
    response_model=ChecklistComAvaliacaoResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="Criar checklist",
    responses={**_CONFLITO, **_INVALIDA},
)
def criar_checklist(
    payload: ChecklistCreate,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Cria uma checklist com seus 23 itens. Pode nascer como rascunho, com campos em branco.
    A resposta traz a avaliação (pendências, reprovação em item crítico e alertas).
    """
    with _traduzir_erros():
        resultado = create_checklist_service(db, payload)

    response.headers["Location"] = str(
        request.url_for("obter_checklist", checklist_id=resultado.checklist.id)
    )
    return _com_avaliacao(resultado)


@router.get(
    "",
    response_model=list[ChecklistResponse],
    summary="Listar checklists",
    responses=_INVALIDA,
)
def listar_checklists(
    skip: int = Query(0, ge=0, description="Registros a pular."),
    limit: int = Query(
        100, ge=1, le=LIMITE_MAXIMO_LISTAGEM, description="Máximo de registros."
    ),
    status: Optional[StatusChecklist] = Query(None, description="Filtra por status."),
    db: Session = Depends(get_db),
):
    """Lista as checklists, das mais recentes para as mais antigas, com suas respostas."""
    with _traduzir_erros():
        return get_checklists(db, skip=skip, limit=limit, status=status)


@router.get(
    "/{checklist_id}",
    response_model=ChecklistResponse,
    summary="Consultar checklist",
    responses=_NAO_ENCONTRADA,
)
def obter_checklist(checklist_id: int = ChecklistId, db: Session = Depends(get_db)):
    """Retorna a checklist com todas as suas respostas."""
    with _traduzir_erros():
        return get_checklist(db, checklist_id)


@router.put(
    "/{checklist_id}",
    response_model=ChecklistComAvaliacaoResponse,
    summary="Editar checklist",
    responses={**_NAO_ENCONTRADA, **_CONFLITO, **_INVALIDA},
)
def editar_checklist(
    payload: ChecklistUpdate,
    checklist_id: int = ChecklistId,
    db: Session = Depends(get_db),
):
    """
    Edita uma checklist ainda editável. Só os campos enviados são alterados; as
    respostas enviadas atualizam os itens correspondentes (por `numero_item`).

    Checklists finalizadas ou canceladas não podem ser alteradas (409). O status
    FINALIZADA só é definido pela rota de finalização.
    """
    with _traduzir_erros():
        resultado = update_checklist_service(db, checklist_id, payload)
    return _com_avaliacao(resultado)


@router.post(
    "/{checklist_id}/verificar",
    response_model=AvaliacaoResponse,
    summary="Verificar checklist",
    responses=_NAO_ENCONTRADA,
)
def verificar_checklist(checklist_id: int = ChecklistId, db: Session = Depends(get_db)):
    """
    Executa as validações sem alterar nada e informa a situação: com pendências,
    preenchida, reprovada em item crítico ou finalizada, além de `pode_finalizar`.
    """
    with _traduzir_erros():
        checklist = get_checklist(db, checklist_id)
        avaliacao = evaluate_checklist(checklist)
    return AvaliacaoResponse.model_validate(avaliacao, from_attributes=True)


@router.post(
    "/{checklist_id}/finalizar",
    response_model=ChecklistComAvaliacaoResponse,
    summary="Finalizar checklist",
    responses={**_NAO_ENCONTRADA, **_CONFLITO, **_INVALIDA},
)
def finalizar_checklist(checklist_id: int = ChecklistId, db: Session = Depends(get_db)):
    """
    Finaliza a checklist somente se todas as verificações passarem.

    - 422: há pendências (campos, itens, horímetros, liderança ou assinaturas).
    - 409: item crítico reprovado, checklist já finalizada ou cancelada.
    """
    with _traduzir_erros():
        resultado = finalize_checklist(db, checklist_id)
    return _com_avaliacao(resultado)


@router.delete(
    "/{checklist_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Excluir checklist",
    responses={**_NAO_ENCONTRADA, **_CONFLITO},
)
def excluir_checklist(checklist_id: int = ChecklistId, db: Session = Depends(get_db)):
    """
    Exclui a checklist e suas respostas. Só rascunhos (ou checklists canceladas)
    podem ser excluídos; preenchidas e finalizadas retornam 409.
    """
    with _traduzir_erros():
        delete_checklist(db, checklist_id)
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)