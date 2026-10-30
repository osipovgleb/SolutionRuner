# ЕГЭ профиль, категория 8 — сверка повреждённых формул с первоисточником

Формулы визуально прочитаны 2026-10-30 с оригинальных SVG страниц «Решу ЕГЭ».
Текстовые `alt` этих изображений местами ошибочны: теряют границы корня,
путают цифры основания логарифма и аргумента, дробный показатель и смешанное число.
Подтверждением служит само изображение, а не сохранённый ответ или текст решения.

[Реестр транскрипций](../../src/solution_runner/pipelines/equations/verified_expression_transcriptions.json)
содержит SHA256 полного исходного HTML условия и распакованного SVG, ссылки
на страницу и изображения, исходный и исправленный HTML, дату и формулу.
При повторной проверке SVG следует распаковать транспортный gzip перед расчётом хеша.
Все прочие формулы, параметры, текст, идентификаторы и ассеты сохраняются.

Исправление готовится только при точном совпадении полного HTML условия
и его хеша. Добавленная инструкция, изменённые цифры или другая разметка
не получают автоматического восстановления. После исправления условие
проверяет обычный общий математический раннер; ответ вычисляется заново.
Номер задачи используется в реестре для аудита, а не для выбора вычисления.
План явно содержит изменение `section:condition`. Apply, INITIALIZE и загрузка
ассетов не выполнялись; задачи на сервере не менялись.

| Группа | Задача | Подтверждённая формула | Первоисточник |
| --- | --- | --- | --- |
| 26740 | 549338 | `4^{\frac{1}{5}}\cdot16^{\frac{9}{10}}` | [Страница](https://math-ege.sdamgia.ru/problem?id=549338), [SVG](https://ege.sdamgia.ru/formula/svg/7f/7f79e162b0772b05fb9d9bc34451f392.svg) |
| 26801 | 65815 | `\frac{a^{-1}b}{(6a)^2b^4}\cdot\frac{36}{a^{-3}b^{-3}}` | [Страница](https://math-ege.sdamgia.ru/problem?id=65815), [SVG](https://ege.sdamgia.ru/formula/svg/83/83f3823a121146e76b6d0447a0e39ce4.svg) |
| 77400 | 77400 | `b^{\frac{1}{5}}\cdot\left(b^{\frac{9}{10}}\right)^2` | [Страница](https://math-ege.sdamgia.ru/problem?id=77400), [SVG](https://ege.sdamgia.ru/formula/svg/e2/e209a8965195b5db2524e365fea22416.svg) |
| 26846 | 68509 | `\log_{0{,}5}32` | [Страница](https://math-ege.sdamgia.ru/problem?id=68509), [SVG](https://ege.sdamgia.ru/formula/svg/e0/e0fa4ea998c87e1dd3ac26fd1d5a50a5.svg) |
| 26846 | 68473 | `\log_{0{,}2}125` | [Страница](https://math-ege.sdamgia.ru/problem?id=68473), [SVG](https://ege.sdamgia.ru/formula/svg/22/223ebb70c8e4951ce7fe2507a1b8305e.svg) |
| 26847 | 68553 | `\log_{20}400` | [Страница](https://math-ege.sdamgia.ru/problem?id=68553), [SVG](https://ege.sdamgia.ru/formula/svg/b0/b067254813184c097b5d77484ceac37a.svg) |
| 26849 | 68583 | `\log_{20}0{,}05+\log_{0{,}5}8` | [Страница](https://math-ege.sdamgia.ru/problem?id=68583), [SVG](https://ege.sdamgia.ru/formula/svg/3d/3de90767f3700a9f71bf32ed0a90eade.svg) |
| 26852 | 26852 | `\frac{\log_{7}13}{\log_{49}13}` | [Страница](https://math-ege.sdamgia.ru/problem?id=26852), [SVG](https://ege.sdamgia.ru/formula/svg/d4/d42a7126172cac41230666fa38025e47.svg) |
| 26852 | 4351 | `\frac{\log_{9}8}{\log_{81}8}` | [Страница](https://math-ege.sdamgia.ru/problem?id=4351), [SVG](https://ege.sdamgia.ru/formula/svg/70/703230de04f91a0514b4d1336a47fc60.svg) |
| 26852 | 68821 | `\frac{\log_{3}7}{\log_{27}7}` | [Страница](https://math-ege.sdamgia.ru/problem?id=68821), [SVG](https://ege.sdamgia.ru/formula/svg/fc/fc0f01fd796b8aa78600b135987c0277.svg) |
| 26860 | 69207 | `\log_{1{,}25}7\cdot\log_{7}0{,}8` | [Страница](https://math-ege.sdamgia.ru/problem?id=69207), [SVG](https://ege.sdamgia.ru/formula/svg/06/0634d28788071edd5367e4fbbfeee20f.svg) |
| 26735 | 26735 | `\sqrt{65^{2}-56^{2}}` | [Страница](https://math-ege.sdamgia.ru/problem?id=26735), [SVG](https://ege.sdamgia.ru/formula/svg/ea/ea28530acc56f90752fe228d611b3cd7.svg) |
| 26830 | 26830 | `\sqrt{(a-6)^{2}}+\sqrt{(a-10)^{2}}` | [Страница](https://math-ege.sdamgia.ru/problem?id=26830), [SVG](https://ege.sdamgia.ru/formula/svg/62/62f5ce2cd3437baf99bbfae57e614f94.svg) |
| 26830 | 67617 | `\sqrt{(a-3)^{2}}+\sqrt{(a-9)^{2}}` | [Страница](https://math-ege.sdamgia.ru/problem?id=67617), [SVG](https://ege.sdamgia.ru/formula/svg/89/89a8e6f4b14857b05dac27dc35432fb0.svg) |
| 26830 | 67669 | `\sqrt{(a-2)^{2}}+\sqrt{(a-4)^{2}}` | [Страница](https://math-ege.sdamgia.ru/problem?id=67669), [SVG](https://ege.sdamgia.ru/formula/svg/59/59cf31601c29fe93dc93e04a3a94f406.svg) |
| 26830 | 67619 | `\sqrt{(a-3)^{2}}+\sqrt{(a-5)^{2}}` | [Страница](https://math-ege.sdamgia.ru/problem?id=67619), [SVG](https://ege.sdamgia.ru/formula/svg/f1/f184942d588cf80dedb51dc3f7422013.svg) |

Для задач 26830, 67617, 67669 и 67619 исходные ограничения на переменную
сохранены без изменений. Положение квадратов под радикалами видно на SVG.
В задаче 65815 числитель содержит `a^{-1}b`; цифры 7 у `b` нет.
В задаче 549338 первое основание — 4, показатель — 1/5, второе основание — 16,
показатель — 9/10. Это подтверждено изображением исходного условия.

Локальные проверки охватывают все 16 транскрипций: независимые тождества,
идемпотентность, неизменность входа, подмену сохранённого ответа и решения,
отказ для неизвестного HTML и включение JSON в пакет. Общие правила решения
сохраняются; в отношении логарифмов с основаниями `a` и `a^r` явно показан
переход к одному основанию перед сокращением.
