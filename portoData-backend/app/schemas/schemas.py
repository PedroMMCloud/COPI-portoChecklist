"""
Schemas Pydantic (v2) para validação de entrada e saída da API de checklists.

Uso:

    from schemas import (
        RespostaEnum,
        RespostaCreate, RespostaResponse,
        ChecklistCreate, ChecklistUpdate, ChecklistResponse,
    )

Exemplo com FastAPI:

    @router.post("/checklists", response_model=ChecklistResponse, status_code=201)
    def criar(payload: ChecklistCreate, db: Session = Depends(get_db)):
        ...

    @router.get("/checklists/{id}", response_model=ChecklistResponse)
    def obter(id: int, db: Session = Depends(get_db)):
        return db.get(Checklist, id)   # ORM -> Pydantic via from_attributes

Só verifiquei a sintaxe: não consegui rodar os schemas porque o Pydantic não 
está instalado no ambiente onde trabalhei, então vale testar com 
pip install pydantic antes de usar.
"""

import enum
from datetime import date, datetime, time
from decimal import Decimal
from typing import Annotated, Any, Iterable, Mapping, Optional

from pydantic import (
    BaseModel, ConfigDict, Field, PlainSerializer,
    field_validator, model_validator,
)

# Total de itens da inspeção (mesmo valor de models.TOTAL_ITENS).
# Definido aqui para que schemas.py não dependa de models.py/DATABASE_URL.
TOTAL_ITENS = 23


# --------------------------------------------------------------------------- #
# Enumerações
# --------------------------------------------------------------------------- #
class RespostaEnum(str, enum.Enum):
    SIM = "SIM"
    NAO = "NAO"
    NAO_APLICAVEL = "NAO_APLICAVEL"


class StatusChecklist(str, enum.Enum):
    RASCUNHO = "RASCUNHO"
    PREENCHIDA = "PREENCHIDA"
    ASSINADA = "ASSINADA"
    CANCELADA = "CANCELADA"


# --------------------------------------------------------------------------- #
# Tipos reutilizáveis
# --------------------------------------------------------------------------- #
# Decimal é serializado como número (e não como string) no JSON de saída.
_como_numero = PlainSerializer(float, return_type=float, when_used="json")

Horimetro = Annotated[
    Decimal, Field(ge=0, max_digits=10, decimal_places=1), _como_numero
]
PercentualCombustivel = Annotated[
    Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2), _como_numero
]


# --------------------------------------------------------------------------- #
# Regras de obrigatoriedade por status
# --------------------------------------------------------------------------- #
CAMPOS_PARA_PREENCHIDA = (
    "codigo_formulario",
    "versao",
    "local_atuacao",
    "turno",
    "data",
    "navio",
    "guindaste",
    "nome_operador",
)
CAMPOS_PARA_ASSINADA = (
    "assinatura_operador",
    "nome_lideranca",
    "assinatura_lideranca",
)


def verificar_requisitos_do_status(
    status: "StatusChecklist | str",
    dados: Mapping[str, Any],
    respostas: Iterable[Any],
) -> None:
    """
    Verifica se a checklist está completa o suficiente para o status informado.

    - RASCUNHO e CANCELADA: nenhuma exigência.
    - PREENCHIDA: campos gerais obrigatórios + os 23 itens respondidos.
    - ASSINADA: o mesmo da PREENCHIDA + liderança e as duas assinaturas.

    `respostas` aceita qualquer objeto com `numero_item` e `resposta`
    (schemas ou objetos ORM). Levanta ValueError se algo estiver faltando.
    Também pode ser reutilizada nas rotas de atualização, combinando os dados
    já salvos com os enviados no PATCH.
    """
    status = StatusChecklist(status)
    if status not in (StatusChecklist.PREENCHIDA, StatusChecklist.ASSINADA):
        return

    obrigatorios = list(CAMPOS_PARA_PREENCHIDA)
    if status == StatusChecklist.ASSINADA:
        obrigatorios += CAMPOS_PARA_ASSINADA

    faltantes = [c for c in obrigatorios if dados.get(c) in (None, "")]
    if faltantes:
        raise ValueError(
            f"Campos obrigatórios para o status {status.value}: "
            + ", ".join(faltantes)
        )

    respondidos = {r.numero_item for r in respostas if r.resposta is not None}
    pendentes = sorted(set(range(1, TOTAL_ITENS + 1)) - respondidos)
    if pendentes:
        raise ValueError(
            f"Itens sem resposta para o status {status.value}: "
            + ", ".join(map(str, pendentes))
        )


# --------------------------------------------------------------------------- #
# Funções auxiliares de validação
# --------------------------------------------------------------------------- #
def _vazio_para_none(valor: Any) -> Any:
    """Converte texto vazio (ou só espaços) em None."""
    if isinstance(valor, str) and not valor.strip():
        return None
    return valor


def _normalizar_enum(valor: Any) -> Any:
    """
    Aceita 'sim', ' SIM ' etc. e também membros de Enum vindos do SQLAlchemy.
    Texto vazio vira None; valores inválidos continuam inválidos (erro 422).
    """
    if isinstance(valor, enum.Enum):
        return valor.value
    if isinstance(valor, str):
        valor = valor.strip().upper()
        return valor or None
    return valor


def _sem_itens_duplicados(respostas: Optional[list["RespostaCreate"]]):
    if respostas is None:
        return respostas
    vistos: set[int] = set()
    duplicados: set[int] = set()
    for r in respostas:
        if r.numero_item in vistos:
            duplicados.add(r.numero_item)
        vistos.add(r.numero_item)
    if duplicados:
        raise ValueError(
            "Itens repetidos na lista de respostas: "
            + ", ".join(map(str, sorted(duplicados)))
        )
    return respostas


