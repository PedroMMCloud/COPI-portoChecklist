# 00 — Contrato (fonte única da verdade) · v0.2

> Congelado no fim do D1. Mudanças só via PR neste arquivo, aprovadas pelo PO.

## 1. Visão
Um app, **uma tela de login** (matrícula + PIN). O **perfil vem do cadastro** (`OPERADOR` ou `ADMIN`), nunca é escolhido na tela; a interface muda sozinha. Atalhos "Entrar como..." existem **só na demo**.
- **Operador:** preenche (inclusive offline), edita enquanto não for vistado, vê só os seus.
- **Administrador:** vê tudo, **confere o conteúdo completo**, **Vistar** (confirma que recebeu e revisou) ou **Solicitar correção** (motivo obrigatório). Não edita checklists.
- Infraestrutura: **implícita**. A API roda direto com Python (Docker é opcional, para deploy/portabilidade) e o app lê a URL do servidor de configuração; a TI do cliente decide a hospedagem (ex.: Azure) depois.

## 2. Filosofia
O checklist é a **métrica**, não o culpado. "Solicitar correção" serve **só para erro ou omissão de preenchimento**; equipamento com defeito é tratado pelo **alerta de impedimento** e pelas observações. O administrador *autentica* o registro, não "reprova" ninguém.

## 3. Estados
```
RASCUNHO (só no app) → PENDENTE_ENVIO (no app, sem internet) → ENVIADO → VISTADO (final)
                                                                ↓  ↑
                                                       CORRECAO_SOLICITADA (operador edita e reenvia → ENVIADO)
```
- O **operador pode editar** enquanto não for `VISTADO` (selo **"Editado"**).
- **Todos os campos** são editáveis; a transparência vem do **log** (campo, antes → depois).
- `VISTADO` trava definitivamente (a API responde **409** a qualquer alteração).
- `impedido` é um alerta paralelo ao estado.

## 4. Regras de negócio
| ID | Regra |
|---|---|
| RN01 | Para enviar, os **23 itens** estão respondidos (S, N ou N/A). |
| RN02 | Resposta **N** exige observação. |
| RN03 | `horimetro_final >= horimetro_inicial` (1 casa decimal). O app sugere o inicial = último final do equipamento. |
| RN04 | `combustivel_pct` entre 0 e 100. |
| RN05 | Item **crítico** com N ⇒ `impedido = true` ⇒ tela "Equipamento impedido de operar" no app + destaque para o admin. **Lista de críticos provisória** (exemplo), a validar com o cliente. |
| RN06 | Turno `T_20_02` com `hora_saida < hora_entrada` é válido (cruza a meia-noite). |
| RN07 | Toda edição gera **evento** no histórico e guarda **snapshot (JSON) da revisão anterior**; `revisao` +1; `editado = true`. |
| RN08 | `VISTADO` é final: sem edição, sem nova solicitação de correção. |
| RN09 | **Solicitar correção:** só `ADMIN`, só em `ENVIADO`, **motivo obrigatório**. |
| RN10 | **Vistar:** só `ADMIN`, só em `ENVIADO`. Registra usuário e data/hora. |
| RN11 | Envio e edição são **idempotentes** pelo `id` (UUID gerado no app): `PUT /checklists/{id}`. |
| RN12 | **Marcar tudo OK (lote):** marca **somente itens ainda sem resposta**, **somente como S**, nunca N/A. Item vem com `origem=LOTE`; ao ser tocado/alterado vira `MANUAL`. |
| RN13 | Operador vê **só os seus**; admin vê todos. |
| RN14 | Reenvio após correção: toque **"Confirmo as correções"** (registrado no log). **Sem nova assinatura.** |
| RN15 | Itens **17 e 19** reescritos de forma positiva (no papel eram invertido/ambíguo) — **a validar com o cliente**. |
| RN16 | O admin só decide depois de ver o **detalhe completo** (todos os 23 itens, observações, assinatura, metadados e linha do tempo). |

## 5. Dados (tabelas — SQLite na demo, compatível com PostgreSQL)
| Tabela | Colunas principais |
|---|---|
| `usuarios` | id, matricula (único), nome, papel, pin_hash, ativo |
| `locais` | id, nome, ativo |
| `equipamentos` | id, identificacao (único), ativo |
| `checklist_templates` | id, codigo, versao, data_versao, titulo, ativo |
| `checklist_template_itens` | id, template_id, numero, descricao, critico, permite_na |
| `checklists` | id (UUID do app), template_id, operador_id, equipamento_id, local_id, data_turno, turno, navio, horimetro_inicial, horimetro_final, combustivel_pct, hora_entrada, hora_saida, observacao_geral, assinatura_operador (PNG base64), status, impedido, revisao, editado, usou_lote, itens_marcados_lote, itens_alterados_apos_lote, inicio_preenchimento_em, finalizado_em, duracao_segundos, vistado_por, vistado_em, criado_no_dispositivo_em, recebido_em, app_versao |
| `checklist_respostas` | checklist_id, item_numero, resposta (S/N/NA), origem (LOTE/MANUAL), observacao |
| `checklist_eventos` | id, checklist_id, tipo (CRIADO, EDITADO, REENVIADO, CORRECAO_SOLICITADA, VISTADO), usuario_id, detalhe (JSON: motivo, diff), criado_em |
| `checklist_revisoes` | id, checklist_id, revisao, snapshot (JSON), criado_em |

