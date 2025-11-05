# Action-Reaction Platform (AREA)

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15.5-black.svg)](https://nextjs.org/)
[![React Native](https://img.shields.io/badge/React%20Native-0.81-blue.svg)](https://reactnative.dev/)

An automation platform enabling users to create workflows by connecting services through triggers (Actions) and automated responses (Reactions). Similar to IFTTT or Zapier, this platform allows seamless integration between popular services like Gmail, Outlook, GitHub, Discord, and more.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Configuration](#environment-configuration)
  - [Running the Application](#running-the-application)
- [Development](#development)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

The **Action-Reaction Platform** is a full-stack automation solution built with a modern monorepo architecture. It consists of:

- **Backend**: FastAPI-powered REST API with PostgreSQL database
- **Web Client**: Next.js application with React and TailwindCSS
- **Mobile Client**: Expo React Native app for iOS and Android

The platform enables users to:
1. **Authenticate** using email/password or OAuth2 (Google, GitHub, Microsoft)
2. **Connect** third-party services via OAuth2
3. **Create Automations** by linking triggers (Actions) from one service to responses (Reactions) in another
4. **Monitor Executions** with detailed logging and status tracking

### Key Concepts

- **Action**: A trigger event from a service (e.g., "New Email Received" from Gmail)
- **Reaction**: An automated response (e.g., "Send Message" to Discord)
- **AREA**: An automation workflow connecting one or more Actions to Reactions
- **Service Integration**: Modular plugin system for third-party services

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │  Web Client  │    │ Mobile (iOS) │    │Mobile(Android)│     │
│  │  (Next.js)   │    │    (Expo)    │    │    (Expo)    │      │
│  │  Port: 3000  │    │              │    │              │      │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘      │
└─────────┼─────────────────────┼─────────────────────┼───────────┘
          │                     │                     │
          └─────────────────────┴─────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     APPLICATION LAYER                            │
│  ┌────────────────────────────────────────────────────────┐     │
│  │           FastAPI REST API (Port: 8080)                │     │
│  │  ┌─────────────────────────────────────────────────┐   │     │
│  │  │  Authentication │ OAuth2 │ Service Management │   │     │
│  │  │  Area Management │ Execution Engine │ Logging  │   │     │
│  │  └─────────────────────────────────────────────────┘   │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
          │                     │                     │
          ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────────┐    ┌──────────────────┐
│  PostgreSQL   │    │  Plugin System    │    │   Schedulers     │
│   Database    │    │  ┌─────────────┐  │    │  ┌────────────┐  │
│   (Port:5432) │    │  │Gmail Plugin │  │    │  │Time-based  │  │
│               │    │  │Discord      │  │    │  │Gmail Poll  │  │
│               │    │  │GitHub       │  │    │  │Discord Poll│  │
│               │    │  │Outlook      │  │    │  │GitHub Poll │  │
│               │    │  │OpenAI       │  │    │  │Weather Poll│  │
│               │    │  │Weather      │  │    │  │...         │  │
│               │    │  │DeepL        │  │    │  └────────────┘  │
│               │    │  └─────────────┘  │    │                  │
└───────────────┘    └───────────────────┘    └──────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  External Services    │
                    │  ┌─────────────────┐  │
                    │  │ Gmail API       │  │
                    │  │ GitHub API      │  │
                    │  │ Discord API     │  │
                    │  │ Microsoft Graph │  │
                    │  │ OpenWeatherMap  │  │
                    │  │ OpenAI API      │  │
                    │  │ DeepL API       │  │
                    │  └─────────────────┘  │
                    └───────────────────────┘
```

### Service Integration Architecture

The platform uses a modular plugin system where each service integration consists of:

1. **Service Catalog Entry**: Defines available actions and reactions
2. **OAuth Provider** (if needed): Handles authentication flow
3. **Plugin Handlers**: Implement action/reaction logic
4. **Schedulers** (optional): Poll external APIs for events

```
Service Catalog (catalog.py)
      │
      ├─► OAuth Provider (oauth/providers/)
      │        └─► Token Management & Refresh
      │
      ├─► Plugin Handlers (simple_plugins/)
      │        └─► Execution Logic
      │
      └─► Schedulers (simple_plugins/)
               └─► Event Polling (Gmail, Discord, GitHub, etc.)
```

### Data Models

**Core Entities:**

```
User
├── email, hashed_password
├── oauth_identifiers (google_oauth_sub, github_oauth_id, microsoft_oauth_id)
├── is_confirmed, is_admin, is_suspended
└── timestamps (created_at, updated_at, confirmed_at)

ServiceConnection
├── user_id (FK → User)
├── service_name
├── encrypted_access_token, encrypted_refresh_token
├── expires_at
└── timestamps

Area (Automation Workflow)
├── user_id (FK → User)
├── name, enabled
├── trigger_service, trigger_action, trigger_params
├── reaction_service, reaction_action, reaction_params
├── steps[] (for multi-step workflows)
└── timestamps

ExecutionLog
├── area_id (FK → Area)
├── trigger_data, reaction_result
├── status (success, failure)
├── error_message
└── executed_at
```

---

## Features

### 🔐 Authentication & Authorization
- Email/password registration with confirmation flow
- OAuth2 integration (Google, GitHub, Microsoft)
- JWT-based authentication
- Multi-provider login support
- Admin role management

### 🔌 Service Integrations
- **Gmail**: Email triggers and actions (send, mark as read, forward)
- **Outlook**: Microsoft 365 email automation
- **Discord**: Message notifications and bot commands
- **GitHub**: Repository events, issue management
- **Google Calendar**: Event triggers and creation
- **Weather**: OpenWeatherMap conditions monitoring
- **OpenAI**: GPT-powered text generation
- **DeepL**: Translation services
- **Time-based**: Scheduled triggers

### ⚡ Automation Features
- Simple trigger → reaction workflows
- Multi-step automation chains
- Variable substitution (e.g., `{{gmail.subject}}`)
- Conditional execution
- Execution logging and monitoring
- Enable/disable automations

### 📊 Monitoring & Logging
- Detailed execution logs
- User activity tracking
- Error reporting and debugging
- Admin dashboard

---

## Tech Stack

### Backend
| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.11 |
| Framework | FastAPI | 0.104+ |
| Database | PostgreSQL | 15 |
| ORM | SQLAlchemy | 2.0+ |
| Migrations | Alembic | 1.12+ |
| Authentication | JWT, OAuth2 | - |
| Testing | pytest | 7.4+ |

### Frontend (Web)
| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | Next.js | 15.5+ |
| Language | TypeScript | 5.0+ |
| UI Library | React | 19.1+ |
| Styling | TailwindCSS | 4.0+ |
| Components | Radix UI | - |
| State | React Context | - |

### Mobile
| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | Expo | 54.0+ |
| Language | TypeScript | 5.9+ |
| UI Library | React Native | 0.81+ |
| Navigation | React Navigation | 7.0+ |

### Infrastructure
| Component | Technology |
|-----------|-----------|
| Containerization | Docker |
| Orchestration | Docker Compose |
| Build Tool | Makefile |
| Deployment | Railway (planned) |

---

## Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:

- **Docker** (version 20.10+) and **Docker Compose** (version 2.0+)
  ```bash
  docker --version
  docker compose version
  ```

- **Git**
  ```bash
  git --version
  ```

- **Make** (usually pre-installed on Linux/macOS)
  ```bash
  make --version
  ```

- **Node.js** (18+) and **npm** (for mobile development only)
  ```bash
  node --version
  npm --version
  ```

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/EpitechPGE3-2025/G-DEV-500-LYN-5-1-area-8.git
   cd G-DEV-500-LYN-5-1-area-8
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   ```

3. **Configure environment variables** (see [Environment Configuration](#environment-configuration))

### Environment Configuration

Edit the `.env` file with your credentials:

#### Required Configuration

```bash
# Encryption (Generate with: openssl rand -hex 32)
ENCRYPTION_KEY=your_secure_random_encryption_key_here

# JWT Configuration
JWT_SECRET_KEY=your_secure_jwt_secret_here
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_ALGORITHM=HS256

# Email Configuration
EMAIL_SENDER=no-reply@yourdomain.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true

# Frontend URLs
FRONTEND_REDIRECT_URL_WEB=http://localhost:3000
FRONTEND_REDIRECT_URL_MOBILE=areamobile://oauth/callback
NEXT_PUBLIC_API_BASE_URL=http://localhost:8080/api/v1

# Database (default for docker-compose)
DATABASE_URL=postgresql+psycopg://area:area@db:5432/area
```

#### OAuth Service Configuration

**Google (Gmail) Setup:**
1. Go to [Google Cloud Console](https://console.developers.google.com/)
2. Create a new project
3. Enable Gmail API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URI: `http://localhost:8080/api/v1/service-connections/callback/gmail`

```bash
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

**GitHub Setup:**
1. Go to [GitHub Developer Settings](https://github.com/settings/apps)
2. Create new OAuth App
3. Authorization callback URL: `http://localhost:8080/api/v1/service-connections/callback/github`

```bash
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
```

**Discord Setup:**
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create new application
3. Add redirect URI: `http://localhost:8080/api/v1/service-connections/callback/discord`
4. Create bot and copy bot token

```bash
DISCORD_CLIENT_ID=your-discord-client-id
DISCORD_CLIENT_SECRET=your-discord-client-secret
DISCORD_BOT_TOKEN=your-discord-bot-token
```

**Microsoft (Outlook) Setup:**
1. Go to [Azure Portal](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
2. Register new application
3. Add redirect URI: `http://localhost:8080/api/v1/service-connections/callback/outlook`
4. Add API permissions: Mail.Read, Mail.Send, Mail.ReadWrite, offline_access

```bash
MICROSOFT_CLIENT_ID=your-microsoft-client-id
MICROSOFT_CLIENT_SECRET=your-microsoft-client-secret
```

**OpenWeatherMap Setup:**
1. Sign up at [OpenWeatherMap](https://openweathermap.org/api)
2. Generate API key

```bash
OPENWEATHERMAP_API_KEY=your-openweathermap-api-key
```

See `.env.example` for complete configuration options and detailed setup instructions.

### Running the Application

#### Production Mode

Start all services (server, database, web client):

```bash
make up
```

This will:
- Build Docker images for server and web
- Start PostgreSQL database
- Run database migrations
- Start FastAPI server on `http://localhost:8080`
- Start Next.js web client on `http://localhost:3000`

**Verify the setup:**
```bash
# Check service status
make ps

# View logs
make logs

# View logs for specific service
make logs S=server
```

**Access the application:**
- Web UI: http://localhost:3000
- API: http://localhost:8080
- API Documentation: http://localhost:8080/docs
- About endpoint: http://localhost:8080/about.json

#### Development Mode (Hot Reload)

For active development with hot reload:

```bash
make dev
```

This enables:
- Automatic code reloading on file changes
- Volume mounts for live code updates
- Faster iteration cycles

**Other useful commands:**
```bash
make dev-logs          # View development logs
make dev-logs S=server # View server logs only
make dev-restart       # Restart dev services
make dev-down          # Stop development services
```

#### Mobile Development

The mobile app runs locally with Expo (not containerized):

```bash
# Start Expo development server
make expo

# Or start in web mode for testing
make expo-web
```

Scan the QR code with Expo Go app (iOS/Android) to run on your device.

#### Stopping Services

```bash
# Stop all services
make down

# Stop and remove volumes (clean state)
make clean
```

---

## Development

### Common Commands

```bash
# Build specific service
make build S=server
make build S=web

# Restart specific service
make restart S=server

# View logs for specific service
make logs S=server
make logs S=web

# Run backend tests
make test

# Access PostgreSQL directly
docker exec -it g-dev-500-lyn-5-1-area-8-db-1 psql -U area -d area
```

### Development Workflow

1. **Make code changes** in your local environment
2. **For containerized services (server, web):**
   - In dev mode (`make dev`): Changes auto-reload
   - In production mode: Rebuild with `make build S=<service>`
3. **For mobile:** Changes auto-reload via Expo
4. **Run tests** to verify changes:
   ```bash
   make test
   ```
5. **Check logs** for debugging:
   ```bash
   make dev-logs S=server
   ```

### Database Migrations

The application uses Alembic for database schema management.

**Migrations run automatically on startup**, but you can manage them manually:

```bash
# Enter the server container
docker exec -it <container-name> bash

# Create a new migration
alembic revision --autogenerate -m "description of changes"

# Apply migrations
alembic upgrade head

# Rollback one version
alembic downgrade -1

# View migration history
alembic history
```

### Adding New Service Integrations

For detailed instructions on extending the platform with new services, see [HOWTOCONTRIBUTE.md](HOWTOCONTRIBUTE.md).

**Quick overview:**
1. Update service catalog (`apps/server/app/integrations/catalog.py`)
2. Create OAuth provider (if needed)
3. Implement plugin handlers
4. Register handlers in registry
5. Add scheduler for polling (if needed)
6. Write tests

---

## API Documentation

### OpenAPI/Swagger

Interactive API documentation is available at:
- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc
- **OpenAPI JSON**: http://localhost:8080/openapi.json

### Core API Endpoints

#### Authentication

```
POST   /api/v1/auth/register              # Register new user
POST   /api/v1/auth/login                 # Login with email/password
POST   /api/v1/auth/confirm               # Confirm email
GET    /api/v1/auth/resend-confirmation   # Resend confirmation email
```

#### OAuth Authentication

```
GET    /api/v1/oauth/{provider}           # Initiate OAuth flow
GET    /api/v1/oauth/{provider}/callback  # OAuth callback
```

#### User Profile

```
GET    /api/v1/users/me                   # Get current user profile
PATCH  /api/v1/users/me                   # Update profile
POST   /api/v1/users/me/password          # Change password
GET    /api/v1/users/me/connections       # List service connections
```

#### Service Connections

```
POST   /api/v1/service-connections/connect/{provider}        # Connect service
GET    /api/v1/service-connections/callback/{provider}       # OAuth callback
GET    /api/v1/service-connections/connections               # List connections
DELETE /api/v1/service-connections/connections/{id}          # Delete connection
DELETE /api/v1/service-connections/disconnect/{service}      # Disconnect service
POST   /api/v1/service-connections/api-key/{provider}        # Add API key
```

#### Services Catalog

```
GET    /api/v1/services                   # List all services
GET    /api/v1/services/{slug}            # Get service details
GET    /api/v1/services/{slug}/actions    # Get service actions
GET    /api/v1/services/{slug}/reactions  # Get service reactions
```

#### Areas (Automations)

```
POST   /api/v1/areas                      # Create new area
GET    /api/v1/areas                      # List user's areas
GET    /api/v1/areas/{id}                 # Get area details
PATCH  /api/v1/areas/{id}                 # Update area
DELETE /api/v1/areas/{id}                 # Delete area
POST   /api/v1/areas/{id}/enable          # Enable area
POST   /api/v1/areas/{id}/disable         # Disable area
```

#### Execution Logs

```
GET    /api/v1/execution-logs             # List execution logs
GET    /api/v1/execution-logs/{id}        # Get log details
GET    /api/v1/areas/{area_id}/logs       # Get logs for specific area
```

#### System

```
GET    /                                   # Root endpoint
GET    /health                             # Health check
GET    /about.json                         # System information
```

### About.json Response

The `/about.json` endpoint provides system metadata:

```json
{
  "client": {
    "host": "192.168.1.100"
  },
  "server": {
    "current_time": 1730390400,
    "services": [
      {
        "name": "Gmail",
        "actions": [
          { "name": "New Email Received", "description": "..." },
          { "name": "New Email from Sender", "description": "..." }
        ],
        "reactions": [
          { "name": "Send Email", "description": "..." },
          { "name": "Mark as Read", "description": "..." }
        ]
      }
    ]
  }
}
```

---

## Project Structure

```
.
├── apps/
│   ├── server/                 # FastAPI Backend
│   │   ├── alembic/           # Database migrations
│   │   ├── app/
│   │   │   ├── api/           # API routes
│   │   │   │   └── routes/    # Endpoint definitions
│   │   │   ├── cli/           # CLI commands
│   │   │   ├── core/          # Core config & utilities
│   │   │   ├── db/            # Database setup
│   │   │   ├── integrations/  # Service integrations
│   │   │   │   ├── catalog.py # Service definitions
│   │   │   │   ├── oauth/     # OAuth providers
│   │   │   │   └── simple_plugins/  # Plugin handlers & schedulers
│   │   │   ├── models/        # SQLAlchemy models
│   │   │   ├── schemas/       # Pydantic schemas
│   │   │   └── services/      # Business logic
│   │   ├── tests/             # Test suite
│   │   ├── main.py            # Application entrypoint
│   │   ├── requirements.txt   # Python dependencies
│   │   └── Dockerfile         # Server container
│   │
│   ├── web/                   # Next.js Web Client
│   │   ├── public/            # Static assets
│   │   ├── src/
│   │   │   └── app/           # Next.js App Router pages
│   │   ├── package.json       # Node dependencies
│   │   ├── next.config.ts     # Next.js configuration
│   │   └── Dockerfile         # Web container
│   │
│   └── mobile/                # Expo Mobile App
│       ├── src/
│       │   ├── components/    # React Native components
│       │   ├── contexts/      # React contexts
│       │   └── utils/         # Utilities
│       ├── App.tsx            # Main app component
│       └── package.json       # Mobile dependencies
│
├── docs/                      # Documentation
│   ├── architecture.md        # Architecture details
│   ├── product-requirements-document.md
│   ├── project-brief.md
│   └── ui-ux-specs.md
│
├── docker-compose.yml         # Production compose
├── docker-compose.dev.yml     # Development compose
├── Makefile                   # Build & run commands
├── .env.example               # Environment template
├── README.md                  # This file
└── HOWTOCONTRIBUTE.md         # Contribution guide
```

### Key Files

- **`Makefile`**: Orchestrates Docker commands and provides convenient shortcuts
- **`docker-compose.yml`**: Production container configuration
- **`docker-compose.dev.yml`**: Development overrides with hot reload
- **`.env`**: Environment variables (not in repo, create from `.env.example`)
- **`apps/server/main.py`**: FastAPI application setup and startup logic
- **`apps/server/app/integrations/catalog.py`**: Single source of truth for all service definitions
- **`apps/server/app/integrations/simple_plugins/registry.py`**: Maps service/action pairs to handler functions

---

## Testing

### Backend Tests

The backend has comprehensive test coverage using pytest.

**Run all tests:**
```bash
make test
```

**Run tests locally (outside Docker):**
```bash
cd apps/server
pip install -r requirements.txt
pytest
```

**Run specific test file:**
```bash
cd apps/server
pytest tests/test_areas_service.py
```

**Run with coverage report:**
```bash
cd apps/server
pytest --cov=app --cov-report=html
```

### Test Structure

```
apps/server/tests/
├── conftest.py                # Test fixtures & configuration
├── test_auth_schemas.py       # Authentication tests
├── test_areas_service.py      # Area management tests
├── test_area_execution.py     # Execution engine tests
├── test_gmail_plugin.py       # Gmail integration tests
├── test_discord_plugin.py     # Discord integration tests
├── test_github_plugin.py      # GitHub integration tests
├── test_oauth_providers.py    # OAuth flow tests
└── ...                        # Other test files
```

### Writing Tests

Follow existing patterns in the test suite:

```python
import pytest
from app.services.areas import AreaService

def test_create_area(db_session, test_user):
    """Test area creation."""
    service = AreaService(db_session)
    area = service.create_area(
        user_id=test_user.id,
        name="Test Area",
        trigger_service="gmail",
        trigger_action="new_email",
        # ...
    )
    assert area.name == "Test Area"
    assert area.enabled is True
```

---

## Deployment

### Docker Deployment

The application is containerized and ready for deployment to any Docker-compatible platform.

**Build production images:**
```bash
docker compose -f docker-compose.yml build
```

**Run in production mode:**
```bash
docker compose -f docker-compose.yml up -d
```

### Railway Deployment (Planned)

The project is designed for deployment on Railway:

1. Connect GitHub repository to Railway
2. Configure environment variables in Railway dashboard
3. Deploy services:
   - **Server**: FastAPI app
   - **Database**: PostgreSQL
   - **Web**: Next.js app

### Environment Variables for Production

Ensure all production environment variables are set:
- Use strong, unique values for `ENCRYPTION_KEY` and `JWT_SECRET_KEY`
- Configure production URLs for `FRONTEND_REDIRECT_URL_WEB`
- Set up production OAuth credentials with correct callback URLs
- Configure production SMTP settings for emails
- Use production database connection string

### Health Checks

Monitor application health:
```bash
curl http://localhost:8080/health
# Response: {"status": "healthy"}
```

---

## Contributing

We welcome contributions! Please see [HOWTOCONTRIBUTE.md](HOWTOCONTRIBUTE.md) for detailed guidelines on:

- Setting up the development environment
- Adding new service integrations
- Adding actions/reactions to existing services
- Code style and testing requirements
- Submission process

**Quick Start for Contributors:**

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes following the contribution guidelines
4. Write tests for new functionality
5. Ensure all tests pass: `make test`
6. Commit with clear messages: `git commit -m "Add amazing feature"`
7. Push to your fork: `git push origin feature/amazing-feature`
8. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Support

For questions, issues, or feature requests:

- **Issues**: [GitHub Issues](https://github.com/EpitechPGE3-2025/G-DEV-500-LYN-5-1-area-8/issues)
- **Documentation**: See `docs/` directory
- **Contributing**: See [HOWTOCONTRIBUTE.md](HOWTOCONTRIBUTE.md)

---

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Frontend powered by [Next.js](https://nextjs.org/) and [React](https://react.dev/)
- Mobile app built with [Expo](https://expo.dev/) and [React Native](https://reactnative.dev/)
- UI components from [Radix UI](https://www.radix-ui.com/)
- Styled with [TailwindCSS](https://tailwindcss.com/)
