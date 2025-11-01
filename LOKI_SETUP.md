# Loki Logging Setup

## Overview

Приложение поддерживает отправку логов в Grafana Loki для централизованного мониторинга.

## Configuration

### Backend Setup

1. Убедитесь, что у вас есть доступ к Loki endpoint
2. Добавьте в `.env` файл:

```env
# Loki endpoint URL
LOKI_URL=http://loki:3100/loki/api/v1/push

# Optional: custom labels for filtering in Grafana
LOKI_LABELS=service=backend,version=1.0
```

### Default Labels

Приложение автоматически добавляет следующие labels:
- `application`: `lang-agent`
- `environment`: значение из `APP_ENV` (production/development)

### Custom Labels

Вы можете добавить дополнительные labels через `LOKI_LABELS`:

```env
LOKI_LABELS=team=backend,service=api,version=1.0.0
```

Формат: `key1=value1,key2=value2`

## Docker Network Setup

Если Loki работает в Docker:

1. Убедитесь, что контейнеры находятся в одной сети:

```yaml
# docker-compose.yml
services:
  backend:
    networks:
      - web  # Traefik network
      - backend
      - monitoring  # Loki network
```

2. Используйте имя сервиса в LOKI_URL:

```env
LOKI_URL=http://loki:3100/loki/api/v1/push
```

## Grafana Configuration

### Adding Loki Data Source

1. В Grafana перейдите в **Configuration → Data Sources**
2. Выберите **Add data source → Loki**
3. Укажите URL: `http://loki:3100`
4. Сохраните и протестируйте

### Viewing Logs

1. Перейдите в **Explore**
2. Выберите Loki data source
3. Используйте LogQL запросы:

```logql
# Все логи приложения
{application="lang-agent"}

# Только ошибки
{application="lang-agent"} |= "ERROR"

# Логи production среды
{application="lang-agent", environment="production"}

# С фильтрацией по тексту
{application="lang-agent"} |= "Telegram"
```

### Example Dashboard Queries

**Error rate:**
```logql
sum(rate({application="lang-agent"} |= "ERROR" [5m])) by (environment)
```

**Log volume by level:**
```logql
sum by(level) (count_over_time({application="lang-agent"}[1m]))
```

## Testing

Проверьте, что логи отправляются:

```bash
# Посмотрите логи контейнера
docker logs backend 2>&1 | grep "Loki logging enabled"

# Должны увидеть:
# [INFO] backend.logging: Loki logging enabled (url=http://loki:3100/loki/api/v1/push)
```

## Troubleshooting

### Логи не появляются в Grafana

1. Проверьте, что `LOKI_URL` правильно настроен
2. Убедитесь, что контейнеры могут общаться между собой
3. Проверьте логи приложения на наличие ошибок:
   ```bash
   docker logs backend 2>&1 | grep -i loki
   ```

### Connection errors

Если видите ошибки подключения:
- Проверьте сетевые настройки Docker
- Убедитесь, что Loki доступен на указанном порту
- Попробуйте использовать IP адрес вместо имени хоста

### Import error

Если видите `python-logging-loki is not installed`:
```bash
pip install python-logging-loki
# или пересоберите Docker image
docker-compose build backend
```

## Disabling Loki

Чтобы отключить отправку логов в Loki, просто оставьте `LOKI_URL` пустым или удалите из `.env`:

```env
LOKI_URL=
```

Логи продолжат выводиться в console (stdout).
