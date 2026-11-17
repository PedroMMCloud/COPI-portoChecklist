"""
o código não foi executado contra um banco PostgreSQL real, porque o ambiente onde 
trabalhei não tem Pydantic nem banco. Faça um teste rápido antes de usar.


Operações CRUD da aplicação PortData (SQLAlchemy 2.x).
Uso:

    from crud import (
        create_checklist, get_checklist, get_checklists,
        update_checklist, delete_checklist,
        save_responses, get_responses,
        ChecklistNaoEncontradaError, OperacaoNaoPermitidaError, DadosInvalidosError,
    )

Erros levantados (traduza para HTTP na camada da API):

    ChecklistNaoEncontradaError -> 404
    OperacaoNaoPermitidaError   -> 409  (regra de negócio, ex.: checklist assinada)
    DadosInvalidosError         -> 422  (dados inconsistentes ou violação de integridade)

Exemplo em main.py (FastAPI):

    @app.exception_handler(ChecklistNaoEncontradaError)
    async def _nao_encontrada(request, exc):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(OperacaoNaoPermitidaError)
    async def _nao_permitida(request, exc):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(DadosInvalidosError)
    async def _invalidos(request, exc):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

Regras do sistema aplicadas aqui:

    - Edição: checklists ASSINADA ou CANCELADA não podem ser alteradas.
    - Exclusão: somente checklists RASCUNHO ou CANCELADA podem ser excluídas.
      PREENCHIDA e ASSINADA são registros de inspeção: devem ser canceladas, não apagadas.
    - Transições de status: veja TRANSICOES_PERMITIDAS.
    - Toda gravação ocorre em uma única transação (commit no sucesso, rollback no erro).
"""

import enum
from collections import Counter
from contextlib import contextmanager
from typing import Any, Iterable, Iterator, Optional, Union

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from models.models import Checklist, ChecklistResposta
from models.models import RespostaEnum as RespostaModelo
from models.models import StatusChecklist as StatusModelo
from schemas.schemas import (
    CAMPOS_PARA_ASSINADA,
    CAMPOS_PARA_PREENCHIDA,
    ChecklistCreate,
    ChecklistUpdate,
    RespostaCreate,
    verificar_requisitos_do_status,
)

# ----------------------- #
# Regras do sistema

STATUS_BLOQUEADOS_PARA_EDICAO = frozenset(
    {StatusModelo.ASSINADA, StatusModelo.CANCELADA}
)
STATUS_EXCLUIVEIS = frozenset({StatusModelo.RASCUNHO, StatusModelo.CANCELADA})
TRANSICOES_PERMITIDAS = {
    StatusModelo.RASCUNHO: {
        StatusModelo.PREENCHIDA,
        StatusModelo.ASSINADA,
        StatusModelo.CANCELADA,
    },
    StatusModelo.PREENCHIDA: {
        StatusModelo.RASCUNHO,
        StatusModelo.ASSINADA,
        StatusModelo.CANCELADA,
    },
    StatusModelo.ASSINADA: set(),
    StatusModelo.CANCELADA: set(),
}
LIMITE_MAXIMO_LISTAGEM = 500


# ----------------- #
# Exceções

class CrudError(Exception):
    """Base das exceções do módulo."""


class ChecklistNaoEncontradaError(CrudError):
    def __init__(self, checklist_id: int):
        self.checklist_id = checklist_id
        super().__init__(f"Checklist {checklist_id} não encontrada.")


class OperacaoNaoPermitidaError(CrudError):
    """A operação contraria uma regra de negócio."""


class DadosInvalidosError(CrudError):
    """Os dados enviados são inconsistentes ou violam o banco."""


# --------------------------- #
# Auxiliares internos

@contextmanager
def _transacao(db: Session) -> Iterator[None]:
    """Executa o bloco em uma transação: commit no sucesso, rollback no erro."""
    try:
        yield
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DadosInvalidosError(
            "A operação viola uma restrição de integridade do banco de dados."
        ) from exc
    except Exception:
        db.rollback()
        raise


def _valor(v: Any) -> Any:
    return v.value if isinstance(v, enum.Enum) else v


def _status_modelo(v: Any) -> StatusModelo:
    try:
        return StatusModelo(_valor(v))
    except ValueError as exc:
        raise DadosInvalidosError(f"Status inválido: {v!r}.") from exc


def _resposta_modelo(v: Any) -> Optional[RespostaModelo]:
    return None if v is None else RespostaModelo(_valor(v))


