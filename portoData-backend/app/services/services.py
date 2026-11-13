"""
Regras de negócio da aplicação PortData.

Camada entre a API e o crud.py: a rota chama o service, o service aplica as regras
e delega a gravação ao CRUD (que cuida da transação).

Uso:

    from services import (
        create_checklist_service, update_checklist_service, finalize_checklist,
        validate_checklist, validate_responses, validate_horimeter,
        verify_critical_items, evaluate_checklist,
    )

Situações de uma checklist (SituacaoChecklist, calculadas a partir do conteúdo):

    COM_PENDENCIAS          campos obrigatórios, itens ou horímetros pendentes/inválidos
    REPROVADA_ITEM_CRITICO  tudo preenchido, mas há item crítico respondido NAO
    PREENCHIDA              tudo preenchido e sem reprovação crítica
    FINALIZADA              status FINALIZADA: registro fechado, imutável
    CANCELADA               status CANCELADA

Itens críticos: a criticidade vem SEMPRE do atributo `critico` de cada resposta
armazenada (ChecklistResposta.critico); este módulo não presume quais itens são críticos.

Regras operacionais adotadas (ajuste as constantes abaixo se o seu procedimento for outro):

    - Item crítico respondido NAO  -> BLOQUEIO: a checklist não pode ser finalizada.
    - Item não crítico respondido NAO -> ALERTA (não bloqueia).
    - Item crítico respondido NAO_APLICAVEL -> ALERTA (conferir a justificativa).
    - Finalizar exige campos gerais, 23 itens respondidos, horímetros consistentes,
      nome da liderança e as duas assinaturas.
    - Checklist finalizada nunca é alterada: toda tentativa gera erro explícito.
    - Só finalize_checklist() leva uma checklist ao status FINALIZADA.

Erros (todos herdam das exceções do crud.py, então os handlers 404/409/422 continuam valendo):

    ChecklistFinalizadaError     409  tentativa de alterar/finalizar checklist finalizada
    ReprovacaoItemCriticoError   409  finalização bloqueada por item crítico reprovado
    ChecklistComPendenciasError  422  pendências impedem a operação
    HorimetroInvalidoError       422  horímetros inconsistentes
"""

import logging
from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Iterable, Optional, Union

from crud import (
    DadosInvalidosError,
    OperacaoNaoPermitidaError,
    create_checklist,
    get_checklist,
    update_checklist,
)
from models import TOTAL_ITENS, Checklist
from models import RespostaEnum as RespostaModelo
from models import StatusChecklist as StatusModelo
from schemas import (
    CAMPOS_PARA_FINALIZADA,
    CAMPOS_PARA_PREENCHIDA,
    ChecklistCreate,
    ChecklistUpdate,
)

logger = logging.getLogger("portdata.services")

# --------------------------------------------------------------------------- #
# Regras configuráveis
# --------------------------------------------------------------------------- #
CAMPOS_OBRIGATORIOS = CAMPOS_PARA_PREENCHIDA
CAMPOS_OBRIGATORIOS_FINALIZACAO = CAMPOS_PARA_FINALIZADA  # assinaturas e liderança

# True: item crítico respondido NAO bloqueia a finalização.
# False: vira apenas alerta.
BLOQUEAR_FINALIZACAO_COM_CRITICO_REPROVADO = True

_RESPOSTAS_VALIDAS = {r.value for r in RespostaModelo}


# --------------------------------------------------------------------------- #
# Exceções
# --------------------------------------------------------------------------- #
class ChecklistFinalizadaError(OperacaoNaoPermitidaError):
    """Tentativa de alterar ou finalizar novamente uma checklist finalizada."""


class ReprovacaoItemCriticoError(OperacaoNaoPermitidaError):
    """Finalização bloqueada por item(ns) crítico(s) respondido(s) como NAO."""

    def __init__(self, bloqueios: list[str]):
        self.bloqueios = list(bloqueios)
        super().__init__(
            "Checklist reprovada em item crítico; não pode ser finalizada. "
            + " ".join(self.bloqueios)
        )


class ChecklistComPendenciasError(DadosInvalidosError):
    """Há pendências que impedem a operação."""

    def __init__(self, pendencias: list[str]):
        self.pendencias = list(pendencias)
        super().__init__("Checklist com pendências: " + "; ".join(self.pendencias) + ".")


