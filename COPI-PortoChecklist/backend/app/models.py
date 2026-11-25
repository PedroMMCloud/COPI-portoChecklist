
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base  # "Base" é a classe-mãe de todas as tabelas (definida em app/db.py)


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------
def novo_id() -> str:
    """Gera um identificador único (UUID), usado como chave primária."""
    return str(uuid.uuid4())


def agora() -> datetime:
    """Devolve a data/hora atual em UTC (padrão para guardar datas no banco)."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# CADASTROS BÁSICOS
# ---------------------------------------------------------------------------
class Usuario(Base):
    """Quem usa o sistema: operadores (preenchem) e administradores (revisam)."""

    __tablename__ = "usuarios"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=novo_id)
    matricula: Mapped[str] = mapped_column(String(20), unique=True)  # unique = não repete
    nome: Mapped[str] = mapped_column(String(120))
    papel: Mapped[str] = mapped_column(String(10))  # OPERADOR | ADMIN
    pin_hash: Mapped[str] = mapped_column(String(255))  # PIN guardado criptografado, nunca em texto puro
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)  # desativar em vez de apagar


class Local(Base):
    """Lugares onde o trabalho acontece (ex.: berço, pátio)."""

    __tablename__ = "locais"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=novo_id)
    nome: Mapped[str] = mapped_column(String(80), unique=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


class Equipamento(Base):
    """Equipamentos que passam por checklist, com identificação única."""

    __tablename__ = "equipamentos"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=novo_id)
    identificacao: Mapped[str] = mapped_column(String(80), unique=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


# ---------------------------------------------------------------------------
# MODELO DO CHECKLIST (o "formulário em branco")
# ---------------------------------------------------------------------------
class Template(Base):
    """Um modelo de checklist, com código e versão (o formulário em branco)."""

    __tablename__ = "checklist_templates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=novo_id)
    codigo: Mapped[str] = mapped_column(String(30))
    versao: Mapped[int] = mapped_column(Integer)
    data_versao: Mapped[str] = mapped_column(String(10))
    titulo: Mapped[str] = mapped_column(String(120))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    # relationship = atalho no Python: template.itens devolve a lista de perguntas
    itens: Mapped[list["TemplateItem"]] = relationship(order_by="TemplateItem.numero")


class TemplateItem(Base):
    """Cada pergunta de um modelo de checklist."""

    __tablename__ = "checklist_template_itens"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=novo_id)
    # ForeignKey = liga este item ao template ao qual ele pertence
    template_id: Mapped[str] = mapped_column(ForeignKey("checklist_templates.id"))
    numero: Mapped[int] = mapped_column(Integer)  # posição da pergunta no formulário
    descricao: Mapped[str] = mapped_column(String(200))
    critico: Mapped[bool] = mapped_column(Boolean, default=False)  # item crítico de segurança
    permite_na: Mapped[bool] = mapped_column(Boolean, default=True)  # aceita "Não se aplica"?


# ---------------------------------------------------------------------------
# PREENCHIMENTO (o que o operador faz)
# ---------------------------------------------------------------------------
class Checklist(Base):
    """Um checklist preenchido por um operador, para um equipamento, em um turno."""

    __tablename__ = "checklists"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID gerado no APP

    # Ligações com outras tabelas
    template_id: Mapped[str] = mapped_column(ForeignKey("checklist_templates.id"))
    operador_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id"))
    equipamento_id: Mapped[str] = mapped_column(ForeignKey("equipamentos.id"))
    local_id: Mapped[str] = mapped_column(ForeignKey("locais.id"))

    # Datas/horas vindas do app ficam como texto ISO (simples para a demo)
    data_turno: Mapped[str] = mapped_column(String(10))
    turno: Mapped[str] = mapped_column(String(10))
    navio: Mapped[str | None] = mapped_column(String(120), nullable=True)  # nullable = opcional

    # Dados da operação
    horimetro_inicial: Mapped[float] = mapped_column(Float)
    horimetro_final: Mapped[float | None] = mapped_column(Float, nullable=True)
    combustivel_pct: Mapped[int] = mapped_column(Integer)
    hora_entrada: Mapped[str] = mapped_column(String(5))
    hora_saida: Mapped[str | None] = mapped_column(String(5), nullable=True)
    observacao_geral: Mapped[str | None] = mapped_column(Text, nullable=True)
    assinatura_operador: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Controle de situação e edição
    status: Mapped[str] = mapped_column(String(25), default="ENVIADO")
    impedido: Mapped[bool] = mapped_column(Boolean, default=False)
    revisao: Mapped[int] = mapped_column(Integer, default=1)  # número da revisão atual
    editado: Mapped[bool] = mapped_column(Boolean, default=False)

    # Estatísticas do preenchimento em lote ("marcar tudo como S")
    usou_lote: Mapped[bool] = mapped_column(Boolean, default=False)
    itens_marcados_lote: Mapped[int] = mapped_column(Integer, default=0)
    itens_alterados_apos_lote: Mapped[int] = mapped_column(Integer, default=0)

    # Tempos e informações do dispositivo
    inicio_preenchimento_em: Mapped[str | None] = mapped_column(String(40), nullable=True)
    finalizado_em: Mapped[str | None] = mapped_column(String(40), nullable=True)
    duracao_segundos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    criado_no_dispositivo_em: Mapped[str | None] = mapped_column(String(40), nullable=True)
    app_versao: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Visto de um administrador
    vistado_por: Mapped[str | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    vistado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Quando o servidor recebeu o checklist
    recebido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)

    # checklist.respostas devolve todas as respostas; apagar o checklist apaga as respostas
    respostas: Mapped[list["Resposta"]] = relationship(
        cascade="all, delete-orphan", order_by="Resposta.item_numero"
    )


class Resposta(Base):
    """A resposta de UM item dentro de UM checklist."""

    __tablename__ = "checklist_respostas"
    # Chave primária composta: cada item só pode ter uma resposta por checklist
   
    checklist_id: Mapped[str] = mapped_column(ForeignKey("checklists.id"), primary_key=True)
    item_numero: Mapped[int] = mapped_column(Integer, primary_key=True)
    resposta: Mapped[str] = mapped_column(String(2))  # S | N | NA
    origem: Mapped[str] = mapped_column(String(6), default="MANUAL")  # LOTE | MANUAL
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# HISTÓRICO E AUDITORIA
# ---------------------------------------------------------------------------
class Evento(Base):
    """Diário do checklist: registra cada coisa que aconteceu, por quem e quando."""

    __tablename__ = "checklist_eventos"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=novo_id)
    checklist_id: Mapped[str] = mapped_column(ForeignKey("checklists.id"))
    tipo: Mapped[str] = mapped_column(String(25))  # CRIADO, EDITADO, REENVIADO, CORRECAO_SOLICITADA, VISTADO
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id"))
    detalhe: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # informações extras livres
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)


class Revisao(Base):
    """'Foto' (snapshot em JSON) do checklist a cada revisão, para consultar versões antigas."""

    __tablename__ = "checklist_revisoes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=novo_id)
    checklist_id: Mapped[str] = mapped_column(ForeignKey("checklists.id"))
    revisao: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSON)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)