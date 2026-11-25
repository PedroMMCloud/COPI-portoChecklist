# Guia 03 — Dados/QA passo a passo (DA-01 a DA-06)

> Seu time é a **garantia de que a demo funciona e de que os dados são verdadeiros**. Você não precisa programar muito: precisa ser **detalhista**, anotar tudo e testar como um operador cansado.

## DA-01 — Conferir os 23 itens com o papel original (D1 noite, ~1h)
**Material:** a foto do checklist (idealmente o PDF/papel original em alta resolução) e `dados/seed/checklist_template_for_opp_0017_v5.json`.
**Passos:**
1. Abra o JSON e a foto lado a lado. Para **cada item de 1 a 23**, preencha a tabela abaixo (copie para uma issue ou planilha).
2. Confira: número, texto (acentos, pontuação), ordem.
3. Itens **17 e 19** foram **reescritos** de propósito (no papel: "Sistema hidráulico apresenta vazamentos?" e "Apresenta avaria na lataria, OK?"). Marque como "reescrito — a validar com o cliente".
4. Na foto os itens **em negrito** são os críticos. Se conseguir enxergar, anote os números; se não, deixe "a confirmar" (o seed usa uma lista **de exemplo**).
5. Confira também: título, código (FOR-OPP-0017), versão (5), data (23/10/2025), turnos (08x14, 14x20, 20x02, 02x08), campos do cabeçalho.
```
| Nº | Texto no papel | Texto no seed | Igual? | Negrito (crítico)? | Observação |
```
**Pronto quando:** a tabela está completa e as divergências viraram uma lista enviada ao PO (a correção é feita no JSON, por PR).

## DA-02 — Dados de demonstração (D2, ~3h)
**Objetivo:** ter o sistema "vivo" na hora da demo: 3 checklists já na base (sem problemas, com crítico, editado).
1. Espere o BE-05 (PUT) estar pronto. Suba o servidor e rode o seed (`python -m scripts.seed`, dentro de `backend/`).
2. Na raiz do repositório: `python dados/scripts/carregar_demo.py http://localhost:8000/api/v1`
3. Esperado no terminal: 4 linhas `ok` (sem_problema, caso_foto, editado x2). Rodar de novo **não duplica**.
4. Abra o `/docs` do servidor (como admin) e confira em `GET /checklists`: 3 registros; o do caso da foto com `impedido: true`; o "editado" com `revisao: 2`.
5. Se falhar: copie o erro completo para a issue; costuma ser nome de equipamento/local diferente do seed ou formato do `/lookups`/`/template` diferente do contrato.
**Pronto quando:** os 3 checklists aparecem para o admin e estão documentados no roteiro.

## DA-03 — Fixtures e variações (D2, ~2h)
O arquivo `dados/fixtures/caso_foto.json` é o **caso de referência**. Crie (em `dados/fixtures/`) variações pequenas para testar regras — cada uma é uma cópia do caso com **um** defeito proposital:
| Arquivo | Defeito | Resultado esperado |
|---|---|---|
| `erro_item_faltando.json` | só 22 respostas | 400 (RN01) |
| `erro_n_sem_observacao.json` | item 1 "N" sem observação | 400 (RN02) |
| `erro_horimetro.json` | final < inicial | 400 (RN03) |
| `erro_sem_assinatura.json` | assinatura vazia | 400 (RN17) |
| `ok_sem_problemas.json` | tudo "S" | 200, `impedido:false` |
| `ok_nao_critico.json` | "N" só no item 5 (não crítico) | 200, `impedido:false` |
Informe BE e FE para usarem nos testes deles.

## DA-04 — Roteiro da demo (D2 rascunho, D4 final, ~3h)
**Preparação (antes de começar):** 2 celulares carregados, APK instalado, servidor rodando, `carregar_demo.py` executado, modo avião desligado, Wi-Fi do hotspot conectado, brilho alto, notificações desligadas.

