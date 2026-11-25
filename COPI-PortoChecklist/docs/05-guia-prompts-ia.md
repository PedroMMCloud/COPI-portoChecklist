# 05 — Guia rápido de IA

## Regras de ouro
1. **Contexto:** cole o trecho do contrato/PRD relevante. 2. **Uma tarefa por prompt.** 3. **Peça teste junto** (com `caso_foto.json`). 4. **Peça explicação** do código. 5. **Rode antes de commitar.** 6. **Nunca cole segredos ou dados reais.** 7. Não consegue explicar? Não faça commit. 8. **30 min travado ⇒ peça ajuda humana.** 9. Confira nomes/versões de pacotes na documentação oficial.

## Molde
```
PAPEL: dev sênior de [Python/FastAPI | Flutter], explicando para iniciante.
CONTEXTO: app de checklist de guindaste offline-first. Regras e API: [cole o trecho do contrato]
TAREFA (uma só): [ex.: serviço de validação RN01–RN06]
RESTRIÇÕES: siga a estrutura de pastas; sem libs novas; código simples e comentado.
ENTREGA: plano curto · código por arquivo · testes com este fixture [cole] · como rodar · riscos.
```

## Revisão de código de IA (2 min)
Entendi cada função? · Segue o contrato? · Trata erro/vazio/sem internet? · Há teste que falha se eu quebrar a regra? · Sem segredo? · Dependência nova é real e necessária? · PR pequeno?

## Git
`git pull` · `git checkout -b feat/BE-05-put-checklist` · commits pequenos (`BE-05: valida horímetro`) · PR com 1 revisão · mover o cartão para Pronto só depois do PO ver funcionando.
