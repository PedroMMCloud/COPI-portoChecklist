# 06 — Prompt para visualizar a ideia no Gemini (Canvas)

> Abra o **Canvas** antes de colar. O HTML gerado é **referência visual do fluxo**, não código para reaproveitar. Se cortar no meio, peça: "continue exatamente de onde parou, só o código restante".

````
Você é um(a) Product Designer + desenvolvedor(a) sênior. Quero VISUALIZAR a dinâmica de uma DEMONSTRAÇÃO de app, a partir do resumo abaixo, para avaliar se o plano está no caminho certo. Responda em português do Brasil.

=== PROJETO ===
MVP de demonstração de um app Android que digitaliza o "Check-List Diário de Guindaste" em papel (formulário FOR-OPP-0017 v5, COPI Operações Integradas). Objetivo: demo ao vivo de 5 a 7 minutos, em DOIS aparelhos.

UM ÚNICO APP, UMA ÚNICA TELA DE LOGIN (matrícula + PIN). O PERFIL VEM DO CADASTRO DO USUÁRIO; nunca é escolhido na tela. A interface muda sozinha:
- OPERADOR: preenche o checklist no início do turno, na cabine, com luva, às vezes à noite e sem internet. Pode EDITAR o próprio checklist enquanto ele não for vistado.
- ADMINISTRADOR: em outro aparelho, confere TUDO o que o operador marcou e então "Vista" o checklist (confirma que recebeu e revisou) ou "Solicita correção" (com motivo). O administrador NÃO edita checklists e NÃO "reprova" ninguém: o checklist é a métrica, não o culpado.
Atalhos de demonstração, claramente rotulados "Atalho de demonstração": "João Silva (Operador)" = matrícula 1001 / PIN 1234; "Administrador" = matrícula 9001 / PIN 0000. PIN errado mostra erro claro.

ESTADOS: Rascunho (só no app) -> Pendente de envio (no app, sem internet) -> Enviado (na base central) -> Vistado (final, trava tudo). Desvio: Enviado -> Correção solicitada (motivo) -> operador edita e reenvia -> Enviado (revisão 2). "Impedido" é um alerta paralelo, não um estado.
A base central é a fonte da verdade; o app guarda cópia local para trabalhar offline. O administrador só vê o que já foi sincronizado.

CORREÇÃO E EDIÇÃO:
- "Solicitar correção" serve APENAS para erro ou omissão de preenchimento (ex.: horímetro digitado errado, item esquecido). Nunca é reprovação do equipamento.
- O operador pode editar TODOS os campos (inclusive identificação) enquanto o checklist não estiver Vistado. A transparência vem do HISTÓRICO, não de travas.
- Ao reenviar após correção: um toque em "Confirmo as correções" (sem nova assinatura). O checklist ganha o selo "Editado" e a revisão aumenta.
- Cada ação gera um evento na LINHA DO TEMPO (Criado, Enviado, Editado, Correção solicitada com motivo, Reenviado, Vistado, cada um com quem e quando). A revisão anterior é guardada. OPCIONAL: mostrar "campo: antes -> depois" nos eventos de edição.
- Vistado é final: não edita e não aceita nova solicitação de correção.

CAMPOS DO CABEÇALHO: local (ex.: Cais 99), turno (08x14, 14x20, 20x02, 02x08), data, equipamento (guindaste), navio (opcional), horímetro inicial e final (1 casa decimal), nível de combustível (0-100%), hora de entrada e saída.
23 ITENS com S / N / N/A + observação por item. Todos redigidos de forma POSITIVA: "S" = tudo bem; "N" = problema.
1 Cinto de segurança, OK? | 2 Botões de controle, funcionando? | 3 Sistema de comunicação (rádio e megafone), OK? | 4 Alerta sonoro - sirene, OK? | 5 Buzina funciona normalmente? | 6 Botões de emergência, OK? | 7 Freio de emergência em condições? | 8 Freios em boas condições de uso? | 9 Limpador de para-brisa funcionando? | 10 Inspeção visual (patolas, pneus e vazamentos), OK? | 11 Painel de comando exibe todas as informações? | 12 Nível de combustível, OK? | 13 Nível de água no radiador, OK? | 14 Nível de óleo do motor, OK? | 15 Nível de óleo da transmissão, OK? | 16 Nível de óleo hidráulico, OK? | 17 Sistema hidráulico SEM vazamentos de óleo? | 18 Funcionamento do grab, cabos de aço? | 19 Lataria SEM avarias? | 20 Extintor de incêndio com data de validade vigente? | 21 Extintor pressurizado? Está em suporte adequado? | 22 Pneus em boas condições? | 23 Ar condicionado em condições de uso?
Rodapé: observação geral e assinatura do operador (na tela).

