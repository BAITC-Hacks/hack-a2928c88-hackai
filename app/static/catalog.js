// T-002: каталог для команд и решения бизнеса. Порядок и баллы приходят из API.
import {specificationPreview} from './specification.js';
const LEVELS = { draft: 'Черновик', working: 'Рабочая', ready: 'Готовая', priority: 'Приоритетная' };
const FIELDS = {
  context: 'Контекст', need: 'Задача', users: 'Пользователи', data: 'Данные',
  constraints: 'Ограничения', expected_result: 'Ожидаемый результат',
  success_criteria: 'Критерии успеха', contact: 'Контакт',
  interaction_format: 'Формат взаимодействия', feedback_process: 'Обратная связь',
};
const STATUSES = { pending: 'Ждёт решения', selected: 'Команда выбрана', rejected: 'Отклонён' };
const PAGE_SIZE = 20;
const INDUSTRY_CHIPS = 8;
const CONDITION_FIELDS = { title: 'Название', industry: 'Отрасль', ...FIELDS };
const COMPARED_FIELDS = {...CONDITION_FIELDS, technical_specification:'Техническое задание'};
const conditionText = value => typeof value === 'string' ? value.replace(/\r\n/g, '\n') : '';
function conditionValue(card, key) {
  if (key !== 'technical_specification') return conditionText(card[key]);
  const doc = card.technical_specification;
  if (!doc || typeof doc !== 'object') return '';
  // Compare agreed text and selected ideas, not timestamps, provider or internal IDs.
  const sections = {title:'Название ТЗ',summary:'Цель и результат',requirements:'Требования',
    architecture:'Подход и ограничения',acceptance:'Приёмка',plan:'Этапы',risks:'Риски',questions:'Вопросы'};
  const ideaFields = {title:'Название идеи',description:'Описание',rationale:'Польза',implementation:'Реализация',acceptance:'Проверка'};
  return [...Object.entries(sections).map(([field,label]) => `${label}: ${conditionText(doc[field])}`),
    ...(doc.ideas || []).map((idea,index) => `Идея ${index+1}\n` +
      Object.entries(ideaFields).map(([field,label]) => `${label}: ${conditionText(idea[field])}`).join('\n'))].join('\n\n');
}
const conditionRevision = value => Number.isInteger(value) && value > 0 ? value : null;

function validConditions(value, taskId) {
  return value && typeof value === 'object' && !Array.isArray(value)
    && typeof taskId === 'string' && value.id === taskId
    && Object.keys(CONDITION_FIELDS).every(key => value[key] == null || typeof value[key] === 'string');
}
let fieldId = 0;

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = String(text);
  if (className) node.className = className;
  return node;
}

function button(text, action, className) {
  const node = element('button', text, className);
  node.type = 'button';
  node.addEventListener('click', action);
  return node;
}

function labeled(text, input, className = 'catalog-field') {
  const label = element('label', undefined, className);
  input.setAttribute('aria-label', text);
  label.append(element('span', text), input);
  return label;
}

function plural(n, one, few, many) {
  const m10 = n % 10, m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few;
  return many;
}

function safeLink(value) {
  try {
    const url = new URL(value);
    if (!['http:', 'https:'].includes(url.protocol)) return null;
    const link = element('a', 'Открыть прототип ↗');
    link.href = url.href;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    return link;
  } catch { return null; }
}

function sourceLabel(sourceId) {
  const id = String(sourceId || '');
  if (id.startsWith('manual:')) return 'введено бизнесом вручную';
  if (id === 'draft') return 'из описания задачи';
  const answer = /^q-(\d+)$/.exec(id);
  return answer ? `из ответа на вопрос ${Number(answer[1]) + 1}` : `источник: ${id}`;
}

function ruler(card, small = true) {
  const total = card.rating?.total ?? 0, level = card.rating?.level || 'draft';
  const bar = element('div', undefined, 'ruler' + (small ? ' sm' : ''));
  bar.dataset.level = level;
  bar.style.setProperty('--v', String(total));
  bar.setAttribute('role', 'img');
  bar.setAttribute('aria-label', `Готовность ${total} из 100`);
  return bar;
}

function stamp(level) {
  return element('span', LEVELS[level] || 'Уровень не указан', `stamp stamp-${level}`);
}

function chip(name, value, text, count, checked) {
  const label = element('label', undefined, 'chip');
  const input = element('input');
  input.type = 'radio';
  input.name = name;
  input.value = value;
  input.checked = checked;
  input.setAttribute('aria-label', text);
  const face = element('span', text);
  if (count !== undefined) face.append(element('em', count));
  label.append(input, face);
  return label;
}

function currentInsights(card) {
  const insights = card.catalog_insights;
  return card.revision != null && insights?.revision === card.revision ? insights : null;
}

function validPosition(rank, total) {
  return Number.isInteger(rank) && Number.isInteger(total) && rank > 0 && rank <= total;
}

function positionLabel(card) {
  const insights = currentInsights(card);
  if (!insights || !validPosition(insights.rank, insights.total)) return null;
  return element('p', `Место №${insights.rank} из ${insights.total} в общем каталоге`, 'catalog-rank');
}