class HorimetroInvalidoError(DadosInvalidosError):
    """Leituras de horímetro inconsistentes."""

    def __init__(self, erros: list[str]):
        self.erros = list(erros)
        super().__init__(" ".join(self.erros))


# --------------------------------------------------------------------------- #
# Resultados
# --------------------------------------------------------------------------- #
class SituacaoChecklist(str, Enum):
    COM_PENDENCIAS = "COM_PENDENCIAS"
    REPROVADA_ITEM_CRITICO = "REPROVADA_ITEM_CRITICO"
    PREENCHIDA = "PREENCHIDA"
    FINALIZADA = "FINALIZADA"
    CANCELADA = "CANCELADA"


@dataclass(frozen=True)
class ResultadoRespostas:
    pendentes: list[int] = field(default_factory=list)   # sem registro ou sem resposta
    invalidos: list[int] = field(default_factory=list)   # item fora de 1..N ou valor inválido
    duplicados: list[int] = field(default_factory=list)  # item repetido

    @property
    def ok(self) -> bool:
        return not (self.pendentes or self.invalidos or self.duplicados)

    def mensagens(self) -> list[str]:
        msgs = []
        if self.pendentes:
            msgs.append("Itens sem resposta: " + _juntar(self.pendentes))
        if self.invalidos:
            msgs.append("Itens com resposta inválida: " + _juntar(self.invalidos))
        if self.duplicados:
            msgs.append("Itens respondidos mais de uma vez: " + _juntar(self.duplicados))
        return msgs


@dataclass(frozen=True)
class ResultadoCriticos:
    reprovados: list[int] = field(default_factory=list)  # critico=True e resposta NAO
    bloqueios: list[str] = field(default_factory=list)
    alertas: list[str] = field(default_factory=list)

    @property
    def tem_bloqueio(self) -> bool:
        return bool(self.bloqueios)


@dataclass(frozen=True)
class Avaliacao:
    situacao: SituacaoChecklist
    mensagem: str
    pendencias: list[str] = field(default_factory=list)              # impedem estar "preenchida"
    pendencias_finalizacao: list[str] = field(default_factory=list)  # só impedem finalizar
    bloqueios: list[str] = field(default_factory=list)
    alertas: list[str] = field(default_factory=list)

    @property
    def pode_finalizar(self) -> bool:
        return (
            self.situacao == SituacaoChecklist.PREENCHIDA
            and not self.pendencias_finalizacao
        )


@dataclass(frozen=True)
class ResultadoChecklist:
    """Retorno dos services: o registro gravado e a avaliação de sua situação."""

    checklist: Checklist
    avaliacao: Avaliacao


# --------------------------------------------------------------------------- #
# Auxiliares
# --------------------------------------------------------------------------- #
def _juntar(numeros: Iterable[int]) -> str:
    return ", ".join(str(n) for n in numeros)


def _valor(v: Any) -> Any:
    return v.value if isinstance(v, Enum) else v


def _status(checklist: Any) -> Optional[StatusModelo]:
    valor = _valor(getattr(checklist, "status", None))
    return StatusModelo(valor) if valor is not None else None


def _coagir(modelo, dados: Any):
    if isinstance(dados, modelo):
        return dados
    try:
        return modelo.model_validate(dados)
    except ValueError as exc:  # pydantic.ValidationError herda de ValueError
        raise DadosInvalidosError(str(exc)) from exc


def _exigir_editavel(checklist: Checklist) -> None:
    status = _status(checklist)
    if status == StatusModelo.FINALIZADA:
        raise ChecklistFinalizadaError(
            f"Checklist {checklist.id} já foi finalizada e não pode ser alterada. "
            "Alterações em checklists finalizadas não são permitidas."
        )
    if status == StatusModelo.CANCELADA:
        raise OperacaoNaoPermitidaError(
            f"Checklist {checklist.id} está cancelada e não pode ser alterada."
        )