# --------------------------------------------------------------------------- #
# Respostas
# --------------------------------------------------------------------------- #
class RespostaCreate(BaseModel):
    """Resposta a um item da inspeção (enviada pelo cliente)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    numero_item: int = Field(
        ge=1, le=TOTAL_ITENS, description=f"Número do item (1 a {TOTAL_ITENS})."
    )
    resposta: Optional[RespostaEnum] = Field(
        default=None,
        description="SIM, NAO ou NAO_APLICAVEL. Nulo = ainda não respondido (rascunho).",
    )
    observacao: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("resposta", mode="before")
    @classmethod
    def _normalizar_resposta(cls, v: Any) -> Any:
        return _normalizar_enum(v)

    @field_validator("observacao", mode="before")
    @classmethod
    def _observacao_vazia(cls, v: Any) -> Any:
        return _vazio_para_none(v)


class RespostaResponse(BaseModel):
    """Resposta retornada pela API (aceita objetos ORM)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    checklist_id: int
    numero_item: int
    descricao: str
    resposta: Optional[RespostaEnum] = None
    observacao: Optional[str] = None
    critico: bool = False

    @field_validator("resposta", mode="before")
    @classmethod
    def _normalizar_resposta(cls, v: Any) -> Any:
        return _normalizar_enum(v)


# --------------------------------------------------------------------------- #
# Checklist
# --------------------------------------------------------------------------- #
class ChecklistCampos(BaseModel):
    """
    Campos gerais da checklist, todos opcionais para permitir rascunhos.
    A obrigatoriedade para PREENCHIDA/ASSINADA é verificada em
    `verificar_requisitos_do_status`.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    codigo_formulario: Optional[str] = Field(default=None, max_length=50)
    versao: Optional[str] = Field(default=None, max_length=20)

    local_atuacao: Optional[str] = Field(default=None, max_length=150)
    turno: Optional[str] = Field(default=None, max_length=30)
    data: Optional[date] = None
    navio: Optional[str] = Field(default=None, max_length=150)
    guindaste: Optional[str] = Field(default=None, max_length=100)

    horimetro_inicial: Optional[Horimetro] = None
    horimetro_final: Optional[Horimetro] = None
    nivel_combustivel: Optional[PercentualCombustivel] = Field(
        default=None, description="Percentual de combustível (0 a 100)."
    )

    # A saída pode ocorrer após a meia-noite, por isso não se compara com a entrada.
    hora_entrada: Optional[time] = None
    hora_saida: Optional[time] = None

    observacao_geral: Optional[str] = Field(default=None, max_length=5000)

    nome_operador: Optional[str] = Field(default=None, max_length=150)
    assinatura_operador: Optional[str] = None
    nome_lideranca: Optional[str] = Field(default=None, max_length=150)
    assinatura_lideranca: Optional[str] = None

    @field_validator(
        "codigo_formulario",
        "versao",
        "local_atuacao",
        "turno",
        "navio",
        "guindaste",
        "observacao_geral",
        "nome_operador",
        "assinatura_operador",
        "nome_lideranca",
        "assinatura_lideranca",
        mode="before",
    )
    @classmethod
    def _texto_vazio_vira_none(cls, v: Any) -> Any:
        return _vazio_para_none(v)

    @model_validator(mode="after")
    def _validar_horimetros(self):
        if (
            self.horimetro_inicial is not None
            and self.horimetro_final is not None
            and self.horimetro_final < self.horimetro_inicial
        ):
            raise ValueError(
                "horimetro_final não pode ser menor que horimetro_inicial."
            )
        return self


class ChecklistCreate(ChecklistCampos):
    """
    Criação de checklist. Por padrão nasce como RASCUNHO e aceita qualquer
    campo em branco. Com status PREENCHIDA ou ASSINADA, exige os dados completos.
    """

    model_config = ConfigDict(extra="forbid")

    status: StatusChecklist = StatusChecklist.RASCUNHO
    respostas: list[RespostaCreate] = Field(default_factory=list)

    @field_validator("status", mode="before")
    @classmethod
    def _normalizar_status(cls, v: Any) -> Any:
        return _normalizar_enum(v)

    @field_validator("respostas")
    @classmethod
    def _respostas_sem_duplicidade(cls, v):
        return _sem_itens_duplicados(v)

    @model_validator(mode="after")
    def _validar_requisitos_do_status(self):
        dados = {
            c: getattr(self, c) for c in CAMPOS_PARA_PREENCHIDA + CAMPOS_PARA_ASSINADA
        }
        verificar_requisitos_do_status(self.status, dados, self.respostas)
        return self


class ChecklistUpdate(ChecklistCampos):
    """
    Atualização parcial (PATCH). Só os campos enviados são alterados:
    use `payload.model_dump(exclude_unset=True)` na rota.

    `respostas` funciona como upsert por `numero_item`: os itens enviados são
    criados/atualizados e os demais permanecem como estão.
    """

    model_config = ConfigDict(extra="forbid")

    status: Optional[StatusChecklist] = None
    respostas: Optional[list[RespostaCreate]] = None

    @field_validator("status", mode="before")
    @classmethod
    def _normalizar_status(cls, v: Any) -> Any:
        return _normalizar_enum(v)

    @field_validator("respostas")
    @classmethod
    def _respostas_sem_duplicidade(cls, v):
        return _sem_itens_duplicados(v)


class ChecklistResponse(ChecklistCampos):
    """Checklist completa retornada pela API (aceita objetos ORM)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: StatusChecklist
    created_at: datetime
    updated_at: datetime
    respostas: list[RespostaResponse] = Field(default_factory=list)

    @field_validator("status", mode="before")
    @classmethod
    def _normalizar_status(cls, v: Any) -> Any:
        return _normalizar_enum(v)