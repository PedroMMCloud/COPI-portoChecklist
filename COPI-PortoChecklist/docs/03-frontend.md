# 03 — PRD Front-end (Android/Flutter)

**Dono de:** app, UX, banco local, sincronização. **Leia antes:** `00-contrato.md` e `app/README.md`.

## UX de campo
Botões grandes (≥ 56 dp), S/N/N-A com **cor + texto/ícone**, alto contraste, teclado numérico no horímetro (máscara `00000.0`), salvar rascunho a cada toque, indicador permanente de conexão/pendências, mensagens em português simples.

## Telas
**Comum:** Login único (atalhos de demo rotulados "Atalho de demonstração") · Configurações (URL do servidor, sincronizar agora, sair).
**Operador:** Home (novo, rascunho, meus checklists com status) · Cabeçalho · Itens 1–23 (progresso x/23, **Marcar tudo OK**) · Alerta de impedimento · Finalização (resumo "X lote · Y manual · Z problemas", assinatura) · Confirmação · **Editar** (motivo da correção em destaque, selo Editado, "Confirmo as correções").
**Admin:** Lista (contadores, impedidos no topo, filtro de status, atualização 15 s + botão) · **Detalhe completo** (faixa "20 OK · 3 com problema · 1 crítico"; cabeçalho; **problemas no topo**; todos os itens OK abaixo com selo lote/manual; observação geral; assinatura; metadados e tempo de preenchimento; linha do tempo; rodapé com **Vistar** e **Solicitar correção**).

## Regras no app (as mesmas do servidor)
RN01–RN06, **RN12 (lote)**, RN14. Lote: confirmação ("Confirmo que inspecionei o equipamento e que todos os itens abaixo estão OK, exceto os que eu alterar"), só itens sem resposta, só "S", selo "lote" some ao tocar. O tempo de preenchimento é mostrado ao admin como **alerta discreto**, não como métrica de desempenho.

## Tarefas (aceite em `tarefas.psv`)
FE-01 projeto+config+mock · FE-02 login/roteamento por perfil · FE-03 banco local · FE-04 cabeçalho · FE-05 itens · FE-06 envio online (**checkpoint D2**) · FE-07 lote · FE-08 impedimento · FE-09 finalização+assinatura · FE-10 fila offline · FE-11 lista admin · FE-12 detalhe+Vistar · FE-13 correção/edição/linha do tempo · FE-14 APK **de release** em 2 aparelhos (permissão INTERNET e HTTP da demo; testar já no D3).

## Testes manuais
Fixture completo (lote + itens 1, 10, 22). Modo avião ponta a ponta ⇒ 1 só registro no servidor. Matar o app no item 12 e reabrir. Duplo toque em Enviar ⇒ 1 envio. Operador não acessa telas do admin. Editar após "correção solicitada" ⇒ selo Editado. Após Vistar ⇒ não edita.
