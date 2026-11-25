# Back-end (FastAPI) — como rodar

## Caminho principal: Python puro (sem Docker)
Requisitos: Python 3.12 (3.11 costuma servir).
```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Abra http://localhost:8000/api/v1/health (deve mostrar `{"status":"ok"}`) e http://localhost:8000/docs (Swagger).
Testes: `pytest`. O banco da demo é o arquivo `backend/checklist.db` (SQLite; já está no .gitignore). Para zerar: apague o arquivo e rode o seed.

## Para os celulares falarem com o seu notebook (demo)
1. Notebook e celulares na **mesma rede** (Wi-Fi ou hotspot do celular).
2. Descubra o IP do notebook: `ipconfig` (Windows) ou `ip a` / `ifconfig` (Linux/macOS). Ex.: `192.168.0.15`.
3. Libere a **porta 8000** no firewall do notebook.
4. No app, configure a URL: `http://192.168.0.15:8000/api/v1`. No celular, teste abrindo `.../health` no navegador.
> Android bloqueia HTTP simples em apps de release por padrão: para a demo, permitir *cleartext* só para esse IP/rede (tarefa FE-14; ver `app/README.md`) ou usar um túnel HTTPS (ex.: ngrok/cloudflared).

## Opcional: Docker (deploy/portabilidade, tarefa BE-12)
```bash
cp .env.example .env     # na raiz do repositório
docker compose up --build
```
Só use se alguém da equipe já souber Docker ou se a TI do cliente pedir contêiner. **Não é necessário para desenvolver nem para a demo.**
