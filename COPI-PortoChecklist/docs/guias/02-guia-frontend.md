# Guia 02 — Front-end (Flutter) passo a passo (FE-01 a FE-14)

> Leia antes: `00-entenda-o-sistema-e-como-trabalhar.md`, `app/README.md` e `docs/00-contrato.md`.

## Decisões para simplificar (3 dias, iniciantes)
| Tema | Escolha | Por quê |
|---|---|---|
| Estado das telas | **`provider`** (`ChangeNotifier`) | Mais simples que Riverpod/Bloc |
| Navegação | **`Navigator.push`** padrão | Sem biblioteca extra |
| Banco local | **`sqflite`** guardando **JSON** (uma tabela de checklists e uma de cache) | Sem geração de código (drift exige `build_runner`) |
| Servidor | Interface `Api` com versão **Mock** e versão **Real** | Dá para trabalhar sem o back-end |
| Assinatura do APK | A padrão do `flutter build apk --release` (serve para a demo) | Sem criar keystore agora |

## O que JÁ está pronto
`app/lib_planejado/domain/modelos.dart` e `regras.dart` (Dart puro, mesmas regras do servidor) e os testes em `app/test_planejado/regras_test.dart`. Eles cobrem: **lote** (RN12), **impedimento** (RN05), **resumo** lote/manual/problemas e **validação para enviar** (RN01–RN04, RN06, RN17). Use-os; **não reescreva regras dentro dos widgets**. (Código ainda não executado: rode `flutter test` no FE-01 e peça à IA para corrigir qualquer erro.)

## Ordem de trabalho (cada passo termina com algo que você VÊ na tela)
**D1:** FE-01 → **D2:** FE-02, FE-03, FE-04, FE-05, FE-06 → **D3:** FE-07…FE-12 → **D4:** FE-13, FE-14.
**Dica:** trabalhem em **duplas**: uma pessoa nas telas do operador (FE-04, 05, 07, 08, 09), outra na infraestrutura (FE-02, 03, 06, 10) e outra no admin (FE-11, 12).

---

## FE-01 — Projeto, estrutura, URL configurável, mock (D1/D2, ~3h)
1. Instale o Flutter (docs.flutter.dev) e rode `flutter doctor` até Android estar ✓. Ative **Depuração USB** no celular.
2. Siga `app/README.md` (`flutter create ... .` + `flutter pub add ...`).
3. Mova `lib_planejado/domain/*` para `lib/domain/` e `test_planejado/regras_test.dart` para `test/`. Rode `flutter test` ⇒ 6 testes verdes.
4. Crie `lib/core/config.dart`:
```dart
class Config {
  // 10.0.2.2 = o notebook visto de dentro do emulador Android. No celular real, use o IP do notebook.
  static const apiUrlPadrao =
      String.fromEnvironment('API_URL', defaultValue: 'http://10.0.2.2:8000/api/v1');
  static const usarMock = bool.fromEnvironment('MOCK', defaultValue: false);
}
```
Rode com: `flutter run --dart-define=MOCK=true` (mock) ou `--dart-define=API_URL=http://192.168.0.15:8000/api/v1`.
5. Crie `lib/data/remote/api.dart` com a **interface** que as telas usam (nunca chame o `dio` direto numa tela):
```dart
abstract class Api {
  Future<Map<String, dynamic>> login(String matricula, String pin);
  Future<Map<String, dynamic>> template();
  Future<Map<String, dynamic>> lookups();
  Future<double?> ultimoHorimetro(String equipamentoId);
  Future<Map<String, dynamic>> enviarChecklist(String id, Map<String, dynamic> payload); // PUT
  Future<Map<String, dynamic>> listarChecklists({String? status});
  Future<Map<String, dynamic>> detalhe(String id);
  Future<void> vistar(String id);
  Future<void> solicitarCorrecao(String id, String motivo);
}
```
6. Crie `ApiMock` (retorna dados de `assets/mock/*.json`, copie `dados/seed/checklist_template_for_opp_0017_v5.json` para `assets/mock/template.json` e declare em `pubspec.yaml` → `flutter: assets: - assets/mock/`) e `ApiReal` (abaixo, FE-02/06).
**Pronto quando:** `flutter run --dart-define=MOCK=true` abre o app num aparelho real; `flutter test` verde.
**Erros comuns:** *Android licenses* → `flutter doctor --android-licenses`. *Aparelho não aparece* → cabo de dados, Depuração USB, `flutter devices`. *Gradle lento na 1ª vez* → normal (até 10 min).
**Prompt pronto:** *"Flutter. Crie a interface abstrata Api (cole) e uma ApiMock que lê JSON de assets/mock. Explique em 5 linhas como escolher Mock x Real com --dart-define."*

