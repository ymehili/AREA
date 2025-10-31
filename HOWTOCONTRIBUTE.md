# How to Contribute to the Action-Reaction Platform

## Table of Contents

1. [Introduction](#introduction)
2. [Project Setup](#project-setup)
3. [Adding New Services](#adding-new-services)
4. [Adding Actions/Reactions to Existing Services](#adding-actionsreactions-to-existing-services)
5. [Adding Other Backend Features](#adding-other-backend-features)
6. [Frontend Extensions](#frontend-extensions)
7. [Testing](#testing)
8. [Submission Guidelines](#submission-guidelines)

---

## Introduction

Welcome to the **Action-Reaction** platform! This is an automation platform (similar to IFTTT/Zapier) that enables users to create workflows by connecting services through triggers (Actions) and automated responses (Reactions).

### Contribution Philosophy

- **Modularity**: Each service integration is self-contained and independent
- **Consistency**: Follow established patterns in the codebase
- **Testing**: All new features must include tests (80% coverage requirement)
- **Documentation**: Update relevant documentation files

---

## Project Setup

### Prerequisites

- **Docker** and **Docker Compose**
- **Git**

### Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/EpitechPGE3-2025/G-DEV-500-LYN-5-1-area-8.git
   cd G-DEV-500-LYN-5-1-area-8
   ```

2. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your OAuth credentials and API keys
   ```

3. Start development:
   ```bash
   make dev
   ```

4. Verify setup:
   ```bash
   curl http://localhost:8080/about.json
   ```

### Common Make Commands

- `make dev` — Start services with hot reload
- `make dev-down` — Stop development services
- `make dev-logs` — View logs (use `S=server` or `S=web` to filter)
- `make test` — Run backend tests
- `make expo` — Start Expo for mobile app

---

## Adding New Services

### Architecture Overview

Here's how the service integration system works:

```
┌─────────────────────────────────────────────────────────────────┐
│                        SERVICE CATALOG                          │
│                  (catalog.py - Single Source)                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │  Service 1 │  │  Service 2 │  │  Service 3 │  ...           │
│  │  - Actions │  │  - Actions │  │  - Actions │                │
│  │  - Reactions│ │  - Reactions│ │  - Reactions│               │
│  └────────────┘  └────────────┘  └────────────┘                │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ├────────────────────┼────────────────────┘
         ▼                    ▼
┌──────────────────┐  ┌──────────────────┐
│  /about.json     │  │   Plugin System  │
│  (Auto-exposed)  │  │   (Handlers)     │
└──────────────────┘  └──────────────────┘
         │                    │
         ▼                    ▼
┌──────────────────┐  ┌──────────────────┐
│   Web/Mobile UI  │  │  Execution Engine│
│  (Discovers      │  │  (Runs Areas)    │
│   Services)      │  │                  │
└──────────────────┘  └──────────────────┘

Flow: User creates Area → Trigger occurs → Handler executes → Result logged
```

**Key Components:**
1. **Service Catalog**: Defines all available services, actions, and reactions
2. **OAuth Providers**: Handle authentication for services requiring OAuth
3. **Plugin Handlers**: Execute the actual logic (send email, create issue, etc.)
4. **Schedulers**: Poll external services for events (optional)
5. **Registry**: Maps service/action pairs to handler functions

---

To add a new service integration (e.g., Slack, Twitter, etc.), follow these steps:

### 1. Update Service Catalog

**File**: `apps/server/app/integrations/catalog.py`

Add your service to the `SERVICE_CATALOG` tuple with:
- **slug**: Unique identifier (lowercase, no spaces)
- **name**: Display name
- **description**: Brief service description
- **actions**: Tuple of triggers (things that happen in the service)
- **reactions**: Tuple of responses (things your automation does)

Each action/reaction needs:
- **key**: Unique identifier within the service
- **name**: Display name
- **description**: What it does
- **params**: Input fields (optional)
- **outputs**: Variables the action produces (optional, actions only)

Refer to existing services in `catalog.py` for examples.

### 2. Create OAuth Provider (if needed)

If your service requires OAuth authentication:

**File**: `apps/server/app/integrations/oauth/providers/<service>.py`

Create a provider class inheriting from `OAuth2Provider` and implement:
- `exchange_code()`: Exchange authorization code for access token
- `refresh_token()`: Refresh expired tokens
- `get_user_info()`: Fetch user profile

**Update**: `apps/server/app/integrations/oauth/factory.py`
- Add provider to `_providers` dict
- Add configuration to `_get_provider_config()`

**Update**: `apps/server/app/core/config.py`
- Add client_id and client_secret settings

**Update**: `.env.example`
- Document required environment variables with setup instructions

### 3. Implement Plugin Handlers

**File**: `apps/server/app/integrations/simple_plugins/<service>_plugin.py`

Create handler functions for your reactions (and some actions if needed).

**Handler Signatures**:
```python
# Synchronous handler
def handler_name(area: Area, params: dict, event: dict) -> None:
    pass

# Asynchronous handler (for I/O operations)
async def handler_name(area: Area, params: dict, event: dict) -> None:
    pass

# Handler with database access
def handler_name(area: Area, params: dict, event: dict, db: Session) -> None:
    pass
```

**Key Points**:
- Use `async def` for handlers making HTTP requests or DB queries
- Get OAuth tokens using helper functions (see existing plugins)
- Always log important events and errors
- Validate required parameters early
- Handle exceptions gracefully

### 4. Register Handlers

**File**: `apps/server/app/integrations/simple_plugins/registry.py`

In `_register_default_handlers()`, import and register your handlers:
```python
from app.integrations.simple_plugins.myservice_plugin import my_handler
self._handlers[("myservice", "action_key")] = my_handler
```

### 5. Implement Scheduler (for polling actions)

If your service needs to poll for events:

**File**: `apps/server/app/integrations/simple_plugins/<service>_scheduler.py`

**Sequence Diagram for Scheduled Actions:**
```
┌─────────┐     ┌──────────┐     ┌─────────┐     ┌──────────┐
│Scheduler│     │  Service │     │ Handler │     │Execution │
│  Task   │     │   API    │     │Registry │     │  Engine  │
└────┬────┘     └────┬─────┘     └────┬────┘     └────┬─────┘
     │               │                 │                │
     │ Poll every N  │                 │                │
     │ seconds       │                 │                │
     ├──────────────>│                 │                │
     │ Get new events│                 │                │
     │<──────────────┤                 │                │
     │               │                 │                │
     │ Event found!  │                 │                │
     ├───────────────┴─────────────────┼───────────────>│
     │          Trigger Area            │     Execute    │
     │                                  │     reactions  │
     │                                  │<───────────────┤
     │                                  │  Get handler   │
     │                                  ├───────────────>│
     │                                  │  Run handler   │
     │                                  │<───────────────┤
     │                                  │   Log result   │
```

Create:
- `_poll_events()`: Background task that polls the service
- `start_<service>_scheduler()`: Start the background task
- `stop_<service>_scheduler()`: Stop the background task
- `is_<service>_scheduler_running()`: Check if running

**Update**: `apps/server/main.py`
- Import scheduler functions
- Call `start_<service>_scheduler()` in startup section
- Call `stop_<service>_scheduler()` in shutdown section

Refer to `gmail_scheduler.py`, `discord_scheduler.py`, or other existing schedulers for patterns.

### 6. Database Migration (if needed)

If you need to store service-specific data:

```bash
cd apps/server
alembic revision --autogenerate -m "add_service_integration_fields"
```

**Important**: Review the auto-generated migration file in `alembic/versions/` before applying. Alembic may not detect all changes correctly.

```bash
alembic upgrade head
```

### 7. Testing

Create test file: `apps/server/tests/test_<service>_plugin.py`

Write tests for handler functions, error handling, OAuth token retrieval, and API interactions. See the [Testing](#testing) section for details.

---

## Adding Actions/Reactions to Existing Services

To add new actions or reactions to an existing service:

### 1. Update Service Catalog

In `apps/server/app/integrations/catalog.py`, find the existing service and add your new `AutomationOption` to the `actions` or `reactions` tuple.

### 2. Implement Handler

Add the handler function to the existing plugin file:
`apps/server/app/integrations/simple_plugins/<service>_plugin.py`

### 3. Register Handler

In `apps/server/app/integrations/simple_plugins/registry.py`, add:
```python
self._handlers[("service", "new_action_key")] = new_handler
```

### 4. Test

Add tests to the existing test file:
`apps/server/tests/test_<service>_plugin.py`

---

## Adding Other Backend Features

### Adding API Endpoints

1. Create/modify route file in `apps/server/app/api/routes/`
2. Create Pydantic schemas in `apps/server/app/schemas/`
3. Register router in `apps/server/main.py` (if new file)
4. Add tests in `apps/server/tests/api/`

### Adding Business Logic Services

1. Create service file in `apps/server/app/services/`
2. Use in API routes via dependency injection
3. Add tests in `apps/server/tests/`

### Adding Database Models

1. Create model in `apps/server/app/models/`
2. Create Pydantic schemas in `apps/server/app/schemas/`
3. Import model in `apps/server/app/models/__init__.py`
4. Create migration: `alembic revision --autogenerate -m "description"`
5. Apply migration: `alembic upgrade head`
6. Create service functions in `apps/server/app/services/`
7. Add API endpoints if needed
8. Write tests

---

## Frontend Extensions

The web and mobile frontends automatically discover services, actions, and reactions from the `/about.json` endpoint. When you add a service to the catalog, it will appear in the UI without additional frontend code.

---

## Testing

### Backend Testing

**Unit Tests**: Test individual functions in isolation
**Integration Tests**: Test full flows including database and API

**Running Tests**:
```bash
make test
```

The project requires 80% test coverage. Test fixtures include `test_user`, `test_area`, `db_session`, `client`, `auth_headers` - see `apps/server/tests/conftest.py`.

### Manual Testing Checklist

When adding a new service:
- [ ] Service appears in `/about.json`
- [ ] OAuth connection works
- [ ] Service appears in web/mobile connections page
- [ ] Actions/reactions work in automation builder
- [ ] Variables from actions work in reactions
- [ ] Automation executes successfully
- [ ] Execution logs created
- [ ] Error handling works
- [ ] Token refresh works (OAuth services)

---

## Submission Guidelines

### Branch Naming

```
<type>/<short-description>

Types: feat, fix, docs, refactor, test, chore

Examples:
- feat/add-twitter-integration
- fix/gmail-token-refresh
- docs/update-contribution-guide
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

Example:
feat(integrations): add Twitter service integration

- Implement OAuth provider
- Add tweet reaction handler
- Update service catalog

Closes #123
```

### Pull Request Process

1. Create feature branch from `main`
2. Make changes following patterns in this guide
3. Write tests (80% coverage required)
4. Update documentation:
   - This file if you introduce new patterns
   - `README.md` if user-facing features change
   - `.env.example` for new environment variables
5. Run tests:
   ```bash
   make test
   ```
6. Commit with conventional commit messages
7. Push and open PR with:
   - Clear description
   - Screenshots for UI changes
   - Checklist of completed items

### PR Review Checklist

Reviewers check:
- [ ] Code follows project structure and patterns
- [ ] All tests pass with 80%+ coverage
- [ ] Documentation updated
- [ ] No secrets in code
- [ ] Security best practices followed
- [ ] Environment variables in `.env.example`

---

## Best Practices

### Security

- **Never commit secrets**: Use `.env` for all API keys and tokens
- **Encrypt sensitive data**: Use `app.core.encryption.encrypt_token()` for tokens at rest
- **Validate input**: Use Pydantic schemas
- **Sanitize logs**: Never log tokens or sensitive data

### Code Quality

- **Type hints**: Always use type hints for better IDE support
- **Async for I/O**: Use `async def` for HTTP requests and external API calls
- **Small functions**: Each function should do one thing
- **DRY principle**: Extract common patterns into utilities
- **Error handling**: Use specific exceptions with meaningful messages
- **Logging**: Use structured logging with context (area_id, user_id, etc.)

### Performance

- **Pagination**: Implement for endpoints returning lists
- **Database queries**: Use eager loading to avoid N+1 queries
- **Caching**: Consider caching frequently accessed data
- **Timeouts**: Always set timeouts for external API calls

### Frontend Accessibility

- Use semantic HTML
- Add ARIA labels for icon-only buttons
- Ensure keyboard navigation works
- Follow WCAG 2.1 AA guidelines (4.5:1 contrast ratio)

---

## Additional Resources

- **Architecture**: `docs/architecture.md`
- **Product Requirements**: `docs/product-requirements-document.md`
- **FastAPI**: https://fastapi.tiangolo.com/
- **SQLAlchemy**: https://docs.sqlalchemy.org/
- **Alembic**: https://alembic.sqlalchemy.org/
- **Next.js**: https://nextjs.org/docs
- **React Native**: https://reactnative.dev/
- **Expo**: https://docs.expo.dev/

---

## Getting Help

- **GitHub Issues**: Report bugs or request features
- **GitHub Discussions**: Ask questions and share ideas
- **Pull Request Comments**: Get feedback on contributions

---

Thank you for contributing! 🚀

