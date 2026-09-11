# SolutionRuner

Детерминированные раннеры TeacherHelper: вычисление ответов, сборка решений,
обработка изображений и применение изменений через MCP.

## Что где лежит

| Путь | Содержимое |
| --- | --- |
| [src/solution_runner/launcher.py](src/solution_runner/launcher.py) | Общая точка входа `.venv/bin/solution-runner`. |
| [pipelines/core/](src/solution_runner/pipelines/core/) | Реестры обработчиков и профилей, общий content runtime, модели, MCP-интерфейс и точные числа. |
| [pipelines/equations/](src/solution_runner/pipelines/equations/) | Обработчики уравнений. |
| [pipelines/vectors/](src/solution_runner/pipelines/vectors/) | Векторы, длины и скалярные произведения. |
| [pipelines/triangles/](src/solution_runner/pipelines/triangles/) | Треугольники: `general/`, `isosceles/`, `right/`. |
| [pipelines/quadrilaterals/](src/solution_runner/pipelines/quadrilaterals/) | Параллелограммы и трапеции. |
| [pipelines/grid_polygon/](src/solution_runner/pipelines/grid_polygon/) | Фигуры на сетке и кольца; здесь пока находится общая оркестрация запусков. |
| [converters/](src/solution_runner/converters/) | Преобразование растров в SVG, очистка SVG, шаблоны и OCR. |
| [tests/](tests/) | Тесты раннеров и конвертеров, фикстуры. |
| [dashboard/](dashboard/) | Локальная OpenKanban-доска групп; SQLite-индекс, dry-run и превью. |
| [issues/](issues/) | Разборы проблем и предложения по развитию. |
| [docs/campaigns/](docs/campaigns/) | Инвентаризация и отчёты обработки групп. |
| `var/` | Манифесты, логи, превью, ассеты и результаты запусков; не отслеживаются Git. |
| [pyproject.toml](pyproject.toml), [package.json](package.json) | Python-пакет, CLI и зависимости; Node используется конвертером с OCR. |

В `grid_polygon/`:

- `geometry/` — разбор SVG и геометрия сетки; `strategies/` — построение решений и рисунков;
- `inventory.py` — выбор задач; `manifest.py` — сохранённое состояние запуска;
- `asset_preparation.py`, `ring_asset_preparation.py` — подготовка изображений;
- `mcp_transport.py`, `mcp_runtime.py` — транспорт и вызовы MCP;
- `solution_plan.py` — план изменений; `solution_runtime.py`, `helpers_runtime.py` — применение и проверка результата;
- `launcher.py`, `progress.py` — порядок этапов, возобновление и прогресс;
- `solution_asset_repair.py` — восстановление рисунков решений;
- `runner_probe.py` — read-only поиск подходящего существующего правила для одной задачи.

## Документация

- [Контракт разработки раннеров](docs/runner-authoring-contract.md) — режимы и этапы работы.
- [Пожелания к стилю](docs/target-vision.md) — оформление решений и рисунков.
- [Пробник раннеров](docs/runner-probe.md) — расположение и интерфейс пробника.
- [Планиметрия 1](docs/planimetry-1-campaign.md) — расположение отчётов кампании.
- [Дизайн доски групп](docs/superpowers/specs/2026-09-10-group-dashboard-design.md) — Initialize, превью и статусы задач.

## Локальная доска

```bash
cd dashboard && npm run build && cd ..
.venv/bin/python -m solution_runner.dashboard.server
```

Новая карточка проходит `Инициализация → На регистрацию`. Initialize один раз
сохраняет в `var/dashboard/dashboard.sqlite3` ID группы, родителя и задач,
наличие разделов и метаданные PNG/SVG; содержимое задач в базу не копируется.
Дальнейший dry-run передаёт общему launcher `--inventory-db` и не повторяет
инвентаризацию группы через MCP. Старый MCP inventory пока остаётся только
переходным CLI fallback для групп без локального индекса.

После Initialize группа регистрируется в выбранной Codex-задаче либо в новой
задаче `gpt-5.6-terra` с уровнем reasoning `medium`. Порядок колонок:
`Инициализация → На регистрацию → В работе → Есть проблемы → На проверке → Готово`.
Apply всей группы доступен только после успешного полного dry-run без записи.

## Как подключаются группы

Общий лаунчер остаётся один: `.venv/bin/solution-runner`.

```text
domain/profiles.py → content_rule_key → core/handler_registry.py
                                         ↓
                                 HandlerSpec.plan(PlanInput)
                                         ↓
                                 core/content_runtime.py
                                 manifest / apply / readback
```

- `profiles.py` в математическом разделе содержит только привязки групп и
  параметры. `core/group_profiles.py` собирает их, отвергая дубликаты и ссылки
  на неизвестные content rules.
- `handlers.py` того же раздела объявляет `HandlerSpec`: ключ, функцию
  обработчика, отображение аргументов, ограничения, требования к изображениям
  и родителю. Общий реестр собирает декларации разделов без перебора задач.
- `PlanInput` — единый вход; адаптер передаёт существующему planner только
  объявленные аргументы. `plan()` возвращает ответ и transformations.
- Неизвестный ключ — ошибка конфигурации, а не попытка выбрать обработчик по
  префиксу или совпавшему ответу. Чистый пробник остаётся отдельной операцией.
- Геометрические стратегии сохраняют существующий реестр
  `grid_polygon/strategies`; это другой подготовительный workflow того же
  общего лаунчера, а не отдельный CLI.

Для новой группы с уже поддержанной математикой добавить привязку в
`profiles.py` и тест. Например, группы 26660 и 26661 обе ссылаются на
`irrational-26660-square-root-rational-affine`; новую ветку в runtime добавлять
не нужно. Для нового правила добавить planner, одну декларацию в `handlers.py`
и тесты. При создании нового математического раздела один раз подключить его
декларации к агрегирующим реестрам.

`triangles/right/runtime.py` — только совместимый импорт общего runtime.
Новый код использует `core/content_runtime.py`. Ключи остаются прежними,
поэтому перенос не меняет записанные в манифестах идентификаторы правил.

Проверка реестров без MCP:

```bash
.venv/bin/python -m pytest tests/pipelines/core/test_handler_registry.py -q
```

Тесты фиксируют прежние маршруты и аргументы, сохранность профилей, отсутствие
дубликатов и неизвестных ключей. Миграционные JSON-фикстуры содержат только
декларации и настройки, не содержимое задач; при намеренном изменении профилей
актуализировать соответствующую запись, не переснимать весь snapshot вслепую.