---

## FE-02 — Login único e perfis (D2, ~3h)
**Fluxo:** tela de login ⇒ `api.login` ⇒ guarda token ⇒ olha `usuario.papel` ⇒ abre **HomeOperador** ou **HomeAdmin**.
```dart
// lib/data/remote/api_real.dart (trecho)
import 'package:dio/dio.dart';

class ApiReal implements Api {
  final Dio _dio;
  String? token;
  ApiReal(String baseUrl)
      : _dio = Dio(BaseOptions(
          baseUrl: baseUrl,
          connectTimeout: const Duration(seconds: 8),
          receiveTimeout: const Duration(seconds: 15),
        ));
  Options get _op => Options(headers: {if (token != null) 'Authorization': 'Bearer $token'});

  @override
  Future<Map<String, dynamic>> login(String matricula, String pin) async {
    final r = await _dio.post('/auth/login', data: {'matricula': matricula, 'pin': pin});
    return Map<String, dynamic>.from(r.data);
  }

  @override
  Future<Map<String, dynamic>> enviarChecklist(String id, Map<String, dynamic> payload) async {
    final r = await _dio.put('/checklists/$id', data: payload, options: _op);
    return Map<String, dynamic>.from(r.data);
  }
  // ... demais métodos no mesmo padrão
}

/// Converte qualquer erro do dio em mensagem para o usuário.
String mensagemDeErro(Object e) {
  if (e is DioException) {
    final d = e.response?.data;
    if (d is Map && d['erro'] is Map) return d['erro']['mensagem'] ?? 'Erro';
    if (d is Map && d['detail'] != null) return d['detail'].toString();
    if (e.type == DioExceptionType.connectionError || e.type == DioExceptionType.connectionTimeout) {
      return 'Sem conexão com o servidor';
    }
  }
  return 'Algo deu errado. Tente novamente.';
}
```
```dart
// lib/features/auth/sessao.dart (ChangeNotifier)
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class Sessao extends ChangeNotifier {
  final _seguro = const FlutterSecureStorage();
  String? token, nome, papel, usuarioId;
  bool get logado => token != null;
  bool get ehAdmin => papel == 'ADMIN';

  Future<void> entrar(Map<String, dynamic> resp) async {
    token = resp['access_token'];
    final u = resp['usuario'];
    nome = u['nome']; papel = u['papel']; usuarioId = u['id'];
    await _seguro.write(key: 'sessao', value: '$token|$nome|$papel|$usuarioId');
    notifyListeners();
  }

  Future<void> restaurar() async { // chamar ao abrir o app: permite abrir SEM internet depois do 1º login
    final v = await _seguro.read(key: 'sessao');
    if (v != null) {
      final p = v.split('|');
      token = p[0]; nome = p[1]; papel = p[2]; usuarioId = p[3];
      notifyListeners();
    }
  }

  Future<void> sair() async { await _seguro.delete(key: 'sessao'); token = null; notifyListeners(); }
}
```
**Tela de login:** campos matrícula e PIN (teclado numérico, PIN oculto), botão **Entrar**, e abaixo uma caixa **"Atalho de demonstração"** com 2 botões que preenchem 1001/1234 e 9001/0000. Erro (PIN errado) em texto vermelho abaixo do botão.
**Pronto quando:** com o mock, 1001 abre a home do operador e 9001 a do admin; fechar e reabrir o app mantém o login; com a API real, PIN errado mostra "Matrícula ou PIN incorretos".
**Erros comuns:** *`MissingPluginException` no secure storage* → pare o app e rode de novo (`flutter run`), não use hot reload após instalar pacote. *`minSdkVersion`* → em `android/app/build.gradle` use `minSdk = 23`.

---

