const LEVELS = { draft: 'Черновик', working: 'Рабочая', ready: 'Готовая', priority: 'Приоритетная' };
const FIELDS = {
  context: 'Контекст', need: 'Задача', users: 'Пользователи', data: 'Данные',
  constraints: 'Ограничения', expected_result: 'Ожидаемый результат',
  success_criteria: 'Критерии успеха', contact: 'Контакт',
  interaction_format: 'Формат взаимодействия', feedback_process: 'Обратная связь',
};
const STATUSES = { pending: 'На рассмотрении', selected: 'Команда выбрана', rejected: 'Отклонён' };
let fieldId = 0;

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = String(text);
  if (className) node.className = className;
  return node;
}

function button(text, action) {
  const node = element('button', text);
  node.type = 'button';
  node.addEventListener('click', action);
  return node;
}

function labeled(text, input) {
  const label = element('label', undefined, 'catalog-field');
  input.setAttribute('aria-label', text);
  label.append(element('span', text), input);
  return label;
}

function safeLink(value) {
  try {
    const url = new URL(value);
    if (!['http:', 'https:'].includes(url.protocol)) return null;
    const link = element('a', 'Открыть прототип');
    link.href = url.href;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    return link;
  } catch { return null; }
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
  if (card.synthetic) section.append(element('p', 'Общий каталог содержит учебные примеры. Эта карточка синтетическая.', 'catalog-muted'));
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
  section.append(element('p', 'Каждое действие — отдельный сценарий от текущей карточки. Прогнозы не суммируются.', 'catalog-muted'), scenarios,
    element('p', 'Предпросмотр по текущему состоянию каталога. Место изменится после подтверждения и публикации.', 'catalog-muted'));
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
  if (review.mode === 'mock') section.append(element('p', 'Демонстрационная проверка · mock. Это не реальный AI-анализ.', 'catalog-warning'));
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
          : 'Замечание — требует проверки человеком', 'catalog-muted'));
    if (issue.quote) item.append(element('blockquote', issue.quote));
    if (issue.message) item.append(element('p', issue.message));
    if (issue.question) item.append(element('p', `Вопрос бизнесу: ${issue.question}`));
    section.append(item);
  }
  return section;
}

