# 07 — Monorepo e trabalho em equipe (3 times em paralelo)

## 1. O que é
**Um único repositório** com uma pasta por time. Todos fazem `git clone` uma vez e trabalham **só na sua pasta**.

| Pasta | Dono | Pode mexer em outras? |
|---|---|---|
| `backend/` | Back-end | Não |
| `app/` | Front-end | Não |
| `dados/` | Dados/QA | Não |
| `docs/`, `README.md`, `scripts/`, `.github/` | PO | Só via PR avisado no grupo |
| **Arquivos compartilhados:** `docs/00-contrato.md`, `docs/tarefas.psv`, `.env.example`, `docker-compose.yml`, `.gitignore` | Todos (com cuidado) | **Só via PR + aviso no grupo** |

Por que dá certo: cada time quase nunca edita o mesmo arquivo que o outro, então há poucos conflitos.

## 2. Rotina de cada pessoa (cole na parede)
```bash
git switch main && git pull                     # 1. todo dia ao começar
git switch -c feat/BE-05-put-checklist           # 2. uma branch por tarefa (ID da issue)
# ... trabalha, testa ...
git add backend/                                 # 3. adicione só a SUA pasta
git commit -m "BE-05: valida horímetro final"    # 4. commits pequenos
git fetch && git merge origin/main               # 5. antes do PR: traz o que mudou
git push -u origin feat/BE-05-put-checklist      # 6. abre o Pull Request no GitHub
```
- **PR pequeno** (uma tarefa), preenchendo o modelo. **1 colega revisa** (outra pessoa, não o autor).
- Depois do merge: mover o cartão para **Pronto** e `git switch main && git pull`.
- **Nunca:** `git push --force`, commitar na `main`, commitar `.env`/senha/keystore, reformatar arquivos de outros times.

## 3. Conflito de merge (vai acontecer; não é erro grave)
1. Não entre em pânico e **não apague o código do colega**. 2. Abra o arquivo, procure `<<<<<<<`, decida junto com o autor do outro lado o que fica. 3. `git add` o arquivo e `git commit`. 4. Travou? Peça ajuda no grupo.

## 4. Como os times se conectam sem se esbarrar
- O **contrato (`00-contrato.md`)** é a "tomada padrão": Front e Back só precisam respeitá-lo.
- Até o Back-end subir (fim do D2), o Front usa o **modo mock**.
- Quem mudar contrato: abre PR em `00-contrato.md`, posta no grupo, e **os líderes dos 3 times respondem "ok"** antes do merge. Sem "ok", não entra.
- Dado de teste comum: `dados/fixtures/caso_foto.json` (todo mundo usa o mesmo).

## 5. Enquanto o PO estiver ausente
1. **Cada time escolhe 1 líder técnico** (quem faz merge dos PRs do próprio time e responde pelo contrato).
2. **Um líder faz de "PO substituto"** (avise o nome no grupo): decide cortes seguindo `01-PRD-PO-plano-3-dias.md` §4 e conduz o **checkpoint do fim do D2**.
3. **Daily assíncrona:** no fim do dia, cada pessoa posta no grupo 3 linhas: *fiz / vou fazer / bloqueio*.
4. **Dúvida de negócio** (ex.: item crítico): não espere. Siga a suposição do contrato, **registre em uma issue "Decisões para o PO"** e continue.
5. Mudou escopo ou contrato? Registre no "Histórico de mudanças" do contrato.
6. Nada de merge com teste quebrado ou sem ninguém ter visto funcionando.

## 6. Configuração do GitHub (PO, antes de sair)
- Settings → Branches → regra para `main`: **exigir Pull Request** com **1 aprovação**.
- Settings → General → marcar **"Automatically delete head branches"**.
- Convidar todos com permissão **Write**.
- Opcional: criar 3 labels de time (já criadas por `scripts/criar_issues.sh`) e fixar uma issue "Decisões para o PO".
