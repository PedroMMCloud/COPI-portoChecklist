# PortData --- Backend de Checklists Portuários

> Backend para criação, preenchimento, edição, validação, armazenamento,
> consulta e compartilhamento de checklists operacionais portuários.

## 1. Sobre o projeto

O **PortData** é uma proposta de sistema para digitalizar checklists
utilizados em operações portuárias. A primeira versão tem como
referência o documento **Check-List Diário de Guindaste**, código
**FOR-OPP-0017**, versão **5**.

O objetivo é substituir o preenchimento exclusivamente em papel por um
fluxo digital, mantendo os campos do documento de referência e
permitindo:

-   Criar checklists e salvar preenchimentos parciais.
-   Consultar checklists existentes.
-   Editar registros enquanto estiverem em situação que permita
    alterações.
-   Registrar as respostas dos 23 itens de inspeção.
-   Armazenar observações individuais e observações gerais.
-   Registrar operador, liderança e assinaturas.
-   Validar informações e identificar respostas críticas.
-   Finalizar e preservar registros.
-   Consultar o histórico de alterações.
-   Gerar relatórios e documentos PDF.
-   Compartilhar informações somente com usuários autorizados.

**Importante:** este projeto é uma proposta técnica. Antes de ser
utilizado em operações reais, os campos, as opções, os itens críticos,
os critérios de bloqueio e os procedimentos de aprovação devem ser
validados pela organização responsável e pelos profissionais de
segurança e operação. O sistema não substitui inspeções presenciais nem
procedimentos operacionais oficiais.

## 2. Escopo inicial: checklist FOR-OPP-0017

### 2.1 Identificação do formulário

  Campo                     Informação
  ------------------------- --------------------------------
  Título                    Check-List Diário de Guindaste
  Código                    FOR-OPP-0017
  Versão de referência      5
  Data indicada no modelo   23/10/2025

A versão e a data acima identificam o documento de referência, não a
data de cada preenchimento.

### 2.2 Dados gerais do preenchimento

O backend deverá armazenar:

-   Local de atuação.
-   Turno de operação.
-   Data da inspeção.
-   Navio.
-   Guindaste.
-   Horímetro inicial.
-   Horímetro final.
-   Nível de combustível.
-   Hora de entrada.
-   Hora de saída.
-   Observação geral.
-   Nome e identificação do operador.
-   Nome e identificação da liderança.
-   Vistos ou assinaturas correspondentes.

Os horários devem ser armazenados em formato apropriado (`TIME`) e as
datas em `DATE`. Os horímetros e percentuais devem utilizar tipos
numéricos com precisão definida, evitando cálculos com ponto flutuante
inadequado.

### 2.3 Itens de inspeção

Cada item terá uma resposta (`SIM`, `NAO` ou `NAO_APLICAVEL`) e uma
observação opcional.

  -----------------------------------------------------------------------
                                        Nº Item
  ---------------------------------------- ------------------------------
                                         1 Cinto de segurança, OK?

                                         2 Botões de controle,
                                           funcionando?

                                         3 Sistema de comunicação (rádio
                                           e megafone), OK?

                                         4 Alerta sonoro - sirene, OK?

                                         5 Buzina funciona normalmente?

                                         6 Botões de emergência, OK?

                                         7 Freio de emergência em
                                           condições?

                                         8 Freios em boas condições de
                                           uso?

                                         9 Limpador de para-brisa
                                           funcionando?

                                        10 Inspeção visual (patolas,
                                           pneus e vazamentos), OK?

                                        11 Painel de comando, exibe todas
                                           as informações?

                                        12 Nível de combustível, OK?

                                        13 Nível de água no radiador, OK?

                                        14 Nível de óleo do motor, OK?

                                        15 Nível de óleo da transmissão,
                                           OK?

                                        16 Nível de óleo hidráulico, OK?

                                        17 Sistema hidráulico apresenta
                                           vazamentos? Possui vazamento
                                           de óleo?

                                        18 Funcionamento do grab, cabos
                                           de aço?

                                        19 Apresenta avaria na lataria,
                                           OK?

                                        20 Extintor de incêndio com data
                                           de validade vigente

                                        21 Extintor pressurizado? Está em
                                           suporte adequado?

                                        22 Pneus em boas condições?

                                        23 Ar condicionado em condições
                                           de uso?
  -----------------------------------------------------------------------

