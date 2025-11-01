# Logging Overview

## Что логируется

Приложение логирует все обращения к боту и LLM с временем выполнения.

### 🤖 Telegram Bot

#### Текстовые сообщения
```
[INFO] Bot message received: user_id=123, username=john, message_length=45
[INFO] Bot message processed: user_id=123, duration_ms=1234.56, reply_length=128
```

#### Команда /add (добавление слов)
```
[INFO] Bot /add command: user_id=123, words_count=3
[INFO] Bot /add command processed: user_id=123, duration_ms=2345.67, results=3
```

#### Команда /flashcard (повторение)
```
[INFO] Bot /flashcard command: user_id=123
[INFO] Bot /flashcard served: user_id=123, duration_ms=156.78, card_id=456
```

#### Ошибки
```
[ERROR] Bot message failed: user_id=123, duration_ms=500.00
[ERROR] Bot /add command failed: user_id=123, duration_ms=1200.00
```

### 🧠 LLM (OpenAI)

#### Обычные запросы (разговор)
```
[INFO] LLM request: model=gpt-4.1-mini, message_length=50, history_entries=5
[INFO] LLM response: model=gpt-4.1-mini, duration_ms=1500.00, response_length=200
```

#### Генерация флеш-карт
```
[INFO] Flashcard generation request: model=gpt-4.1-mini, word=привет
[INFO] Flashcard generation success: word=привет, duration_ms=2000.00, source=привет, target=γεια
```

#### Ошибки LLM
```
[ERROR] LLM request failed: model=gpt-4.1-mini, duration_ms=5000.00
[ERROR] Flashcard generation failed: word=test, duration_ms=3000.00
```

## Как использовать в Grafana

### Мониторинг активности бота
```logql
# Количество обращений за последний час
sum(count_over_time({job="lang-agent"} |= "Bot message received" [1h]))
```

### Среднее время ответа
```logql
# Среднее время обработки сообщений
avg_over_time(
  {job="lang-agent"} |= "Bot message processed"
  | regexp `duration_ms=(?P<duration>[\\d.]+)`
  | unwrap duration [5m]
)

# Среднее время ответа LLM
avg_over_time(
  {job="lang-agent"} |= "LLM response"
  | regexp `duration_ms=(?P<duration>[\\d.]+)`
  | unwrap duration [5m]
)
```

### Медленные запросы
```logql
# Запросы > 2 секунд
{job="lang-agent"} |~ "duration_ms=([2-9]\\d{3}|\\d{4,})"
```

### Ошибки по типам
```logql
# Ошибки бота
{job="lang-agent"} |= "Bot" |= "failed"

# Ошибки LLM
{job="lang-agent"} |= "LLM" |= "failed"
```

## Полезные дашборды

### 1. Bot Activity Dashboard
- Количество обращений в час/день
- Среднее время обработки
- Топ пользователей (по user_id)
- Распределение команд (/add vs /flashcard vs текст)

### 2. LLM Performance Dashboard
- Количество запросов к LLM
- Среднее/P95/P99 время ответа
- Ошибки и их частота
- Соотношение обычных запросов к генерации флеш-карт

### 3. Errors Dashboard
- Error rate за период
- Типы ошибок
- Затронутые пользователи
- Время когда произошли ошибки

## Примеры запросов

**Посмотреть активность конкретного пользователя:**
```logql
{job="lang-agent"} |= "user_id=123"
```

**Найти медленные генерации флеш-карт:**
```logql
{job="lang-agent"}
  |= "Flashcard generation success"
  |~ "duration_ms=([3-9]\\d{3}|\\d{4,})"
```

**Подсчитать сколько слов было добавлено:**
```logql
sum(
  sum_over_time(
    {job="lang-agent"}
      |= "Bot /add command processed"
      | regexp `results=(?P<count>\\d+)`
      | unwrap count [1h]
  )
)
```

**Успешность генерации карт (success rate):**
```logql
sum(count_over_time({job="lang-agent"} |= "Flashcard generation success" [1h]))
/
sum(count_over_time({job="lang-agent"} |= "Flashcard generation request" [1h]))
* 100
```

## См. также

- **GRAFANA_QUERIES.md** - полная шпаргалка по LogQL запросам
- **LOKI_SETUP.md** - настройка Loki логирования
- **QUICK_START_LOKI.md** - быстрый старт