## FE-03 — Banco local (D2–D3, ~4h)
Duas tabelas e só: **cache** (chave → JSON) e **checklists** (id → JSON + status de sincronização).
```dart
// lib/data/local/banco_local.dart
import 'dart:convert';
import 'package:path/path.dart';
import 'package:sqflite/sqflite.dart';

class BancoLocal {
  static Database? _db;

  static Future<Database> abrir() async {
    if (_db != null) return _db!;
    _db = await openDatabase(
      join(await getDatabasesPath(), 'checklist.db'),
      version: 1,
      onCreate: (db, _) async {
        await db.execute('CREATE TABLE cache(chave TEXT PRIMARY KEY, json TEXT NOT NULL)');
        await db.execute('''CREATE TABLE checklists(
          id TEXT PRIMARY KEY, json TEXT NOT NULL, status TEXT NOT NULL,
          tentativas INTEGER NOT NULL DEFAULT 0, ultimo_erro TEXT, atualizado_em TEXT NOT NULL)''');
      },
    );
    return _db!;
  }

  static Future<void> guardarCache(String chave, Object json) async {
    final db = await abrir();
    await db.insert('cache', {'chave': chave, 'json': jsonEncode(json)},
        conflictAlgorithm: ConflictAlgorithm.replace);
  }

  static Future<dynamic> lerCache(String chave) async {
    final db = await abrir();
    final l = await db.query('cache', where: 'chave = ?', whereArgs: [chave]);
    return l.isEmpty ? null : jsonDecode(l.first['json'] as String);
  }

  /// status local: RASCUNHO | PENDENTE_ENVIO | SINCRONIZADO | ERRO_VALIDACAO
  static Future<void> salvarChecklist(String id, Map<String, dynamic> json, String status) async {
    final db = await abrir();
    await db.insert(
      'checklists',
      {'id': id, 'json': jsonEncode(json), 'status': status, 'atualizado_em': DateTime.now().toUtc().toIso8601String()},
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  static Future<List<Map<String, dynamic>>> listarChecklists({String? status}) async {
    final db = await abrir();
    final l = await db.query('checklists',
        where: status == null ? null : 'status = ?', whereArgs: status == null ? null : [status],
        orderBy: 'atualizado_em ASC');
    return [for (final r in l) {...r, 'json': jsonDecode(r['json'] as String)}];
  }
}
```
Depois do **login** (e a cada abertura com internet), baixe `template()` e `lookups()` e guarde com `guardarCache('template', ...)` / `guardarCache('lookups', ...)`. As telas leem **sempre do cache**.
**Pronto quando:** com internet você baixa o template; depois, em **modo avião**, o app ainda mostra os 23 itens e as listas de cais/guindaste; um rascunho sobrevive a fechar o app.
**Prompt pronto:** *"Flutter + sqflite. Revise esta classe BancoLocal (cole) e escreva testes simples. Não troque para drift."*

---

## FE-04 — Cabeçalho (D2, ~3h)
**Campos:** local (lista de `lookups`), turno (4 botões; **sugerir pelo horário** do celular), data (hoje), equipamento (lista), navio (opcional), horímetro inicial (teclado numérico, 1 casa; **sugerir** `ultimoHorimetro` quando houver internet/cache), combustível (0–100: `Slider` com valor grande ao lado), hora de entrada (agora).
**Estado:** um `ChangeNotifier` `ChecklistEmEdicao` guarda cabeçalho + lista de `RespostaItem` (23, todas `resposta: null`) + `inicioPreenchimento` (`DateTime.now()` ao abrir). Gere o **UUID** aqui: `const Uuid().v4()`. **Salve rascunho a cada alteração** (`BancoLocal.salvarChecklist(id, json, 'RASCUNHO')`).
**Sugestão de turno (regra simples):** 08:00–13:59 ⇒ `T_08_14`; 14:00–19:59 ⇒ `T_14_20`; 20:00–01:59 ⇒ `T_20_02`; 02:00–07:59 ⇒ `T_02_08`.
**Pronto quando:** o botão **Continuar** só habilita com local, equipamento e horímetro válidos; a máscara aceita `36466.1` e rejeita `36466.15`.
**Erros comuns:** *teclado numérico sem ponto* → `keyboardType: TextInputType.numberWithOptions(decimal: true)`. *Vírgula no Brasil* → troque `,` por `.` antes de converter com `double.tryParse`.

