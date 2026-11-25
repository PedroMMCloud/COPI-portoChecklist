# Guia 00 — Entenda o sistema e como trabalhar (TODOS leem primeiro, 15 min)

## 1. O sistema em uma página
```
 CELULAR DO OPERADOR                 SERVIDOR (notebook na demo)            CELULAR DO ADMIN
 ┌──────────────────┐                ┌───────────────────────────┐          ┌──────────────────┐
 │ App Flutter      │   internet     │ API (FastAPI)             │ internet │ App Flutter      │
 │  ├ telas         │ ─────────────▶ │  ├ login (JWT)            │ ◀─────── │  (mesmo app,     │
 │  ├ regras        │  PUT checklist │  ├ regras (validação...)  │  lista   │   outro perfil)  │
 │  └ banco local   │ ◀───────────── │  └ banco (SQLite)         │  detalhe │                  │
 │    (SQLite)      │   resposta     │      checklists, eventos  │  vistar  │                  │
 └──────────────────┘                └───────────────────────────┘          └──────────────────┘
   funciona SEM internet                  fonte da verdade
```
- **App = 1 só.** O login diz quem você é (operador ou admin) e a tela muda sozinha.
- **Banco local** = o operador nunca perde o que preencheu, mesmo sem sinal.
- **Servidor** = guarda tudo, aplica as regras de novo (nunca confie só no app) e responde ao admin.

## 2. A história de um checklist (siga com o dedo)
| # | O que acontece | Quem faz | Tarefas |
|---|---|---|---|
| 1 | João abre o app e entra com matrícula 1001 + PIN | App → API `/auth/login` | FE-02, BE-03 |
| 2 | O app baixa o template (23 itens) e as listas (cais, guindastes) e guarda no celular | App ← API `/template`, `/lookups` | FE-03, BE-04 |
| 3 | João preenche o cabeçalho. O app sugere o horímetro inicial | App (+ API `/ultimo-horimetro`) | FE-04, BE-10 |
| 4 | Toca em **Marcar tudo OK**, confirma, e muda os itens 1, 10 e 22 para "N" com observação | App (regras locais) | FE-05, FE-07 |
| 5 | O item 1 é crítico ⇒ aparece **"Equipamento impedido de operar"** | App | FE-08 |
| 6 | João informa horímetro final/saída e **assina na tela** | App | FE-09 |
| 7 | Sem internet: o checklist fica **PENDENTE_ENVIO** no celular | App (banco local) | FE-10 |
| 8 | A internet volta: o app envia `PUT /checklists/{id}`. O servidor valida, calcula impedimento e grava com status **ENVIADO** | App → API | FE-10, BE-05 |
| 9 | A admin abre a lista: impedidos em vermelho no topo. Abre o **detalhe completo** | App admin ← API | FE-11, FE-12, BE-06 |
| 10 | Ela pede correção: "Horímetro final conferir" ⇒ **CORRECAO_SOLICITADA** | App admin → API | FE-13, BE-08 |
| 11 | João vê o motivo, edita, toca "Confirmo as correções" e reenvia (selo **Editado**, revisão 2) | App → API | FE-13, BE-05, BE-09 |
| 12 | A admin vê a linha do tempo e toca **Vistar** ⇒ **VISTADO** (travado) | App admin → API | FE-12, BE-07 |

## 3. Vocabulário
**Endpoint/rota:** endereço da API (ex.: `PUT /checklists/{id}`). · **JSON:** formato de dados trocados. · **JWT/token:** "crachá" que o app mostra à API depois do login. · **Idempotente:** mandar duas vezes dá o mesmo resultado de mandar uma. · **Snapshot:** cópia da versão anterior. · **Mock:** dados falsos para trabalhar sem o servidor. · **PR (Pull Request):** pedido para juntar seu código à `main`. · **Fixture:** dado de teste fixo (`caso_foto.json`). · **Seed:** dados iniciais (usuários, itens). · **Crítico:** item que, com "N", impede a operação.

## 4. Como executar QUALQUER tarefa (ritual de 8 passos)
1. **Pegue uma issue** (só 2 "Em andamento" por pessoa) e crie a branch `feat/ID-descricao`.
2. **Leia** o critério de aceite da issue + a seção do seu guia + as regras (RN) citadas em `00-contrato.md`.
3. **Explique com suas palavras** para um colega (ou para a IA): "o que entra, o que sai, como sei que acabou?". Se não souber, pergunte antes de codar.
4. **Peça um plano à IA** (use o prompt pronto do guia) e escolha o menor primeiro passo.
5. **Faça em pedaços pequenos** e rode a cada pedaço (não escreva 200 linhas antes de rodar).
6. **Teste**: com o caso `dados/fixtures/caso_foto.json` e com **um caso ruim** (campo vazio, sem internet).
7. **Abra o PR** (modelo preenchido), peça 1 revisão e mostre funcionando (print/vídeo curto).
8. **Mova o cartão para Pronto** só depois de o PO (ou o PO substituto) ver. Anote no PR o que aprendeu/ficou pendente.

**Regra dos 30 minutos:** travado há 30 min? Poste no grupo no formato:
```
Tarefa: BE-05 | O que tentei: ... | Erro (copie o texto completo): ... | Comando/arquivo: ... | Meu sistema: Windows 11
```

## 5. Quem entrega o quê para quem (e quando)
| De → Para | O quê | Até |
|---|---|---|
| BE → FE | URL do servidor + `/docs` + usuários demo funcionando (BE-02..BE-05) | fim do D2 (até lá o FE usa mock) |
| BE → DA | `PUT` funcionando para o script `carregar_demo.py` | início do D3 |
| DA → todos | Seed conferido com o papel (DA-01) e `caso_foto.json` | D1 noite / D2 manhã |
| FE → PO | APK de teste | fim do D2 (checkpoint), fim do D3, D4 |
| Todos → PO | Roteiro da demo rodando 2x seguidas | fim do D4 |
