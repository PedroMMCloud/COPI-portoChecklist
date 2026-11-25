# 01 — PRD do PO + Plano de 3 dias

## 1. Objetivo
**Demo ao vivo de 5–7 min, em dois aparelhos, que rode duas vezes seguidas sem falhar.** Não é produto final.

## 2. Roteiro da demo (é o critério de aceite do projeto)
1. Celular A: login do operador (atalho de demo). 2. Preencher o cabeçalho. 3. **Marcar tudo OK** (confirmação) e alterar os itens 1, 10 e 22 com observação ⇒ aparece **"Equipamento impedido"**. 4. Ligar modo avião, finalizar, assinar ⇒ "Pendente de envio". 5. Desligar modo avião ⇒ sincroniza. 6. Celular B: login do admin ⇒ lista com **impedido em destaque**, contadores. 7. Abrir o **detalhe completo** (problemas no topo, todos os itens, assinatura, metadados). 8. **Solicitar correção** (ex.: "Horímetro final conferir"). 9. Celular A: vê o motivo, edita, toca "Confirmo as correções" ⇒ selo **Editado**. 10. Celular B: vê a linha do tempo e **Vistar** ⇒ final/travado.

## 3. Escopo
**MUST:** login único; cabeçalho; 23 itens S/N/N-A + observação; lote "Marcar tudo OK"; alerta de impedimento; assinatura; offline + sincronização; lista do admin com contadores; detalhe completo; Vistar; Solicitar correção; edição pelo operador + selo Editado + log; APK em 2 aparelhos.
**SHOULD (só se sobrar):** destaque "o que mudou" entre revisões; filtros extras.
**FORA:** Azure como requisito, PDF, CRUD de cadastros (entram por seed), dashboard, relatórios, iOS, integrações, notificações, fotos.

## 4. Plano
> **D1 = hoje (ajustes e preparação).** D2–D4 desenvolvimento. Dias extras só para ensaio e bugs. O código **congela no fim do D4**.

| Quando | Meta (fim do dia) | Front-end | Back-end | Dados/QA |
|---|---|---|---|---|
| **D1 (noite)** | Todo mundo roda o "hello world" | Flutter instalado, projeto criado | servidor local rodando ⇒ `/health` | Conferir seed com o papel |
| **D2** | **Fatia ponta a ponta online** | Login, cabeçalho, 23 itens, envio | Login, template, `PUT /checklists`, listagem | Seed demo, fixture, roteiro |
| **Checkpoint D2** | O fixture chega ao servidor e aparece na lista do admin? | | | **Se não: cortar já correção/edição** |
| **D3** | **Offline + valor** | Lote, impedimento, assinatura, fila offline, telas do admin | Impedimento, vistar, solicitar correção, eventos | Teste em 2 aparelhos |
| **D4** | **Edição + APK + ensaio** | Edição, selo, linha do tempo, APK | Snapshot, trava `VISTADO`, deploy | Ensaio 2x + vídeo plano B |

**Ordem de corte se atrasar:** 1) destaque "o que mudou", 2) selo/linha do tempo, 3) Solicitar correção. **Nunca cortar:** offline, impedimento, detalhe completo, Vistar.

## 5. Papel do PO (resumo)
- Decide o que entra/sai (regra: **entra um, sai um**). Remove bloqueios em até 2 h.
- Daily de 15 min. Atualiza o quadro 2x/dia. Só move para **Pronto** após **ver funcionando**.
- Semáforo diário: 🟢 no prazo · 🟡 risco com plano · 🔴 atrasado ⇒ decidir corte.

## 6. Definition of Done
PR revisado por 1 colega · critério de aceite cumprido · testado com `caso_foto.json` · sem segredo/dado real · docs atualizados se mudou contrato · PO viu funcionando.

## 7. Riscos
| Risco | Resposta |
|---|---|
| Equipe iniciante trava | Duplas, tarefas P/M/G, pedir ajuda após 30 min |
| Sincronização é a parte mais difícil | App funciona local primeiro; contrato `PUT` idempotente; checkpoint D2 |
| Sem internet na apresentação | Servidor no notebook + celulares no mesmo Wi-Fi/hotspot; **testar no D3** |
| Código de IA com erro | PR + testes; `05-guia-prompts-ia.md` |
| Mudança de escopo | Só o PO aprova |
| Aparelhos/versão Android | Descobrir hoje; testar em aparelho real no D3 |

## 8. Tarefas
Lista completa em `tarefas.psv` (importe com `scripts/criar_issues.sh`). Resumo: **PO 5 · BE 12 · FE 14 · DA/QA 6**.
