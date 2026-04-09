# Azure Monitoring Solution

A fully managed Azure-native website monitoring platform with login validation, multi-page checks, and real-time alerting.

## Architecture

```
Azure Function (Timer - every 5 min)
        ↓
Triggers Monitoring Jobs
        ↓
Azure Container Apps (Playwright engine)
        ↓
Results → FastAPI (App Service)
        ↓
Store → Azure MySQL Flexible Server
        ↓
Alerts → Email (Azure Communication Services) / Teams Webhook
```

## Azure Services

| Component | Azure Service |
|---|---|
| API + Dashboard | App Service (Linux) |
| Monitoring Engine | Container Apps (Playwright) |
| Database | MySQL Flexible Server |
| Scheduler | Azure Functions (Timer Trigger) |
| Secrets | Key Vault |
| Notifications | Communication Services + Teams |
| Observability | Application Insights |

## Features

- **Uptime Monitoring** — HTTP/page load checks with response time tracking
- **Login Validation** — Automated login flows using Playwright headless browser
- **Multi-Page Validation** — Navigate multiple pages after login, validate elements and text
- **Alert System** — Email and Teams notifications after consecutive failures
- **Dashboard** — Real-time stats, response time charts, alert management
- **Encrypted Credentials** — Site login credentials encrypted at rest (Fernet)

## Quick Start (Local Development)

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for frontend development)
- Python 3.12+ (for backend development)

### Run with Docker Compose

```bash
docker-compose up --build
```

This starts:
- **MySQL** on port 3306
- **Backend API** on http://localhost:8000 (Swagger: http://localhost:8000/api/docs)
- **Monitoring Engine** on http://localhost:8001
- **Frontend** on http://localhost:3000

### First-Time Setup

1. Register a user:
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin123", "full_name": "Admin"}'
```

2. Open http://localhost:3000 and sign in

3. Add sites to monitor via the dashboard

## Project Structure

```
├── backend/              # FastAPI backend (App Service)
│   ├── app/
│   │   ├── core/         # Config, database, security
│   │   ├── models/       # SQLAlchemy models + Pydantic schemas
│   │   ├── routes/       # API endpoints (auth, sites, monitoring)
│   │   └── services/     # Alert logic, notifications
│   ├── alembic/          # Database migrations
│   └── Dockerfile
├── frontend/             # React + Vite dashboard
│   ├── src/
│   │   ├── pages/        # Dashboard, Sites, Alerts, etc.
│   │   ├── services/     # API client
│   │   └── styles/       # CSS (fldata.com color scheme)
│   └── Dockerfile
├── monitoring-engine/    # Playwright-based checker (Container Apps)
│   ├── app/
│   │   ├── checks.py     # Uptime, login, multi-page checks
│   │   └── main.py       # FastAPI endpoint for running checks
│   └── Dockerfile
├── scheduler/            # Azure Functions timer trigger
│   └── function_app.py
├── infrastructure/       # Azure Bicep IaC
│   └── main.bicep
└── docker-compose.yml    # Local development
```

## Deploy to Azure

### 1. Create Resources (Bicep)

```bash
az group create --name monitoring-rg --location eastus

az deployment group create \
  --resource-group monitoring-rg \
  --template-file infrastructure/main.bicep \
  --parameters prefix=monitor mysqlAdminPassword=YourSecurePassword123!
```

### 2. Build & Push Container Images

```bash
az acr create --name monitoracr --resource-group monitoring-rg --sku Basic
az acr login --name monitoracr

docker build -t monitoracr.azurecr.io/backend:latest ./backend
docker build -t monitoracr.azurecr.io/monitoring-engine:latest ./monitoring-engine
docker build -t monitoracr.azurecr.io/frontend:latest ./frontend

docker push monitoracr.azurecr.io/backend:latest
docker push monitoracr.azurecr.io/monitoring-engine:latest
docker push monitoracr.azurecr.io/frontend:latest
```

### 3. Deploy Azure Function (Scheduler)

```bash
cd scheduler
func azure functionapp publish monitor-scheduler
```

### 4. Configure Secrets in Key Vault

```bash
az keyvault secret set --vault-name monitor-kv --name DB-PASSWORD --value "YourPassword"
az keyvault secret set --vault-name monitor-kv --name SECRET-KEY --value "your-jwt-secret"
az keyvault secret set --vault-name monitor-kv --name ENCRYPTION-KEY --value "your-32-byte-key"
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Register user |
| POST | `/api/v1/auth/login` | Login (returns JWT) |
| GET | `/api/v1/auth/me` | Current user info |
| GET | `/api/v1/sites/` | List all sites |
| POST | `/api/v1/sites/` | Create site |
| PUT | `/api/v1/sites/{id}` | Update site |
| DELETE | `/api/v1/sites/{id}` | Delete site |
| POST | `/api/v1/monitoring/results` | Submit check result |
| GET | `/api/v1/monitoring/results/{site_id}` | Get results for site |
| GET | `/api/v1/monitoring/dashboard` | Dashboard stats |
| GET | `/api/v1/monitoring/alerts` | List alerts |
| POST | `/api/v1/monitoring/alerts/{id}/resolve` | Resolve alert |

## Environment Variables

See `backend/.env.example` for the full list of configuration options.

## Design

UI follows the [Frontline Data Solutions](https://www.fldata.com) color scheme:
- Primary Blue: `#007aff`
- Navy: `#001e3f`
- Orange Accent: `#fc5c1d`
- Font: System UI stack (-apple-system, Segoe UI, Roboto)
