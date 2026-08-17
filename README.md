# Vision Platform Central

Serviço central de coleta para o ecossistema GeoFissura Vision Platform.

## Responsabilidades

- Coletar observações das Vision Platform Locais
- Persistir metadados de imagens capturadas
- Verificar integridade (hash SHA-256)
- Confirmar recebimento idempotente via `/ack`
- Registrar status e falhas de comunicação com locais
- Preparar terreno para processamento pesado (IA, séries temporais)

## Stack

- Python 3.11+
- FastAPI + Uvicorn
- SQLAlchemy + PostgreSQL
- Pydantic Settings
- HTTPX (cliente para locais)

## Configuração

Copie `.env.example` para `.env` e configure:

```bash
cp .env.example .env
```

## Desenvolvimento

```bash
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
ruff check src/ tests/
pytest
```

## Deploy

```bash
pip install -e .
sudo cp deploy/systemd/vision-platform-central.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable vision-platform-central
sudo systemctl start vision-platform-central
```

## API

| Endpoint | Método | Descrição |
|---|---|---|
| `/health` | GET | Health check |
| `/api/v1/status` | GET | Status do central |
| `/api/v1/locals` | GET | Locais registrados |
| `/api/v1/observations` | GET | Observações coletadas |
