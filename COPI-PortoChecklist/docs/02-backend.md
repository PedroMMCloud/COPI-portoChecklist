# 02 — PRD Back-end

**Dono de:** API, regras de negócio, banco e servidor da demo. **Leia antes:** `00-contrato.md`.

## Stack (proposta; o time pode trocar se dominar outra, mantendo o contrato)
Python 3.12 · FastAPI · SQLAlchemy 2 · SQLite (demo; compatível com PostgreSQL) · PyJWT · argon2 · pytest. **Docker é opcional.**
O esqueleto já roda com Python puro (ver `backend/README.md`) ⇒ `/api/v1/health` e `/docs`.

## Estrutura
`app/main.py` (rotas registradas) · `app/models.py` (tabelas do contrato §5) · `app/schemas.py` (Pydantic) · `app/routers/` (finas) · `app/services/` (**regras**) · `scripts/seed.py` · `tests/`.

## Requisitos essenciais
- Login por matrícula + PIN (hash argon2) ⇒ JWT com `papel`.
- `PUT /checklists/{id}` **cria ou edita** (idempotente): valida RN01–RN06, calcula `impedido`, usa o operador do token, aplica **RN07/RN08** (evento + snapshot, `revisao`+1, `editado`, 409 se `VISTADO`).
- `vistar` e `solicitar-correcao` conforme RN09/RN10; admin nunca edita checklist.
- `GET /checklists` com contadores (`pendentes`, `impedidos`, `correcao`, `vistados_hoje`) e filtros; RN13.
- Segurança mínima: segredos em `.env`, nunca logar PIN/token/assinatura, CORS configurável.

## Tarefas (detalhe e aceite em `tarefas.psv`)
BE-01 ambiente local · BE-02 modelos+seed · BE-03 login · BE-04 template/lookups · **BE-05 PUT checklist** · BE-06 listagem/detalhe · BE-07 vistar · BE-08 solicitar correção · BE-09 eventos+snapshot+trava · BE-10 último horímetro · BE-11 testes · BE-12 servidor da demo acessível pelos 2 aparelhos (Docker opcional).

## Testes mínimos (com `caso_foto.json`)
1. Fixture ⇒ aceito, `impedido=true`, status `ENVIADO`. 2. Falta 1 item ⇒ 400. 3. N sem observação ⇒ 400. 4. Horímetro final < inicial ⇒ 400. 5. Mesmo `id` 2x ⇒ 1 registro. 6. Operador tenta vistar ⇒ 403. 7. Admin vista ⇒ 200; vista de novo ⇒ 409. 8. PUT após `VISTADO` ⇒ 409. 9. Edição ⇒ `revisao=2`, `editado=true`, 1 snapshot, 1 evento. 10. Operador A não lê checklist do B. 11. `T_20_02` com saída < entrada ⇒ aceito.

## Dicas
Uma rota por vez, testando no `/docs`. Escreva o teste do fixture **antes**. Peça à IA para explicar antes de colar.
