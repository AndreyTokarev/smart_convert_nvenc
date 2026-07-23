# Документация smart_convert_nvenc

## Зачем проект

Большой архив **видеокурсов** съедает диск; файлы могут дублироваться. Нужно **сжать архив** (читаемые слайды + разборчивая речь), убрать/найти дубликаты и освободить место под новые курсы — быстро, через **NVIDIA NVENC**.

| Документ | Описание |
|----------|----------|
| [refactoring-plan.md](./refactoring-plan.md) | Цель, фазы, **журнал решений**, дорожная карта |
| [adr/README.md](./adr/README.md) | ADR: архитектурные решения |
| [adr/0001-course-inbox-outbox-tmp.md](./adr/0001-course-inbox-outbox-tmp.md) | Конвейер `courses/inbox` → `tmp` → `outbox` |
| [review-codec-advice.md](./review-codec-advice.md) | Рецензия исходного чата |
| [chat-optimal-mpeg4-codec.md](./chat-optimal-mpeg4-codec.md) | Исходный чат с другой моделью |

Отметки по открытым вопросам кодека — в **Журнале решений** внутри [refactoring-plan.md](./refactoring-plan.md).  
Решение по папкам курсов — в **ADR-0001**.
