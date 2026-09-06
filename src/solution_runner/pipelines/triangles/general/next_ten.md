# Следующие группы после 27767

Аудит выполнен по каталогу `41bc4d03-40cd-4407-8dea-df76e3f47ea8`.
Общий запуск включает все задачи каждой группы. Первая задача используется
обработчиком как источник разметки решения и изображений и также проходит
проверку решения, ответа и Helpers.

| Группа | Родитель | UUID для контрольного запуска | Что извлекает обработчик | Проверяемое вычисление |
|---|---|---|---|---|
| 27768 | `c4be5180-cbf9-4cb2-9051-a6f3977b7a6b` | `c4be5180-cbf9-4cb2-9051-a6f3977b7a6b` (27768; в группе только родитель) | `AD` — биссектриса; `AB=AD=CD`; требуется меньший угол | `36°`; сохраняется решение родителя |
| 27769 | `519ad299-a918-4132-af1c-c294d885f25e` | `723a0461-a294-490c-b7e9-323ca04e479e` (47569) | углы `A=100°`, `C=13°`; продолжение `AB`; `BD=BC`; требуется `D` | `B=180−A−C=67°`, `D=B/2=33,5°` |
| 27776 | `23ec181e-5fc3-4f55-b6df-b44c9ceaa107` | `a4963bdf-64c1-4c70-95ec-b9b192b80baf` (47893) | `B=50°`, `C=77°`; `AD` — биссектриса; `AE=AC`; требуется `BDE` | `BDE=C−B=27°` |
| 27777 | `2594697d-e227-4185-a518-77c6db76e38e` | `f32e7d80-37bf-4497-a09b-8e75bfc213e4` (47943) | `A=17°`, `B=46°`; `CD` — биссектриса внешнего угла; `CE=CB`; требуется `BDE` | `BCD=(A+B)/2=31,5°`, `CBD=180−B=134°`, `BDE=29°` |
| 27778 | `0df330e4-328b-4750-831f-d7d1967fbbf1` | `157ccd53-44f5-437b-a7c6-2e45d23d7823` (47995) | `A=60°`, `B=53°`; три биссектрисы пересекаются в `O`; требуется `AOF` | `AOF=90−B/2=63,5°` |
| 27779 | `a33dca79-0cb6-4c59-ae86-895d5a2c379b` | `fafaf3b2-8e04-43ce-b06d-cb23486e719f` (48045) | `A=21°`, `B=11°`; три высоты пересекаются в `O`; требуется `AOF` | `AOF=B=11°` |
| 317337 | `64480258-1fec-4a84-90d1-db7c3c9aa713` | `9b5b4d8d-aa7c-44e5-8d00-ae6d85498843` (317351) | `DE` — средняя линия; площадь одного из `ADE/BDE/CDE`; требуется `ABC` | для `CDE=10`: `ABC=4·10=40`; первая схема в условии, вторая в решении |
| 319058 | `2abbd5b7-198b-49eb-8f09-cb883bf73920` | `7bc24e7a-f9d4-424c-a055-d13f4028c27f` (319263) | `ABC=12`; `DE∥AB` — средняя линия; требуется площадь трапеции | `CDE=12/4=3`, трапеция `12−3=9`; картинка переносится в условие |
| 500142 | `0af2397f-64b2-44d9-a3ed-eebc43d1f13e` | `17808f04-3337-45d7-b0c0-43bf86a2668a` (500162) | угол `A`; острые `B` и `C`; высоты `BD` и `CE`; требуется `DOE` | для `A=43°`: `DOE=360−90−90−43=137°`; решение и картинка берутся у родителя |
| 510796 | `975ff994-2799-4c19-8596-f939f6aef460` | `975ff994-2799-4c19-8596-f939f6aef460` (510796; в группе только родитель) | угол `A`; продолжения высот `BD` и `CE`; требуется `DOE` | `DOE=180−A=45°`; сохраняется структура решения родителя |

Группы `27768` и `510796` содержат только родительскую задачу. Она всё равно
проходит обработчик, проверку ответа и Helpers.

## Запуск по одной дочерней задаче

Во всех командах нужен новый каталог запуска: `--resume-solutions` добавлять
не следует.

```bash
.venv/bin/solution-runner --group 27768 --confirm-catalog 41bc4d03-40cd-4407-8dea-df76e3f47ea8 --only-problem-id c4be5180-cbf9-4cb2-9051-a6f3977b7a6b --max-workers 1 --batch-size 1 --apply
.venv/bin/solution-runner --group 27769 --confirm-catalog 41bc4d03-40cd-4407-8dea-df76e3f47ea8 --only-problem-id 723a0461-a294-490c-b7e9-323ca04e479e --max-workers 1 --batch-size 1 --apply
.venv/bin/solution-runner --group 27776 --confirm-catalog 41bc4d03-40cd-4407-8dea-df76e3f47ea8 --only-problem-id a4963bdf-64c1-4c70-95ec-b9b192b80baf --max-workers 1 --batch-size 1 --apply
.venv/bin/solution-runner --group 27777 --confirm-catalog 41bc4d03-40cd-4407-8dea-df76e3f47ea8 --only-problem-id f32e7d80-37bf-4497-a09b-8e75bfc213e4 --max-workers 1 --batch-size 1 --apply
.venv/bin/solution-runner --group 27778 --confirm-catalog 41bc4d03-40cd-4407-8dea-df76e3f47ea8 --only-problem-id 157ccd53-44f5-437b-a7c6-2e45d23d7823 --max-workers 1 --batch-size 1 --apply
.venv/bin/solution-runner --group 27779 --confirm-catalog 41bc4d03-40cd-4407-8dea-df76e3f47ea8 --only-problem-id fafaf3b2-8e04-43ce-b06d-cb23486e719f --max-workers 1 --batch-size 1 --apply
.venv/bin/solution-runner --group 317337 --confirm-catalog 41bc4d03-40cd-4407-8dea-df76e3f47ea8 --only-problem-id 9b5b4d8d-aa7c-44e5-8d00-ae6d85498843 --max-workers 1 --batch-size 1 --apply
.venv/bin/solution-runner --group 319058 --confirm-catalog 41bc4d03-40cd-4407-8dea-df76e3f47ea8 --only-problem-id 7bc24e7a-f9d4-424c-a055-d13f4028c27f --max-workers 1 --batch-size 1 --apply
.venv/bin/solution-runner --group 500142 --confirm-catalog 41bc4d03-40cd-4407-8dea-df76e3f47ea8 --only-problem-id 17808f04-3337-45d7-b0c0-43bf86a2668a --max-workers 1 --batch-size 1 --apply
.venv/bin/solution-runner --group 510796 --confirm-catalog 41bc4d03-40cd-4407-8dea-df76e3f47ea8 --only-problem-id 975ff994-2799-4c19-8596-f939f6aef460 --max-workers 1 --batch-size 1 --apply
```

## Запуск всех задач во всех зарегистрированных группах

Первая задача остаётся источником эталонного решения и изображений, но также
проходит через тот же обработчик и Helpers, чтобы оформление всей группы было
одинаковым.

```bash
cd /Users/a1/projects/SolutionRuner

catalog=41bc4d03-40cd-4407-8dea-df76e3f47ea8
failed=0
for group in 27768 27769 27776 27777 27778 27779 317337 319058 500142 510796; do
  .venv/bin/solution-runner \
    --group "$group" \
    --confirm-catalog "$catalog" \
    --max-workers 5 \
    --batch-size 10 \
    --apply || failed=1
done
exit "$failed"
```