BOTÃO "MARCAR TUDO OK" (lote): o checklist é diário e marcar 23 itens cansa; o operador marca tudo OK e altera só o que não está OK. É um registro de SEGURANÇA, então há salvaguardas:
- Botão visível no topo da tela de itens, somente enquanto houver itens sem resposta.
- Confirmação curta: "Confirmo que inspecionei o equipamento e que todos os itens abaixo estão OK, exceto os que eu alterar." Botões: Confirmar / Cancelar.
- Marca SOMENTE itens ainda sem resposta, SOMENTE como "S"; nunca N/A; nunca sobrescreve respostas já dadas.
- Itens marcados em lote exibem selo discreto "lote"; ao tocar/alterar, o selo some e o item passa a "manual".
- Na finalização, o resumo mostra: "X em lote · Y manuais · Z com problema".
- Fica registrado: se usou lote, quantos itens vieram do lote, quantos foram alterados depois, e o tempo total de preenchimento.
- Controle SOMENTE do protótipo (barra no topo da página): interruptor "Lote inclui itens críticos" (padrão: ligado).

REGRAS:
- Enviar exige os 23 itens respondidos; "N" exige observação.
- Itens CRÍTICOS com "N" => tela "Equipamento impedido de operar" ao operador e destaque vermelho ao administrador. Críticos EXEMPLO (provisório, a validar com o cliente): 1, 4, 6, 7, 8, 10, 16, 17, 18, 20, 21, 22. Rotule na barra do protótipo: "Itens críticos: exemplo de configuração".
- Horímetro final >= inicial; o app sugere o inicial com o último final do equipamento.
- Turno 20x02 cruza a meia-noite (saída 02:00 < entrada 20:00 é válido).
- Operador vê só os seus checklists; administrador vê todos.
- Offline-first: o operador preenche e finaliza sem internet; ao reconectar sincroniza sem duplicar.
- Cadastros (usuários 1001 João Silva, 1002 Maria Souza, 9001 Administrador; equipamentos GUINDASTE-280/281/282; locais Cais 99 e Cais 100) vêm de seed.

TELAS
OPERADOR: Login; Home (Novo checklist, rascunho, meus checklists com status e selos Editado/Correção solicitada, indicador de conexão); Cabeçalho; Itens 1-23 (progresso x/23, Marcar tudo OK); Alerta de impedimento; Finalização (horímetro final, hora de saída, observação geral, resumo lote/manual/problemas, assinatura); Confirmação; Edição (quando houver correção solicitada: motivo em destaque no topo + "Confirmo as correções").
ADMINISTRADOR:
- Lista: contadores no topo (Pendentes de visto | Impedidos | Correção solicitada | Vistados hoje); filtro por status; impedidos em vermelho no topo; cada linha com operador, equipamento, cais, turno, data e selos IMPEDIDO / lote / Editado; atualização por botão e automática a cada 15 s com contador visível "atualiza em Xs".
- DETALHE COMPLETO (regra: o administrador NUNCA vista sem ver tudo). Ordem: (1) faixa "20 OK · 3 com problema · 1 crítico" e selo IMPEDIDO; (2) cabeçalho completo; (3) itens COM PROBLEMA no topo, em destaque, com a observação; (4) TODOS os itens OK logo abaixo, completos, em seção já aberta, cada um com selo lote/manual; (5) observação geral; (6) assinatura do operador; (7) metadados: início e fim do preenchimento, sincronização, tempo total (mostrar como alerta discreto se for muito curto, p.ex. "preenchido em menos de 1 min", sem tom de vigilância), se usou lote e quantos itens; (8) LINHA DO TEMPO de eventos; (9) rodapé fixo com VISTAR e SOLICITAR CORREÇÃO (este abre campo de motivo obrigatório). Após Vistar, os botões somem e aparece "Vistado por [nome] em [data/hora] — registro travado".