O formulário de referência informa que determinados itens de segurança,
destacados em negrito, impossibilitam a operação do equipamento. A
relação exata desses itens deve ser confirmada no documento oficial. No
sistema, essa regra será representada por um atributo configurável, como
`critico`, no cadastro do item.

## 3. Tecnologias previstas

  Tecnologia       Uso
  ---------------- -----------------------------------------------------------
  Python 3         Linguagem principal
  FastAPI          Construção da API REST
  Pydantic         Validação de entrada e saída
  SQLAlchemy 2.x   Mapeamento objeto-relacional e acesso ao banco
  PostgreSQL       Banco de dados relacional
  Alembic          Migrações e versionamento do schema
  PyJWT            Autenticação baseada em tokens JWT
  pwdlib           Hash e verificação de senhas
  ReportLab        Geração de documentos PDF
  Pytest           Testes automatizados
  HTTPX            Cliente HTTP para testes e integrações, quando necessário

### Instalação inicial das dependências

Crie e ative um ambiente virtual:

``` bash
python -m venv .venv
```

Windows PowerShell:

``` powershell
.venv\Scripts\Activate.ps1
```

Linux/macOS:

``` bash
source .venv/bin/activate
```

Instale as dependências:

``` bash
pip install fastapi uvicorn sqlalchemy "psycopg[binary]" pydantic pydantic-settings alembic httpx pytest pyjwt "pwdlib[argon2]" reportlab python-multipart
```

Quando o projeto estiver configurado, registre as versões utilizadas em
`requirements.txt`:

``` bash
pip freeze > requirements.txt
```

## 4. Arquitetura do backend

A aplicação será organizada em camadas. Cada camada terá uma
responsabilidade específica:

-   **Routers:** recebem requisições HTTP e encaminham as operações.
-   **Schemas:** validam os dados recebidos e definem as respostas da
    API.
-   **Services:** implementam regras de negócio e coordenam operações.
-   **Repositories:** concentram consultas e operações de persistência.
-   **Models:** representam as tabelas e relacionamentos do banco.
-   **Database:** configura engine, sessões e dependência de acesso ao
    banco.
-   **Core:** centraliza configurações, autenticação e permissões.
-   **Utils:** reúne funções auxiliares.
-   **Tests:** verifica o comportamento dos módulos.

### 4.1 Estrutura de diretórios sugerida

