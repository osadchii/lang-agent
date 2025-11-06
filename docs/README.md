# Project Documentation

Welcome to the Greek Language Learning Platform documentation. This directory contains comprehensive documentation for developers, operations, and architecture.

## Quick Navigation

### Architecture
- **[Agents](architecture/agents.md)** — Development practices, AI agent guidelines, and project workflow
- **[Logging Overview](architecture/logging-overview.md)** — System-wide logging architecture and best practices
- **[Architecture Decision Records (ADRs)](adr/)** — Historical architectural decisions and their context
  - [0001 - Telegram Runtime](adr/0001-telegram-runtime.md)
  - [0002 - Telegram WebApp User Context](adr/0002-telegram-webapp-user-context.md)

### Setup & Configuration Guides
- **[Telegram Webhook Setup](guides/telegram-webhook-setup.md)** — Configure Telegram bot webhooks
- **[Telegram Mini App Testing](guides/telegram-miniapp-testing.md)** — Test the mini app locally and in Telegram
- **[Loki Setup](guides/loki-setup.md)** — Deploy and configure Loki for log aggregation
- **[Quick Start Loki](guides/quick-start-loki.md)** — Fast-track Loki deployment guide
- **[Grafana Queries](guides/grafana-queries.md)** — Pre-built queries for monitoring and debugging

### Development
- **[Logger Factory](development/logger-factory.md)** — How to use the centralized logging system in code

### Security
- **[Security Guidelines](SECURITY.md)** — Authentication, authorization, and security best practices
- **[Migration Security](MIGRATION_SECURITY.md)** — Security considerations during migrations

## Contributing

When adding new documentation:
1. Place files in the appropriate subdirectory (`architecture/`, `guides/`, `development/`)
2. Update this README with a link to your new document
3. Use clear, descriptive filenames in kebab-case
4. Write in English
5. Include code examples where applicable

## Documentation Standards

- **Language**: All documentation must be in English
- **Format**: Use GitHub-flavored Markdown
- **Structure**: Use clear headings and sections
- **Code blocks**: Specify language for syntax highlighting
- **Links**: Use relative links for internal documentation
- **Updates**: Keep documentation in sync with code changes

## Related Documentation

- **[Main README](../README.md)** — Project overview and quick start guide
- **[Backend README](../apps/backend/README.md)** — Backend-specific documentation
- **[Frontend README](../apps/frontend/README.md)** — Frontend-specific documentation
- **[Claude Guidelines](../CLAUDE.md)** — AI assistant development guidelines