# --------------------------------------------------------------------------- #
# Validações
# --------------------------------------------------------------------------- #
def validate_checklist(checklist: Any, para_finalizar: bool = False) -> list[str]:
    """
    Retorna os nomes dos campos obrigatórios não preenchidos (lista vazia = ok).
    Com `para_finalizar=True` inclui também liderança e assinaturas.
    Aceita objeto ORM ou schema.
    """
    obrigatorios = list(CAMPOS_OBRIGATORIOS)
    if para_finalizar:
        obrigatorios += CAMPOS_OBRIGATORIOS_FINALIZACAO

    faltantes = []
    for campo in obrigatorios:
        valor = getattr(checklist, campo, None)
        if valor is None or (isinstance(valor, str) and not valor.strip()):
            faltantes.append(campo)
    return faltantes


def validate_responses(respostas: Iterable[Any]) -> ResultadoRespostas:
    """
    Verifica se os 23 itens possuem resposta válida (SIM, NAO ou NAO_APLICAVEL).

    - pendentes: item sem registro ou com resposta nula;
    - invalidos: número fora de 1..23 ou valor de resposta inválido;
    - duplicados: item repetido.
    """
    respostas = list(respostas)
    contagem = Counter(r.numero_item for r in respostas)
    duplicados = sorted(n for n, qtd in contagem.items() if qtd > 1)

    respondidos: set[int] = set()
    invalidos: set[int] = set()
    for r in respostas:
        numero = r.numero_item
        if not 1 <= numero <= TOTAL_ITENS:
            invalidos.add(numero)
            continue
        valor = _valor(r.resposta)
        if valor is None:
            continue
        if valor not in _RESPOSTAS_VALIDAS:
            invalidos.add(numero)
            continue
        respondidos.add(numero)

    pendentes = sorted(set(range(1, TOTAL_ITENS + 1)) - respondidos - invalidos)
    return ResultadoRespostas(
        pendentes=pendentes, invalidos=sorted(invalidos), duplicados=duplicados
    )


def validate_horimeter(
    horimetro_inicial: Optional[Decimal], horimetro_final: Optional[Decimal]
) -> list[str]:
    """
    Verifica se o horímetro final é igual ou superior ao inicial e se nenhum é negativo.
    Retorna mensagens de erro (lista vazia = ok). Leitura ausente não é erro aqui.
    """
    erros = []
    if horimetro_inicial is not None and horimetro_inicial < 0:
        erros.append("O horímetro inicial não pode ser negativo.")
    if horimetro_final is not None and horimetro_final < 0:
        erros.append("O horímetro final não pode ser negativo.")
    if (
        horimetro_inicial is not None
        and horimetro_final is not None
        and horimetro_final < horimetro_inicial
    ):
        erros.append(
            f"O horímetro final ({horimetro_final}) não pode ser menor que o "
            f"inicial ({horimetro_inicial})."
        )
    return erros


def verify_critical_items(respostas: Iterable[Any]) -> ResultadoCriticos:
    """
    Identifica itens críticos reprovados usando o atributo `critico` de cada resposta
    (objetos ChecklistResposta ou RespostaResponse; nenhum item é presumido crítico).

    - critico=True  e NAO            -> bloqueio (ou alerta, se a regra for desativada)
    - critico=False e NAO            -> alerta
    - critico=True  e NAO_APLICAVEL  -> alerta
    """
    reprovados: list[int] = []
    bloqueios: list[str] = []
    alertas: list[str] = []

    for r in sorted(respostas, key=lambda x: x.numero_item):
        valor = _valor(r.resposta)
        descricao = getattr(r, "descricao", "") or ""
        rotulo = f"Item {r.numero_item} ({descricao})" if descricao else f"Item {r.numero_item}"
        obs = f" Observação: {r.observacao}" if getattr(r, "observacao", None) else ""

        if valor == RespostaModelo.NAO.value and r.critico:
            reprovados.append(r.numero_item)
            texto = f"{rotulo} é crítico e foi respondido NAO.{obs}"
            if BLOQUEAR_FINALIZACAO_COM_CRITICO_REPROVADO:
                bloqueios.append(texto)
            else:
                alertas.append(texto)
        elif valor == RespostaModelo.NAO.value:
            alertas.append(f"{rotulo} foi respondido NAO (item não crítico).{obs}")
        elif valor == RespostaModelo.NAO_APLICAVEL.value and r.critico:
            alertas.append(
                f"{rotulo} é crítico e foi marcado como NAO_APLICAVEL; confirme a justificativa.{obs}"
            )

    return ResultadoCriticos(reprovados=reprovados, bloqueios=bloqueios, alertas=alertas)


