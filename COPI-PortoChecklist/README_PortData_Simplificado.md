# PortData — Backend de Checklists Portuários

Backend para digitalizar, preencher, editar, consultar e armazenar checklists de equipamentos utilizados em operações portuárias.

A primeira versão terá como referência o formulário **Check-List Diário de Guindaste**, código **FOR-OPP-0017**, versão **5**. O projeto prioriza um MVP: uma estrutura simples, com os recursos necessários para o CRUD e as validações essenciais.

> **Atenção:** antes do uso operacional, a organização deverá confirmar os campos, os itens críticos e os critérios de aprovação do formulário oficial. O sistema não substitui inspeções presenciais nem procedimentos de segurança.

## 1. Objetivos

- Criar checklists e salvar rascunhos.
- Consultar e listar registros.
- Editar checklists ainda abertas.
- Armazenar os 23 itens, suas respostas e observações.
- Validar campos e informações.
- Identificar respostas críticas e inconsistências.
- Finalizar e preservar registros.

## 2. Tecnologias

| Tecnologia | Utilização |
|---|---|
| Python 3.11+ | Linguagem principal |
| FastAPI | API REST |
| SQLAlchemy | Acesso ao banco |
| Pydantic | Validação dos dados |
| PostgreSQL | Banco de dados |
| Uvicorn | Servidor ASGI |
| Pytest | Testes automatizados |

## 3. Estrutura do projeto

