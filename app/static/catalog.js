const LEVELS = { draft: 'Черновик', working: 'Рабочая', ready: 'Готовая', priority: 'Приоритетная' };
const FIELDS = {
  context: 'Контекст', need: 'Задача', users: 'Пользователи', data: 'Данные',
  constraints: 'Ограничения', expected_result: 'Ожидаемый результат',
  success_criteria: 'Критерии успеха', contact: 'Контакт',
  interaction_format: 'Формат взаимодействия', feedback_process: 'Обратная связь',
};
const STATUSES = { pending: 'На рассмотрении', selected: 'Команда выбрана', rejected: 'Отклонён' };

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

/** Mount with the Promise-based adapter from TEAM.md. refresh() reloads the active filters. */
export function mountCatalog(root, api) {
  const panel = element('section', undefined, 'catalog-panel');
  root.replaceChildren(panel);
  const heading = element('header');
  heading.append(element('p', 'AI SANA / КОМАНДАМ', 'catalog-eyebrow'), element('h2', 'Задачи бизнеса'),
    element('p', 'Найдите задачу, предложите решение и пройдите этапы вместе с бизнесом.'));
  const filters = element('form', undefined, 'catalog-filters');
  const industry = element('input');
  industry.type = 'search';
  industry.placeholder = 'Например, образование';
  const level = element('select');
  for (const [value, text] of [['', 'Все уровни'], ...Object.entries(LEVELS)]) {
    const option = element('option', text);
    option.value = value;
    level.append(option);
  }
  const apply = element('button', 'Показать задачи');
  apply.type = 'submit';
  filters.append(labeled('Отрасль', industry), labeled('Готовность задачи', level), apply);
  const notice = element('p', '', 'catalog-notice');
  notice.setAttribute('role', 'status');
  notice.setAttribute('aria-live', 'polite');
  const layout = element('div', undefined, 'catalog-layout');
  const list = element('div', undefined, 'catalog-list');
  list.setAttribute('aria-label', 'Опубликованные задачи');
  const detail = element('section', undefined, 'catalog-detail');
  detail.setAttribute('aria-label', 'Карточка задачи');
  layout.append(list, detail);
  panel.append(heading, filters, notice, layout);
  let cards = [], teams = [], selectedId = null, proposals = [];
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
    list.replaceChildren(element('p', `Найдено задач: ${cards.length}`, 'catalog-muted'));
    if (!cards.length) list.append(element('p', 'Задач пока нет. Попробуйте изменить фильтры.'));
    // The adapter owns ranking. Preserve its order exactly.
    for (const card of cards) {
      const item = element('article', undefined, 'catalog-card');
      item.classList.toggle('catalog-active', card.id === selectedId);
      const open = button(card.id === selectedId ? 'Карточка открыта' : 'Посмотреть задачу', () => openCard(card.id));
      open.setAttribute('aria-pressed', String(card.id === selectedId));
      item.append(element('p', card.industry || 'Отрасль не указана', 'catalog-eyebrow'),
        element('h3', card.title || 'Задача без названия'), badges(card),
        element('p', card.need || card.context || 'Описание пока не заполнено.'), open);
      list.append(item);
    }
  }

  function openCard(id) {
    return run('Загружаем отклики…', async () => {
      const loaded = await api.listProposals(id);
      selectedId = id;
      proposals = loaded;
      renderList();
      renderDetail();
      say('Карточка загружена.');
      detail.querySelector('h3')?.focus();
    });
  }

  function renderDetail() {
    detail.replaceChildren();
    const card = cards.find(item => item.id === selectedId);
    if (!card) {
      detail.append(element('p', 'Выберите задачу, чтобы посмотреть подробности и отправить отклик.', 'catalog-empty'));
      return;
    }
    const title = element('h3', card.title || 'Задача без названия');
    title.tabIndex = -1;
    detail.append(title, badges(card));
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
    detail.append(rating, proposalForm(card), proposalSection());
  }

  function proposalForm(card) {
    const form = element('form', undefined, 'catalog-proposal-form');
    form.append(element('h4', 'Предложить решение'));
    const team = element('select');
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
    team.addEventListener('change', () => {
      const selected = teams.find(item => String(item.id) === team.value);
      teamInfo.textContent = selected ? ['interests', 'skills', 'technologies'].map((key, i) => {
        const value = selected[key];
        return `${['Интересы', 'Навыки', 'Технологии'][i]}: ${Array.isArray(value) ? value.join(', ') : value || 'не указаны'}`;
      }).join(' · ') : '';
    });
    form.append(labeled('Учебная команда', team), teamInfo);
    const inputs = {};
    for (const [key, label, tag] of [
      ['idea', 'Идея решения', 'textarea'], ['plan', 'План работы', 'textarea'],
      ['timeline', 'Срок', 'input'], ['prototype_url', 'Ссылка на прототип (необязательно)', 'input'],
    ]) {
      const input = element(tag);
      input.name = key;
      input.required = key !== 'prototype_url';
      if (tag === 'textarea') input.rows = 3;
      if (key === 'prototype_url') { input.type = 'url'; input.placeholder = 'https://'; }
      input.addEventListener('input', () => input.setCustomValidity(''));
      inputs[key] = input;
      form.append(labeled(label, input));
    }
    const submit = element('button', 'Отправить отклик');
    submit.type = 'submit';
    submit.disabled = !teams.length;
    form.append(submit);
    if (!teams.length) form.append(element('p', 'Добавьте команду и обновите каталог, чтобы отправить отклик.'));
    form.addEventListener('submit', event => {
      event.preventDefault();
      if (busy) return;
      for (const input of Object.values(inputs)) {
        input.setCustomValidity(input.required && !input.value.trim() ? 'Заполните поле.' : '');
      }
      const url = inputs.prototype_url.value.trim();
      if (url && !safeLink(url)) inputs.prototype_url.setCustomValidity('Укажите ссылку с протоколом https:// или http://.');
      if (!form.reportValidity()) return;
      const selected = teams.find(item => String(item.id) === team.value);
      if (!selected) return;
      run('Отправляем отклик…', async () => {
        const proposal = await api.createProposal(card.id, {
          team_id: selected.id, ...Object.fromEntries(Object.entries(inputs).map(([key, input]) => [key, input.value.trim()])),
        });
        proposals = [...proposals.filter(item => item.id !== proposal.id), proposal];
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
      const requested = { industry: industry.value.trim(), level: level.value };
      const [loadedCards, loadedTeams] = await Promise.all([api.listCards(requested), api.listTeams()]);
      const published = loadedCards.filter(card => card.published);
      const nextId = published.some(card => card.id === selectedId) ? selectedId : null;
      const loadedProposals = nextId !== null ? await api.listProposals(nextId) : [];
      cards = published;
      teams = loadedTeams;
      selectedId = nextId;
      proposals = loadedProposals;
      renderList();
      renderDetail();
      say(`Каталог обновлён. Опубликованных задач: ${cards.length}.`);
    });
  }
  filters.addEventListener('submit', event => { event.preventDefault(); void refresh(); });
  renderDetail();
  void refresh();
  return { refresh };
}