| # | Quem | Ação | O que o cliente deve perceber | Esperado na tela |
|---|---|---|---|---|
| 1 | Celular A | Entrar como João (atalho de demo) | "É o mesmo app, entra com matrícula" | Home do operador |
| 2 | A | Novo checklist: Cais 99, guindaste 280, turno 20x02, horímetro sugerido, combustível 95% | "O horímetro já vem sugerido" | Cabeçalho válido |
| 3 | A | **Marcar tudo OK** (confirmar) | "Não preciso tocar 23 vezes" | 23 itens com selo "lote" |
| 4 | A | Itens 1, 10 e 22 ⇒ N com observação | "Só altero o que está errado" | Alerta **Equipamento impedido** |
| 5 | A | **Modo avião**. Finalizar, assinar, enviar | "Funciona sem internet" | Status "Pendente de envio" |
| 6 | A | Desligar modo avião | "Sincroniza sozinho, sem duplicar" | Status "Enviado" |
| 7 | Celular B | Entrar como Administrador | "Outro aparelho, outra visão" | Lista com contadores |
| 8 | B | Abrir o checklist impedido: **detalhe completo** | "Vejo tudo que o operador marcou antes de vistar" | 3 problemas no topo, 20 OK abaixo, assinatura |
| 9 | B | **Solicitar correção**: "Conferir horímetro final" | "Peço correção sem culpar ninguém" | Status "Correção solicitada" |
| 10 | A | Ver motivo, editar horímetro, **Confirmo as correções** | "Corrijo e fica tudo registrado" | Selo **Editado** |
| 11 | B | Ver linha do tempo e **Vistar** | "Tem histórico e ao vistar trava" | "Vistado por ... — travado" |
**Tempo-alvo:** 5–7 min. **Falas:** 1 frase por passo (o benefício, não a tecnologia).

## DA-05 — Teste em 2 aparelhos e bugs (D3 e D4, ~4h por rodada)
**Como testar:** siga o roteiro **e** os casos abaixo; anote **tudo** que estranhar.
| Grupo | Caso | Esperado |
|---|---|---|
| Login | PIN errado | Mensagem clara, não entra |
| Login | Fechar e reabrir o app sem internet | Continua logado |
| Itens | N sem observação | Bloqueia o envio |
| Itens | Marcar tudo OK com algum item já respondido | Não sobrescreve |
| Itens | Tocar num item do lote | Selo "lote" some |
| Crítico | N no item 1 | Alerta de impedimento |
| Offline | Modo avião do início ao fim | Salva; envia ao voltar; **1 registro** |
| Offline | Tocar Enviar 2x | 1 registro |
| Offline | Matar o app no item 12 e reabrir | Continua no item 12 |
| Validação | Horímetro final < inicial | Erro claro |
| Validação | Turno 20x02, saída 02:00 | Aceita |
| Admin | Lista atualiza em ≤ 15 s | Sim |
| Admin | Detalhe mostra 23 itens, assinatura, metadados, linha do tempo | Sim |
| Admin | Vistar 2x | Segunda vez impedida |
| Operador | Editar após vistado | Impossível |
| Operador | Ver checklist de outro operador | Impossível |
| Rede | Servidor desligado durante o envio | Fica pendente; app não trava |
| Aparelho | Girar tela / fonte grande | Nada quebra |
**Modelo de bug (issue):**
```
Título: [FE-10] Enviar 2x duplica registro
Passos: 1... 2... 3...
Esperado: ... | Aconteceu: ... | Aparelho/Android: ... | Versão do APK: ... | Evidência: print/vídeo
Gravidade: Bloqueia a demo / Atrapalha / Cosmético
```
**Pronto quando:** não há bug "bloqueia a demo" aberto e o roteiro passa 2x seguidas.

## DA-06 — Ensaio e vídeo de plano B (D4, ~3h)
1. **Ensaio com cronômetro:** faça o roteiro completo 2 vezes seguidas. Anote o tempo e onde travou/hesitou. Objetivo: 5–7 min.
2. **Reset entre ensaios:** apague `backend/checklist.db`, rode o seed e `carregar_demo.py` (ou use um comando "reiniciar demo" que o BE preparar).
3. **Vídeo de plano B:** grave a tela dos 2 celulares (gravador de tela do Android) fazendo o roteiro inteiro, **sem cortes**. Salve em dois lugares (notebook + nuvem).
4. **Lista de verificação do dia** (imprima): carregadores · APK instalado · servidor no notebook com bateria/ligado na tomada · IP anotado · hotspot testado · vídeo aberto no notebook · dados de demo carregados.
5. **Se algo falhar ao vivo:** respire, diga "vou mostrar a gravação deste trecho", continue. Nunca debug ao vivo na frente do cliente.
**Pronto quando:** vídeo gravado e checklist do dia marcado.