def _coagir(modelo, dados: Any):
    """Aceita o schema já validado ou um dict/objeto compatível."""
    if isinstance(dados, modelo):
        return dados
    try:
        return modelo.model_validate(dados)
    except ValueError as exc:  # pydantic.ValidationError herda de ValueError
        raise DadosInvalidosError(str(exc)) from exc


def _normalizar_respostas(respostas: Iterable[Any]) -> list[RespostaCreate]:
    lista = [_coagir(RespostaCreate, r) for r in respostas]
    repetidos = sorted(n for n, qtd in Counter(r.numero_item for r in lista).items() if qtd > 1)
    if repetidos:
        raise DadosInvalidosError(
            "Itens repetidos na lista de respostas: " + ", ".join(map(str, repetidos))
        )
    return lista


def _obter_checklist(
    db: Session, checklist_id: int, bloquear: bool = False
) -> Checklist:
    """
    Busca a checklist com suas respostas (ordenadas por número do item).
    Com `bloquear=True` usa SELECT ... FOR UPDATE, serializando alterações
    concorrentes sobre a mesma checklist. `populate_existing` garante dados
    atualizados mesmo que o objeto já esteja na sessão.
    """
    stmt = (
        select(Checklist)
        .options(selectinload(Checklist.respostas))
        .where(Checklist.id == checklist_id)
        .execution_options(populate_existing=True)
    )
    if bloquear:
        stmt = stmt.with_for_update()
    checklist = db.execute(stmt).scalar_one_or_none()
    if checklist is None:
        raise ChecklistNaoEncontradaError(checklist_id)
    return checklist


def _exigir_edicao_permitida(checklist: Checklist) -> None:
    if checklist.status in STATUS_BLOQUEADOS_PARA_EDICAO:
        raise OperacaoNaoPermitidaError(
            f"Checklist {checklist.id} está {checklist.status.value} e não pode ser alterada."
        )


def _validar_transicao(atual: StatusModelo, novo: StatusModelo) -> None:
    if novo != atual and novo not in TRANSICOES_PERMITIDAS[atual]:
        raise OperacaoNaoPermitidaError(
            f"Transição de status não permitida: {atual.value} -> {novo.value}."
        )


def _validar_requisitos(checklist: Checklist, status: StatusModelo) -> None:
    """Exige dados completos para PREENCHIDA/ASSINADA (usa as regras de schemas.py)."""
    dados = {
        c: getattr(checklist, c)
        for c in CAMPOS_PARA_PREENCHIDA + CAMPOS_PARA_ASSINADA
    }
    try:
        verificar_requisitos_do_status(status.value, dados, checklist.respostas)
    except ValueError as exc:
        raise DadosInvalidosError(str(exc)) from exc


def _aplicar_respostas(checklist: Checklist, respostas: list[RespostaCreate]) -> None:
    """
    Upsert por numero_item. Garante os 23 itens na checklist e altera apenas
    os campos enviados (resposta e/ou observacao) de cada item informado.
    """
    checklist.criar_respostas_padrao()
    por_numero = {r.numero_item: r for r in checklist.respostas}
    for item in respostas:
        existente = por_numero[item.numero_item]
        if "resposta" in item.model_fields_set:
            existente.resposta = _resposta_modelo(item.resposta)
        if "observacao" in item.model_fields_set:
            existente.observacao = item.observacao


# ------------------ #
# CREATE

def create_checklist(
    db: Session, checklist_data: Union[ChecklistCreate, dict]
) -> Checklist:
    """
    Cria a checklist com os 23 itens de inspeção e aplica as respostas enviadas.
    Checklist e respostas são gravadas na mesma transação.
    """
    dados = _coagir(ChecklistCreate, checklist_data)

    checklist = Checklist(
        **dados.model_dump(exclude={"respostas", "status"}),
        status=_status_modelo(dados.status),
    )
    _aplicar_respostas(checklist, _normalizar_respostas(dados.respostas))

    with _transacao(db):
        db.add(checklist)
    # Recarrega com valores gerados pelo banco (id, created_at...) e respostas.
    return _obter_checklist(db, checklist.id)


# -------------------- #
# READ

def get_checklist(db: Session, checklist_id: int) -> Checklist:
    """Retorna a checklist com suas respostas ou levanta ChecklistNaoEncontradaError."""
    return _obter_checklist(db, checklist_id)


