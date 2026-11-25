#!/usr/bin/env bash
# Cria labels e issues no GitHub a partir de docs/tarefas.psv (requer GitHub CLI: gh auth login).
set -euo pipefail
cd "$(dirname "$0")/.."
for l in PO BE FE DA D1 D2 D3 D4 MUST SHOULD; do gh label create "$l" --force >/dev/null 2>&1 || true; done
tail -n +2 docs/tarefas.psv | while IFS='|' read -r id titulo time dia tam prio criterio; do
  [ -z "${id:-}" ] && continue
  gh issue create --title "[$id] $titulo" --label "$time,$dia,$prio" \
    --body "**Tamanho:** $tam | **Dia alvo:** $dia | **Prioridade:** $prio

**Critério de aceite:** $criterio

Ver docs/00-contrato.md e o PRD do seu time. Só mover para Pronto depois que o PO vir funcionando."
done