/** Mount with the Promise-based adapter from TEAM.md. refresh() reloads the active filters. */
export function mountCatalog(root, api) {
  const panel = element('section', undefined, 'catalog-panel');
  root.replaceChildren(panel);
  const heading = element('header');
  heading.append(element('p', 'AI SANA / КОМАНДАМ', 'catalog-eyebrow'), element('h2', 'Задачи бизнеса'),
    element('p', 'Найдите задачу, предложите решение и пройдите этапы вместе с бизнесом.'));
  const filters = element('form', undefined, 'catalog-filters');
  const industry = element('select');
  function setIndustries(values, selected) {
    industry.replaceChildren();
    for (const value of ['', ...values]) {
      const option = element('option', value || 'Все отрасли');
      option.value = value;
      industry.append(option);
    }
    industry.value = selected;
  }
  setIndustries([], '');
  const level = element('select');
  for (const [value, text] of [['', 'Все уровни'], ...Object.entries(LEVELS)]) {
    const option = element('option', text);
    option.value = value;
    level.append(option);
  }
  const apply = element('button', 'Показать задачи');
  apply.type = 'submit';
  const search = element('input');
  search.type = 'search';
  search.placeholder = 'Название или описание';
  search.addEventListener('input', () => {
    page = 1;
    renderList();
  });
  const reset = button('Сбросить фильтры', () => {
    if (busy) return;
    industry.value = '';
    level.value = '';
    search.value = '';
    page = 1;
    void refresh();
  });
  filters.append(labeled('Отрасль', industry), labeled('Готовность задачи', level), apply, reset);
  const notice = element('p', '', 'catalog-notice');
  notice.setAttribute('role', 'status');
  notice.setAttribute('aria-live', 'polite');
  const layout = element('div', undefined, 'catalog-layout');
  const list = element('div', undefined, 'catalog-list');
  list.setAttribute('aria-label', 'Опубликованные задачи');
  const detail = element('section', undefined, 'catalog-detail');
  detail.setAttribute('aria-label', 'Карточка задачи');
  layout.append(list, detail);
  const searchField = labeled('Поиск по задачам', search);
  searchField.classList.add('catalog-search');
  const navigationWarning = element('div', undefined, 'catalog-navigation-warning');
  panel.append(heading, filters, searchField, notice, navigationWarning, layout);
  let cards = [], teams = [], selectedId = null, proposals = [];
  let selectedCard = null;
  let proposalDraft = {};
  let page = 1;
  let appliedFilters = { industry: '', level: '' };
  const pageSize = 20;
  let busy = false;

  function say(text, error = false) {
    notice.textContent = text;
    notice.classList.toggle('catalog-error', error);
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
      controls.forEach((node, index) => { node.disabled = disabled[index]; });
      busy = false;
      panel.setAttribute('aria-busy', 'false');
    }
  }

  function badges(card) {
    const row = element('div', undefined, 'catalog-badges');
    row.append(element('span', `${card.rating?.total ?? '—'} / 100`, 'catalog-score'),
      element('span', LEVELS[card.rating?.level] || 'Уровень не указан', 'catalog-badge'));
    if (card.rating?.total < 40) row.append(element('span', 'Нужны уточнения', 'catalog-warning'));
    if (card.synthetic) row.append(element('span', 'Синтетический пример', 'catalog-badge'));
    if (card.mode === 'mock') row.append(element('span', 'Демо · mock', 'catalog-badge'));
    return row;
  }

  function renderList() {
    const query = search.value.trim().toLocaleLowerCase();
    const found = cards.filter(card => ['title', 'context', 'need', 'expected_result']
      .some(key => String(card[key] || '').toLocaleLowerCase().includes(query)));
    const pages = Math.max(1, Math.ceil(found.length / pageSize));
    page = Math.min(page, pages);
    const count = element('p', `Найдено задач: ${found.length}`, 'catalog-muted');
    count.setAttribute('role', 'status');
    list.replaceChildren(count);
    if (!found.length) list.append(element('p', 'Задач пока нет. Измените поиск или сбросьте фильтры.'));
    // The adapter owns ranking. Preserve its order exactly.
    for (const card of found.slice((page - 1) * pageSize, page * pageSize)) {
      const item = element('article', undefined, 'catalog-card');
      item.classList.toggle('catalog-active', card.id === selectedId);
      const open = button(card.id === selectedId ? 'Карточка открыта' : 'Посмотреть задачу', () => openCard(card.id));
      open.setAttribute('aria-pressed', String(card.id === selectedId));
      item.append(element('p', card.industry || 'Отрасль не указана', 'catalog-eyebrow'),
        element('h3', card.title || 'Задача без названия'), badges(card));
      const position = positionLabel(card);
      if (position) item.append(position);
      item.append(
        element('p', card.need || card.context || 'Описание пока не заполнено.'), open);
      list.append(item);
    }
    const pager = element('nav', undefined, 'catalog-pagination');
    pager.setAttribute('aria-label', 'Страницы каталога');
    const move = step => {
      if (busy) return;
      page += step;
      renderList();
      list.querySelector('.catalog-page-number')?.focus();
    };
    const previous = button('Назад', () => move(-1));
    const next = button('Далее', () => move(1));
    previous.disabled = page === 1;
    next.disabled = page === pages;
    const number = element('span', `Страница ${page} из ${pages}`, 'catalog-page-number');
    number.tabIndex = -1;
    pager.append(previous, number, next);
    list.append(pager);
  }

  function openCard(id) {
    if (busy || id === selectedId) return;
    if (Object.values(proposalDraft).some(value => String(value).length > 0)) {
      const warning = element('p', 'В отклике есть несохранённые данные. При открытии другой задачи они будут потеряны.');
      const cancel = button('Остаться в текущей карточке', () => {
        navigationWarning.replaceChildren();
        detail.querySelector('h3')?.focus();
      });
      navigationWarning.setAttribute('role', 'alert');
      navigationWarning.replaceChildren(warning, cancel,
        button('Открыть другую и удалить черновик', () => loadCard(id)));
      cancel.focus();
      return;
    }
    return loadCard(id);
  }

  function loadCard(id) {
    return run('Загружаем отклики…', async () => {
      const loaded = await api.listProposals(id);
      selectedId = id;
      selectedCard = cards.find(item => item.id === id);
      proposalDraft = {};
      navigationWarning.replaceChildren();
      proposals = loaded;
      renderList();
      renderDetail();
      say('Карточка загружена.');
      detail.querySelector('h3')?.focus();
    });
  }

  function renderDetail() {
    detail.replaceChildren();
    const card = selectedCard;
    if (!card) {
      detail.append(element('p', 'Выберите задачу, чтобы посмотреть подробности и отправить отклик.', 'catalog-empty'));
      return;
    }
    const title = element('h3', card.title || 'Задача без названия');
    title.tabIndex = -1;
    detail.append(title, badges(card));
    const position = positionLabel(card);
    if (position) detail.append(position);
    const fields = element('dl', undefined, 'catalog-facts');
    for (const [key, label] of Object.entries(FIELDS)) {
      const value = element('dd', card[key] || 'Не указано');
      if (card.confirmed_fields?.includes(key)) value.append(element('small', 'Подтверждено бизнесом', 'catalog-muted'));
      const evidence = card.evidence?.[key];
      if (evidence?.quote) value.append(element('blockquote', evidence.quote));
      if (evidence?.source_id) value.append(element('small', `Источник: ${evidence.source_id}`, 'catalog-muted'));
      fields.append(element('dt', label), value);
    }
    detail.append(fields);
    const rating = element('details');
    rating.append(element('summary', 'Из чего складывается рейтинг'));
    for (const item of card.rating?.items || []) {
      rating.append(element('p', `${item.label}: ${item.earned} / ${item.maximum}. ${item.explanation || ''}`));
    }
    if (card.rating?.missing_fields?.length) {
      rating.append(element('p', `Не хватает: ${card.rating.missing_fields.map(key => FIELDS[key] || key).join(', ')}`));
    }
    detail.append(rating, reviewSection(card), improvementSection(card), proposalForm(card), proposalSection());
  }

  function proposalForm(card) {
    const form = element('form', undefined, 'catalog-proposal-form');
    // Validate explicitly so URL errors remain visible beside the field.
    form.noValidate = true;
    form.append(element('h4', 'Предложить решение'));
    const team = element('select');
    team.name = 'team_id';
    team.required = true;
    const placeholder = element('option', teams.length ? 'Выберите учебную команду' : 'Нет доступных команд');
    placeholder.value = '';
    team.append(placeholder);
    for (const item of teams) {
      const option = element('option', item.name);
      option.value = String(item.id);
      team.append(option);
    }
    const teamInfo = element('p', '', 'catalog-muted');
    team.value = proposalDraft.team_id || '';
    const showTeam = () => {
      const selected = teams.find(item => String(item.id) === team.value);
      teamInfo.textContent = selected ? ['interests', 'skills', 'technologies'].map((key, i) => {
        const value = selected[key];
        return `${['Интересы', 'Навыки', 'Технологии'][i]}: ${Array.isArray(value) ? value.join(', ') : value || 'не указаны'}`;
      }).join(' · ') : '';
    };
    team.addEventListener('change', showTeam);
    showTeam();
    form.append(labeled('Учебная команда', team), teamInfo);
    const inputs = {};
    for (const [key, label, tag] of [
      ['idea', 'Идея решения', 'textarea'], ['plan', 'План работы', 'textarea'],
      ['timeline', 'Срок', 'input'], ['prototype_url', 'Ссылка на прототип', 'input'],
    ]) {
      const input = element(tag);
      input.name = key;
      input.value = proposalDraft[key] || '';
      input.required = true;
      if (tag === 'textarea') input.rows = 3;
      if (key === 'prototype_url') { input.type = 'url'; input.placeholder = 'https://'; }
      input.addEventListener('input', () => input.setCustomValidity(''));
      inputs[key] = input;
      form.append(labeled(label, input));
    }
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
    const submit = element('button', 'Отправить отклик');
    submit.type = 'submit';
    submit.disabled = !teams.length;
    form.append(submit);
    const saveDraft = () => {
      proposalDraft = { team_id: team.value,
        ...Object.fromEntries(Object.entries(inputs).map(([key, input]) => [key, input.value])) };
    };
    form.addEventListener('input', saveDraft);
    form.addEventListener('change', saveDraft);
    if (!teams.length) form.append(element('p', 'Добавьте команду и обновите каталог, чтобы отправить отклик.'));
    form.addEventListener('submit', event => {
      event.preventDefault();
      if (busy) return;
      for (const input of Object.values(inputs)) {
        input.setCustomValidity(input.required && !input.value.trim() ? 'Заполните поле.' : '');
      }
      validatePrototype();
      if (!form.reportValidity()) return;
      const selected = teams.find(item => String(item.id) === team.value);
      if (!selected) return;
      run('Отправляем отклик…', async () => {
        const proposal = await api.createProposal(card.id, {
          team_id: selected.id, ...Object.fromEntries(Object.entries(inputs).map(([key, input]) => [key, input.value.trim()])),
        });
        proposals = [...proposals.filter(item => item.id !== proposal.id), proposal];
        proposalDraft = {};
        navigationWarning.replaceChildren();
        renderDetail();
        say('Отклик отправлен и добавлен в список для бизнеса.');
      });
    });
    return form;
  }

  function proposalSection() {
    const section = element('section', undefined, 'catalog-proposals');
    section.append(element('h4', 'Бизнесу: отклики команд'),
      element('p', 'Можно выбрать несколько команд. Решение принимает бизнес. Баллы прогресса учитываются отдельно от рейтинга задачи.', 'catalog-muted'));
    if (!proposals.length) section.append(element('p', 'Откликов пока нет.'));
    for (const proposal of proposals) {
      const item = element('article', undefined, 'catalog-proposal');
      item.append(element('h5', proposal.team_name || `Команда ${proposal.team_id}`),
        element('span', STATUSES[proposal.status] || proposal.status, 'catalog-badge'));
      for (const [key, label] of [['idea', 'Идея'], ['plan', 'План'], ['timeline', 'Срок']]) {
        item.append(element('p', `${label}: ${proposal[key] || 'Не указано'}`));
      }
      const link = safeLink(proposal.prototype_url);
      if (link) item.append(link);
      item.append(element('p', `Баллы прогресса: ${proposal.progress_points ?? 0}`, 'catalog-progress'));
      const actions = element('div', undefined, 'catalog-actions');
      for (const [action, label, status] of [['select', 'Выбрать', 'selected'], ['reject', 'Отклонить', 'rejected']]) {
        const control = button(label, () => run('Сохраняем решение…', async () => {
          const updated = await api.decideProposal(proposal.id, { action });
          proposals = proposals.map(current => current.id === updated.id ? updated : current);
          section.replaceWith(proposalSection());
          say('Статус отклика обновлён.');
        }));
        control.disabled = proposal.status === status;
        actions.append(control);
      }
      if (proposal.status === 'selected') {
        actions.append(button('Подтвердить этап', () => run('Подтверждаем этап…', async () => {
          const result = await api.confirmMilestone(proposal.id);
          // Never add points locally: reload the server's authoritative balance.
          try {
            proposals = await api.listProposals(selectedId);
            section.replaceWith(proposalSection());
          } catch (error) {
            say(`Этап подтверждён, но баллы не удалось обновить. Обновите каталог. ${error?.message || ''}`, true);
            return;
          }
          say(result.already_awarded ? 'Этот этап уже подтверждён. Повторного начисления нет.' : `Этап подтверждён. Баллы за этап: ${result.points}.`);
        })));
      }
      item.append(actions);
      section.append(item);
    }
    return section;
  }

  function refresh() {
    return run('Загружаем каталог…', async () => {
      const [allCards, loadedTeams] = await Promise.all([api.listCards({}), api.listTeams()]);
      const industries = [...new Set(allCards.map(card => card.industry).filter(value => typeof value === 'string' && value !== ''))];
      const requested = { industry: industries.includes(industry.value) ? industry.value : '', level: level.value };
      const industryRemoved = Boolean(industry.value && !requested.industry);
      const loadedCards = requested.industry || requested.level ? await api.listCards(requested) : allCards;
      const published = loadedCards.filter(card => card.published);
      const loadedProposals = selectedId !== null ? await api.listProposals(selectedId) : [];
      cards = published;
      teams = loadedTeams;
      selectedCard = allCards.find(card => card.id === selectedId) || selectedCard;
      proposals = loadedProposals;
      if (requested.industry !== appliedFilters.industry || requested.level !== appliedFilters.level) page = 1;
      appliedFilters = requested;
      setIndustries(industries, requested.industry);
      renderList();
      renderDetail();
      say(`${industryRemoved ? 'Выбранная отрасль исчезла; фильтр сброшен. ' : ''}Каталог обновлён. Опубликованных задач: ${cards.length}.`);
    });
  }
  filters.addEventListener('submit', event => { event.preventDefault(); void refresh(); });
  renderDetail();
  void refresh();
  return { refresh };
}
