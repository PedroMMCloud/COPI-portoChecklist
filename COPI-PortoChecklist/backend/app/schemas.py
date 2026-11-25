# "Schemas" descrevem o formato dos JSONs que entram e saem da API.
# O FastAPI usa estas classes para:
#   - conferir o tipo de cada campo antes de a rota rodar (erro 422 se estiver errado)
#   - gerar a documentação em /docs
#
# As regras de negócio (item crítico, horímetro, etc.) ficam em app/regras.py.

from typing import Literal

from pydantic import BaseModel


class RespostaIn(BaseModel):
    """Resposta de um item do checklist."""

    item_numero: int
    resposta: Literal["S", "N", "NA"]
    origem: Literal["LOTE", "MANUAL"] = "MANUAL"
    observacao: str | None = None


class ChecklistIn(BaseModel):
    """Checklist completo, como o app envia."""

    template_id: str
    equipamento_id: str
    local_id: str
    data_turno: str
    turno: str
    navio: str | None = None
    horimetro_inicial: float
    horimetro_final: float | None = None
    combustivel_pct: int
    hora_entrada: str
    hora_saida: str | None = None
    observacao_geral: str | None = None
    assinatura_operador: str | None = None
    usou_lote: bool = False
    itens_marcados_lote: int = 0
    itens_alterados_apos_lote: int = 0
    inicio_preenchimento_em: str | None = None
    finalizado_em: str | None = None
    duracao_segundos: int | None = None
    confirmacao_correcao: bool = False
    criado_no_dispositivo_em: str | None = None
    app_versao: str | None = None
    respostas: list[RespostaIn]


class ChecklistOut(BaseModel):
    """Resposta da API depois de enviar/editar um checklist."""

    id: str
    status: str
    revisao: int
    impedido: bool
    editado: bool

class CorrecaoIn(BaseModel):
    """Dados enviados pelo administrador ao solicitar correção."""

    motivo: str