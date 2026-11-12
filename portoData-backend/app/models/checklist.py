from sqlalchemy import (
    Column, Integer, String, Date, Numeric, ForeignKey, Text
)

from sqlalchemy.orm import relationship
from app.database.connection import Base


class Checklist(Base):

    __tablename__ = "checklists"
    id = Column(Integer, primary_key=True, index=True)

    modelo_id = Column(
        Integer,
        ForeignKey("checklist_modelos.id"),
        nullable=False
    )

    local_atuacao = Column(String(100), nullable=False)
    turno = Column(String(10), nullable=False)
    data = Column(Date, nullable=False)
    navio = Column(String(150))
    guindaste = Column(String(150), nullable=False)
    horimetro_inicial = Column(Numeric(12, 2))
    horimetro_final = Column(Numeric(12, 2))
    nivel_combustivel = Column(Numeric(5, 2))
    hora_entrada = Column(String(5))
    hora_saida = Column(String(5))
    observacao_geral = Column(Text)
    status = Column(String(30), default="RASCUNHO")
    
    respostas = relationship(
        "ChecklistResposta",
        back_populates="checklist",
        cascade="all, delete-orphan"
    )