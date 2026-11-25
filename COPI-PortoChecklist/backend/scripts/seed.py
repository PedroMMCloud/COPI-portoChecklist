# Popula o banco com dados iniciais (usuários, locais, equipamentos e o template
# do checklist) lendo arquivos JSON da pasta definida em settings.SEED_DIR.
# Pode ser executado várias vezes: só insere o que ainda não existe.
# Dependência extra:  pip install argon2-cffi
# Como rodar (na raiz do projeto):  python -m app.seed

import json
from pathlib import Path

from argon2 import PasswordHasher
from sqlalchemy import select

import app.models as m
from app.config import settings
from app.db import Base, SessionLocal, engine

# Objeto que gera e verifica hashes argon2 (usa parâmetros seguros por padrão)
ph = PasswordHasher()

ARQ_DEMO = "demo_usuarios_locais_equipamentos.json"
ARQ_TEMPLATE = "checklist_template_for_opp_0017_v5.json"


def ler(nome: str) -> dict:
    """Lê um arquivo JSON de dentro de settings.SEED_DIR."""
    caminho = Path(settings.SEED_DIR) / nome
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo de seed não encontrado: {caminho}")
    return json.loads(caminho.read_text(encoding="utf-8"))


def hash_pin(pin: str) -> str:
    """Transforma o PIN em hash argon2 (o PIN em texto puro nunca vai ao banco)."""
    return ph.hash(pin)


def seed_demo(db, demo: dict) -> dict:
    """Cria usuários, locais e equipamentos que ainda não existem."""
    criados = {"usuarios": 0, "locais": 0, "equipamentos": 0}

    for u in demo["usuarios"]:
        existe = db.scalars(select(m.Usuario).filter_by(matricula=u["matricula"])).first()
        if not existe:
            db.add(
                m.Usuario(
                    matricula=u["matricula"],
                    nome=u["nome"],
                    papel=u["papel"],
                    pin_hash=hash_pin(u["pin"]),
                )
            )
            criados["usuarios"] += 1

    for loc in demo["locais"]:
        existe = db.scalars(select(m.Local).filter_by(nome=loc["nome"])).first()
        if not existe:
            db.add(m.Local(nome=loc["nome"]))
            criados["locais"] += 1

    for eq in demo["equipamentos"]:
        existe = db.scalars(
            select(m.Equipamento).filter_by(identificacao=eq["identificacao"])
        ).first()
        if not existe:
            # O campo "observacao" do JSON é só uma nota; não existe no modelo, então é ignorado
            db.add(m.Equipamento(identificacao=eq["identificacao"]))
            criados["equipamentos"] += 1

    return criados


def seed_template(db, t: dict) -> int:
    """Cria o template e seus itens, se essa combinação código + versão ainda não existe.

    Retorna a quantidade de itens criados (0 se o template já existia).
    """
    existe = db.scalars(
        select(m.Template).filter_by(codigo=t["codigo"], versao=t["versao"])
    ).first()
    if existe:
        return 0

    tpl = m.Template(
        codigo=t["codigo"],
        versao=t["versao"],
        data_versao=t["data_versao"],
        titulo=t["titulo"],
    )
    db.add(tpl)
    db.flush()  # envia ao banco para que tpl.id já esteja disponível

    for i in t["itens"]:
        db.add(
            m.TemplateItem(
                template_id=tpl.id,
                numero=i["numero"],
                descricao=i["descricao"],
                critico=i.get("critico", False),
                permite_na=i.get("permite_na", True),
            )
        )
    return len(t["itens"])


def main() -> None:
    # Cria as tabelas que ainda não existem
    Base.metadata.create_all(engine)

    demo = ler(ARQ_DEMO)
    template = ler(ARQ_TEMPLATE)

    # "with" garante que a sessão é fechada; se der erro antes do commit, nada é salvo
    with SessionLocal() as db:
        criados = seed_demo(db, demo)
        itens = seed_template(db, template)
        db.commit()

    print("seed ok")
    print(
        f"  usuários: {criados['usuarios']} | locais: {criados['locais']} "
        f"| equipamentos: {criados['equipamentos']} | itens de template: {itens}"
    )


if __name__ == "__main__":
    main()