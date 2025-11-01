# Grafana LogQL Queries Cheatsheet

## Что искать в Grafana

### Базовые labels (всегда есть):
- `job="lang-agent"` ← **используйте этот!**
- `application="lang-agent"`
- `environment="production"` (или `development`)
- `host="<container-name>"`

## Основные запросы

### 1. Все логи приложения
```logql
{job="lang-agent"}
```

### 2. Только ошибки
```logql
{job="lang-agent"} |= "ERROR"
{job="lang-agent"} |= "[ERROR]"
```

### 3. Telegram бот
```logql
{job="lang-agent"} |= "Telegram"
{job="lang-agent"} |= "aiogram"
{job="lang-agent"} |~ "Telegram|aiogram"
```

### 4. API запросы
```logql
# Все API запросы
{job="lang-agent"} |= "/api/"

# Конкретный эндпоинт
{job="lang-agent"} |= "POST /api/decks"
{job="lang-agent"} |= "GET /health"

# По коду ответа
{job="lang-agent"} |= "200"
{job="lang-agent"} |= "500"
```

### 5. По времени
```logql
# Последние 5 минут
{job="lang-agent"}

# Последний час
{job="lang-agent"} [1h]

# С определенного времени
{job="lang-agent"} |= "ERROR" [5m]
```

### 6. Частота ошибок
```logql
sum(rate({job="lang-agent"} |= "ERROR" [5m]))
```

### 7. По уровню логирования
```logql
{job="lang-agent"} |= "[INFO]"
{job="lang-agent"} |= "[WARNING]"
{job="lang-agent"} |= "[ERROR]"
{job="lang-agent"} |= "[DEBUG]"
```

### 8. Конкретный модуль
```logql
{job="lang-agent"} |= "backend.services.telegram_bot"
{job="lang-agent"} |= "backend.api"
{job="lang-agent"} |= "uvicorn"
```

## Проверка что логи приходят

1. **Сначала проверьте labels:**
```logql
{job=~".+"}
```

2. **Посмотрите что есть за последний час:**
```logql
{job="lang-agent"} [1h]
```

3. **Если пусто - проверьте в логах контейнера:**
```bash
docker logs backend 2>&1 | grep "Loki logging enabled"
```

## Dashboard метрики

### Error rate за 5 минут
```logql
sum(rate({job="lang-agent"} |= "ERROR" [5m])) by (environment)
```

### Количество логов по уровню
```logql
sum by(level) (count_over_time({job="lang-agent"}[1m]))
```

### Top 10 самых частых сообщений
```logql
topk(10, sum by (msg) (count_over_time({job="lang-agent"}[5m])))
```

## Troubleshooting

### Логи не появляются?

1. Проверьте `.env`:
```bash
cat .env | grep LOKI_URL
# Должно быть: LOKI_URL=http://loki:3100/loki/api/v1/push
```

2. Проверьте что Loki handler включен:
```bash
docker logs backend 2>&1 | grep -i loki
# Должно быть: Loki logging enabled (url=...)
```

3. Проверьте доступность Loki:
```bash
docker exec backend curl http://loki:3100/ready
```

4. Отправьте тестовый запрос:
```bash
curl http://localhost:8000/health
# Должен появиться лог в Grafana через несколько секунд
```

### Labels пустые?

Попробуйте поискать по `job` label:
```logql
{job="lang-agent"}
```

Если всё равно ничего нет - проверьте что контейнеры в одной сети:
```bash
docker network ls
docker inspect backend | grep -A 10 Networks
docker inspect loki | grep -A 10 Networks
```

## Полезные фильтры

### Исключить healthcheck
```logql
{job="lang-agent"} != "/health"
```

### Только медленные запросы (если логируете время)
```logql
{job="lang-agent"} |= "took" | json | took > 1000
```

### Только production
```logql
{job="lang-agent", environment="production"}
```

### Не включать определенные модули
```logql
{job="lang-agent"} != "aiogram" != "asyncio"
```
