# Copilot Instructions for Clean Python Project Structure

## Overview
You are working on a production-grade Python project following clean architecture principles. Always maintain the established patterns and boundaries.

## Core Principles

### 1. Architecture Boundaries
- **Domain Layer** (`src/my_project/domain/`): Pure business logic, no external dependencies
- **Application Layer** (`src/my_project/application/`): Use cases, orchestration, protocols/interfaces
- **Infrastructure Layer** (`src/my_project/infrastructure/`): External integrations (DB, HTTP, filesystem)
- **NEVER** import infrastructure code from domain layer

### 2. Package Structure Rules
- **Always use `src/` layout**: All imports must work from `src/` directory
- **Package-first**: Think in terms of packages, not standalone scripts
- **Tests mirror source**: `tests/unit/test_*.py` mirrors `src/my_project/*/`
- **Explicit imports**: Use absolute imports from package root

### 3. Code Quality Gates
- **Type hints required**: All public APIs must be fully typed
- **Linting**: Code must pass ruff checks (formatting + linting)
- **Type checking**: Code must pass mypy/pyright validation
- **Tests required**: New features need corresponding tests

## File Placement Guidelines

### New Domain Logic
```python
# src/my_project/domain/new_feature.py
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class NewEntity:
    id: int
    name: str

def validate_business_rule(entity: NewEntity) -> bool:
    """Pure function, no side effects."""
    return len(entity.name) > 0
```

### New Application Service
```python
# src/my_project/application/services.py
from my_project.application.ports import Repository
from my_project.domain.models import Entity

class EntityService:
    def __init__(self, repo: Repository) -> None:
        self.repo = repo

    def create_entity(self, name: str) -> Entity:
        # Orchestration logic here
        entity = Entity(id=self.repo.next_id(), name=name)
        return self.repo.save(entity)
```

### New Infrastructure Implementation
```python
# src/my_project/infrastructure/db/sqlite_repo.py
import sqlite3
from my_project.application.ports import Repository
from my_project.domain.models import Entity

class SQLiteRepository(Repository):
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def save(self, entity: Entity) -> Entity:
        # Infrastructure details here
        with sqlite3.connect(self.db_path) as conn:
            # ... implementation
            pass
        return entity
```

### New Tests
```python
# tests/unit/test_domain_new_feature.py
import pytest
from my_project.domain.new_feature import validate_business_rule, NewEntity

def test_business_rule_validation():
    valid_entity = NewEntity(id=1, name="test")
    invalid_entity = NewEntity(id=2, name="")

    assert validate_business_rule(valid_entity) is True
    assert validate_business_rule(invalid_entity) is False
```

## Import Patterns

### ✅ Correct Imports
```python
# From domain layer
from my_project.domain.models import User
from my_project.domain.rules import validate_user

# From application layer
from my_project.application.services import UserService
from my_project.application.ports import UserRepository

# From infrastructure layer
from my_project.infrastructure.db.sqlite_repo import SQLiteUserRepository
```

### ❌ Incorrect Imports
```python
# Don't import infrastructure from domain
from my_project.infrastructure.db.sqlite_repo import SQLiteUserRepository  # WRONG in domain!

# Don't use relative imports
from ..domain.models import User  # WRONG - use absolute

# Don't import from tests or scripts
from tests.conftest import test_user  # WRONG in source code
```

## Configuration Handling

### Settings Pattern
```python
# src/my_project/config/settings.py
from pydantic import BaseSettings

class AppSettings(BaseSettings):
    db_url: str = "sqlite:///data/app.db"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = AppSettings()
```

### Usage in Application Code
```python
# src/my_project/application/services.py
from my_project.config.settings import settings

class SomeService:
    def __init__(self) -> None:
        self.db_url = settings.db_url
```

## Entry Points

### Console Script (CLI)
```python
# src/my_project/cli.py
import typer
from my_project.config.settings import settings
from my_project.application.services import MainService

app = typer.Typer()

@app.command()
def run():
    service = MainService()
    service.execute()

if __name__ == "__main__":
    app()
```

### Service Entry Point
```python
# src/my_project/main.py
import uvicorn
from my_project.config.settings import settings

if __name__ == "__main__":
    uvicorn.run(
        "my_project.infrastructure.http.api:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
```

## Testing Patterns

### Unit Tests Structure
```
tests/
├── conftest.py              # Shared fixtures
├── unit/
│   ├── domain/             # Mirror src structure
│   ├── application/
│   └── infrastructure/
└── integration/            # End-to-end tests
```

### Test Fixtures
```python
# tests/conftest.py
import pytest
from my_project.infrastructure.db.sqlite_repo import SQLiteRepository

@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test.db"
    return SQLiteRepository(str(db_path))

@pytest.fixture
def user_service(temp_db):
    from my_project.application.services import UserService
    return UserService(temp_db)
```

### Mocking External Dependencies
```python
# tests/unit/application/test_services.py
from unittest.mock import Mock
import pytest

def test_user_creation(user_service):
    # Service under test
    user = user_service.create_user("test@example.com")

    assert user.email == "test@example.com"
    assert user.id is not None
```

## Code Style Guidelines

### Type Hints
```python
# ✅ Good
def process_users(users: list[User]) -> list[ProcessedUser]:
    pass

# ❌ Bad
def process_users(users):
    pass
```

### Error Handling
```python
# ✅ Domain errors
class DomainError(Exception):
    pass

# ✅ Application layer catches infrastructure errors
try:
    self.repo.save(entity)
except InfrastructureError as e:
    raise DomainError("Save failed") from e
```

### Naming Conventions
- **Classes**: PascalCase
- **Functions/Methods**: snake_case
- **Constants**: UPPER_SNAKE_CASE
- **Modules**: snake_case
- **Tests**: test_*.py, test_* functions

## Common Patterns to Follow

### Dependency Injection
```python
# ✅ Constructor injection
class OrderService:
    def __init__(self, repo: OrderRepository, payment: PaymentService) -> None:
        self.repo = repo
        self.payment = payment
```

### Protocol-Based Design
```python
# src/my_project/application/ports.py
from typing import Protocol

class EmailSender(Protocol):
    def send(self, to: str, subject: str, body: str) -> None:
        ...

# Implementation in infrastructure
class SMTPEmailSender:
    def send(self, to: str, subject: str, body: str) -> None:
        # SMTP implementation
        pass
```

### Structured Logging
```python
# src/my_project/observability/logging.py
import structlog

logger = structlog.get_logger()

# Usage
logger.info("user_created", user_id=user.id, email=user.email)
```

## When Adding New Features

1. **Start with domain**: Define the business logic first
2. **Add application layer**: Define use cases and interfaces
3. **Implement infrastructure**: Add concrete implementations
4. **Write tests**: Unit tests for each layer
5. **Update configuration**: Add any new settings
6. **Add CLI commands**: If user-facing functionality

## Refactoring Existing Code

- **Maintain boundaries**: Don't break architectural layers
- **Update tests**: Any refactoring requires test updates
- **Type safety**: Improve type hints when refactoring
- **Documentation**: Update docstrings and comments

## Performance Considerations

- **Lazy imports**: Use imports inside functions for optional dependencies
- **Async/await**: Use async patterns for I/O operations
- **Caching**: Consider caching layers in application services
- **Profiling**: Add observability for performance monitoring

Remember: This is a production system. Prioritize maintainability, testability, and clear boundaries over short-term convenience.</content>
<parameter name="filePath">/Users/andrei/projects/freestyle-challenge/.cursor/copilot-instructions.md