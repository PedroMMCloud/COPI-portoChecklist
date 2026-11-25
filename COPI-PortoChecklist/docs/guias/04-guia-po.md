# Guia 04 — PO passo a passo (PO-01 a PO-05 + kit para quem substituir o PO)

## PO-01 — Congelar premissas e contrato (D1 noite, ~1h)
1. Poste no grupo (modelo abaixo) e peça **"li e confirmo"** de cada líder.
2. Confirme a **stack** (Flutter + FastAPI) com a equipe; se algum time domina outra coisa, registre a mudança no contrato (§11) **antes** de começar.
3. Defina: PO substituto (se você vai se ausentar), 1 líder técnico por time, horário da daily.
```
Pessoal, o projeto é um app Android que substitui o checklist de papel do guindaste (FOR-OPP-0017).
Meta: demo ao vivo de 5–7 min em 2 celulares. Prazo: D2–D4 para desenvolver, depois só ensaio e correção.
Leiam hoje: README.md, docs/guias/00-entenda-o-sistema-e-como-trabalhar.md e o guia do seu time.
Contrato: docs/00-contrato.md (nada muda sem PR + ok dos 3 líderes).
Respondam "li e confirmo" + quem é o líder do seu time. Daily: [horário].
```
**Pronto quando:** 3 confirmações recebidas, líderes e substituto definidos.

## PO-02 — Perguntas ao cliente (D1, ~30 min)
```
Assunto: Checklist digital de guindaste — 5 confirmações para a demonstração

Olá [nome], para a demonstração do app precisamos confirmar:
1. Quais itens do checklist estão em NEGRITO no formulário original (os que impossibilitam a operação)? Pode enviar o original em boa resolução?
2. Quando um item crítico está "Não", o que acontece hoje (quem é avisado? o equipamento é travado)?
3. Podemos reescrever os itens 17 ("Sistema hidráulico apresenta vazamentos?") e 19 ("Apresenta avaria na lataria, OK?") de forma positiva ("sem vazamentos", "sem avarias")?
4. Que celulares/tablets (marca, Android) os operadores usam? Há internet nos cais?
5. O visto da liderança precisa de assinatura na tela ou basta o usuário e a data/hora do registro?
Enquanto isso seguimos com suposições que ajustamos depois. Obrigado!
```
**Pronto quando:** e-mail enviado. As respostas, quando chegarem, viram issues e entram no contrato (via PR).

## PO-03 — Checkpoint do fim do D2 (~30 min)
**Pergunta única:** *"O caso da foto sai do celular, chega ao servidor e aparece na lista do admin?"*
| Situação | Decisão |
|---|---|
| ✅ Sim | Seguir o plano |
| 🟡 Quase (falta pouco, 1 bloqueio claro) | Dar até a manhã do D3; cortar "o que mudou" e o selo/linha do tempo |
| 🔴 Não | Cortar já **Solicitar correção** e **edição**; foco em offline + impedimento + detalhe + Vistar |
Registre a decisão no contrato (§11) e avise o grupo. **Nunca cortar:** offline, impedimento, detalhe completo, Vistar.

## PO-04 — Roteiro e ensaio (D4, ~2h)
Use o roteiro de `03-guia-dados-qa.md` (DA-04). Faça **você mesmo** o papel do apresentador, ao vivo, 2 vezes seguidas com cronômetro. Anote travas em issues com gravidade. **Feature freeze no fim do D4:** depois disso só correção de bug "bloqueia a demo".

## PO-05 — Aceite final e backlog da fase 2 (D4, ~1h)
**Aceite (marque tudo):**
- [ ] Roteiro roda 2x seguidas sem falha, nos 2 aparelhos, com APK de release
- [ ] Offline funciona (modo avião) e sincroniza sem duplicar
- [ ] Item crítico gera alerta; admin vê detalhe completo; Vistar trava
- [ ] Solicitar correção + edição + selo Editado + linha do tempo
- [ ] Vídeo de plano B gravado; servidor e IP anotados
- [ ] Segredos fora do Git (`.env`)
**Backlog da fase 2 (registre como issues):** hospedagem (Azure/TI do cliente) e HTTPS · login corporativo · cadastro de usuários/equipamentos pelo app · PDF oficial · dashboard/relatórios · fotos nos itens · notificações · destaque do "o que mudou" entre revisões · itens críticos reais e textos aprovados pelo cliente · política de dados/LGPD e retenção.

---

## Kit para quem for substituir o PO (leia se você está no lugar dele)
1. **Seu trabalho:** decidir cortes (regra do PO-03), conduzir o checkpoint do D2 e destravar dúvidas de negócio em até 2 h. Quando não souber: siga a **suposição do contrato**, registre na issue "Decisões para o PO" e continue.
2. **Daily assíncrona:** no fim do dia cada pessoa posta *fiz / vou fazer / bloqueio*. Você responde os bloqueios.
3. **Só mova para Pronto** o que você **viu funcionando** (print/vídeo curto no PR).
4. **Regra "entra um, sai um":** pedido novo? Só entra se sair algo de tamanho igual.
5. **Semáforo diário** (poste no grupo): 🟢 no prazo · 🟡 risco com plano · 🔴 atrasado (decida o corte).
6. **Contrato:** mudanças só com PR + "ok" dos 3 líderes. Você aprova o merge.