function improvementSection(card) {
  const section = element('section', undefined, 'catalog-insights');
  section.append(element('h4', 'Как бизнес может улучшить задачу'));
  const insights = currentInsights(card);
  if (card.synthetic) section.append(element('p', 'Общий каталог содержит учебные примеры. Эта карточка синтетическая.', 'muted'));
  if (!insights || !Array.isArray(insights.actions)) {
    section.append(element('p', 'Прогноз улучшений пока недоступен для этой версии карточки.'));
    return section;
  }
  if (!insights.actions.length) {
    section.append(element('p', 'Все поля рейтинга заполнены и подтверждены'));
    return section;
  }
  const scenarios = element('ol', undefined, 'catalog-scenarios');
  for (const action of insights.actions.slice(0, 3)) {
    if (!action || typeof action.label !== 'string' || !Number.isFinite(action.delta)
      || !Number.isFinite(action.score_after) || !Number.isFinite(card.rating?.total)) continue;
    const item = element('li');
    item.append(element('h5', action.label));
    if (action.instruction) item.append(element('p', action.instruction));
    item.append(element('p', `Изменение рейтинга: ${action.delta >= 0 ? '+' : ''}${action.delta} баллов.`, 'catalog-progress'),
      element('p', `При выполнении этого действия и повторной публикации: ${card.rating.total} → ${action.score_after} баллов.`));
    if (validPosition(action.rank_after, insights.total)) {
      item.append(element('p', `Предполагаемое место №${action.rank_after} из ${insights.total}.`));
    }
    scenarios.append(item);
  }
  section.append(element('p', 'Каждое действие — отдельный сценарий от текущей карточки. Прогнозы не суммируются.', 'muted'), scenarios,
    element('p', 'Предпросмотр по текущему состоянию каталога. Место изменится после подтверждения и публикации.', 'muted'));
  if (!scenarios.children.length) section.append(element('p', 'Прогноз улучшений пока недоступен для этой версии карточки.'));
  return section;
}

function reviewSection(card) {
  const section = element('section', undefined, 'catalog-review');
  section.append(element('h4', 'Что стоит уточнить до старта'));
  const insights = currentInsights(card);
  const review = card.catalog_insights?.review;
  if (review?.status === 'stale' || (review?.revision != null && review.revision !== card.revision)) {
    section.append(element('p', 'Карточка изменилась — результаты проверки устарели'));
    return section;
  }
  if (!insights) {
    section.append(element('p', 'Проверка недоступна для этой версии карточки.'));
    return section;
  }
  if (!review || review.status === 'not_run') {
    section.append(element('p', 'Проверка ещё не выполнена'));
    return section;
  }
  if (review.mode === 'mock') section.append(element('p', 'Демонстрационная проверка · mock. Это не реальный AI-анализ.', 'tag tag-warn'));
  if (review.status !== 'complete' || review.revision !== card.revision || !Array.isArray(review.issues)) {
    section.append(element('p', 'Проверка сейчас недоступна. Это не мешает отправить отклик.'));
    return section;
  }
  if (!review.issues.length) {
    section.append(element('p', 'Проверка не выявила замечаний; это не гарантия реализуемости'));
    return section;
  }
  for (const issue of review.issues.slice(0, 3)) {
    if (!issue) continue;
    const item = element('article', undefined, 'catalog-review-issue');
    item.append(element('h5', FIELDS[issue.field] || (issue.field === 'title' ? 'Название' : issue.field || 'Карточка')),
      element('p', issue.kind === 'rule' ? 'Проверка правилом'
        : issue.kind === 'ai' ? 'AI-предположение — требует проверки человеком'
          : 'Замечание — требует проверки человеком', 'muted'));
    if (issue.quote) item.append(element('blockquote', issue.quote));
    if (issue.message) item.append(element('p', issue.message));
    if (issue.question) item.append(element('p', `Вопрос бизнесу: ${issue.question}`));
    section.append(item);
  }
  return section;
}

