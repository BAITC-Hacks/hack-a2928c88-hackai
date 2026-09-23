// T-001: экран бизнеса. Баллы не считаем — только показываем rating из API.
const FIELDS = [
  ['title', 'Название'],
  ['context', 'Контекст'],
  ['need', 'Что нужно'],
  ['users', 'Пользователи'],
  ['data', 'Данные'],
  ['constraints', 'Ограничения'],
  ['expected_result', 'Ожидаемый результат'],
  ['success_criteria', 'Критерии успеха'],
  ['contact', 'Контакт'],
  ['interaction_format', 'Формат взаимодействия'],
  ['feedback_process', 'Обратная связь'],
];
const FIELD_LABEL = Object.fromEntries(FIELDS);
const FIELD_HINT = {
  context: 'Что происходит сейчас и в чём затруднение',
  need: 'Что должно измениться',
  users: 'Для кого создаётся решение',
  data: 'Какие данные, примеры или источники доступны команде',
  constraints: 'Сроки, технологии, доступы',
  expected_result: 'Какой конкретный результат вы ждёте',
  success_criteria: 'Измеримые признаки, что результат принят',
  contact: 'Кто отвечает со стороны бизнеса',
  interaction_format: 'Встречи, созвоны, чат',
  feedback_process: 'Как и когда даёте обратную связь',
};
const LONG_FIELDS = new Set(['context', 'need', 'users', 'data', 'constraints', 'expected_result', 'success_criteria', 'feedback_process']);
const LEVELS = {draft: 'Черновик', working: 'Рабочая', ready: 'Готовая', priority: 'Приоритетная'};
const STEPS = ['Черновик', 'Вопросы', 'Карточка', 'Публикация'];

function points(n) {
  const mod10 = n % 10, mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return 'балл';
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return 'балла';
  return 'баллов';
}

function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === 'class') node.className = value;
    else if (key === 'text') node.textContent = value;
    else if (key in node) node[key] = value;
    else node.setAttribute(key, value);
  }
  for (const child of children) if (child != null) node.append(child);
  return node;
}

function sourceLabel(sourceId) {
  const id = String(sourceId || '');
  if (id.startsWith('manual:')) return 'введено вручную';
  if (id === 'draft') return 'из описания задачи';
  const answer = /^q-(\d+)$/.exec(id);
  if (answer) return 'из ответа на вопрос ' + (Number(answer[1]) + 1);
  return 'источник: ' + id;
}

/** Ruler + ticks for a score. Values come from the API; the screen only draws them. */
export function ruler(total, level, {small = false, ticks = false} = {}) {
  const bar = el('div', {class: 'ruler' + (small ? ' sm' : ''), role: 'img',
    'aria-label': `Готовность ${total} из 100, уровень «${LEVELS[level] || level}»`});
  bar.dataset.level = level;
  bar.style.setProperty('--v', String(total));
  if (!ticks) return bar;
  const marks = el('div', {class: 'ruler-ticks', 'aria-hidden': 'true'});
  for (const at of [0, 40, 70, 90]) marks.append(el('span', {text: String(at), style: `left:${at}%`}));
  return el('div', {}, bar, marks);
}

export function stamp(level, extra = '') {
  return el('span', {class: 'stamp stamp-' + level, text: (LEVELS[level] || level) + extra});
}