---

## FE-05 — Itens 1–23 (D2, ~5h)
**Tela:** barra de progresso fixa no topo ("12/23 respondidos") + `ListView` de **cartões**. Cada cartão: número, texto, selo **CRÍTICO** (se `critico`), 3 botões **grandes (≥ 56 dp)** — **S** (verde, ✓), **N** (vermelho, ✗), **N/A** (cinza, –) — e, quando for N, um campo de observação **obrigatório** (borda vermelha enquanto vazio).
**Regras:** ao tocar num botão chame `responderManual(resposta, 'S')` (do `regras.dart`: já troca a origem para MANUAL). Itens sem resposta ficam com borda tracejada/cinza.
**Pronto quando:** dá para responder os 23 em menos de 5 min; fechar e reabrir mantém as respostas; N sem observação mostra o aviso.
**Prompt pronto:** *"Flutter. Crie o widget CartaoItem: recebe ItemTemplate e RespostaItem (cole as classes), mostra 3 botões grandes S/N/N-A com cor E ícone, selo CRÍTICO e TextField de observação obrigatório quando N. Chama um callback onChanged. Alto contraste."*

---

## FE-06 — Envio online (D2, ~3h) ⭐ **checkpoint do D2**
1. Monte o JSON exatamente como o contrato §6 (`respostas` com `item_numero`, `resposta`, `origem`, `observacao`) a partir do estado.
2. `api.enviarChecklist(id, payload)`. Em sucesso, `BancoLocal.salvarChecklist(id, json, 'SINCRONIZADO')`.
3. **Para o D2** basta: um botão **Enviar** (mesmo sem a tela de finalização) que manda o caso da foto; confira no `/docs` do servidor (ou no admin) que chegou.
**Pronto quando:** o fixture sai do celular e aparece no servidor com `impedido: true`.
**Erros comuns:** *`Connection refused`* → URL errada, notebook em outra rede ou firewall (veja `backend/README.md`). *HTTP bloqueado no Android* → `usesCleartextTraffic` no manifest (veja `app/README.md`). *400 do servidor* → leia `erro.campos`; costuma ser observação faltando ou horímetro final vazio.

---

## FE-07 — "Marcar tudo OK" (D3, ~3h)
1. Botão no topo da lista, **visível só enquanto houver item sem resposta**.
2. Ao tocar: `AlertDialog` com o texto *"Confirmo que inspecionei o equipamento e que todos os itens abaixo estão OK, exceto os que eu alterar."* + **Confirmar** / **Cancelar**.
3. Confirmar ⇒ `marcarTudoOk(respostas, itens, incluirCriticos: ...)` (já pronta). Guarde `usouLote = true` e `itensMarcadosLote = n`.
4. Cartões com `origem == 'LOTE'` mostram o selo discreto **"lote"**; ao tocar, vira manual e o selo some (já feito por `responderManual`).
5. Ao enviar, calcule `itens_alterados_apos_lote` = itens que foram marcados em lote e depois tocados (guarde um contador ao alterar um item que **era** LOTE).
**Pronto quando:** testes de `regras_test.dart` verdes e na tela: nada é sobrescrito, N/A nunca é marcado, o selo some ao tocar.

## FE-08 — Alerta de impedimento (D3, ~1h)
Sempre que uma resposta virar N, chame `criticosComProblema(respostas, itens)`. Se não for vazia, abra uma tela/diálogo **vermelho em tela cheia**: ícone ⚠, "**Equipamento impedido de operar**", lista dos itens críticos com problema, botão **Entendi e continuar**. Mostre o selo também no resumo da finalização.
**Pronto quando:** no caso da foto, marcar o item 1 como N abre o alerta (o 10 e o 22 também são críticos, não repetir o diálogo a cada item: mostre uma vez e um selo fixo no topo).