/** Mount with the Promise-based adapter from TEAM.md. Returns refresh() and focusCard(card). */
export function mountCatalog(root, api) {
  const panel = element('div', undefined, 'catalog-panel catalog-screen');
  root.replaceChildren(panel);

  const state = {
    q: '', industry: '', level: '', page: 0, total: 0, cards: [], facets: null,
    teams: [], teamId: '', recs: [], selected: null, proposals: [], tab: 'task',
    pinned: null, showAllIndustries: false,
  };
  let busy = false;
  // Drafts belong to tasks, not to the current tab, page, or team persona.
  const drafts = new Map();
  const conditionChecks = new Map();
  const expandedConditions = new Set();
  const expandedSnapshots = new Set();

  // Header with team persona
  const persona = element('select');
  persona.id = 'catalog-persona';
  persona.addEventListener('change', () => { state.teamId = persona.value; void loadRecs(); });
  const head = element('header', undefined, 'catalog-head');
  const headCopy = element('div');
  headCopy.append(element('p', 'Командам', 'eyebrow'), element('h2', 'Задачи бизнеса'),
    element('p', 'Все опубликованные задачи доступны любой команде. Выше — те, что готовы к работе. Низкий рейтинг не запрещает отклик.', 'muted catalog-lede'));
  head.append(headCopy, labeled('Вы — команда', persona, 'catalog-field catalog-persona'));

  // Filters
  const filters = element('form', undefined, 'catalog-filters');
  filters.setAttribute('role', 'search');
  const search = element('input');
  search.type = 'search';
  search.id = 'catalog-q';
  search.placeholder = 'чат-бот, CSV, расписание, конвейер…';
  search.maxLength = 200;
  const find = element('button', 'Найти', 'btn-primary');
  find.type = 'submit';
  const searchRow = element('div', undefined, 'catalog-search');
  searchRow.append(labeled('Поиск по задачам', search), find);
  const levelChips = element('fieldset', undefined, 'chips catalog-levels');
  const industryChips = element('fieldset', undefined, 'chips catalog-industries');
  filters.append(searchRow, levelChips, industryChips);

  const notice = element('p', '', 'catalog-notice');
  notice.setAttribute('role', 'status');
  notice.setAttribute('aria-live', 'polite');

  const recsBox = element('section', undefined, 'catalog-recs');
  recsBox.setAttribute('aria-label', 'Рекомендации для команды');
  recsBox.hidden = true;

  const layout = element('div', undefined, 'catalog-layout');
  const listCol = element('div', undefined, 'catalog-list');
  listCol.setAttribute('aria-label', 'Опубликованные задачи');
  const detail = element('section', undefined, 'catalog-detail');
  detail.setAttribute('aria-label', 'Карточка задачи');
  const backdrop = element('div', undefined, 'catalog-backdrop');
  backdrop.addEventListener('click', closeSheet);
  layout.append(listCol, detail, backdrop);
  panel.append(head, filters, notice, recsBox, layout);

  function say(text, error = false) {
    notice.textContent = text;
    notice.classList.toggle('catalog-error', error);
    notice.classList.toggle('msg', error);
    notice.classList.toggle('msg-error', error);
    notice.setAttribute('role', error ? 'alert' : 'status');
  }

  // Serialize requests so double clicks and late responses cannot change another card.
  async function run(message, work) {
    if (busy) return;
    busy = true;
    const controls = [...panel.querySelectorAll('button, input, select, textarea')];
    const disabled = controls.map(node => node.disabled);
    controls.forEach(node => { node.disabled = true; });
    panel.setAttribute('aria-busy', 'true');
    say(message);
    try { await work(); }
    catch (error) { say(`Не удалось выполнить действие. ${error?.message || 'Попробуйте ещё раз.'}`, true); }
    finally {
      controls.forEach((node, index) => { if (node.isConnected) node.disabled = disabled[index]; });
      busy = false;
      panel.setAttribute('aria-busy', 'false');
    }
  }

  function renderFilters() {
    const levels = state.facets?.levels || {};
    levelChips.replaceChildren(element('legend', 'Готовность', 'visually-hidden'),
      chip('catalog-level', '', 'Все уровни', state.facets?.total, state.level === ''),
      ...Object.entries(LEVELS).map(([value, text]) => chip('catalog-level', value, text, levels[value] ?? 0, state.level === value)));
    const industries = state.facets?.industries || [];
    const shown = state.showAllIndustries ? industries : industries.slice(0, INDUSTRY_CHIPS);
    if (state.industry && !shown.some(i => i.name === state.industry)) {
      const current = industries.find(i => i.name === state.industry);
      if (current) shown.push(current);
    }
    industryChips.replaceChildren(element('legend', 'Отрасль', 'visually-hidden'),
      chip('catalog-industry', '', 'Все отрасли', undefined, state.industry === ''),
      ...shown.map(i => chip('catalog-industry', i.name, i.name, i.count, state.industry === i.name)));
    if (industries.length > INDUSTRY_CHIPS) {
      const more = button(state.showAllIndustries ? 'Свернуть' : `Ещё ${industries.length - INDUSTRY_CHIPS}`, () => {
        state.showAllIndustries = !state.showAllIndustries;
        renderFilters();
      }, 'btn-quiet catalog-more');
      industryChips.append(more);
    }
  }

  filters.addEventListener('change', event => {
    if (event.target.name === 'catalog-level') state.level = event.target.value;
    else if (event.target.name === 'catalog-industry') state.industry = event.target.value;
    else return;
    state.page = 0;
    void loadPage('Фильтруем…');
  });
  filters.addEventListener('submit', event => {
    event.preventDefault();
    state.q = search.value.trim();
    state.page = 0;
    void loadPage('Ищем…');
  });

  function renderPersona() {
    persona.replaceChildren(element('option', 'Не выбрана'));
    persona.firstChild.value = '';
    for (const team of state.teams) {
      const option = element('option', team.name);
      option.value = String(team.id);
      option.selected = String(team.id) === state.teamId;
      persona.append(option);
    }
  }

  async function loadRecs() {
    if (!state.teamId) { state.recs = []; renderRecs(); renderDetail(); return; }
    await run('Подбираем задачи для команды…', async () => {
      state.recs = await api.teamRecommendations(state.teamId, 5);
      renderRecs();
      renderDetail();
      say(state.recs.length ? `Рекомендации обновлены: ${state.recs.length}.` : 'Для этой команды совпадений по профилю нет. Каталог доступен целиком.');
    });
  }

  function renderRecs() {
    const team = state.teams.find(t => String(t.id) === state.teamId);
    recsBox.hidden = !team || !state.recs.length;
    if (recsBox.hidden) { recsBox.replaceChildren(); return; }
    const list = element('ol', undefined, 'catalog-recs-list');
    for (const card of state.recs) {
      const item = element('li');
      const open = button('', () => openCard(card), 'catalog-rec');
      open.append(element('span', card.industry, 'eyebrow'), element('span', card.title, 'catalog-rec-title'),
        ruler(card), element('span', `${card.rating.total} · ${card.matched.slice(0, 2).join(', ')}`, 'catalog-rec-why num'));
      item.append(open);
      list.append(item);
    }
    const title = element('div', undefined, 'catalog-recs-head');
    title.append(element('h3', `Подходят команде ${team.name}`),
      element('p', 'По совпадению слов профиля команды с текстом задачи. Только задачи от 40 баллов. Остальной каталог не скрыт.', 'muted'));
    recsBox.replaceChildren(title, list);
  }

  function cardRow(card, {pinned = false} = {}) {
    const level = card.rating?.level || 'draft';
    const item = element('article', undefined, `catalog-card level-${level}`);
    item.classList.toggle('catalog-active', card.id === state.selected?.id);
    item.classList.toggle('is-pinned', pinned);
    if (pinned) item.append(element('p', 'Только что опубликовано', 'catalog-pin'));
    const title = element('h3');
    const open = button(card.title || 'Задача без названия', () => openCard(card), 'catalog-open');
    open.setAttribute('aria-pressed', String(card.id === state.selected?.id));
    title.append(open);
    const score = element('div', undefined, 'catalog-score');
    score.append(element('b', card.rating?.total ?? '—', 'num'), stamp(level));
    const foot = element('p', undefined, 'catalog-foot');
    const count = card.proposals_count ?? 0;
    foot.append(element('span', `${count} ${plural(count, 'отклик', 'отклика', 'откликов')}`));
    if ((card.rating?.total ?? 0) < 40) foot.append(element('span', 'Нужны уточнения', 'tag tag-warn'));
    if (card.mode === 'live') foot.append(element('span', 'AI live', 'tag tag-live'));
    item.append(element('p', card.industry || 'Отрасль не указана', 'eyebrow'), title, score, ruler(card), foot);
    if (card.synthetic) foot.append(element('span', 'Синтетический пример', 'tag'));
    if (card.mode === 'mock') foot.append(element('span', 'Демо · mock', 'tag tag-mock'));
    const position = positionLabel(card);
    if (position) item.append(position);
    return item;
  }

  function renderList() {
    const pages = Math.max(1, Math.ceil(state.total / PAGE_SIZE));
    const from = state.total ? state.page * PAGE_SIZE + 1 : 0;
    const to = Math.min(state.total, (state.page + 1) * PAGE_SIZE);
    const header = element('header', undefined, 'catalog-list-head');
    header.append(element('span', `Найдено задач: ${state.total}`), element('span', 'по готовности ↓', 'muted'));
    const nodes = [header];
    if (state.pinned && !state.cards.some(c => c.id === state.pinned.id)) nodes.push(cardRow(state.pinned, {pinned: true}));
    if (!state.cards.length) {
      const empty = element('div', undefined, 'catalog-empty');
      empty.append(element('p', 'Под эти фильтры задач нет.'),
        button('Сбросить фильтры', () => { resetFilters(); void loadPage('Сбрасываем фильтры…'); }, 'btn-quiet'));
      nodes.push(empty);
    }
    for (const card of state.cards) nodes.push(cardRow(card, {pinned: card.id === state.pinned?.id}));
    if (pages > 1) {
      const nav = element('nav', undefined, 'catalog-pager');
      nav.setAttribute('aria-label', 'Страницы каталога');
      nav.append(element('span', `${from}–${to} из ${state.total}`, 'muted num'));
      const go = page => () => { state.page = page; void loadPage('Загружаем страницу…', {scroll: true}); };
      const numbers = element('div', undefined, 'catalog-pages');
      const prev = button('←', go(state.page - 1));
      prev.disabled = state.page === 0;
      prev.setAttribute('aria-label', 'Предыдущая страница');
      numbers.append(prev);
      const wanted = [...new Set([0, state.page - 1, state.page, state.page + 1, pages - 1])].filter(p => p >= 0 && p < pages).sort((a, b) => a - b);
      wanted.forEach((p, i) => {
        if (i && p - wanted[i - 1] > 1) numbers.append(element('span', '…', 'muted'));
        const b = button(String(p + 1), go(p), 'num');
        if (p === state.page) b.setAttribute('aria-current', 'page');
        numbers.append(b);
      });
      const next = button('→', go(state.page + 1));
      next.disabled = state.page >= pages - 1;
      next.setAttribute('aria-label', 'Следующая страница');
      numbers.append(next);
      nav.append(numbers);
      nodes.push(nav);
    }
    listCol.replaceChildren(...nodes);
  }

  function resetFilters() {
    state.q = state.industry = state.level = '';
    search.value = '';
    state.page = 0;
  }

  function openCard(card) {
    return run('Загружаем отклики…', async () => {
      const loaded = await api.listProposals(card.id);
      state.selected = card;
      state.proposals = loaded;
      state.tab = 'task';
      renderList();
      renderDetail();
      openSheet();
      say(`Открыта задача «${card.title || 'без названия'}».`);
      detail.querySelector('h3')?.focus({preventScroll: true});
    });
  }

  function isSheet() { return matchMedia('(max-width: 760px)').matches; }
  function openSheet() {
    if (!isSheet()) return;
    detail.classList.add('is-open');
    backdrop.classList.add('is-open');
  }
  function closeSheet() {
    detail.classList.remove('is-open');
    backdrop.classList.remove('is-open');
    listCol.querySelector('.catalog-active .catalog-open')?.focus({preventScroll: true});
  }
  detail.addEventListener('keydown', event => { if (event.key === 'Escape') closeSheet(); });

  function renderEmptyDetail() {
    const box = element('div', undefined, 'catalog-empty-detail');
    box.append(element('h3', 'Выберите задачу'),
      element('p', 'Откройте карточку слева, чтобы прочитать условия, отправить отклик от команды или, от лица бизнеса, выбрать команду.', 'muted'));
    const legend = element('ul', undefined, 'catalog-legend');
    for (const [level, range, note] of [['priority', '90–100', 'полностью готова, выделена'], ['ready', '70–89', 'выше в каталоге'],
      ['working', '40–69', 'можно рекомендовать'], ['draft', '0–39', 'видна, нужны уточнения']]) {
      const li = element('li');
      li.append(stamp(level), element('span', range, 'num'), element('span', note, 'muted'));
      legend.append(li);
    }
    box.append(legend);
    return box;
  }

  function renderDetail() {
    const card = state.selected;
    if (!card) { detail.replaceChildren(renderEmptyDetail()); return; }
    const top = element('div', undefined, 'catalog-detail-head');
    const close = button('Закрыть', closeSheet, 'btn-quiet catalog-close');
    const meta = element('p', undefined, 'eyebrow');
    meta.textContent = [card.industry, card.first_published_at ? 'опубликовано ' + new Date(card.first_published_at).toLocaleDateString('ru-RU') : ''].filter(Boolean).join(' · ');
    const title = element('h3', card.title || 'Задача без названия');
    title.tabIndex = -1;
    const scoreLine = element('div', undefined, 'catalog-detail-score');
    scoreLine.append(element('b', card.rating?.total ?? '—', 'num'), ruler(card, false), stamp(card.rating?.level || 'draft'));
    const badges = element('div', undefined, 'catalog-badges');
    if (card.synthetic) badges.append(element('span', 'Синтетический пример', 'tag'));
    if (card.mode === 'mock') badges.append(element('span', 'Карточка собрана без реального AI', 'tag tag-mock'));
    if ((card.rating?.total ?? 0) < 40) badges.append(element('span', 'Нужны уточнения — откликаться можно', 'tag tag-warn'));
    top.append(close, meta, title, scoreLine, badges);
    const position = positionLabel(card);
    if (position) top.append(position);

    const tabs = element('div', undefined, 'tabs catalog-tabs');
    tabs.setAttribute('role', 'tablist');
    const tabDefs = [['task', 'Задача'], ['apply', 'Откликнуться'], ['proposals', 'Отклики']];
    for (const [key, text] of tabDefs) {
      const tab = button(text, () => { state.tab = key; renderDetail(); detail.querySelector(`[data-tab="${key}"]`)?.focus(); });
      tab.dataset.tab = key;
      tab.setAttribute('role', 'tab');
      tab.setAttribute('aria-selected', String(state.tab === key));
      if (key === 'proposals') tab.append(element('em', state.proposals.length, 'num'));
      tabs.append(tab);
    }
    const body = element('div', undefined, 'catalog-tabpanel');
    body.setAttribute('role', 'tabpanel');
    if (state.tab === 'task') body.append(...taskPanel(card));
    else if (state.tab === 'apply') body.append(proposalForm(card));
    else body.append(proposalSection(card));
    detail.replaceChildren(top, tabs, body);
  }

  function taskPanel(card) {
    const nodes = [];
    if (card.technical_specification) {
      const spec = element('details', undefined, 'catalog-specification');
      spec.append(element('summary', 'Техническое задание, утверждённое бизнесом'));
      const download = element('a', 'Скачать утверждённое ТЗ в PDF', 'spec-download');
      download.href = `/api/cards/${encodeURIComponent(card.id)}/specification.pdf`;
      download.download = 'sana-specification.pdf';
      spec.append(download, specificationPreview(card.technical_specification));
      nodes.push(spec);
    }
    const rec = state.recs.find(r => r.id === card.id);
    const team = state.teams.find(t => String(t.id) === state.teamId);
    if (rec && team) nodes.push(element('p', `Совпадает с профилем ${team.name}: ${rec.matched.join(', ')}.`, 'catalog-fit'));
    const facts = element('dl', undefined, 'catalog-facts');
    for (const [key, label] of Object.entries(FIELDS)) {
      const value = element('dd', card[key] || 'Не указано');
      if (!card[key]) value.classList.add('is-empty');
      if (card.confirmed_fields?.includes(key)) value.append(element('small', '✓ подтверждено бизнесом', 'catalog-confirmed'));
      const evidence = card.evidence?.[key];
      if (evidence?.quote && evidence.quote !== card[key]) value.append(element('blockquote', evidence.quote));
      if (evidence?.source_id) value.append(element('small', sourceLabel(evidence.source_id), 'muted'));
      facts.append(element('dt', label), value);
    }
    nodes.push(facts);
    const rating = element('details', undefined, 'catalog-rating');
    rating.append(element('summary', 'Из чего складывается рейтинг'));
    const items = element('ul', undefined, 'catalog-rating-items');
    for (const item of card.rating?.items || []) {
      const li = element('li');
      li.append(element('span', item.label), element('span', `${item.earned} / ${item.maximum}`, 'num'));
      items.append(li);
    }
    rating.append(items);
    const gains = card.rating?.gains || [];
    if (gains.length) {
      rating.append(element('p', 'Бизнес может поднять рейтинг: ' + gains.map(g => `${FIELDS[g.field] || g.field} +${g.points}`).join(', ') + '.', 'muted'));
    }
    nodes.push(rating, reviewSection(card), improvementSection(card));
    const cta = button('Откликнуться на задачу', () => { state.tab = 'apply'; renderDetail(); }, 'btn-primary catalog-cta');
    nodes.push(cta);
    return nodes;
  }

  function teamSummary(team) {
    if (!team) return '';
    return ['interests', 'skills', 'technologies'].map((key, i) => {
      const value = team[key];
      return `${['Интересы', 'Навыки', 'Технологии'][i]}: ${Array.isArray(value) ? value.join(', ') : value || 'не указаны'}`;
    }).join(' · ');
  }

  function proposalForm(card) {
    const form = element('form', undefined, 'catalog-proposal-form');
    form.noValidate = true;
    const draft = drafts.get(card.id) || {team_id: state.teamId};
    form.append(element('h4', 'Предложить решение'),
      element('p', 'Отклик увидит бизнес. Он сам сравнивает предложения и выбирает команду — система никого не назначает.', 'muted'));
    const team = element('select');
    team.required = true;
    team.name = 'team_id';
    const placeholder = element('option', state.teams.length ? 'Выберите учебную команду' : 'Нет доступных команд');
    placeholder.value = '';
    team.append(placeholder);
    for (const item of state.teams) {
      const option = element('option', item.name);
      option.value = String(item.id);
      option.selected = String(item.id) === draft.team_id;
      team.append(option);
    }
    team.value = draft.team_id || '';
    const teamInfo = element('p', teamSummary(state.teams.find(t => String(t.id) === team.value)), 'muted catalog-team-info');
    team.addEventListener('change', () => { teamInfo.textContent = teamSummary(state.teams.find(t => String(t.id) === team.value)); });
    form.append(labeled('Учебная команда', team), teamInfo);
    const inputs = {};
    for (const [key, label, tag, hint] of [
      ['idea', 'Идея решения', 'textarea', 'Что сделаете и почему это решит задачу'],
      ['plan', 'План работы', 'textarea', '3–5 шагов'],
      ['timeline', 'Срок', 'input', 'Например: 4 недели'],
      ['prototype_url', 'Ссылка на прототип или репозиторий', 'input', 'https://'],
    ]) {
      const input = element(tag);
      input.name = key;
      input.value = draft[key] || '';
      input.required = true;
      input.placeholder = hint;
      if (tag === 'textarea') input.rows = 3;
      if (key === 'prototype_url') input.type = 'url';
      input.addEventListener('input', () => input.setCustomValidity(''));
      inputs[key] = input;
      form.append(labeled(label, input));
    }
    const saveDraft = () => drafts.set(card.id, {team_id: team.value,
      ...Object.fromEntries(Object.entries(inputs).map(([key, input]) => [key, input.value]))});
    form.addEventListener('input', saveDraft);
    form.addEventListener('change', saveDraft);
    // Store the initial persona too, so later persona changes cannot move this draft.
    saveDraft();
    const urlInput = inputs.prototype_url;
    const urlError = element('small', '', 'catalog-field-error');
    urlError.id = `catalog-prototype-error-${++fieldId}`;
    urlError.setAttribute('aria-live', 'polite');
    urlInput.setAttribute('aria-describedby', urlError.id);
    urlInput.parentElement.append(urlError);
    function validatePrototype() {
      const value = urlInput.value.trim();
      const message = !value ? 'Укажите ссылку на прототип.'
        : !/^https?:\/\//i.test(value) || !safeLink(value)
          ? 'Укажите корректную ссылку на прототип с http:// или https://.' : '';
      urlError.textContent = message;
      urlInput.setCustomValidity(message);
      urlInput.setAttribute('aria-invalid', String(Boolean(message)));
    }
    urlInput.addEventListener('input', () => {
      if (urlError.textContent) validatePrototype();
    });
    const submit = element('button', 'Отправить отклик', 'btn-primary');
    submit.type = 'submit';
    submit.disabled = !state.teams.length;
    form.append(submit);
    form.addEventListener('submit', event => {
      event.preventDefault();
      if (busy) return;
      for (const input of Object.values(inputs)) {
        input.setCustomValidity(input.required && !input.value.trim() ? 'Заполните поле.' : '');
      }
      validatePrototype();
      if (!form.reportValidity()) return;
      const selected = state.teams.find(item => String(item.id) === team.value);
      if (!selected) return;
      run('Отправляем отклик…', async () => {
        const proposal = await api.createProposal(card.id, {
          team_id: selected.id, ...Object.fromEntries(Object.entries(inputs).map(([key, input]) => [key, input.value.trim()])),
        });
        state.proposals = [...state.proposals.filter(item => item.id !== proposal.id), proposal];
        drafts.delete(card.id);
        if (conditionChecks.get(card.id)?.status !== 'loading') conditionChecks.delete(card.id);
        bumpCount(card.id, state.proposals.length);
        state.tab = 'proposals';
        renderList();
        renderDetail();
        say('Отклик отправлен. Он появился во вкладке «Отклики» для бизнеса.');
      });
    });
    return form;
  }

  function bumpCount(cardId, count) {
    const update = c => (c && c.id === cardId ? {...c, proposals_count: count} : c);
    state.cards = state.cards.map(update);
    state.pinned = update(state.pinned);
    state.selected = update(state.selected);
  }

  function renderConditionResults(taskId) {
    // An independent read must never replace another task's panel or its draft.
    if (state.selected?.id !== taskId || state.tab !== 'proposals') return;
    detail.querySelector('.catalog-proposals')?.replaceWith(proposalSection(state.selected));
  }

  async function checkConditions(taskId) {
    if (conditionChecks.get(taskId)?.status === 'loading') return;
    // Discard the previous result immediately: a failed refresh is not a current check.
    const check = {status: 'loading'};
    conditionChecks.set(taskId, check);
    renderConditionResults(taskId);
    try {
      const published = await api.listCards({});
      if (!Array.isArray(published)) throw new Error('Invalid catalogue response');
      const current = published.find(card => card?.id === taskId && card.published !== false);
      check.checkedAt = new Date().toLocaleString('ru-RU');
      if (!current) check.status = 'unavailable';
      else {
        if (!validConditions(current, taskId)) throw new Error('Invalid published conditions');
        check.card = current;
        check.status = 'complete';
      }
    } catch {
      check.status = 'error';
      delete check.card;
      delete check.checkedAt;
    }
    renderConditionResults(taskId);
  }

  function conditionsHistory(proposal) {
    const history = element('details', undefined, 'catalog-conditions');
    history.open = expandedConditions.has(proposal.id);
    history.addEventListener('toggle', () => {
      if (history.isConnected) {
        if (history.open) expandedConditions.add(proposal.id);
        else expandedConditions.delete(proposal.id);
      }
    });
    const summary = element('summary', 'Условия на момент отклика');
    history.append(summary);
    const snapshot = proposal.task_snapshot;
    if (snapshot == null) {
      history.append(element('p', 'Условия на момент отклика не сохранены', 'muted'));
      return history;
    }
    if (!validConditions(snapshot, proposal.task_id)) {
      history.append(element('p', 'История условий недоступна: сохранённый снимок не соответствует задаче.', 'muted'));
      return history;
    }
    const revision = conditionRevision(proposal.card_revision) ?? conditionRevision(snapshot.revision);
    history.append(element('p', revision ? `Отклик на версию ${revision}.` : 'Версия условий отклика неизвестна.', 'muted'));
    const check = conditionChecks.get(proposal.task_id);
    const compare = button(check?.status === 'error' ? 'Повторить проверку условий' : 'Проверить опубликованные условия',
      () => checkConditions(proposal.task_id), 'btn-quiet');
    compare.disabled = check?.status === 'loading';
    history.append(compare);
    const result = element('div', undefined, 'catalog-conditions-result');
    result.setAttribute('role', 'status');
    if (!check) result.append(element('p', 'Проверка ещё не выполнена. Один запрос обновит сравнение для всех откликов этой задачи.', 'muted'));
    else if (check.status === 'loading') result.append(element('p', 'Проверяем опубликованные условия…'));
    else if (check.status === 'error') result.append(element('p', 'Не удалось проверить актуальные условия', 'catalog-field-error'));
    else {
      result.append(element('p', `Время проверки: ${check.checkedAt}.`, 'muted'));
      if (check.status === 'unavailable') result.append(element('p', 'Опубликованная версия недоступна'));
      else if (revision && conditionRevision(check.card.revision) && check.card.revision < revision) {
        result.append(element('p', 'Сохранённая проверка старше версии отклика. Проверьте опубликованные условия ещё раз.'));
      } else {
        const currentRevision = conditionRevision(check.card.revision);
        result.append(element('p', currentRevision ? `Проверена опубликованная версия ${currentRevision}.` : 'Номер проверенной опубликованной версии неизвестен.', 'muted'));
        const changes = Object.entries(COMPARED_FIELDS).filter(([key]) => conditionValue(snapshot,key) !== conditionValue(check.card,key));
        if (!changes.length) result.append(element('p', 'На момент проверки опубликованные условия совпадают с условиями отклика'));
        else {
          summary.append(element('span', 'Условия изменились после отклика', 'tag tag-warn'));
          result.append(element('p', `Изменено ${changes.length} ${plural(changes.length, 'поле', 'поля', 'полей')}.`, 'catalog-progress'));
          const table = element('table', undefined, 'catalog-conditions-table');
          table.append(element('caption', 'Изменения опубликованных условий'));
          const head = element('thead');
          const headers = element('tr');
          for (const label of ['Поле', 'Было', 'Опубликовано сейчас']) {
            const cell = element('th', label); cell.scope = 'col'; headers.append(cell);
          }
          head.append(headers);
          const body = element('tbody');
          for (const [key, label] of changes) {
            const row = element('tr');
            const name = element('th', label); name.scope = 'row';
            row.append(name, element('td', conditionValue(snapshot,key) || 'Не указано'),
              element('td', conditionValue(check.card,key) || 'Не указано'));
            body.append(row);
          }
          table.append(head, body);
          result.append(table);
        }
      }
    }
    history.append(result);
    const saved = element('details', undefined, 'catalog-snapshot');
    saved.open = expandedSnapshots.has(proposal.id);
    saved.addEventListener('toggle', () => {
      if (!saved.isConnected) return;
      if (saved.open) expandedSnapshots.add(proposal.id);
      else expandedSnapshots.delete(proposal.id);
    });
    saved.append(element('summary', 'Сохранённый снимок условий'));
    const fields = element('dl', undefined, 'catalog-facts');
    for (const [key, label] of Object.entries(COMPARED_FIELDS)) {
      fields.append(element('dt', label), element('dd', conditionValue(snapshot,key) || 'Не указано'));
    }
    saved.append(fields);
    history.append(saved, element('p', 'Изменение условий не означает согласие команды. Обсудите изменения перед началом работы.', 'muted'));
    return history;
  }

  function proposalSection(card) {
    const section = element('section', undefined, 'catalog-proposals');
    section.append(element('h4', 'Бизнесу: отклики команд'),
      element('p', 'Сравните предложения и решите вручную: можно выбрать несколько команд или ни одной. Баллы прогресса команды считаются отдельно от рейтинга задачи.', 'muted'));
    if (!state.proposals.length) {
      section.append(element('p', 'Откликов пока нет. Первая команда может откликнуться во вкладке «Откликнуться».', 'catalog-empty'));
      return section;
    }
    const grid = element('div', undefined, 'catalog-compare');
    for (const proposal of state.proposals) {
      const team = state.teams.find(t => t.id === proposal.team_id);
      const item = element('article', undefined, `catalog-proposal status-${proposal.status}`);
      const who = element('div', undefined, 'catalog-proposal-who');
      who.append(element('h5', proposal.team_name || `Команда ${proposal.team_id}`),
        element('span', STATUSES[proposal.status] || proposal.status, `tag status-tag status-${proposal.status}`));
      if (team) {
        const tags = element('div', undefined, 'catalog-skills');
        for (const skill of [...team.skills, ...team.technologies].slice(0, 5)) tags.append(element('span', skill));
        who.append(tags);
      }
      const what = element('div', undefined, 'catalog-proposal-what');
      for (const [key, label] of [['idea', 'Идея'], ['plan', 'План'], ['timeline', 'Срок']]) {
        const row = element('p');
        row.append(element('b', label + ': '), document.createTextNode(proposal[key] || 'Не указано'));
        what.append(row);
      }
      const link = safeLink(proposal.prototype_url);
      if (link) what.append(link);
      const decide = element('div', undefined, 'catalog-proposal-decide');
      decide.append(element('p', `Баллы прогресса: ${proposal.progress_points ?? 0}`, 'catalog-progress num'));
      const actions = element('div', undefined, 'catalog-actions');
      for (const [action, label, status] of [['select', 'Выбрать', 'selected'], ['reject', 'Отклонить', 'rejected']]) {
        const control = button(label, () => run('Сохраняем решение…', async () => {
          const updated = await api.decideProposal(proposal.id, { action });
          state.proposals = state.proposals.map(current => current.id === updated.id ? updated : current);
          renderDetail();
          say('Статус отклика обновлён.');
        }), action === 'select' ? 'btn-primary' : '');
        control.disabled = proposal.status === status;
        actions.append(control);
      }
      if (proposal.status === 'selected') {
        actions.append(button('Подтвердить этап', () => run('Подтверждаем этап…', async () => {
          const result = await api.confirmMilestone(proposal.id);
          // Never add points locally: reload the server's authoritative balance.
          try {
            state.proposals = await api.listProposals(card.id);
            renderDetail();
          } catch (error) {
            say(`Этап подтверждён, но баллы не удалось обновить. Обновите каталог. ${error?.message || ''}`, true);
            return;
          }
          say(result.already_awarded ? 'Этот этап уже подтверждён. Повторного начисления нет.' : `Этап подтверждён. Баллы за этап: ${result.points}.`);
        })));
      }
      decide.append(actions);
      item.append(who, what, decide, conditionsHistory(proposal));
      grid.append(item);
    }
    section.append(grid);
    return section;
  }

  async function fetchPage() {
    const page = await api.listCardsPage({q: state.q, industry: state.industry, level: state.level,
      limit: PAGE_SIZE, offset: state.page * PAGE_SIZE});
    state.cards = page.items.filter(card => card.published !== false);
    state.total = page.total;
  }

  function loadPage(message, {scroll = false} = {}) {
    return run(message, async () => {
      await fetchPage();
      renderFilters();
      renderList();
      say(`Найдено задач: ${state.total}.`);
      if (scroll) listCol.scrollIntoView({block: 'start', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
    });
  }

  function refresh() {
    return run('Загружаем каталог…', async () => {
      const [facets, teams] = await Promise.all([api.catalogFacets(), api.listTeams()]);
      state.facets = facets;
      state.teams = teams;
      const industryRemoved = state.industry && !facets.industries.some(item => item.name === state.industry);
      if (industryRemoved) { state.industry = ''; state.page = 0; }
      await fetchPage();
      if (state.page > 0 && !state.cards.length) {
        state.page = Math.max(0, Math.ceil(state.total / PAGE_SIZE) - 1);
        await fetchPage();
      }
      state.selected = state.cards.find(card => card.id === state.selected?.id) || state.selected;
      if (state.selected) state.proposals = await api.listProposals(state.selected.id);
      renderPersona();
      renderFilters();
      renderList();
      renderDetail();
      say(`${industryRemoved ? 'Выбранная отрасль исчезла; фильтр сброшен. ' : ''}Каталог обновлён. Опубликованных задач: ${facets.total}.`);
    });
  }

  /** Show a card that was just published, even if it is not on the current page. */
  async function focusCard(card) {
    state.pinned = {...card, proposals_count: card.proposals_count ?? 0};
    resetFilters();
    await refresh();
    await openCard(state.pinned);
    listCol.querySelector('.is-pinned')?.scrollIntoView({block: 'nearest'});
  }

  renderDetail();
  void refresh();
  return { refresh, focusCard };
}