export function mountBusiness(root, api, onPublished = () => {}) {
  root.classList.add('business-panel');
  root.replaceChildren();

  const state = {draftId: null, questions: [], questionCount: 0, questionsReady: false, card: null,
    dirty: new Set(), checked: new Set(), busy: false, conflict: false};
  const locked = new Map();

  const steps = el('ol', {class: 'bp-steps', 'aria-label': 'Шаги сценария'});
  const status = el('p', {class: 'bp-status', role: 'status', 'aria-live': 'polite'});
  const error = el('p', {class: 'bp-error msg msg-error', role: 'alert', hidden: true});
  const inputStep = el('section', {class: 'bp-step bp-step-input', 'aria-labelledby': 'bp-input-h'});
  const questionStep = el('section', {class: 'bp-step', hidden: true, 'aria-labelledby': 'bp-questions-h'});
  const cardStep = el('section', {class: 'bp-step bp-step-card', hidden: true, 'aria-labelledby': 'bp-card-h'});
  const reloadBtn = el('button', {type: 'button', text: 'Загрузить актуальную карточку', hidden: true});
  const reloadWarning = el('p', {class: 'bp-hint', hidden: true, text: 'Загрузка заменит несохранённые правки и снимет все отметки для подтверждения. Нажмите кнопку только если готовы их потерять.'});
  reloadBtn.addEventListener('click', () => run(reloadBtn, 'Загружаем…', async () => {
    const card = await api.getCard(state.card.id);
    state.conflict = false;
    reloadBtn.hidden = reloadWarning.hidden = true;
    showCard(card, null);
  }));
  const resetBtn = el('button', {type: 'button', class: 'bp-link', text: 'Новая задача'});
  resetBtn.addEventListener('click', () => { if (!state.busy) mountBusiness(root, api, onPublished); });
  const head = el('div', {class: 'bp-head'},
    el('div', {}, el('p', {class: 'eyebrow', text: 'Бизнесу'}), el('h2', {text: 'Паспорт готовности задачи'})),
    resetBtn);
  root.append(head, steps, status, error, reloadWarning, reloadBtn, inputStep, questionStep, cardStep);

  function renderSteps() {
    const card = state.card;
    const filled = card ? FIELDS.filter(([k]) => (card[k] || '').trim()).length : 0;
    const confirmed = card ? (card.confirmed_fields || []).length : 0;
    const current = !state.questionsReady ? 0 : !card ? 1 : card.published && !card.has_unpublished_changes ? 3 : 2;
    const notes = [
      industry.value.trim() || 'описание и отрасль',
      state.questionCount ? state.questionCount + ' вопросов' : 'минимум 3 вопроса',
      card ? `подтверждено ${confirmed} из ${filled}` : 'поля и подтверждение',
      card?.published ? (card.has_unpublished_changes ? 'есть новые правки' : 'в каталоге') : 'в общий каталог',
    ];
    steps.replaceChildren(...STEPS.map((name, i) => {
      const done = i < current || (i === 3 && card?.published && !card.has_unpublished_changes);
      const item = el('li', {class: 'bp-stepper' + (done ? ' is-done' : i === current ? ' is-now' : '')},
        el('b', {class: 'num', text: done ? '✓' : String(i + 1), 'aria-hidden': 'true'}),
        el('span', {}, el('span', {class: 'bp-step-name', text: name}), el('small', {text: notes[i]})));
      if (i === current) item.setAttribute('aria-current', 'step');
      return item;
    }));
  }

  function lockControls() {
    if (!state.busy) return;
    for (const control of root.querySelectorAll('button, input, textarea, select')) {
      if (!locked.has(control)) locked.set(control, {disabled: control.disabled, readOnly: control.readOnly});
      control.disabled = true;
    }
  }

  function syncSteps() {
    // A created draft keeps its original source even when clarification fails.
    if (state.draftId) text.readOnly = industry.readOnly = true;
    clarifyBtn.disabled = state.questionsReady || !!state.card;
    inputStep.hidden = questionStep.hidden = !!state.card;
    if (!state.card) questionStep.hidden = !state.questionsReady;
    renderSteps();
    lockControls();
  }

  // Один запрос за раз; сохраняем состояния всех элементов, включая новый DOM.
  async function run(button, loadingText, action) {
    if (state.busy) return;
    state.busy = true;
    error.hidden = true;
    status.textContent = loadingText;
    lockControls();
    const label = button.textContent;
    button.textContent = loadingText;
    root.setAttribute('aria-busy', 'true');
    try {
      await action();
      status.textContent = '';
    } catch (e) {
      status.textContent = '';
      error.textContent = 'Ошибка: ' + (e && e.message ? e.message : 'не удалось выполнить запрос');
      error.hidden = false;
      if (state.card && (e?.status === 409 || /Карточка изменилась|конфликт|устаревш/i.test(e?.message || ''))) {
        state.conflict = true;
        reloadBtn.hidden = reloadWarning.hidden = false;
        error.textContent = 'Карточка изменена в другом окне. Ваши правки сохранены на экране. Загрузите актуальную версию перед следующим действием.';
      }
    } finally {
      button.textContent = label;
      for (const [control, original] of locked) {
        control.disabled = original.disabled;
        if (original.readOnly !== undefined) control.readOnly = original.readOnly;
      }
      locked.clear();
      root.removeAttribute('aria-busy');
      state.busy = false;
      syncSteps();
    }
  }

  function badges(source) {
    const box = el('div', {class: 'bp-badges'});
    if (source.mode === 'mock') box.append(el('span', {class: 'tag tag-mock', text: 'mock: ответ без реального AI'}));
    else if (source.mode) box.append(el('span', {class: 'tag tag-live', text: 'AI: ' + source.mode + (source.provider ? ' · ' + source.provider : '')}));
    if (source.synthetic) box.append(el('span', {class: 'tag', text: 'Синтетика'}));
    return box;
  }

  // Шаг 1 — описание и отрасль.
  const text = el('textarea', {id: 'bp-text', rows: 5, required: true, placeholder: 'Например: «Нужен чат-бот для нашего магазина, чтобы отвечал клиентам». Можно коротко — система задаст вопросы.'});
  const industry = el('input', {id: 'bp-industry', required: true, placeholder: 'Например: логистика', autocomplete: 'off'});
  const clarifyBtn = el('button', {type: 'submit', class: 'bp-primary', text: 'Уточнить задачу'});
  const inputForm = el('form', {class: 'bp-form bp-intro'},
    el('div', {class: 'bp-intro-copy'},
      el('h3', {id: 'bp-input-h', text: 'Опишите задачу как есть'}),
      el('p', {class: 'muted', text: 'Система найдёт, чего не хватает, и задаст уточняющие вопросы. AI не добавляет фактов от себя: каждое поле карточки ссылается на ваш текст, а баллы начисляются только за поля, которые вы подтвердили.'}),
      el('ul', {class: 'bp-scale'},
        ...[['draft', '0–39', 'видна, но требует уточнения'], ['working', '40–69', 'можно рекомендовать командам'],
          ['ready', '70–89', 'выше в каталоге'], ['priority', '90–100', 'выделяется в каталоге']]
          .map(([lvl, range, note]) => el('li', {}, stamp(lvl), el('span', {class: 'num', text: range}), el('span', {class: 'muted', text: note}))))),
    el('div', {class: 'bp-intro-form'},
      el('label', {for: 'bp-text', text: 'Описание задачи'}), text,
      el('label', {for: 'bp-industry', text: 'Отрасль'}), industry,
      el('div', {class: 'bp-actions'}, clarifyBtn)));
  inputStep.append(inputForm);
  industry.addEventListener('input', renderSteps);

  inputForm.addEventListener('submit', event => {
    event.preventDefault();
    if (state.busy || state.card || state.questionsReady) return;
    if (!text.value.trim() || !industry.value.trim()) {
      error.textContent = 'Заполните описание и отрасль';
      error.hidden = false;
      return;
    }
    run(clarifyBtn, 'Готовим вопросы…', async () => {
      if (!state.draftId) {
        const draft = await api.createDraft({text: text.value.trim(), industry: industry.value.trim()});
        state.draftId = draft.id;
      }
      const result = await api.clarifyDraft(state.draftId);
      state.questions = result.questions || [];
      state.questionCount = state.questions.length;
      state.questionsReady = true;
      text.readOnly = industry.readOnly = true;
      renderQuestions(result);
    });
  });

  // Шаг 2 — уточняющие вопросы.
  function renderQuestions(result) {
    const answers = new Map();
    const list = el('ol', {class: 'bp-questions'});
    for (const q of state.questions) {
      const id = 'bp-q-' + q.id;
      const area = el('textarea', {id, rows: 2});
      answers.set(q.id, area);
      list.append(el('li', {},
        el('label', {for: id, text: q.question}),
        el('span', {class: 'bp-hint', text: '→ поле «' + (FIELD_LABEL[q.field] || q.field) + '»'}),
        area));
    }
    const buildBtn = el('button', {type: 'submit', class: 'bp-primary', text: 'Собрать карточку'});
    const form = el('form', {class: 'bp-form'}, list,
      el('div', {class: 'bp-actions'}, buildBtn, el('span', {class: 'bp-hint', text: 'Можно ответить не на все вопросы — пустые поля останутся пустыми.'})));
    form.addEventListener('submit', event => {
      event.preventDefault();
      if (state.busy || state.card) return;
      run(buildBtn, 'Собираем карточку…', async () => {
        const payload = {};
        for (const [id, area] of answers) if (area.value.trim()) payload[id] = area.value.trim();
        const card = await api.buildCard(state.draftId, {answers: payload});
        state.questions.length = 0;
        form.querySelectorAll('textarea').forEach(a => { a.readOnly = true; });
        showCard(card, null);
      });
    });
    questionStep.replaceChildren(
      el('div', {class: 'bp-section-head'}, el('h3', {id: 'bp-questions-h', text: 'Уточняющие вопросы'}), badges(result)),
      el('p', {class: 'bp-hint', text: 'Ответы станут источниками для полей карточки. Черновик: «' + text.value.trim() + '»'}), form);
    questionStep.hidden = false;
  }

  // Шаг 3 — карточка, подтверждение, рейтинг, публикация.
  function showCard(card, previousTotal) {
    state.card = card;
    state.dirty.clear();
    state.checked.clear();
    renderCard(previousTotal);
    syncSteps();
  }

  function gainsOf(card) {
    return Object.fromEntries((card.rating?.gains || []).map(g => [g.field, g.points]));
  }

  function renderCard(previousTotal) {
    const card = state.card;
    const gains = gainsOf(card);
    const confirmed = new Set(card.confirmed_fields || []);
    const groups = {review: [], empty: [], done: []};
    for (const [key, label] of FIELDS.slice(1)) {
      const filled = (card[key] || '').trim();
      groups[!filled ? 'empty' : confirmed.has(key) ? 'done' : 'review'].push(renderField(card, key, label, gains[key]));
    }
    const group = (key, title, note, rows) => rows.length ? el('section', {class: 'bp-group bp-group-' + key},
      el('header', {}, el('h4', {text: title + ' · ' + rows.length}), el('span', {class: 'bp-hint', text: note})), ...rows) : null;

    const saveBtn = el('button', {type: 'button', text: 'Сохранить изменения'});
    const confirmBtn = el('button', {type: 'button', class: 'bp-primary', text: 'Подтвердить отмеченные'});
    const publishBtn = el('button', {type: 'button', text: card.published ? 'Опубликовать изменения' : 'Опубликовать'});
    const published = el('p', {class: 'bp-success msg msg-ok', role: 'status', hidden: true});
    const reviewPanel = el('section', {class: 'bp-review', 'aria-label': 'Проверка задачи перед стартом'});
    renderReview(reviewPanel);

    saveBtn.addEventListener('click', () => {
      if (!state.dirty.size) { status.textContent = 'Нет несохранённых изменений'; return; }
      run(saveBtn, 'Сохраняем…', saveChanges);
    });

    confirmBtn.addEventListener('click', () => {
      run(confirmBtn, 'Подтверждаем…', async () => {
        if (state.conflict) throw new Error('Сначала загрузите актуальную карточку');
        if (!state.checked.size) throw new Error('Отметьте хотя бы одно заполненное неподтверждённое поле');
        await saveChanges();
        const confirmedNow = new Set(state.card.confirmed_fields || []);
        const fields = [...state.checked].filter(f => !confirmedNow.has(f) && (state.card[f] || '').trim());
        if (!fields.length) throw new Error('Отметьте хотя бы одно заполненное неподтверждённое поле');
        const before = state.card.rating.total;
        showCard(await api.confirmCard(state.card.id, {fields}), before);
      });
    });

    publishBtn.addEventListener('click', () => {
      run(publishBtn, 'Публикуем…', async () => {
        if (state.conflict) throw new Error('Сначала загрузите актуальную карточку');
        if (state.dirty.size) throw new Error('Сохраните и подтвердите изменённые поля перед публикацией');
        const card = await api.publishCard(state.card.id);
        showCard(card, null);
        const done = cardStep.querySelector('.bp-success');
        done.textContent = 'Карточка «' + (card.title || 'без названия') + '» опубликована с рейтингом ' + card.rating.total + '. Открываем её в каталоге.';
        done.hidden = false;
        onPublished(card);
      });
    });

    const checkAll = el('button', {type: 'button', class: 'bp-link', text: 'Отметить все для подтверждения'});
    checkAll.addEventListener('click', () => {
      for (const box of cardStep.querySelectorAll('.bp-check input:not(:disabled)')) {
        box.checked = true;
        box.dispatchEvent(new Event('change'));
      }
    });

    cardStep.replaceChildren(...[
      el('div', {class: 'bp-section-head'}, el('h3', {id: 'bp-card-h', text: 'Карточка задачи'}), badges(card)),
      card.published ? el('p', {class: 'bp-hint', text: card.has_unpublished_changes ? 'Опубликована, есть неопубликованные изменения.' : 'Опубликована и видна командам.'}) : null,
      warnings(card),
      el('div', {class: 'bp-layout'},
        el('div', {class: 'bp-fields'},
          renderField(card, 'title', FIELD_LABEL.title, undefined, true),
          group('review', 'Проверьте и подтвердите', 'баллы начислятся после подтверждения', groups.review),
          group('empty', 'Пусто', 'заполните, чтобы поднять рейтинг', groups.empty),
          group('done', 'Подтверждено', 'правка снимет подтверждение', groups.done),
          el('div', {class: 'bp-actionbar'},
            unconfirmedHint(card),
            el('div', {class: 'bp-actions'}, checkAll, saveBtn, confirmBtn, publishBtn)),
          published, reviewPanel),
        renderRating(card.rating, previousTotal))].filter(Boolean));
    cardStep.hidden = false;
    lockControls();
  }

  async function saveChanges() {
    if (state.conflict) throw new Error('Сначала загрузите актуальную карточку');
    if (!state.dirty.size) return;
    const changes = {};
    for (const f of state.dirty) changes[f] = cardStep.querySelector('[data-field="' + f + '"]').value;
    const checked = new Set(state.checked);
    const before = state.card.rating.total;
    showCard(await api.updateCard(state.card.id, {changes}), before);
    // Отметки пользователя на несохранённых раньше полях не теряем — подтверждение уходит отдельным запросом.
    for (const f of checked) if ((state.card[f] || '').trim() && !(state.card.confirmed_fields || []).includes(f)) state.checked.add(f);
    renderCard(before);
  }

  function renderField(card, key, label, gain, isTitle = false) {
    const id = 'bp-f-' + key;
    const value = card[key] || '';
    const input = LONG_FIELDS.has(key)
      ? el('textarea', {id, rows: value.length > 120 ? 3 : 2, value, placeholder: FIELD_HINT[key] || ''})
      : el('input', {id, value, placeholder: isTitle ? 'Короткое название задачи' : FIELD_HINT[key] || ''});
    input.dataset.field = key;
    const confirmedOnServer = (card.confirmed_fields || []).includes(key);
    const check = el('input', {type: 'checkbox', id: id + '-ok', checked: state.checked.has(key), disabled: confirmedOnServer || !value.trim()});
    const confirmationStatus = el('span', {class: 'bp-confirmation', text: confirmedOnServer ? '✓ Подтверждено' : value.trim() ? 'Не подтверждено' : ''});
    const gainTag = gain ? el('span', {class: 'tag tag-gain num', text: '+' + gain}) : null;
    const row = el('div', {class: 'bp-field' + (confirmedOnServer ? ' bp-confirmed' : '') + (isTitle ? ' bp-field-title' : '') + (!value.trim() ? ' bp-empty' : '')},
      el('div', {class: 'bp-field-head'},
        el('label', {for: id, class: 'bp-field-label', text: label}),
        isTitle ? el('span', {class: 'bp-hint', text: 'не даёт баллов, но нужно для публикации'}) : gainTag),
      input,
      value.trim() ? evidence(card.evidence && card.evidence[key]) : null,
      el('div', {class: 'bp-field-foot'},
        confirmationStatus,
        el('label', {class: 'bp-check', for: id + '-ok'}, check, document.createTextNode(' Подтвердить это поле'))));

    input.addEventListener('input', () => {
      state.dirty.add(key);
      state.checked.delete(key);
      check.checked = false;
      check.disabled = !input.value.trim();
      row.classList.remove('bp-confirmed');
      row.classList.add('bp-dirty');
      confirmationStatus.textContent = 'Есть несохранённые правки — после сохранения потребуется подтверждение';
      const reviewPanel = cardStep.querySelector('.bp-review');
      if (reviewPanel) renderReview(reviewPanel);
    });
    check.addEventListener('change', () => {
      if (check.checked) state.checked.add(key); else state.checked.delete(key);
      row.classList.toggle('bp-marked', check.checked);
    });
    return row;
  }

  function evidence(item) {
    if (!item || !item.quote) return el('p', {class: 'bp-evidence bp-evidence-none', text: 'Источник не найден — проверьте поле вручную'});
    return el('p', {class: 'bp-evidence'},
      el('span', {class: 'bp-source', text: sourceLabel(item.source_id)}),
      el('q', {text: item.quote}));
  }

  function warnings(card) {
    if (!card.warnings || !card.warnings.length) return null;
    const list = el('ul', {class: 'bp-warnings'});
    for (const w of card.warnings) list.append(el('li', {text: String(w)}));
    return list;
  }

  function unconfirmedHint(card) {
    const confirmed = new Set(card.confirmed_fields || []);
    const left = FIELDS.filter(([k]) => (card[k] || '').trim() && !confirmed.has(k)).map(([, l]) => l);
    if (!(card.title || '').trim()) left.unshift('укажите название');
    if (!left.length) return el('p', {class: 'bp-hint bp-ready', text: 'Все заполненные поля подтверждены — можно публиковать.'});
    return el('p', {class: 'bp-hint', text: 'Перед публикацией: ' + left.join(', ') + '.'});
  }

  function focusField(key) {
    const input = cardStep.querySelector('[data-field="' + key + '"]');
    if (!input) return;
    input.scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'center'});
    input.focus({preventScroll: true});
  }

  function renderReview(panel) {
    const card = state.card;
    const review = card.review || {status: 'not_run'};
    const dirty = state.dirty.size > 0;
    const stale = review.status === 'stale' || (review.revision != null && review.revision !== card.revision);
    const btn = el('button', {type: 'button', class: 'bp-primary',
      text: review.status === 'not_run' ? 'Что помешает начать?' : 'Проверить ещё раз'});
    btn.disabled = dirty || state.conflict;
    btn.addEventListener('click', () => run(btn, 'Проверяем задачу…', async () => {
      if (state.dirty.size) throw new Error('Сначала сохраните изменения карточки');
      if (state.conflict) throw new Error('Сначала загрузите актуальную карточку');
      // Do not rerender the editor: preserve the human's pending confirmation checkboxes.
      try {
        const updated = await api.reviewCard(card.id);
        state.card = updated;
        renderReview(panel);
        lockControls();
      } catch (error) {
        panel.querySelector('.bp-review-status').textContent = 'Проверка недоступна. Введённые данные сохранены; повторите запрос.';
        throw error;
      }
    }));
    const note = el('p', {class: 'bp-review-status', role: 'status', 'aria-live': 'polite'});
    panel.replaceChildren(el('h4', {text: 'Что стоит уточнить до старта'}),
      el('p', {class: 'bp-hint', text: 'Проверка не меняет рейтинг и ничего не подтверждает. Ответы и решение остаются за вами.'}), btn, note);
    if (dirty) { note.textContent = 'Есть несохранённые правки. Сохраните их перед проверкой; прежние результаты не относятся к текущему тексту.'; return; }
    if (stale) { note.textContent = 'Карточка изменилась — результаты проверки устарели. Запустите проверку ещё раз.'; return; }
    if (review.status === 'not_run') { note.textContent = 'Проверка ещё не выполнена.'; return; }
    if (review.status !== 'complete') { note.textContent = 'Проверка недоступна. Повторите запрос.'; return; }
    panel.append(el('p', {class: 'bp-hint', text: review.mode === 'mock'
      ? 'Демонстрационная проверка · mock: только правила, без реального AI.'
      : 'AI-проверка · ' + (review.provider || 'live') + '. Замечания требуют проверки человеком.'}));
    if (!review.issues?.length) note.textContent = 'Проверка не выявила замечаний; это не гарантия реализуемости.';
    for (const issue of (review.issues || []).slice(0, 3)) {
      const focus = el('button', {type: 'button', class: 'bp-link', text: 'Уточнить поле'});
      focus.addEventListener('click', () => focusField(issue.field));
      const item = el('article', {class: 'bp-review-issue'},
        el('h5', {text: FIELD_LABEL[issue.field] || issue.field}),
        el('p', {class: 'bp-hint', text: issue.kind === 'rule' ? 'Проверка правилом' : 'AI-предположение, проверьте'}),
        issue.quote ? el('blockquote', {text: issue.quote}) : el('p', {class: 'bp-hint', text: 'Поле пустое — цитаты нет.'}),
        el('p', {text: issue.message}), el('p', {text: issue.question}), focus);
      panel.append(item);
    }
    panel.append(el('p', {class: 'bp-hint', text: 'Чтобы проверка стала видна командам, опубликуйте карточку после ручного подтверждения полей.'}));
  }

  function renderRating(rating, previousTotal) {
    const box = el('aside', {class: 'bp-rating', 'aria-label': 'Рейтинг готовности'});
    if (!rating) return box;
    const total = el('div', {class: 'bp-total'},
      el('strong', {class: 'num', text: String(rating.total)}),
      el('span', {class: 'num', text: '/100'}));
    if (previousTotal != null) {
      const diff = rating.total - previousTotal;
      total.append(el('span', {class: 'bp-delta num' + (diff > 0 ? ' bp-up' : diff < 0 ? ' bp-down' : ''), role: 'status',
        text: diff === 0 ? '±0' : (diff > 0 ? '+' : '−') + Math.abs(diff), title: diff === 0 ? 'Баллы не изменились' : Math.abs(diff) + ' ' + points(Math.abs(diff))}));
    }
    box.append(el('h4', {text: 'Готовность задачи'}), total, ruler(rating.total, rating.level, {ticks: true}), stamp(rating.level));

    const gains = rating.gains || [];
    if (rating.next_level) {
      const n = rating.points_to_next;
      const enough = gains.find(g => g.points >= n);
      box.append(el('p', {class: 'bp-next'},
        document.createTextNode('До «' + LEVELS[rating.next_level] + '» — '), el('b', {class: 'num', text: n + ' ' + points(n)}),
        document.createTextNode(enough ? '. Хватит поля «' + FIELD_LABEL[enough.field] + '».' : '.')));
    } else if (rating.total >= 90) {
      box.append(el('p', {class: 'bp-next', text: 'Максимальный уровень: задача выделяется в каталоге.'}));
    }
    if (gains.length) {
      const list = el('ul', {class: 'bp-gains', 'aria-label': 'Что добавит баллы'});
      for (const g of gains) {
        const go = el('button', {type: 'button', class: 'bp-gain'},
          el('span', {text: FIELD_LABEL[g.field] || g.field}), el('span', {class: 'tag tag-gain num', text: '+' + g.points}));
        go.addEventListener('click', () => focusField(g.field));
        list.append(el('li', {}, go));
      }
      box.append(el('p', {class: 'eyebrow', text: 'Что добавит баллы'}), list);
    } else if (rating.missing_fields?.length) {
      box.append(el('p', {class: 'bp-missing', text: 'Не хватает: ' + rating.missing_fields.map(f => FIELD_LABEL[f] || f).join(', ')}));
    }

    const breakdown = el('details', {class: 'bp-breakdown'}, el('summary', {text: 'Как посчитано'}));
    const items = el('ul', {class: 'bp-items'});
    for (const item of rating.items || []) {
      const bar = el('div', {class: 'bp-bar'}, el('span', {style: 'width:' + (item.maximum ? Math.round(100 * item.earned / item.maximum) : 0) + '%'}));
      const fields = [...(item.confirmed_fields || []).map(f => '✓ ' + (FIELD_LABEL[f] || f)), ...(item.missing_fields || []).map(f => '○ ' + (FIELD_LABEL[f] || f))];
      items.append(el('li', {},
        el('div', {class: 'bp-item-head'}, el('span', {text: item.label}), el('span', {class: 'num', text: item.earned + '/' + item.maximum})),
        bar,
        el('p', {class: 'bp-hint', text: fields.join(' · ')})));
    }
    breakdown.append(items, el('p', {class: 'bp-hint', text: 'Баллы начисляются только за поля, подтверждённые человеком. Название баллов не даёт.'}));
    box.append(breakdown);
    return box;
  }

  syncSteps();
}