FORA DE ESCOPO: dashboard, relatórios, PDF, iOS, integrações, notificações, fotos, cadastro pelo app. A hospedagem é implícita e não aparece no protótipo.

CASO DE TESTE: operador João Silva, Cais 99, 20x02, 03/11/2026, entrada 20:00, saída 02:00, combustível 95%, horímetro inicial 36466.1 e final 36470.8; itens "N": 1 (obs "Não tem"), 10 (obs "Patola 1 e 3 com vazamento"), 22 (obs "Calibrar pneus"); demais "S"; observação geral "Lança do guindaste está cortando". O botão "Preencher com o caso de teste" deve reproduzir o fluxo realista: lote + alteração manual dos itens 1, 10 e 22.

=== O QUE EU QUERO (nesta ordem) ===
1) RESUMO EXECUTIVO (máx. 8 linhas).
2) FLUXOS EM MERMAID (blocos separados): (a) operador, do login ao envio, com "Marcar tudo OK"; (b) sincronização offline com falha e reenvio; (c) administrador, da lista ao Vistar, com Solicitar correção e o retorno do operador (edição e reenvio); (d) diagrama de estados do checklist.
3) PROTÓTIPO: UM ÚNICO arquivo HTML autocontido (HTML + CSS + JS puro, sem bibliotecas externas, sem localStorage), com DOIS CELULARES LADO A LADO (~390px, moldura simples): à esquerda o OPERADOR, à direita o ADMINISTRADOR, compartilhando uma "BASE CENTRAL" simulada em memória, exibida em um painel pequeno com a lista de checklists, status e revisão em tempo real. Em telas estreitas, os celulares se empilham.
   Requisitos: login único com atalhos rotulados (perfil definido pelo cadastro, sem seletor de perfil); navegação real em todas as telas; botões S/N/N-A grandes com cor E texto/ícone; barra de progresso x/23; observação obrigatória no "N"; tela de impedimento; "Marcar tudo OK" com confirmação, selos e resumo; interruptor "Sem internet (simular)" SÓ no celular do operador (ligado => "Pendente de envio"; desligado => sincroniza com pequeno atraso e indicador); lista do admin com atualização a cada 15 s e botão; detalhe completo; Vistar; Solicitar correção com motivo; operador vê o motivo, edita, toca "Confirmo as correções" e o selo "Editado" aparece; linha do tempo; assinatura em canvas com "limpar"; botões "Preencher com o caso de teste" e "Reiniciar demo" fora das molduras; validações visíveis (horímetro, itens sem resposta, assinatura vazia, PIN inválido); textos em português, alto contraste, alvos de toque >= 56px.
   Entregue o código completo em UM bloco, pronto para o Canvas.
4) ROTEIRO DA DEMO: 8 a 10 passos com o que o apresentador clica em cada celular e o valor percebido (inclua lote, modo sem internet, conferência completa, solicitar correção, edição e vistar).
5) LACUNAS E RISCOS: (a) ambiguidades do resumo; (b) riscos de usabilidade em campo (inclua o risco de usar o lote sem inspecionar e o de o histórico de edições ser lido como punição); (c) riscos técnicos da demo ao vivo; (d) até 5 perguntas ao cliente. Aponte contradições, se houver.

Regras: não invente funcionalidades fora do escopo; liste suas suposições no fim. Seja direto.
````