# --------------------------------------------------------------------------- #
# Avaliação da situação
# --------------------------------------------------------------------------- #
def evaluate_checklist(checklist: Checklist) -> Avaliacao:
    """
    Classifica a checklist em COM_PENDENCIAS, REPROVADA_ITEM_CRITICO, PREENCHIDA,
    FINALIZADA ou CANCELADA, com mensagem clara, pendências, bloqueios e alertas.
    """
    # Campos gerais pendentes.
    faltantes = validate_checklist(checklist)
    pendencias = [f"campo obrigatório não preenchido: {c}" for c in faltantes]

    # Itens pendentes/inválidos.
    resp = validate_responses(checklist.respostas)
    pendencias += [m[0].lower() + m[1:] for m in resp.mensagens()]

    # Horímetros inconsistentes.
    erros_horimetro = validate_horimeter(
        checklist.horimetro_inicial, checklist.horimetro_final
    )
    pendencias += [m[0].lower() + m[1:] for m in erros_horimetro]

    # Liderança e assinaturas: só impedem a finalização.
    faltam_finalizar = [
        c for c in validate_checklist(checklist, para_finalizar=True) if c not in faltantes
    ]
    pendencias_finalizacao = [
        f"campo obrigatório para finalizar não preenchido: {c}" for c in faltam_finalizar
    ]

    criticos = verify_critical_items(checklist.respostas)
    status = _status(checklist)

    if status == StatusModelo.FINALIZADA:
        situacao, mensagem = SituacaoChecklist.FINALIZADA, (
            f"Checklist {checklist.id} finalizada. O registro é imutável."
        )
    elif status == StatusModelo.CANCELADA:
        situacao, mensagem = SituacaoChecklist.CANCELADA, (
            f"Checklist {checklist.id} cancelada."
        )
    elif pendencias:
        situacao = SituacaoChecklist.COM_PENDENCIAS
        mensagem = "Checklist com pendências: " + "; ".join(pendencias) + "."
        if criticos.tem_bloqueio:
            mensagem += (
                " Há também reprovação em item crítico: itens "
                + _juntar(criticos.reprovados) + "."
            )
    elif criticos.tem_bloqueio:
        situacao = SituacaoChecklist.REPROVADA_ITEM_CRITICO
        mensagem = (
            "Checklist preenchida, porém reprovada em item crítico "
            f"(itens {_juntar(criticos.reprovados)}). Não pode ser finalizada "
            "enquanto o item não for corrigido."
        )
    else:
        situacao = SituacaoChecklist.PREENCHIDA
        mensagem = "Checklist preenchida."
        if pendencias_finalizacao:
            mensagem += " Para finalizar, falta: " + "; ".join(pendencias_finalizacao) + "."
        else:
            mensagem += " Pronta para finalização."

    return Avaliacao(
        situacao=situacao,
        mensagem=mensagem,
        pendencias=pendencias,
        pendencias_finalizacao=pendencias_finalizacao,
        bloqueios=criticos.bloqueios,
        alertas=criticos.alertas,
    )


def _exigir_finalizavel(avaliacao: Avaliacao) -> None:
    """Levanta o erro apropriado se a checklist não puder ser finalizada."""
    if avaliacao.pendencias or avaliacao.pendencias_finalizacao:
        raise ChecklistComPendenciasError(
            avaliacao.pendencias + avaliacao.pendencias_finalizacao
        )
    if avaliacao.bloqueios:
        raise ReprovacaoItemCriticoError(avaliacao.bloqueios)


