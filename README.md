# WebAI Tool

Автономная агентная система для инженерии ПО. Анализирует существующий код, генерирует документацию (SRS) и автоматически реализует проекты по спецификации.

## Возможности

- **Обратный инжиниринг** — сканирует проект, анализирует структуру и генерирует SRS-документацию
- **Прямой инжиниринг** — читает спецификацию и автономно пишет/модифицирует код
- **Repomap** — генерирует карту репозитория (дерево файлов + сигнатуры классов/функций) через tree-sitter `.scm` запросы. Поддержка Python, JavaScript, TypeScript, Vue
- **Symbol Graph** — граф зависимостей на уровне символов с 7 уровнями приоритета (self-access, same-file, import-resolved, type-resolved, scope-match, global-unique, unique-method). Резолвинг импортов, вывод типов, JSON-кеширование
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
| `src/repo_map.py` | Генератор карты репозитория (tree-sitter `.scm` запросы: классы, функции, методы, Vue SFC секции) |
| `src/graph/` | Пакет символьного графа: модели, резолвинг импортов, вывод типов, RepoGraphLite, JSON-кеш |
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
just repo-map ./my-project
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

Юнит-тесты (~79 штук) покрывают: парсинг Python/JS/TS/Vue, `.scm` запросы, символьный граф (7 приоритетов), резолвинг импортов, вывод типов, JSON-кеш, генерацию дерева, безопасность (path traversal, symlinks, file size limits, depth limits, output truncation).

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
│   ├── repo_map.py          # Генератор карты репозитория (.scm запросы)
│   ├── graph/               # Символьный граф зависимостей
│   │   ├── models.py        # Dataclass-модели (SymbolNode, Edge, ImportTag, ...)
│   │   ├── import_resolver.py # Резолвинг импортов через .scm запросы
│   │   ├── type_resolver.py # Вывод типов (4 AST-паттерна)
│   │   ├── repo_graph.py    # RepoGraphLite + @tool get_symbol_context/graph
│   │   └── graph_store.py   # JSON-кеш в .repo-graph/
│   ├── queries/             # Tree-sitter .scm файлы запросов
│   │   ├── python-tags.scm
│   │   ├── javascript-tags.scm
│   │   ├── typescript-tags.scm
│   │   ├── tsx-tags.scm
│   │   ├── python-imports.scm
│   │   ├── javascript-imports.scm
│   │   └── typescript-imports.scm
│   ├── lg_tools.py          # Инструменты (shell_exec)
│   ├── gener.py             # LLM-интерфейс
│   ├── makesrs_prod.py      # Генератор SRS
│   ├── prompts.py           # Промпты
│   └── main.py              # Точка входа
├── tests/
│   ├── unit/                # Юнит-тесты
│   │   ├── test_repo_map.py
│   │   ├── test_models.py
│   │   ├── test_import_resolver.py
│   │   ├── test_type_resolver.py
│   │   ├── test_repo_graph_lite.py
│   │   └── test_graph_store.py
│   ├── integration/         # Интеграционные тесты
│   │   ├── test_hello_world.py
│   │   ├── test_add_feature.py
│   │   └── test_from_spec.py
│   └── data/                # Тестовые данные
├── docs/
│   ├── overview.md          # Документация архитектуры
│   ├── loop-detection.md    # Детекция зацикливания
│   └── repomap-roadmap.md   # Роадмап развития repomap
├── scripts/                 # Скрипты для justfile рецептов
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
