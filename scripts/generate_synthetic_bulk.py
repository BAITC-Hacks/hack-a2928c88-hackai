"""Deterministic, explicitly synthetic catalogue expansion: 400 task scenarios."""
from app.schemas import CardContent, TaskCard
from app.rating import calculate_rating, confirm_fields

SECTORS = [
    ('Образование', 'учебный центр', 'заявок на курсы', 'администраторы курсов'),
    ('Розничная торговля', 'магазин', 'заказов товаров', 'менеджеры магазина'),
    ('Логистика', 'служба доставки', 'заявок на доставку', 'диспетчеры'),
    ('Туризм', 'туристическое бюро', 'запросов на экскурсии', 'координаторы туров'),
    ('Сельское хозяйство', 'фермерский кооператив', 'заявок на технику', 'координаторы хозяйства'),
    ('Производство', 'учебная мастерская', 'заказов на изготовление', 'мастера смены'),
    ('Культура', 'культурный центр', 'заявок на мероприятия', 'организаторы'),
    ('Спорт', 'спортивный клуб', 'заявок на занятия', 'администраторы клуба'),
    ('ЖКХ', 'сервисная компания', 'обращений по обслуживанию', 'диспетчеры обслуживания'),
    ('Экология', 'пункт переработки', 'заявок на приём материалов', 'координаторы приёма'),
]
WORKFLOWS = [
    ('Проверка полноты', 'выделять записи без обязательных сведений', 'реестр пропусков с объяснениями'),
    ('Поиск дублей', 'находить повторные записи и показывать пары для проверки человеком', 'список возможных дублей'),
    ('Навигация по статусам', 'собирать понятную сводку текущих статусов', 'панель статусов с фильтрами'),
    ('Поиск по справочнику', 'находить подходящие записи справочника по тексту запроса', 'поиск с цитатами из справочника'),
    ('Разбор свободного текста', 'преобразовывать свободное описание в редактируемые поля', 'редактор структурированных записей'),
    ('Контроль сроков', 'показывать записи с истёкшим указанным сроком', 'реестр сроков с объяснением правила'),
    ('Подготовка отчёта', 'собирать отчёт за выбранный период', 'отчёт с ссылками на исходные строки'),
    ('Сравнение версий', 'выделять изменения между двумя выгрузками', 'таблица добавлений и изменений'),
    ('Проверка формата', 'выявлять неверные форматы дат и идентификаторов', 'отчёт проверки с номерами строк'),
    ('Черновики ответов', 'готовить ответы только по переданному справочнику', 'редактируемые ответы с источниками'),
]


def generate(team_ids):
    assert team_ids
    result = {'drafts': [], 'cards': [], 'teams': [], 'proposals': []}
    keep = [
        {'title', 'context', 'need'},
        {'title', 'context', 'need', 'data', 'users'},
        {'title', 'context', 'need', 'data', 'users', 'expected_result', 'constraints'},
        set(CardContent.model_fields),
    ]
    for sector_index, (industry, business, records, users) in enumerate(SECTORS):
        for workflow_index, (name, action, output) in enumerate(WORKFLOWS):
            for completeness in range(4):
                n = len(result['cards']) + 1
                code = f'{n:04d}'
                size = 80 + 10 * sector_index + 5 * workflow_index + completeness
                content = dict(
                    title=f'{name}: {records} — учебный кейс {code}',
                    context=f'Вымышленный {business} «Сана-{code}» обрабатывает {size} {records} в месяц вручную.',
                    need=f'Нужно {action} для {records}; окончательные решения принимает сотрудник.',
                    users=f'Пользователи: {users} вымышленной организации «Сана-{code}».',
                    data=f'Для сценария предполагается CSV с {size} синтетическими записями и учебный справочник. Файлы не приложены; реальные данные не заявляются.',
                    constraints=f'Учебный прототип за {2 + workflow_index % 5} недели; без закрытых API и реальных персональных данных.',
                    expected_result=f'Работающий прототип: {output} для {records}, с возможностью ручной проверки.',
                    success_criteria=f'На 20 вручную размеченных учебных примерах не менее {16 + workflow_index % 4} результатов соответствуют эталону; исходные записи доступны для проверки. Это целевой критерий, не достигнутая метрика.',
                    contact=f'demo-{code}@example.com (вымышленный контакт)',
                    interaction_format='Учебная консультация раз в неделю; фактическая договорённость с бизнесом отсутствует.',
                    feedback_process='Автор учебного кейса сверяет прототип с контрольными примерами и возвращает замечания.',
                )
                content = {f: value if f in keep[completeness] else '' for f, value in content.items()}
                draft_id, card_id = f'BULK-D{code}', f'BULK-T{code}'
                text = 'СИНТЕТИЧЕСКИЙ СЦЕНАРИЙ. ' + ' '.join(value for field, value in content.items() if value and field != 'title')
                result['drafts'].append({'id': draft_id, 'industry': industry, 'text': text})
                card = TaskCard(id=card_id, draft_id=draft_id, industry=industry, synthetic=True, **content)
                fields = [f for f in CardContent.model_fields if getattr(card, f).strip()]
                confirmed = confirm_fields(card, fields, business_actor='synthetic-fixture-author')
                result['cards'].append({'id': card_id, 'draft_id': draft_id, 'score': calculate_rating(confirmed).total, **content})
                result['proposals'].append({
                    'task_id': card_id, 'team_id': team_ids[(n - 1) % len(team_ids)],
                    'idea': f'Синтетическое предложение: {output} для учебного кейса {code}.',
                    'plan': 'Уточнить пропуски с автором; подготовить синтетические примеры; реализовать прототип; показать проверку по эталону.',
                    'timeline': f'{2 + workflow_index % 5} недели',
                    'prototype_url': f'https://example.com/sana-synthetic/{code}',
                })
    return result