``` text
portdata-backend/
├── app/
│   ├── main.py
│   ├── database/
│   │   └── connection.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── checklist_model.py
│   │   ├── checklist_item.py
│   │   ├── checklist.py
│   │   ├── checklist_response.py
│   │   ├── checklist_signature.py
│   │   ├── user.py
│   │   └── audit_log.py
│   ├── schemas/
│   │   ├── checklist_schema.py
│   │   ├── response_schema.py
│   │   ├── signature_schema.py
│   │   └── user_schema.py
│   ├── repositories/
│   │   ├── checklist_repository.py
│   │   ├── response_repository.py
│   │   ├── item_repository.py
│   │   ├── user_repository.py
│   │   └── audit_repository.py
│   ├── services/
│   │   ├── checklist_service.py
│   │   ├── response_service.py
│   │   ├── verification_service.py
│   │   ├── signature_service.py
│   │   ├── audit_service.py
│   │   ├── report_service.py
│   │   └── sharing_service.py
│   ├── routers/
│   │   ├── checklist_router.py
│   │   ├── response_router.py
│   │   ├── verification_router.py
│   │   ├── signature_router.py
│   │   ├── report_router.py
│   │   ├── auth_router.py
│   │   └── sharing_router.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── dependencies.py
│   │   ├── permissions.py
│   │   └── exceptions.py
│   ├── utils/
│   │   ├── date_utils.py
│   │   ├── file_utils.py
│   │   └── pdf_utils.py
│   └── templates/
│       └── checklist_template_service.py
├── tests/
│   ├── test_checklist.py
│   ├── test_responses.py
│   ├── test_verifications.py
│   ├── test_signatures.py
│   ├── test_auth.py
│   ├── test_reports.py
│   └── test_sharing.py
├── alembic/
├── alembic.ini
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

A estrutura é uma referência inicial. Arquivos podem ser adicionados ou
agrupados conforme a implementação evoluir.

## 5. Descrição dos arquivos e responsabilidades

### 5.1 `app/main.py`

Inicializa a aplicação FastAPI, registra os routers, configura
middlewares, handlers de exceção e o ciclo de vida da aplicação
(`lifespan`).

Recursos principais:

-   `FastAPI()`: instancia a aplicação.
-   `include_router()`: registra os endpoints.
-   `add_middleware()`: adiciona middlewares.
-   `app.get()`: cria uma rota simples de saúde.
-   `lifespan`: executa tarefas de inicialização e encerramento.

### 5.2 `app/database/connection.py`

Configura a conexão com o PostgreSQL.

Principais recursos:

-   `create_engine()`: cria o engine SQLAlchemy.
-   `sessionmaker()`: configura a fábrica de sessões.
-   `DeclarativeBase`: classe-base dos modelos ORM.
-   `get_db()`: fornece uma sessão por requisição e garante seu
    fechamento.
-   `engine.dispose()`: libera recursos do engine no encerramento,
    quando aplicável.

As tabelas devem ser criadas e atualizadas por migrações Alembic, não
por alterações automáticas em produção.

### 5.3 Models --- `app/models/`

  -----------------------------------------------------------------------
  Arquivo                             Responsabilidade
  ----------------------------------- -----------------------------------
  `checklist_model.py`                Cadastro dos modelos de checklist,
                                      código e versão

  `checklist_item.py`                 Cadastro dos itens, descrições,
                                      obrigatoriedade e criticidade

  `checklist.py`                      Dados gerais de cada preenchimento

  `checklist_response.py`             Respostas e observações dos itens

  `checklist_signature.py`            Referências e dados das assinaturas

  `user.py`                           Usuários, credenciais protegidas e
                                      perfis

  `audit_log.py`                      Histórico de ações e alterações
  -----------------------------------------------------------------------

Recursos SQLAlchemy importantes:

-   `mapped_column()` ou `Column()`: define colunas.
-   `ForeignKey()`: estabelece chaves estrangeiras.
-   `relationship()`: define relacionamentos ORM.
-   `UniqueConstraint()`: impede duplicidades.
-   `CheckConstraint()`: aplica restrições no banco.

### 5.4 Schemas --- `app/schemas/`

  -----------------------------------------------------------------------
  Arquivo                             Classes sugeridas
  ----------------------------------- -----------------------------------
  `checklist_schema.py`               `ChecklistCreate`,
                                      `ChecklistUpdate`,
                                      `ChecklistResponse`

  `response_schema.py`                `RespostaEnum`,
                                      `ChecklistResponseItem`,
                                      `RespostaUpdate`

  `signature_schema.py`               `SignatureCreate`,
                                      `SignatureResponse`

  `user_schema.py`                    `UserCreate`, `UserLogin`,
                                      `UserUpdate`, `UserResponse`
  -----------------------------------------------------------------------

Recursos Pydantic importantes:

-   `BaseModel`: define schemas.
-   `Field()`: configura validações.
-   `field_validator`: valida campos individualmente.
-   `model_validator`: valida combinações de campos.
-   `ConfigDict(from_attributes=True)`: permite construir schemas a
    partir de objetos ORM.

### 5.5 Repositories --- `app/repositories/`

  -----------------------------------------------------------------------
  Arquivo                             Funções sugeridas
  ----------------------------------- -----------------------------------
  `checklist_repository.py`           `create()`, `get_by_id()`,
                                      `get_all()`, `update()`,
                                      `get_by_date()`,
                                      `get_by_equipment()`

  `response_repository.py`            `create_response()`,
                                      `get_responses_by_checklist()`,
                                      `get_response_by_item()`,
                                      `update_response()`

  `item_repository.py`                `get_all_items()`,
                                      `get_item_by_id()`,
                                      `get_critical_items()`,
                                      `get_items_by_model()`

  `user_repository.py`                `get_by_email()`, `get_by_id()`,
                                      `create()`, `update()`,
                                      `deactivate()`

  `audit_repository.py`               `create_log()`,
                                      `get_logs_by_checklist()`,
                                      `get_logs_by_user()`
  -----------------------------------------------------------------------

Essas funções representam operações de persistência. A regra sobre
quando uma operação é permitida deve ficar na camada Service.

### 5.6 Services --- `app/services/`

  -----------------------------------------------------------------------
  Arquivo                             Funções sugeridas e
                                      responsabilidades
  ----------------------------------- -----------------------------------
  `checklist_service.py`              `create_checklist()`,
                                      `get_checklist()`,
                                      `list_checklists()`,
                                      `update_checklist()`,
                                      `save_draft()`,
                                      `finalize_checklist()`,
                                      `archive_checklist()`

  `response_service.py`               `create_response()`,
                                      `update_response()`,
                                      `get_all_responses()`,
                                      `validate_response()`,
                                      `save_all_responses()`

  `verification_service.py`           `verify_required_fields()`,
                                      `verify_all_responses()`,
                                      `verify_critical_items()`,
                                      `verify_horimeter()`,
                                      `verify_fuel_level()`,
                                      `generate_verification_result()`

  `signature_service.py`              `register_signature()`,
                                      `validate_signature()`,
                                      `get_signatures()`,
                                      `verify_required_signatures()`

  `audit_service.py`                  `record_creation()`,
                                      `record_update()`,
                                      `record_finalization()`,
                                      `record_archiving()`,
                                      `get_checklist_history()`

  `report_service.py`                 `generate_checklist_pdf()`,
                                      `generate_checklist_report()`,
                                      `generate_period_report()`,
                                      `export_checklists_csv()`

  `sharing_service.py`                `share_checklist()`,
                                      `revoke_sharing()`,
                                      `verify_sharing_permission()`,
                                      `get_shared_checklists()`
  -----------------------------------------------------------------------

Os Services devem coordenar as transações e chamar os Repositories
necessários. Operações relacionadas --- por exemplo, criar a checklist,
gravar suas respostas e registrar auditoria --- devem ser atômicas
sempre que fizerem parte da mesma operação.

### 5.7 Routers --- `app/routers/`

Os routers expõem as funcionalidades por HTTP e encaminham as chamadas
aos Services.

  -----------------------------------------------------------------------
  Arquivo                             Responsabilidade
  ----------------------------------- -----------------------------------
  `checklist_router.py`               Criar, consultar, editar, finalizar
                                      e arquivar checklists

  `response_router.py`                Registrar e consultar respostas

  `verification_router.py`            Executar e consultar verificações

  `signature_router.py`               Registrar e consultar assinaturas

  `report_router.py`                  Disponibilizar relatórios e PDFs

  `auth_router.py`                    Cadastro, login e identificação do
                                      usuário

  `sharing_router.py`                 Compartilhar e revogar acesso
  -----------------------------------------------------------------------

### 5.8 Core --- `app/core/`

  -----------------------------------------------------------------------
  Arquivo                             Responsabilidade
  ----------------------------------- -----------------------------------
  `config.py`                         Configurações por variáveis de
                                      ambiente com `BaseSettings`

  `security.py`                       Hash de senhas, verificação de
                                      senhas e criação/validação de
                                      tokens

  `dependencies.py`                   Dependências como
                                      `get_current_user()`

  `permissions.py`                    Regras como `can_edit_checklist()`,
                                      `can_view_checklist()` e
                                      `can_finalize_checklist()`

  `exceptions.py`                     Exceções personalizadas e
                                      tratamento padronizado de erros
  -----------------------------------------------------------------------

### 5.9 Utils --- `app/utils/`

  -----------------------------------------------------------------------
  Arquivo                             Funções sugeridas
  ----------------------------------- -----------------------------------
  `date_utils.py`                     `format_date()`,
                                      `validate_date_range()`,
                                      `calculate_duration()`,
                                      `validate_time_range()`

  `file_utils.py`                     `validate_file_type()`,
                                      `validate_file_size()`,
                                      `generate_file_name()`,
                                      `delete_temporary_file()`

  `pdf_utils.py`                      `create_pdf()`,
                                      `add_checklist_header()`,
                                      `add_checklist_items()`,
                                      `add_signatures()`,
                                      `add_observations()`, `save_pdf()`
  -----------------------------------------------------------------------

### 5.10 Templates --- `app/templates/`

`checklist_template_service.py` deverá permitir criar e consultar
modelos, adicionar itens, ativar ou desativar modelos e criar novas
versões. Uma versão já utilizada em preenchimentos finalizados deve ser
preservada para manter a rastreabilidade histórica.

## 6. Proposta de banco de dados

O banco será relacional e utilizará PostgreSQL. A estrutura inicial
poderá conter as seguintes entidades:

  Tabela                    Finalidade
  ------------------------- ----------------------------------------
  `checklist_modelos`       Modelos e versões oficiais
  `checklist_itens`         Itens pertencentes a cada modelo
  `checklists`              Preenchimentos individuais
  `checklist_respostas`     Respostas de cada item
  `checklist_assinaturas`   Assinaturas do operador e da liderança
  `usuarios`                Usuários e perfis
  `auditoria`               Histórico de alterações
  `compartilhamentos`       Permissões de acesso compartilhado

### Relacionamentos principais

-   Um modelo possui vários itens.
-   Um modelo pode originar vários preenchimentos.
-   Uma checklist possui várias respostas.
-   Cada resposta referencia um item do modelo utilizado.
-   Uma checklist pode possuir assinaturas de diferentes responsáveis.
-   Um usuário pode criar ou alterar várias checklists.
-   Uma checklist pode possuir vários registros de auditoria.

Restrições recomendadas:

-   `UNIQUE(checklist_id, item_id)` em respostas, para impedir duas
    respostas do mesmo item no mesmo preenchimento.
-   Chaves estrangeiras para preservar a integridade referencial.
-   Restrições de domínio para respostas, status e percentuais.
-   Índices para data, equipamento, modelo, status e identificadores
    usados nas consultas.

## 7. Regras de negócio e validações

### 7.1 Respostas permitidas

Cada item deverá aceitar somente:

-   `SIM`
-   `NAO`
-   `NAO_APLICAVEL`

Uma observação poderá ser opcional ou obrigatória conforme a regra
definida para o item. Por exemplo, a organização poderá exigir uma
observação quando a resposta for `NAO`.

### 7.2 Itens críticos

O cadastro de cada item deverá possuir um atributo booleano, como
`critico`.

Na finalização, o serviço de verificação deverá:

1.  Identificar respostas ausentes.
2.  Conferir os campos obrigatórios.
3.  Identificar itens críticos respondidos como `NAO`.
4.  Produzir um resultado de validação.
5.  Impedir a liberação operacional quando houver uma reprovação
    crítica, de acordo com a regra oficial aprovada.

Uma checklist preenchida não significa, por si só, que o equipamento
está liberado para operar. O resultado deve distinguir, no mínimo,
preenchimento válido, pendências e bloqueios operacionais.

### 7.3 Horímetros e combustível

-   O horímetro final não deve ser inferior ao inicial, salvo
    procedimento excepcional documentado.
-   O nível de combustível deve respeitar o intervalo de 0 a 100%.
-   Datas e horários devem ser validados.
-   O fuso horário usado para registros de auditoria deve ser definido e
    documentado.

### 7.4 Estados da checklist

Uma proposta inicial de estados:

-   `RASCUNHO`: preenchimento em andamento.
-   `PENDENTE_APROVACAO`: preenchida, aguardando validação ou aprovação.
-   `FINALIZADA`: processo de preenchimento e aprovação concluído.
-   `ARQUIVADA`: registro preservado, sem uso operacional corrente.
-   `BLOQUEADA`: possui condição impeditiva identificada.

A transição entre estados deverá ser controlada por regras de negócio e
permissões. Uma checklist finalizada não deve ser editada
silenciosamente; correções devem seguir um processo de retificação com
justificativa e auditoria.

## 8. Endpoints previstos

Prefixo geral: `/api`

  ----------------------------------------------------------------------------------------
  Método HTTP             Endpoint                                 Finalidade
  ----------------------- ---------------------------------------- -----------------------
  `POST`                  `/checklists`                            Criar checklist

  `GET`                   `/checklists`                            Listar checklists

  `GET`                   `/checklists/{id}`                       Consultar checklist
                                                                   completa

  `PUT`                   `/checklists/{id}`                       Atualizar dados gerais
                                                                   permitidos

  `PATCH`                 `/checklists/{id}/respostas/{item_id}`   Atualizar resposta de
                                                                   um item

  `POST`                  `/checklists/{id}/verificar`             Executar verificações

  `GET`                   `/checklists/{id}/verificacoes`          Consultar resultado das
                                                                   verificações

  `POST`                  `/checklists/{id}/finalizar`             Solicitar finalização

  `POST`                  `/checklists/{id}/assinaturas`           Registrar assinatura

  `GET`                   `/checklists/{id}/assinaturas`           Consultar assinaturas

  `GET`                   `/relatorios/checklist/{id}/pdf`         Gerar ou consultar PDF

  `POST`                  `/checklists/{id}/compartilhar`          Conceder
                                                                   compartilhamento

  `GET`                   `/checklists/compartilhadas`             Listar checklists
                                                                   compartilhadas

  `DELETE`                `/compartilhamentos/{id}`                Revogar
                                                                   compartilhamento

  `POST`                  `/auth/login`                            Autenticar usuário

  `GET`                   `/auth/me`                               Consultar usuário
                                                                   autenticado
  ----------------------------------------------------------------------------------------

Os endpoints são uma proposta inicial. A implementação deverá definir
códigos HTTP, paginação, filtros, autenticação, autorização e formatos
de resposta.

## 9. Fluxo de funcionamento

Exemplo do fluxo de criação e finalização:

1.  O operador autentica-se na aplicação.
2.  O frontend solicita os modelos de checklist disponíveis.
3.  O operador seleciona o modelo de guindaste.
4.  O backend cria um registro em estado `RASCUNHO`.
5.  O operador preenche os dados gerais.
6.  O frontend envia as respostas dos itens.
7.  O backend valida e armazena as informações.
8.  O operador pode recuperar o rascunho e continuar o preenchimento.
9.  Ao solicitar a finalização, o backend verifica campos, respostas,
    itens críticos e assinaturas exigidas.
10. O sistema registra o resultado e a auditoria.
11. Se as condições de finalização forem atendidas, o registro é
    finalizado.
12. O relatório pode ser gerado em PDF e disponibilizado a usuários
    autorizados.

### Fluxo técnico de uma requisição

``` text
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
Repository (persistência)
   |
   v
