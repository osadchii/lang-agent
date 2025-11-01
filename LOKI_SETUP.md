# Loki Logging Setup

## Quick Start

1. **Добавьте в `.env`:**
   ```env
   LOKI_URL=http://loki:3100/loki/api/v1/push
   ```

2. **Перезапустите backend:**
   ```bash
   docker-compose restart backend
   ```

3. **Проверьте что работает:**
   ```bash
   docker logs backend 2>&1 | grep "Loki logging enabled"
   ```

4. **В Grafana Explore используйте:**
   ```logql
   {job="lang-agent"}
   ```

## Overview

Приложение поддерживает отправку логов в Grafana Loki для централизованного мониторинга.

**LOKI_LABELS не обязательны!** По умолчанию автоматически добавляются:
- `job="lang-agent"`
- `application="lang-agent"`
- `environment="production"` (из APP_ENV)
- `host="<container-name>"`

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
# ОСНОВНЫЕ LABELS:
# - job="lang-agent" (всегда добавляется автоматически)
# - application="lang-agent" (если задан в env)
# - environment="production" (из APP_ENV)
# - host="hostname" (имя контейнера)

# Все логи приложения (используйте job label)
{job="lang-agent"}

# Или по application
{application="lang-agent"}

# Только ошибки (ищите по тексту)
{job="lang-agent"} |= "ERROR"

# Логи production среды
{job="lang-agent", environment="production"}

# Telegram бот логи
{job="lang-agent"} |= "Telegram"
{job="lang-agent"} |~ "aiogram|Telegram"

# FastAPI логи
{job="lang-agent"} |= "uvicorn"

# Конкретные эндпоинты
{job="lang-agent"} |= "POST /api/"
{job="lang-agent"} |= "GET /health"

# По уровню логирования
{job="lang-agent"} |= "[ERROR]"
{job="lang-agent"} |= "[WARNING]"
{job="lang-agent"} |= "[INFO]"
```

### Проверка что логи приходят

Сначала убедитесь, что логи вообще есть:

```logql
# Показать все labels (чтобы понять что есть)
{job=~".+"}

# Или просто всё что есть за последние 5 минут
{job="lang-agent"}
```

Если labels пустые или ничего не находится:
1. Проверьте правильность `LOKI_URL`
2. Убедитесь что контейнеры в одной сети
3. Посмотрите логи контейнера на ошибки

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

### 1. Проверьте что Loki handler включен:

```bash
# Посмотрите логи контейнера
docker logs backend 2>&1 | grep -i loki

# Должны увидеть:
# [INFO] backend.logging: Logging configured (level=INFO)
# [INFO] backend.logging: Loki logging enabled (url=http://loki:3100/loki/api/v1/push, labels={...})
```

### 2. Проверьте подключение к Loki:

```bash
# Из контейнера backend попробуйте достучаться до Loki
docker exec backend curl -v http://loki:3100/ready

# Или проверьте что Loki доступен
curl http://localhost:3100/ready
```

### 3. В Grafana Explore:

Попробуйте самый простой запрос:
```logql
{job="lang-agent"}
```

Если ничего нет, попробуйте посмотреть ВСЕ labels:
```logql
{job=~".+"}
```

### 4. Отправьте тестовый запрос к API:

```bash
curl http://localhost:8000/health
```

Этот запрос должен создать лог записи в Loki.

## Troubleshooting

### Labels пустые в Grafana

Если вы видите пустые labels в Grafana:

1. **Проверьте labels которые отправляются:**
   ```bash
   docker logs backend 2>&1 | grep "Loki logging enabled"
   # Должно показать: labels={'application': 'lang-agent', 'environment': 'production', ...}
   ```

2. **Попробуйте искать по job label:**
   ```logql
   {job="lang-agent"}
   ```
   Label `job` добавляется автоматически

3. **Посмотрите ВСЕ доступные labels:**
   В Grafana Explore нажмите на "Label browser" или используйте:
   ```logql
   {job=~".+"}
   ```

### Логи не появляются в Grafana

1. **Проверьте настройку Loki URL:**
   ```bash
   docker logs backend 2>&1 | grep -i loki
   ```

2. **Проверьте что контейнеры в одной сети:**
   ```bash
   # Посмотрите сети backend контейнера
   docker inspect backend | grep -A 10 Networks

   # Посмотрите сети loki контейнера
   docker inspect loki | grep -A 10 Networks
   ```

   Если они в разных сетях, добавьте в docker-compose.yml:
   ```yaml
   services:
     backend:
       networks:
         - web
         - backend
         - monitoring  # <- добавьте сеть где находится Loki
   ```

3. **Проверьте доступность Loki из backend:**
   ```bash
   docker exec backend curl -v http://loki:3100/ready
   docker exec backend ping -c 3 loki
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