def get_checklists(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[Union[StatusModelo, str]] = None,
) -> list[Checklist]:
    """
    Lista as checklists (mais recentes primeiro), com respostas carregadas
    em uma única consulta extra. Suporta paginação e filtro por status.
    """
    if skip < 0 or not 1 <= limit <= LIMITE_MAXIMO_LISTAGEM:
        raise DadosInvalidosError(
            f"Paginação inválida: skip >= 0 e 1 <= limit <= {LIMITE_MAXIMO_LISTAGEM}."
        )

    stmt = select(Checklist).options(selectinload(Checklist.respostas))
    if status is not None:
        stmt = stmt.where(Checklist.status == _status_modelo(status))
    stmt = (
        stmt.order_by(Checklist.data.desc().nulls_last(), Checklist.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def get_responses(db: Session, checklist_id: int) -> list[ChecklistResposta]:
    """Retorna as respostas da checklist, ordenadas pelo número do item."""
    if db.scalar(select(Checklist.id).where(Checklist.id == checklist_id)) is None:
        raise ChecklistNaoEncontradaError(checklist_id)

    stmt = (
        select(ChecklistResposta)
        .where(ChecklistResposta.checklist_id == checklist_id)
        .order_by(ChecklistResposta.numero_item)
    )
    return list(db.scalars(stmt).all())


# ----------------------- #
# UPDATE

def update_checklist(
    db: Session, checklist_id: int, checklist_data: Union[ChecklistUpdate, dict]
) -> Checklist:
    """
    Atualização parcial: só os campos enviados são alterados (id e datas de
    controle nunca). Campos gerais, status e respostas são gravados juntos.

    Regras: checklist ASSINADA/CANCELADA é imutável; o status segue
    TRANSICOES_PERMITIDAS; PREENCHIDA/ASSINADA exigem dados completos.
    """
    dados = _coagir(ChecklistUpdate, checklist_data)
    respostas = (
        _normalizar_respostas(dados.respostas) if dados.respostas is not None else []
    )

    with _transacao(db):
        checklist = _obter_checklist(db, checklist_id, bloquear=True)
        _exigir_edicao_permitida(checklist)

        novo_status = (
            _status_modelo(dados.status) if dados.status is not None else checklist.status
        )
        _validar_transicao(checklist.status, novo_status)

        for campo, valor in dados.model_dump(
            exclude_unset=True, exclude={"respostas", "status"}
        ).items():
            setattr(checklist, campo, valor)

        # O schema valida os horímetros só dentro do payload; aqui, com os valores finais.
        ini, fim = checklist.horimetro_inicial, checklist.horimetro_final
        if ini is not None and fim is not None and fim < ini:
            raise DadosInvalidosError(
                "horimetro_final não pode ser menor que horimetro_inicial."
            )

        if respostas:
            _aplicar_respostas(checklist, respostas)

        _validar_requisitos(checklist, novo_status)

        checklist.status = novo_status
        checklist.updated_at = func.now()  # também registra alterações só nas respostas

    return _obter_checklist(db, checklist_id)


# -------------------- #
# DELETE

def delete_checklist(db: Session, checklist_id: int) -> None:
    """
    Exclui a checklist e suas respostas (cascade) somente se estiver RASCUNHO
    ou CANCELADA. Caso contrário levanta OperacaoNaoPermitidaError.
    """
    with _transacao(db):
        checklist = _obter_checklist(db, checklist_id, bloquear=True)
        if checklist.status not in STATUS_EXCLUIVEIS:
            raise OperacaoNaoPermitidaError(
                f"Checklist {checklist_id} está {checklist.status.value} e não pode ser "
                "excluída. Cancele-a em vez de excluir."
            )
        db.delete(checklist)


# ----------------- #
# Respostas

def save_responses(
    db: Session, checklist_id: int, responses: Iterable[Union[RespostaCreate, dict]]
) -> list[ChecklistResposta]:
    """
    Cadastra ou atualiza respostas por numero_item (upsert) e retorna todas as
    respostas da checklist. Só os campos enviados de cada item são alterados.

    Regras: checklist ASSINADA/CANCELADA não aceita alterações; em uma checklist
    PREENCHIDA todos os itens devem continuar respondidos.
    """
    respostas = _normalizar_respostas(responses)

    with _transacao(db):
        checklist = _obter_checklist(db, checklist_id, bloquear=True)
        _exigir_edicao_permitida(checklist)

        _aplicar_respostas(checklist, respostas)
        _validar_requisitos(checklist, checklist.status)

        checklist.updated_at = func.now()

    return get_responses(db, checklist_id)