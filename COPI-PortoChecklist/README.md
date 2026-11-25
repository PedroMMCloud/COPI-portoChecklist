# Checklist Digital de Guindaste — MVP de demonstração

App Android que substitui o papel **FOR-OPP-0017 v5 (COPI)**. Um app, uma tela de login, dois perfis (Operador e Administrador), funcionando **offline** e sincronizando com um servidor central.
**Meta:** demo ao vivo de 5–7 min em dois aparelhos. Prazo: **3 dias de desenvolvimento (D2–D4)**; os dias extras são só para ensaio e correção.

## Leia nesta ordem
1. `docs/00-contrato.md` — **todos** (regras, API, estados). Se divergir de qualquer coisa, este arquivo manda.
2. `docs/01-PRD-PO-plano-3-dias.md` — escopo, plano, cortes.
3. O PRD do seu time: `02-backend.md` · `03-frontend.md` · `04-dados-qa.md`
4. `docs/05-guia-prompts-ia.md` — como usar IA sem se perder.
5. `docs/06-prompt-gemini-canvas.md` — prompt para visualizar a ideia antes de codar.

## Estrutura
```
backend/   API (FastAPI) + banco (SQLite na demo) — roda direto com Python, sem Docker
app/       App Flutter (criar com `flutter create`, ver app/README.md)
dados/     seed (23 itens, usuários demo) e fixtures (caso da foto)
docs/      contrato, PRDs, tarefas.psv
scripts/   criar_issues.sh (cria as tarefas no GitHub)
```

## Receita de bolo (quem monta o repositório — PO/líder)
1. **Criar o repo:** `git init && git branch -M main && git add . && git commit -m "base do projeto" && gh repo create checklist-guindaste --private --source . --push` (ou crie pelo site e faça `git remote add origin ... && git push -u origin main`).
2. **Proteger a `main`:** Settings → Branches → exigir Pull Request com 1 aprovação.
3. **Convidar a equipe** (Settings → Collaborators).
4. **Criar as tarefas:** `gh auth login` e depois `bash scripts/criar_issues.sh` (no Windows, use o Git Bash) (gera as 37 issues com labels de time/dia).
5. **Criar o quadro:** GitHub → Projects → Board com colunas `A fazer · Em andamento · Em revisão · Pronto · Bloqueado`; adicionar as issues.
6. **Copiar o ambiente:** `cp .env.example .env` (dentro de `backend/` se rodar com Python; veja `backend/README.md`).
7. **Testar o servidor (sem Docker):** seguir `backend/README.md` (3 comandos com Python) → abrir http://localhost:8000/api/v1/health e http://localhost:8000/docs. *Docker é opcional* (só para deploy/portabilidade; ver `backend/README.md`).
8. **Criar o app (time Front-end):** ver `app/README.md`.
9. **Daily de 15 min** todo dia no mesmo horário. **PR pequeno + 1 revisão**, nome de branch `tipo/ID-descricao` (ex.: `feat/BE-05-put-checklist`).

## Regras de convivência
- Nada de segredo, `.env`, keystore ou dado real no Git.
- Mudou algo do contrato? Abra PR em `docs/00-contrato.md` e avise na daily.
- Travado há 30 min? Peça ajuda a um colega ou ao PO.
