# Быстрый старт Loki логирования

## 1. Настройка

В вашем `.env` файле добавьте одну строку:

```env
LOKI_URL=http://loki:3100/loki/api/v1/push
```

**Замените `loki` на имя вашего Loki контейнера!**

## 2. Перезапуск

```bash
docker-compose restart backend
```

## 3. Проверка

```bash
# Должны увидеть эту строку:
docker logs backend 2>&1 | grep "Loki logging enabled"
```

## 4. В Grafana

Перейдите в **Explore** и используйте:

```logql
{job="lang-agent"}
```

Вот и всё! 🎉

---

## ВАЖНО: Labels

**LOKI_LABELS НЕ ОБЯЗАТЕЛЬНЫ!**

По умолчанию автоматически добавляются:
- ✅ `job="lang-agent"` ← **ищите по этому!**
- ✅ `application="lang-agent"`
- ✅ `environment="production"` (из APP_ENV)
- ✅ `host="container-name"`

## Что смотреть в Grafana

### Все логи:
```logql
{job="lang-agent"}
```

### Только ошибки:
```logql
{job="lang-agent"} |= "ERROR"
```

### Telegram бот:
```logql
{job="lang-agent"} |= "Telegram"
```

### API запросы:
```logql
{job="lang-agent"} |= "/api/"
```

## Troubleshooting

### Логи не появляются?

**Шаг 1: Проверьте что backend видит Loki**
```bash
docker exec backend curl http://loki:3100/ready
```

Если ошибка - контейнеры в разных сетях!

**Шаг 2: Добавьте сеть в docker-compose.yml**
```yaml
services:
  backend:
    networks:
      - web
      - backend
      - monitoring  # <- добавьте сеть где Loki
```

**Шаг 3: Перезапустите**
```bash
docker-compose down
docker-compose up -d
```

### Labels пустые?

Используйте `job` label:
```logql
{job="lang-agent"}
```

Если совсем ничего нет, посмотрите все labels:
```logql
{job=~".+"}
```

## Полная документация

- **LOKI_SETUP.md** - детальная настройка
- **GRAFANA_QUERIES.md** - шпаргалка по запросам LogQL

---

**TL;DR:**
1. `LOKI_URL=http://loki:3100/loki/api/v1/push` в `.env`
2. `docker-compose restart backend`
3. В Grafana: `{job="lang-agent"}`
