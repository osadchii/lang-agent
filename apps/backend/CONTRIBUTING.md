# Contributing Guidelines

## Development Workflow

### Before Starting Work

1. Ensure you're on the latest code:
   ```bash
   git pull origin main
   ```

2. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

### Making Changes

1. **Write or modify code** following project conventions
2. **Update or add tests** for any new functionality or bug fixes
3. **Run migrations** if you modified database models:
   ```bash
   source .venv/bin/activate  # or ../../.venv/bin/activate from project root
   cd apps/backend
   python -m backend.cli migrate
   ```

### Testing Requirements

**CRITICAL**: Always run tests after making changes, especially when:
- Modifying database models or migrations
- Changing business logic in services
- Adding new features
- Fixing bugs

```bash
source .venv/bin/activate  # or ../../.venv/bin/activate from project root
cd apps/backend
python -m pytest tests/ -v
```

All tests must pass before submitting a pull request.

### Code Quality

- Follow existing code style and patterns
- Add docstrings to public functions and classes
- Keep functions focused and single-purpose
- Use type hints for function signatures
- Handle errors appropriately

### Database Changes

When adding or modifying database models:

1. Update the model in `src/backend/services/storage/models.py`
2. Create a migration file in `migrations/versions/`
3. **Use `batch_alter_table` for SQLite compatibility** when altering tables:
   ```python
   def upgrade() -> None:
       with op.batch_alter_table("table_name", schema=None) as batch_op:
           batch_op.add_column(...)
   ```
4. Test the migration with both SQLite (tests) and PostgreSQL (production)
5. Add tests that verify the new schema works correctly

### Pull Request Checklist

Before submitting a PR, ensure:

- [ ] All tests pass (`pytest tests/ -v`)
- [ ] New features have corresponding tests
- [ ] Database migrations are included if models changed
- [ ] Code follows project style and conventions
- [ ] Commit messages are clear and descriptive

## Running Tests

### Run all tests:
```bash
pytest tests/ -v
```

### Run specific test file:
```bash
pytest tests/test_flashcards.py -v
```

### Run specific test:
```bash
pytest tests/test_flashcards.py::test_add_words_creates_cards_and_links_user -v
```

### Run with coverage:
```bash
pytest tests/ --cov=backend --cov-report=html
```

## Common Issues

### Tests fail with SQLAlchemy relationship errors
- Ensure all relationships specify `foreign_keys` when there are multiple foreign keys between tables
- Use `viewonly=True` for relationships that shouldn't be used for writes

### Migration fails with "No support for ALTER of constraints in SQLite"
- Use `batch_alter_table` context manager for all table alterations
- See `migrations/versions/0003_add_active_deck.py` for an example

### Import errors when running tests
- Ensure you're in the correct directory and venv is activated
- Install the package in editable mode: `pip install -e .`
