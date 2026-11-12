from sqlalchemy import (
    Column, Integer, String, ForeignKey, LargeBinary
)

from app.database.connection import Base

class ChecklistAssinatura(Base):

    __tablename__ = "checklist_assinaturas"
    id = Column(Integer, primary_key=True, index=True)

    checklist_id = Column(
        Integer,
        ForeignKey("checklists.id"),
        nullable=False
    )

    tipo = Column(String(20), nullable=False)
    nome = Column(String(150), nullable=False)
    assinatura_url = Column(String(500), nullable=True)