Turnos: `T_08_14`, `T_14_20`, `T_20_02`, `T_02_08`. Datas em UTC (ISO 8601); exibir em `America/Fortaleza`.

## 6. API v0.1 (`/api/v1`, JSON, `Authorization: Bearer <jwt>`)
| Método | Rota | Quem | Descrição |
|---|---|---|---|
| POST | `/auth/login` | todos | `{matricula, pin}` → `{access_token, usuario:{id,nome,papel}}` |
| GET | `/template` | app | template ativo + 23 itens |
| GET | `/lookups` | app | locais, equipamentos, turnos (para uso offline) |
| GET | `/equipamentos/{id}/ultimo-horimetro` | operador | sugestão do horímetro inicial |
| **PUT** | `/checklists/{id}` | operador (dono) | **cria ou edita** (idempotente). 409 se `VISTADO` |
| GET | `/checklists` | todos* | filtros: `status, equipamento_id, local_id, impedido, de, ate` + contadores |
| GET | `/checklists/{id}` | todos* | detalhe completo com respostas e eventos |
| POST | `/checklists/{id}/vistar` | admin | → `VISTADO` |
| POST | `/checklists/{id}/solicitar-correcao` | admin | `{motivo}` → `CORRECAO_SOLICITADA` |
| GET | `/health` | público | `{status:"ok"}` (URL completa: `/api/v1/health`) |
*RN13.

**Códigos:** 200/201 ok · 400 validação · 401 sem login · 403 sem permissão · 404 · 409 conflito (ex.: já vistado).
**Erro padrão:** `{"erro":{"codigo":"VALIDACAO","mensagem":"...","campos":[{"campo":"horimetro_final","regra":"RN03"}]}}`

**Corpo do `PUT`** (o app envia sempre o checklist completo):
```json
{
  "template_id": "<id vindo de GET /template>", "equipamento_id": "<id de /lookups>", "local_id": "<id de /lookups>",
  "data_turno": "2026-11-03", "turno": "T_20_02", "navio": null,
  "horimetro_inicial": 36466.1, "horimetro_final": 36470.8, "combustivel_pct": 95,
  "hora_entrada": "20:00", "hora_saida": "02:00", "observacao_geral": "...",
  "assinatura_operador": "<png base64>",
  "usou_lote": true, "itens_marcados_lote": 23, "itens_alterados_apos_lote": 3,
  "inicio_preenchimento_em": "...Z", "finalizado_em": "...Z", "duracao_segundos": 90,
  "confirmacao_correcao": false,
  "criado_no_dispositivo_em": "...Z", "app_versao": "0.1.0",
  "respostas": [{"item_numero": 1, "resposta": "N", "origem": "MANUAL", "observacao": "Não tem"}]
}
```
O `id` vai na URL. **O servidor define o `status`** (nunca vem do app) e usa o operador do token. `confirmacao_correcao=true` só no reenvio após correção solicitada (RN14).
O fixture `dados/fixtures/caso_foto.json` traz **nomes** (matrícula, equipamento, local) para leitura humana; nos testes, converta para os IDs do seed.

## 7. Sincronização
1. O app grava **primeiro no aparelho**. 2. Com internet, envia `PUT /checklists/{id}` em ordem de criação. 3. 200/201 ⇒ sincronizado; 400 ⇒ mostra motivo; 5xx/timeout ⇒ tenta de novo (30 s, 2 min, 10 min…). 4. Reenviar é seguro (RN11). 5. Template e lookups são baixados no login e a cada abertura com internet. 6. O admin só vê o que já foi sincronizado; lista atualiza a cada **15 s** + botão "Atualizar".

## 8. Os 23 itens
Ver `dados/seed/checklist_template_for_opp_0017_v5.json` (**conferir item a item com o papel original — DA-01**). Itens 17 e 19 reescritos; coluna `critico` é **provisória**.

## 9. Dados de teste
`dados/fixtures/caso_foto.json` = caso da foto (Cais 99, 20x02, itens 1, 10 e 22 com "N" ⇒ `impedido=true`). Usuários demo em `dados/seed/demo_usuarios_locais_equipamentos.json` (1001/1234 operador, 9001/0000 admin).

## 10. Perguntas abertas (não bloqueiam a demo)
1. Quais itens são críticos (negrito no papel)? 2. Podemos reescrever os itens 17 e 19? 3. O lote pode incluir itens críticos? 4. Quais aparelhos (Android) e há internet nos cais? 5. O visto da liderança precisa de assinatura na tela ou basta usuário + hora?

## 11. Histórico de mudanças
| Data | Versão | Mudança |
|---|---|---|
| 16/11 | 0.2 | Fluxo de edição pelo operador, solicitar correção, vistar, lote, log |