## FE-09 — Finalização e assinatura (D3, ~4h)
**Tela:** horímetro final, hora de saída (padrão: agora), observação geral, **resumo** (`resumir(...)` ⇒ "20 em lote · 3 manuais · 3 com problema" + selo IMPEDIDO), campo de **assinatura** e botão **Enviar**.
```dart
import 'dart:convert';
import 'package:signature/signature.dart';

final assinatura = SignatureController(penStrokeWidth: 3);
// na tela:  Signature(controller: assinatura, height: 200, backgroundColor: Colors.white)
// botão Limpar: assinatura.clear()
// ao enviar:
final bytes = await assinatura.toPngBytes();
final base64Png = bytes == null ? null : base64Encode(bytes);
```
Antes de enviar chame `validarParaEnviar(...)` (pronta). Se vier lista de erros ⇒ mostre-os (um por linha) e **não envie**. Se vazia: preencha `finalizado_em`, `duracao_segundos`, salve como `PENDENTE_ENVIO` e chame o sincronizador (FE-10). Depois vá para a tela de confirmação ("Salvo no aparelho" ou "Enviado").
**Pronto quando:** sem assinatura/horímetro/saída não envia; horímetro final menor que o inicial mostra erro claro; o resumo bate com o que foi marcado.

## FE-10 — Fila offline e sincronização (D3, ~6h) ⭐ a mais difícil
**Ideia:** o app **nunca** envia direto: salva como `PENDENTE_ENVIO` e o **Sincronizador** esvazia a fila (em ordem). É seguro repetir porque o servidor é idempotente (RN11).
```dart
// lib/sync/sincronizador.dart
import 'package:dio/dio.dart';

class Sincronizador {
  final Api api;
  bool _rodando = false;
  Sincronizador(this.api);

  /// Retorna quantos checklists foram enviados. Para na primeira falha de rede (mantém a ordem).
  Future<int> sincronizar() async {
    if (_rodando) return 0;
    _rodando = true;
    var enviados = 0;
    try {
      final pendentes = await BancoLocal.listarChecklists(status: 'PENDENTE_ENVIO');
      for (final linha in pendentes) {
        final id = linha['id'] as String;
        final payload = Map<String, dynamic>.from(linha['json']);
        try {
          await api.enviarChecklist(id, payload);
          await BancoLocal.salvarChecklist(id, payload, 'SINCRONIZADO');
          enviados++;
        } on DioException catch (e) {
          final c = e.response?.statusCode;
          if (c == 401) break;                      // sessão expirada: pedir login, NÃO apagar nada
          if (c != null && c >= 400 && c < 500) {   // 400/403/409: repetir não adianta
            await BancoLocal.salvarChecklist(id, {...payload, 'ultimo_erro': mensagemDeErro(e)}, 'ERRO_VALIDACAO');
            continue;
          }
          break;                                    // sem rede / 5xx: tenta depois
        }
      }
    } finally {
      _rodando = false;
    }
    return enviados;
  }
}
```
**Gatilhos para chamar `sincronizar()`:** (1) ao abrir o app; (2) logo depois de **Enviar**; (3) quando a conexão mudar (`Connectivity().onConnectivityChanged.listen(...)`); (4) `Timer.periodic(30s)`; (5) botão **Sincronizar agora** nas Configurações.
**Indicadores (obrigatórios):** na Home mostre "● Online/○ Sem internet" e "N pendente(s) de envio"; cada checklist da lista mostra seu status (`Rascunho`, `Pendente de envio`, `Enviado`, `Erro: ...`).
**Teste do critério:** ligue **modo avião** ⇒ preencha e finalize ⇒ status "Pendente de envio" ⇒ desligue o modo avião ⇒ em até 30 s vira "Enviado" e há **1 só** registro no servidor (confira a lista do admin). Toque em Enviar 2x ⇒ continua 1 registro.
**Erros comuns:** *`connectivity_plus` devolve lista na v6* → trate `List<ConnectivityResult>`. *Conexão "ligada" sem internet* → por isso o envio tenta e trata o erro, em vez de confiar no ícone. *App fechado não sincroniza* → aceitável na demo (sincroniza ao abrir).
**Prompt pronto:** *"Flutter. Revise este Sincronizador (cole) e BancoLocal (cole). Liste cenários de falha (sem rede, 401, 409, app fechado no meio do envio) e diga se o código os trata. Não mude a arquitetura."*

---

