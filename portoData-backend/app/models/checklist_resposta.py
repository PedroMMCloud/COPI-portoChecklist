from sqlalchemy import (
    Column, Integer, String, ForeignKey, Text
)

from sqlalchemy.orm import relationship
from app.database.connection import Base


class ChecklistResposta(Base):

    __tablename__ = "checklist_respostas"

    id = Column(Integer, primary_key=True, index=True)

    checklist_id = Column(
        Integer,
        ForeignKey("checklists.id"),
        nullable=False
    )

    item_id = Column(
        Integer,
        ForeignKey("checklist_itens.id"),
        nullable=False
    )

    resposta = Column(String(20), nullable=False)
    observacao = Column(Text, nullable=True)

    checklist = relationship(
        "Checklist",
        back_populates="respostas"
    )