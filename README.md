# WebAI Tool

Автономная агентная система для инженерии ПО. Анализирует существующий код, генерирует документацию (SRS) и автоматически реализует проекты по спецификации.

## Возможности

- **Обратный инжиниринг** — сканирует проект, анализирует структуру и генерирует SRS-документацию
- **Прямой инжиниринг** — читает спецификацию и автономно пишет/модифицирует код
- **Repomap** — генерирует карту репозитория (дерево файлов + сигнатуры классов/функций) через tree-sitter. Поддержка Python, JavaScript, TypeScript, Vue
- **Защита от зацикливания** — детекция повторяющихся мыслей агента и принудительная проверка завершения

## Архитектура

Ядро системы — **LangGraph** граф с циклической state-машиной:

```
think → state_check → code_action → think (цикл до достижения цели)
                ↘ review → END (при обнаружении [GOAL_ACHIEVED])
```

### Основные модули

| Модуль | Описание |
|--------|----------|
| `src/lg_agent.py` | Ядро агента: граф, состояние (`AgentState`), узлы `think`, `code_action`, `state_check`, `review` |
| `src/repomap.py` | Генератор карты репозитория (tree-sitter AST: классы, функции, методы, Vue SFC секции) |
| `src/lg_tools.py` | Инструменты агента (shell_exec) |
| `src/gener.py` | Интерфейс к LLM (OpenAI-совместимый API) |
| `src/makesrs_prod.py` | Движок генерации SRS из исходного кода |
| `src/prompts.py` | Промпты для анализа, планирования и проверки кода |
| `src/main.py` | Точка входа: генерация документации → запуск агента |

## Быстрый старт

### 1. Установка

Требуется [uv](https://docs.astral.sh/uv/) и (опционально) [just](https://github.com/casey/just).

```bash
git clone https://github.com/WebAITool/webai-tool.git
cd webai-tool

# через just
just setup

# или вручную
cp .env.example .env
uv sync
```

### 2. Настройка LLM

Отредактируйте `.env`:

```env
LLM_MODEL=arcee-ai/trinity-large-preview:free
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=your-key-here
```

Поддерживается любой OpenAI-совместимый API (OpenRouter, polza.ai, локальные серверы).

### 3. Запуск

```bash
# Через just (рекомендуется)
just run "создать landing page" "vue 3, tailwind" ./output

# Или напрямую
uv run python -c "
import sys; sys.path.insert(0, 'src')
from lg_agent import run_agent
run_agent('создать файл hello.txt', 'простой тест', prjdir='./output')
"

# Посмотреть карту репозитория
just repomap ./my-project
```

## Тестирование

```bash
# Юнит-тесты (repomap, парсеры, безопасность)
just test-unit

# Интеграционные тесты (требуется LLM API ключ в .env)
just test-integration

# Все тесты
just test
```

Юнит-тесты (29 штук) покрывают: парсинг Python/JS/TS/Vue, генерацию дерева, безопасность (path traversal, symlinks, file size limits, depth limits, output truncation).

Интеграционные тесты:

| Тест | Что проверяет |
|------|---------------|
| `test_hello_world` | Агент создаёт файл `hello.txt` с текстом «Hello, World!» |
| `test_add_feature` | Агент добавляет фичу в существующий Vue + FastAPI проект |
| `test_from_spec` | Агент получает мини-SRS, реализует FastAPI-сервер, тест запускает сервер и проверяет эндпоинты HTTP-запросами |

## Структура проекта

```
webai-tool/
├── src/
│   ├── lg_agent.py          # Ядро агента (LangGraph)
│   ├── repomap.py           # Генератор карты репозитория
│   ├── lg_tools.py          # Инструменты (shell_exec)
│   ├── gener.py             # LLM-интерфейс
│   ├── makesrs_prod.py      # Генератор SRS
│   ├── prompts.py           # Промпты
│   └── main.py              # Точка входа
├── tests/
│   ├── unit/                # Юнит-тесты
│   │   └── test_repomap.py
│   ├── integration/         # Интеграционные тесты
│   │   ├── test_hello_world.py
│   │   ├── test_add_feature.py
│   │   └── test_from_spec.py
│   └── data/                # Тестовые данные
├── docs/
│   ├── overview.md          # Документация архитектуры
│   ├── loop-detection.md    # Детекция зацикливания
│   └── repomap-roadmap.md   # Роадмап развития repomap
├── justfile                 # Команды разработки (кроссплатформенный)
├── .env.example             # Шаблон конфигурации
└── pyproject.toml           # Зависимости проекта
```

## Зависимости

- Python >= 3.12
- `langchain-openai`, `langchain-core`, `langchain-experimental`, `langgraph`
- `tree-sitter`, `tree-sitter-language-pack`
- `python-dotenv`

Dev: `pytest`, `pytest-cov`, `mutmut`