# --------------------------------------------------------------------------- #
# Serviços
# --------------------------------------------------------------------------- #
def create_checklist_service(
    db, checklist_data: Union[ChecklistCreate, dict]
) -> ResultadoChecklist:
    """
    Cria a checklist e armazena suas respostas em uma única transação (via CRUD).

    Regras: só nasce como RASCUNHO ou PREENCHIDA; FINALIZADA exige
    finalize_checklist() e criar já CANCELADA não faz sentido. Retorna o registro
    e a avaliação (pendências, reprovação crítica, alertas).
    """
    dados = _coagir(ChecklistCreate, checklist_data)

    if dados.status not in (StatusModelo.RASCUNHO.value, StatusModelo.PREENCHIDA.value):
        raise OperacaoNaoPermitidaError(
            "Uma checklist só pode ser criada como RASCUNHO ou PREENCHIDA. "
            "Para finalizá-la, use a finalização após criar."
        )

    erros = validate_horimeter(dados.horimetro_inicial, dados.horimetro_final)
    if erros:
        raise HorimetroInvalidoError(erros)

    checklist = create_checklist(db, dados)
    avaliacao = evaluate_checklist(checklist)
    logger.info("Checklist %s criada (%s).", checklist.id, avaliacao.situacao.value)
    return ResultadoChecklist(checklist, avaliacao)


def update_checklist_service(
    db, checklist_id: int, checklist_data: Union[ChecklistUpdate, dict]
) -> ResultadoChecklist:
    """
    Verifica se a checklist pode ser editada e encaminha os dados ao CRUD.

    - Checklist finalizada: ChecklistFinalizadaError (nunca altera em silêncio).
    - Checklist cancelada: OperacaoNaoPermitidaError.
    - Status FINALIZADA não pode ser definido aqui: use finalize_checklist().
    """
    dados = _coagir(ChecklistUpdate, checklist_data)

    checklist = get_checklist(db, checklist_id)  # ChecklistNaoEncontradaError se não existir
    _exigir_editavel(checklist)

    if dados.status == StatusModelo.FINALIZADA.value:
        raise OperacaoNaoPermitidaError(
            "O status FINALIZADA só pode ser definido por finalize_checklist(), "
            "que executa todas as verificações."
        )

    # Horímetros com os valores finais (payload combinado ao que já está salvo).
    inicial = (
        dados.horimetro_inicial
        if "horimetro_inicial" in dados.model_fields_set
        else checklist.horimetro_inicial
    )
    final = (
        dados.horimetro_final
        if "horimetro_final" in dados.model_fields_set
        else checklist.horimetro_final
    )
    erros = validate_horimeter(inicial, final)
    if erros:
        raise HorimetroInvalidoError(erros)

    atualizada = update_checklist(db, checklist_id, dados)
    return ResultadoChecklist(atualizada, evaluate_checklist(atualizada))


def finalize_checklist(db, checklist_id: int) -> ResultadoChecklist:
    """
    Finaliza a checklist (status FINALIZADA) somente se todos os requisitos forem atendidos:
    campos obrigatórios, 23 itens respondidos, horímetros consistentes, liderança e
    assinaturas, e nenhum item crítico (atributo `critico`) respondido NAO.

    As verificações rodam dentro da transação do CRUD, com a linha da checklist
    bloqueada, então nada muda entre a verificação e a gravação.

    Erros: ChecklistFinalizadaError (já finalizada), OperacaoNaoPermitidaError (cancelada),
    ChecklistComPendenciasError (pendências), ReprovacaoItemCriticoError (item crítico NAO).
    """
    checklist = get_checklist(db, checklist_id)
    status = _status(checklist)

    if status == StatusModelo.FINALIZADA:
        raise ChecklistFinalizadaError(
            f"Checklist {checklist_id} já está finalizada; não é possível finalizá-la novamente."
        )
    if status == StatusModelo.CANCELADA:
        raise OperacaoNaoPermitidaError(
            f"Checklist {checklist_id} está cancelada e não pode ser finalizada."
        )

    def _verificar(c: Checklist, novo_status: StatusModelo) -> None:
        if novo_status == StatusModelo.FINALIZADA:
            try:
                _exigir_finalizavel(evaluate_checklist(c))
            except ReprovacaoItemCriticoError as exc:
                logger.warning(
                    "Finalização da checklist %s bloqueada: %s", checklist_id, exc
                )
                raise

    finalizada = update_checklist(
        db,
        checklist_id,
        ChecklistUpdate(status=StatusModelo.FINALIZADA.value),
        validar_antes_de_gravar=_verificar,
    )
    logger.info("Checklist %s finalizada.", checklist_id)
    return ResultadoChecklist(finalizada, evaluate_checklist(finalizada))