```text
portdata-backend/
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── crud.py
│   ├── services.py
│   └── routers/
│       └── checklists.py
├── tests/
│   └── test_checklists.py
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## 4. Responsabilidade dos arquivos

| Arquivo | Responsabilidade |
|---|---|
| `main.py` | Inicializar FastAPI e registrar as rotas |
| `database.py` | Configurar engine, sessões e `get_db()` |
| `models.py` | Definir as tabelas e relacionamentos SQLAlchemy |
| `schemas.py` | Validar dados de entrada e saída com Pydantic |
| `crud.py` | Criar, consultar, editar e persistir registros |
| `services.py` | Aplicar regras de negócio e verificações |
| `routers/checklists.py` | Receber requisições HTTP e chamar os Services |
| `tests/test_checklists.py` | Testar criação, consulta, edição e validações |

### Detalhamento

**`database.py`**
- `create_engine()`: cria o engine de conexão.
- `sessionmaker()`: configura a fábrica de sessões.
- `DeclarativeBase`: classe-base dos modelos.
- `get_db()`: fornece e fecha a sessão usada na requisição.

**`models.py`**

Para o MVP, duas tabelas principais são suficientes:

1. `Checklist`: dados gerais, identificação do formulário, status, operador e liderança.
2. `ChecklistResposta`: checklist relacionada, número e descrição do item, resposta, observação e indicador de criticidade.

**`schemas.py`**

Classes sugeridas:
- `ChecklistCreate`
- `ChecklistUpdate`
- `ChecklistResponse`
- `RespostaCreate`
- `RespostaResponse`
- `RespostaEnum`

As respostas devem aceitar somente `SIM`, `NAO` ou `NAO_APLICAVEL`.

**`crud.py`**

Funções sugeridas:
- `create_checklist()`
- `get_checklist()`
- `get_checklists()`
- `update_checklist()`
- `delete_checklist()`
- `save_responses()`
- `get_responses()`

**`services.py`**

Funções sugeridas:
- `create_checklist_service()`
- `update_checklist_service()`
- `validate_checklist()`
- `validate_responses()`
- `validate_horimeter()`
- `verify_critical_items()`
- `finalize_checklist()`

**`routers/checklists.py`**

Expõe os endpoints, recebe os dados, utiliza os Schemas e encaminha as operações aos Services.

## 5. Dados que devem ser armazenados

### Dados gerais

O formulário de referência contém:

- Código do formulário e versão.
- Local de atuação.
- Turno de operação: 08 x 14, 14 x 20, 20 x 02 ou 02 x 08.
- Data.
- Navio.
- Guindaste.
- Horímetro inicial e final.
- Nível de combustível.
- Hora de entrada e saída.
- Observação geral.
- Nome do operador e visto/assinatura.
- Nome da liderança e visto/assinatura.

A referência do formulário é **FOR-OPP-0017, versão 5**. A data impressa no modelo é 23/10/2025; ela não deve ser confundida com a data de cada preenchimento.

### Os 23 itens de inspeção

Cada item terá resposta (`SIM`, `NAO` ou `NAO_APLICAVEL`) e observação opcional.

| Nº | Descrição |
|---:|---|
| 1 | Cinto de segurança, OK? |
| 2 | Botões de controle, funcionando? |
| 3 | Sistema de comunicação (rádio e megafone), OK? |
| 4 | Alerta sonoro - sirene, OK? |
| 5 | Buzina funciona normalmente? |
| 6 | Botões de emergência, OK? |
| 7 | Freio de emergência em condições? |
| 8 | Freios em boas condições de uso? |
| 9 | Limpador de para-brisa funcionando? |
| 10 | Inspeção visual (patolas, pneus e vazamentos), OK? |
| 11 | Painel de comando, exibe todas as informações? |
| 12 | Nível de combustível, OK? |
| 13 | Nível de água no radiador, OK? |
| 14 | Nível de óleo do motor, OK? |
| 15 | Nível de óleo da transmissão, OK? |
| 16 | Nível de óleo hidráulico, OK? |
| 17 | Sistema hidráulico apresenta vazamentos? Possui vazamento de óleo? |
| 18 | Funcionamento do grab, cabos de aço? |
| 19 | Apresenta avaria na lataria, OK? |
| 20 | Extintor de incêndio com data de validade vigente |
| 21 | Extintor pressurizado? Está em suporte adequado? |
| 22 | Pneus em boas condições? |
| 23 | Ar condicionado em condições de uso? |

O formulário informa que itens de segurança destacados em negrito impossibilitam a operação. A lista exata dos itens críticos deve ser confirmada com o documento oficial e configurada no sistema; não deve ser presumida.

## 6. Endpoints previstos

| Método | Endpoint | Finalidade |
|---|---|---|
| POST | `/api/checklists` | Criar checklist |
| GET | `/api/checklists` | Listar checklists |
| GET | `/api/checklists/{id}` | Consultar checklist e respostas |
| PUT | `/api/checklists/{id}` | Editar checklist |
| POST | `/api/checklists/{id}/verificar` | Executar validações |
| POST | `/api/checklists/{id}/finalizar` | Finalizar checklist |
| DELETE | `/api/checklists/{id}` | Excluir rascunho, conforme regra de acesso |

## 7. Regras essenciais

1. Permitir salvar rascunhos incompletos.
2. Aceitar somente as três opções de resposta previstas.
3. Impedir respostas duplicadas para o mesmo item na mesma checklist.
4. Validar que o horímetro final não seja inferior ao inicial, salvo exceção documentada.
5. Validar o combustível entre 0 e 100%.
6. Exigir os campos e respostas obrigatórios para finalizar.
7. Gerar alerta ou bloqueio quando um item crítico for reprovado, conforme regra oficial aprovada.
8. Impedir edição silenciosa de checklists finalizadas; correções devem ter procedimento de retificação.

## 8. Instalação

Crie e ative um ambiente virtual.

Windows PowerShell:

```powershell
python -m venv .venv
.venv\\Scripts\\Activate.ps1
```

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

Instale as dependências:

```bash
pip install fastapi uvicorn sqlalchemy "psycopg[binary]" pydantic pydantic-settings pytest
```

Registre as dependências:

```bash
pip freeze > requirements.txt
```

## 9. Configuração

Crie `.env` na raiz do projeto:

```env
DATABASE_URL=postgresql+psycopg://usuario:senha@localhost:5432/portdata
```

Mantenha `.env` fora do Git. Inclua um `.env.example` com valores ilustrativos e nunca publique credenciais reais.

## 10. Execução

Na raiz do projeto:

```bash
uvicorn app.main:app --reload
```

Endereços locais padrão:

- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

Execute os testes com:

```bash
pytest
```

## 11. Fluxo da aplicação

```text
Frontend
   |
   v
Router (FastAPI)
   |
   v
Schema (Pydantic)
   |
   v
Service (regras de negócio)
   |
   v
CRUD (operações no banco)
   |
   v
Models / SQLAlchemy
   |
   v
PostgreSQL
```

O Router recebe a requisição, o Schema valida os dados, o Service aplica as regras e o CRUD realiza a persistência. A gravação da checklist e de suas respostas deve usar uma transação para evitar registros incompletos por falha.

## 12. Segurança e evolução

Esta primeira versão concentra-se no CRUD e na persistência. Antes de disponibilizar dados operacionais pela internet ou compartilhar informações entre organizações, será necessário implementar autenticação, autorização por perfil/organização, HTTPS, auditoria, backups e proteção de documentos e assinaturas.

Próximas evoluções(se possíveis):
- Autenticação e perfis de acesso.
- Histórico de alterações.
- Geração de PDF.
- Compartilhamento controlado.
- Outros modelos de checklist.
- Aplicativo móvel e sincronização offline.

## 13. Prompts de desemvolvimento. 

Criei uma lista contendo os prompys de desenvolvimento para cada arquivo do backend do projeto, aqui o link:
https://docs.google.com/document/d/17uL3PfhxuUY6xpNtzIidcC3hXY3ZdumwWuYN7ar2cKw/edit?tab=t.0.

---


