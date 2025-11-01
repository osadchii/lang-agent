# Централизованная Фабрика Логгеров

## Обзор

Создана централизованная фабрика логгеров которая гарантирует что **все** логгеры в приложении правильно сконфигурированы с handlers (console + Loki).

## Проблема (до изменений)

- Логгеры создавались через `logging.getLogger(__name__)` на уровне модуля
- Это происходило **ДО** вызова `configure_logging()`
- Логгеры не получали правильную конфигурацию handlers
- Логи не попадали в Loki
- При недоступном Loki возникала бесконечная рекурсия (urllib3 логи → Loki handler → ошибка → urllib3 логи → ...)

## Решение

### 1. Фабрика логгеров (`logger_factory.py`)

```python
from backend.logger_factory import get_logger

logger = get_logger(__name__)
logger.info("Это сообщение пойдет и в консоль, и в Loki")
```

**Гарантии фабрики:**
- ✅ Все логгеры получают правильные handlers (console + Loki)
- ✅ Работает независимо от порядка создания логгеров
- ✅ Автоматически конфигурирует новые логгеры
- ✅ Нет дубликатов логов

### 2. Функция `configure_logger(logger_instance)`

Навешивает handlers напрямую на конкретный инстанс логгера:

```python
from backend.logging import configure_logger

# Вызывается автоматически из фабрики
logger = logging.getLogger("my_logger")
configure_logger(logger)  # Добавляет console + Loki handlers
```

**Что делает:**
- Очищает существующие handlers
- Добавляет все configured handlers (console + Loki)
- Устанавливает правильный уровень логирования
- Отключает propagation (handlers навешаны напрямую)

### 3. Защита от бесконечной рекурсии

**Проблема:** Когда Loki недоступен, urllib3 генерирует DEBUG логи об ошибке подключения → они идут в Loki handler → который снова пытается подключиться → urllib3 снова логирует → рекурсия

**Решение:**
```python
# В configure_logging():
# Отключаем urllib3/requests логи ПЕРЕД созданием Loki handler
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("urllib3").propagate = False
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("requests").propagate = False

# Добавляем фильтр на Loki handler
class NoHTTPLibLogsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not record.name.startswith(("urllib3", "requests"))

loki_handler.addFilter(NoHTTPLibLogsFilter())
```

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    configure_logging()                       │
│  - Создает handlers (console + Loki)                        │
│  - Сохраняет в _configured_handlers                         │
│  - Конфигурирует root logger                                │
│  - Переконфигурирует все существующие логгеры               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   logger_factory.py                          │
│                                                              │
│  get_logger(name)                                           │
│    ├─ logging.getLogger(name)  # Singleton                 │
│    └─ configure_logger(logger) # Навешивает handlers       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   configure_logger()                         │
│  - logger.handlers.clear()                                  │
│  - logger.addHandler(console_handler)                       │
│  - logger.addHandler(loki_handler)                          │
│  - logger.setLevel(level)                                   │
│  - logger.propagate = False                                 │
└─────────────────────────────────────────────────────────────┘
```

## Использование

### Создание логгера

**Правильно:** ✅
```python
from backend.logger_factory import get_logger

logger = get_logger(__name__)
```

**Неправильно:** ❌
```python
import logging

logger = logging.getLogger(__name__)  # НЕ ИСПОЛЬЗОВАТЬ!
```

### Конфигурация в приложении

```python
# В runtime.py или dependencies.py
from backend.logging import configure_logging
from backend.config import AppConfig

config = AppConfig.load()

# ВАЖНО: Вызвать ДО импорта сервисов!
configure_logging(
    level=config.log_level,
    loki_url=config.loki_url,
    loki_labels=config.loki_labels,
)

# Теперь импортируем сервисы
from backend.services import ...
```

### Переконфигурация существующих логгеров

Если логгеры создаются в runtime (например, aiogram):

```python
from backend.logger_factory import reconfigure_all_loggers

# При первом webhook от Телеги
reconfigure_all_loggers()  # Переконфигурирует все логгеры включая aiogram
```

## Настройка Loki

### Локальная разработка (без Loki)

```env
# .env
LOKI_URL=
```

Логи будут только в консоли. Это нормально для локальной разработки.

### Production (с Loki в Docker)

```env
# .env
LOKI_URL=http://loki:3100/loki/api/v1/push
LOKI_LABELS=team=backend,version=1.0
```

**Важно:**
- Убедитесь что backend и loki в одной Docker сети
- Имя `loki` должно резолвиться в Docker DNS

## Тестирование

```python
# test_logging.py
from backend.logger_factory import get_logger
from backend.logging import configure_logging
from backend.config import AppConfig

config = AppConfig.load()
configure_logging(config.log_level, config.loki_url, config.loki_labels)

logger = get_logger("test")
logger.info("Test message - should appear in console and Loki")
```

## Миграция существующего кода

### Шаг 1: Заменить импорты

```python
# Было:
import logging
logger = logging.getLogger(__name__)

# Стало:
from backend.logger_factory import get_logger
logger = get_logger(__name__)
```

### Шаг 2: Удалить ручную конфигурацию

```python
# Было:
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(...)

# Стало:
logger = get_logger(__name__)
# Handlers добавляются автоматически!
```

### Шаг 3: Вызывать configure_logging рано

```python
# В main.py или app.py
# ПЕРЕД импортом сервисов:
configure_logging(...)

# После:
from .services import ...  # Эти модули используют get_logger
```

## Отладка

### Проверка что логгер сконфигурирован

```python
logger = get_logger(__name__)
print(f"Handlers: {logger.handlers}")  # Должно быть 2: console + loki
print(f"Level: {logger.level}")        # Должен быть настроенный уровень
print(f"Propagate: {logger.propagate}") # Должно быть False
```

### Проверка что Loki работает

В Grafana Explore:
```logql
{job="lang-agent"} | json
```

Должны увидеть логи приложения.

## Преимущества

1. **Гарантированная конфигурация** - все логгеры точно получают handlers
2. **Нет дубликатов** - propagation отключен, handlers навешаны напрямую
3. **Работает с любыми библиотеками** - даже если aiogram создает свои логгеры
4. **Защита от рекурсии** - urllib3 логи не попадают в Loki handler
5. **Простое использование** - один импорт, один вызов
6. **Централизованная конфигурация** - handlers настраиваются в одном месте

## Миграция уже сделана в:

- ✅ `api/routers/telegram.py`
- ✅ `services/telegram_bot.py`
- ✅ `services/llm.py`
- ✅ `api/app.py`
- ✅ `logging.py` (использует фабрику для своих логов)

## Смотрите также

- `LOKI_SETUP.md` - настройка Loki в Docker
- `LOGGING_OVERVIEW.md` - что логируется в приложении
- `GRAFANA_QUERIES.md` - полезные LogQL запросы