Model / SQLAlchemy
   |
   v
PostgreSQL
```

A resposta percorre o caminho inverso e é serializada pelo schema de
saída.

## 10. Autenticação, autorização e compartilhamento

O sistema deverá proteger dados operacionais e permitir acesso conforme
o perfil do usuário.

Perfis iniciais possíveis:

-   **Operador:** cria e preenche checklists conforme sua autorização.
-   **Liderança:** consulta, revisa e aprova registros conforme suas
    atribuições.
-   **Administrador:** gerencia usuários, modelos e configurações.
-   **Consulta:** visualiza somente os registros autorizados.

Requisitos de segurança:

-   Armazenar senhas somente como hashes seguros.
-   Utilizar tokens com expiração e validação.
-   Aplicar autorização no backend em todas as operações protegidas.
-   Isolar dados por organização, quando houver múltiplas empresas.
-   Registrar ações relevantes em auditoria.
-   Proteger arquivos e assinaturas.
-   Utilizar HTTPS em ambientes implantados.
-   Guardar segredos em variáveis de ambiente ou gerenciador de
    segredos.
-   Não publicar dados operacionais ou credenciais no repositório.

O compartilhamento deverá conceder acesso explícito, limitado e
revogável. Links públicos sem autenticação não são recomendados para
documentos operacionais.

## 11. Auditoria, integridade e preservação

Cada alteração relevante deverá registrar:

-   Usuário responsável.
-   Data e horário.
-   Ação realizada.
-   Checklist afetada.
-   Campo alterado.
-   Valor anterior e novo valor, quando aplicável.
-   Justificativa, quando exigida.

A finalização deverá preservar uma versão consistente do registro.
Recomenda-se armazenar também uma cópia do PDF final e, se necessário,
um identificador de integridade (hash) do arquivo.

A exclusão definitiva de documentos finalizados deve ser evitada. A
política de retenção e descarte deverá ser definida pela organização e
pelas normas aplicáveis.

## 12. Testes automatizados

Os testes serão desenvolvidos com Pytest.

  -----------------------------------------------------------------------
  Arquivo                             Cenários principais
  ----------------------------------- -----------------------------------
  `test_checklist.py`                 Criar, consultar, editar e arquivar

  `test_responses.py`                 Validar respostas e impedir
                                      duplicidades

  `test_verifications.py`             Campos ausentes, horímetros e itens
                                      críticos

  `test_signatures.py`                Registro e validação de assinaturas

  `test_auth.py`                      Login, token e permissões

  `test_reports.py`                   Geração e conteúdo do PDF

  `test_sharing.py`                   Concessão, consulta e revogação de
                                      acesso
  -----------------------------------------------------------------------

Também deverão existir testes de integração com um banco de testes
separado do banco de desenvolvimento ou produção.

Executar testes:

``` bash
pytest
```

## 13. Migrações com Alembic

O Alembic controlará as alterações da estrutura do banco.

Comandos usuais:

``` bash
alembic init alembic
```

Criar uma migração:

``` bash
alembic revision --autogenerate -m "cria estrutura inicial"
```

Aplicar migrações:

``` bash
alembic upgrade head
```

Consultar a versão atual:

``` bash
alembic current
```

Reverter uma revisão:

``` bash
alembic downgrade -1
```

As migrações devem ser revisadas antes de serem aplicadas, especialmente
em ambientes com dados existentes.

## 14. Configuração do ambiente

Crie um arquivo `.env` local, que não deve ser enviado ao GitHub:

``` env
APP_NAME=PortData API
APP_ENV=development
DATABASE_URL=postgresql+psycopg://usuario:senha@localhost:5432/portdata
SECRET_KEY=troque-por-um-segredo-forte
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Crie um `.env.example` com valores ilustrativos, sem credenciais reais:

