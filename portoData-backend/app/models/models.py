"""
Modelos ORM das checklists portuárias.

Uso:
    from models import Checklist, ChecklistResposta, RespostaEnum, StatusChecklist
"""

import enum
from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime,
    Enum, ForeignKey, Integer,Numeric,
    String, Text, Time, UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.database import Base


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
# Catálogo dos 23 itens de inspeção: (número, descrição, crítico)
# --------------------------------------------------------------------------- #
ITENS_CHECKLIST: list[tuple[int, str, bool]] = [
    (1, "Cinto de segurança, OK?", True),
    (2, "Botões de controle, funcionando?", True),
    (3, "Sistema de comunicação (rádio e megafone), OK?", True),
    (4, "Alerta sonoro - sirene, OK?", True),
    (5, "Buzina funciona normalmente?", True),
    (6, "Botões de emergência, OK?", True),
    (7, "Freio de emergência em condições?", True),
    (8, "Freios em boas condições de uso?", True),
    (9, "Limpador de para-brisa funcionando?", True),
    (10, "Inspeção visual (patolas, pneus e vazamentos), OK?", False),
    (11, "Painel de comando, exibe todas as informações?", False),
    (12, "Nível de combustível, OK?", False),
    (13, "Nível de água no radiador, OK?", False),
    (14, "Nível de óleo do motor, OK?", False),
    (15, "Nível de óleo da transmissão, OK?", False),
    (16, "Nível de óleo hidráulico, OK?", False),
    (17, "Sistema hidráulico apresenta vazamentos? Possui vazamento de óleo?", False),
    (18, "Funcionamento do grab, cabos de aço?", False),
    (19, "Apresenta avaria na lataria, OK?", False),
    (20, "Extintor de incêndio com data de validade vigente", False),
    (21, "Extintor pressurizado? Está em suporte adequado?", False),
    (22, "Pneus em boas condições?", False),
    (23, "Ar condicionado em condições de uso?", False),

]

TOTAL_ITENS = len(ITENS_CHECKLIST)


# --------------------------------------------------------------------------- #
# Checklist (dados gerais da inspeção)
# --------------------------------------------------------------------------- #
class Checklist(Base):
    __tablename__ = "checklists"

    __table_args__ = (
        CheckConstraint(
            "nivel_combustivel IS NULL OR (nivel_combustivel >= 0 AND nivel_combustivel <= 100)",
            name="ck_checklists_nivel_combustivel",
        ),
        CheckConstraint(
            "horimetro_final IS NULL OR horimetro_inicial IS NULL "
            "OR horimetro_final >= horimetro_inicial",
            name="ck_checklists_horimetro",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Campos gerais opcionais no banco para permitir checklists em RASCUNHO;
    # a obrigatoriedade para PREENCHIDA/ASSINADA é validada em schemas.py.
    # Identificação do formulário
    codigo_formulario: Mapped[Optional[str]] = mapped_column(String(50))
    versao: Mapped[Optional[str]] = mapped_column(String(20))

    # Dados da operação
    local_atuacao: Mapped[Optional[str]] = mapped_column(String(150))
    turno: Mapped[Optional[str]] = mapped_column(String(30))
    data: Mapped[Optional[date]] = mapped_column(Date, index=True)
    navio: Mapped[Optional[str]] = mapped_column(String(150), index=True)
    guindaste: Mapped[Optional[str]] = mapped_column(String(100), index=True)

    # Leituras do equipamento
    horimetro_inicial: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 1))
    horimetro_final: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 1))
    nivel_combustivel: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))

    # Horários da operação
    hora_entrada: Mapped[Optional[time]] = mapped_column(Time)
    hora_saida: Mapped[Optional[time]] = mapped_column(Time)

    observacao_geral: Mapped[Optional[str]] = mapped_column(Text)

    # Responsáveis e assinaturas (texto/base64 ou caminho/URL do arquivo)
    nome_operador: Mapped[Optional[str]] = mapped_column(String(150))
    assinatura_operador: Mapped[Optional[str]] = mapped_column(Text)
    nome_lideranca: Mapped[Optional[str]] = mapped_column(String(150))
    assinatura_lideranca: Mapped[Optional[str]] = mapped_column(Text)

    status: Mapped[StatusChecklist] = mapped_column(
        Enum(StatusChecklist, native_enum=False, length=20, create_constraint=True,
             name="status_checklist"),
        nullable=False,
        default=StatusChecklist.RASCUNHO,
        server_default=StatusChecklist.RASCUNHO.value,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Uma checklist possui várias respostas; ao excluí-la, as respostas são removidas.
    respostas: Mapped[list["ChecklistResposta"]] = relationship(
        back_populates="checklist",
        cascade="all, delete-orphan",
        order_by="ChecklistResposta.numero_item",
    )

    def criar_respostas_padrao(self) -> None:
        """Adiciona os 23 itens à checklist (sem resposta definida ainda)."""
        existentes = {r.numero_item for r in self.respostas}
        for numero, descricao, critico in ITENS_CHECKLIST:
            if numero not in existentes:
                self.respostas.append(
                    ChecklistResposta(
                        numero_item=numero,
                        descricao=descricao,
                        critico=critico,
                    )
                )

    def __repr__(self) -> str:
        return (
            f"<Checklist id={self.id} guindaste={self.guindaste!r} "
            f"data={self.data} status={self.status.value if self.status else None}>"
        )


# --------------------------------------------------------------------------- #
# ChecklistResposta (um registro por item inspecionado)
# --------------------------------------------------------------------------- #
class ChecklistResposta(Base):
    __tablename__ = "checklist_respostas"

    __table_args__ = (
        # Impede resposta duplicada do mesmo item na mesma checklist.
        UniqueConstraint("checklist_id", "numero_item", name="uq_checklist_item"),
        CheckConstraint(
            f"numero_item >= 1 AND numero_item <= {TOTAL_ITENS}",
            name="ck_checklist_respostas_numero_item",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    checklist_id: Mapped[int] = mapped_column(
        ForeignKey("checklists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    numero_item: Mapped[int] = mapped_column(Integer, nullable=False)
    descricao: Mapped[str] = mapped_column(String(255), nullable=False)

    # Nulo enquanto o item ainda não foi respondido (checklist em rascunho).
    resposta: Mapped[Optional[RespostaEnum]] = mapped_column(
        Enum(RespostaEnum, native_enum=False, length=20, create_constraint=True,
             name="resposta_item")
    )
    observacao: Mapped[Optional[str]] = mapped_column(Text)

    critico: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    checklist: Mapped["Checklist"] = relationship(back_populates="respostas")

    def __repr__(self) -> str:
        return (
            f"<ChecklistResposta checklist_id={self.checklist_id} "
            f"item={self.numero_item} resposta={self.resposta.value if self.resposta else None}>"
        )