## FE-11 — Admin: lista (D3, ~4h)
**Tela:** 4 cartões de **contadores** no topo (Pendentes | Impedidos | Correção solicitada | Vistados hoje) ⇒ filtro por status (chips) ⇒ lista com **impedidos em vermelho no topo** (o servidor já ordena), cada linha com operador, equipamento, cais, turno, data e selos **IMPEDIDO / lote / Editado**. Botão **Atualizar** e atualização automática:
```dart
Timer.periodic(const Duration(seconds: 15), (_) => recarregar());   // cancele no dispose()!
```
Mostre "atualiza em Xs" (um `ValueNotifier<int>` que conta de 15 a 0). Toque ⇒ detalhe.
**Pronto quando:** com o caso da foto enviado por outro celular, ele aparece em ≤ 15 s com selo IMPEDIDO e o contador de impedidos = 1.
**Erro comum:** *vazamento de Timer* → `timer.cancel()` no `dispose`.

## FE-12 — Admin: detalhe completo e Vistar (D3, ~6h)
**Regra do produto: o admin NUNCA vista sem ver tudo.** Ordem da tela (uma `ListView`):
1. Faixa de resumo **"20 OK · 3 com problema · 1 crítico"** + selo **IMPEDIDO** (vermelho).
2. Cabeçalho completo (local, turno, data, equipamento, navio, horímetros, combustível, entrada/saída).
3. **Itens com problema** no topo, em vermelho, com a observação.
4. **Todos os itens OK** logo abaixo (seção **já aberta**), na ordem do formulário, cada um com selo `lote`/`manual`.
5. Observação geral. 6. **Assinatura** do operador (`Image.memory(base64Decode(...))`).
7. Metadados: início/fim do preenchimento, tempo total (se < 1 min, mostre um aviso discreto "preenchido em menos de 1 min"), usou lote e quantos itens.
8. **Linha do tempo** (`eventos`): ícone + "Editado por João — 18/11 21:05" (e o diff, se houver).
9. **Rodapé fixo** com **VISTAR** e **SOLICITAR CORREÇÃO** (o 2º abre um diálogo com campo de motivo **obrigatório**).
Depois de vistar: os botões somem e aparece "**Vistado por [nome] em [data/hora] — registro travado**".
**Pronto quando:** o caso da foto mostra exatamente 3 problemas no topo e 20 OK abaixo; vistar trava (a lista mostra Vistado e o operador não consegue mais editar).

## FE-13 — Correção e edição pelo operador (D4, ~6h)
1. **Home do operador:** ao abrir (e com pull-to-refresh) chame `listarChecklists()`; cada item da lista mostra o status do servidor. Se `status == CORRECAO_SOLICITADA`, mostre um **cartão amarelo com o motivo** (`motivo_correcao`).
2. **Editar:** permitido enquanto o status do servidor **não for VISTADO**. Abra o mesmo formulário preenchido (a partir do JSON local; se não existir, use `detalhe(id)`). **Todos os campos editáveis.**
3. Ao salvar, grave como `PENDENTE_ENVIO` com `confirmacao_correcao: true` (se estava em correção solicitada). Peça um **toque de confirmação** ("Confirmo as correções") — **sem nova assinatura**.
4. Selo **"Editado"** quando `editado == true`; mostre a linha do tempo no detalhe do operador também (somente leitura).
5. VISTADO ⇒ botão Editar desaparece.
**Pronto quando:** roteiro da demo, passos 8–10, funciona entre os 2 celulares.

## FE-14 — APK de release em 2 aparelhos (D4, ~3h)
1. Ajuste o `AndroidManifest.xml` (permissão INTERNET + `usesCleartextTraffic` — veja `app/README.md`).
2. `flutter build apk --release --dart-define=API_URL=http://IP_DO_NOTEBOOK:8000/api/v1` ⇒ arquivo em `build/app/outputs/flutter-apk/app-release.apk`.
3. Instale nos 2 aparelhos (cabo: `flutter install`, ou envie o APK e permita "fontes desconhecidas").
4. Rode o **roteiro completo** em modo avião e normal.
**Pronto quando:** o roteiro da demo roda 2x seguidas nos dois aparelhos com o **APK de release** (não só `flutter run`).
**Erros comuns:** *app de release sem rede* → faltou a permissão INTERNET. *HTTP recusado* → faltou `usesCleartextTraffic`. *IP mudou* → mantenha a URL configurável nas Configurações (e não recompile na hora da demo).