``` env
APP_NAME=PortData API
APP_ENV=development
DATABASE_URL=postgresql+psycopg://usuario:senha@localhost:5432/portdata
SECRET_KEY=change-me
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

A aplicação deverá carregar essas configurações por meio de
`pydantic-settings`.

## 15. Como executar a API

Depois de configurar o PostgreSQL, instalar as dependências e preparar o
arquivo `.env`:

``` bash
uvicorn app.main:app --reload
```

Endereço local padrão:

``` text
http://127.0.0.1:8000
```

Documentação interativa:

``` text
http://127.0.0.1:8000/docs
```

Documentação alternativa:

``` text
http://127.0.0.1:8000/redoc
```

Esses endereços estarão disponíveis quando a aplicação estiver em
execução.

## 16. Plano de desenvolvimento

  -----------------------------------------------------------------------
  Etapa                               Entrega
  ----------------------------------- -----------------------------------
  1\. Ambiente e banco                Ambiente Python, PostgreSQL,
                                      conexão e Alembic

  2\. Estrutura da checklist          Models, itens, relacionamentos e
                                      Schemas

  3\. CRUD                            Repositories, Services e endpoints
                                      de criação, consulta e edição

  4\. Verificações                    Validações, itens críticos e
                                      finalização

  5\. Segurança e histórico           Autenticação, permissões,
                                      assinaturas e auditoria

  6\. Relatórios e compartilhamento   PDF, exportação, compartilhamento e
                                      testes de integração

  7\. Implantação                     Configuração de produção,
                                      monitoramento, backups e
                                      documentação
  -----------------------------------------------------------------------

A prioridade deve ser concluir e testar o núcleo: cadastro do modelo,
criação de rascunhos, armazenamento das respostas, consulta e edição
controlada. Recursos adicionais podem ser implementados depois.

## 17. Próximas evoluções

Após a primeira versão funcional, o sistema poderá evoluir para:

-   Outros tipos de equipamentos e checklists.
-   Gestão de diferentes terminais e organizações.
-   Painel de indicadores operacionais.
-   Pesquisa por navio, equipamento, operador, data e status.
-   Notificações sobre pendências e reprovações.
-   Integração com sistemas portuários existentes.
-   Aplicativo móvel e suporte a operação offline com sincronização
    controlada.
-   Leitura assistida de checklists físicas por OCR, sempre com
    conferência humana.
-   Relatórios gerenciais e análise histórica.

## 18. Contribuição

Sugestão de fluxo de contribuição:

1.  Criar uma Issue descrevendo a tarefa.
2.  Criar uma branch específica.
3.  Implementar a funcionalidade.
4.  Adicionar ou atualizar testes.
5.  Executar `pytest`.
6.  Abrir um Pull Request relacionado à Issue.
7.  Solicitar revisão antes de integrar à branch principal.

## 19. Licença e uso

A licença do projeto ainda deverá ser definida pelos responsáveis. Até
que isso ocorra, não se deve presumir autorização para reutilização,
distribuição ou uso comercial do código.

------------------------------------------------------------------------

**PortData --- Backend de gerenciamento de checklists e informações
operacionais portuárias.**
