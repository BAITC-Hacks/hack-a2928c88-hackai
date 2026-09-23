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
const LONG_FIELDS = new Set(['context', 'need', 'users', 'data', 'constraints', 'expected_result', 'success_criteria', 'feedback_process']);
const LEVELS = {draft: 'Черновик', working: 'Рабочая', ready: 'Готовая', priority: 'Приоритетная'};

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

export function mountBusiness(root, api, onPublished = () => {}) {
  root.classList.add('business-panel');
  root.replaceChildren();

  const state = {draftId: null, questions: [], questionsReady: false, card: null, dirty: new Set(), checked: new Set(), busy: false, conflict: false};
  const locked = new Map();

  const status = el('p', {class: 'bp-status', role: 'status', 'aria-live': 'polite'});
  const error = el('p', {class: 'bp-error', role: 'alert', hidden: true});
  const inputStep = el('div', {class: 'bp-step'});
  const questionStep = el('div', {class: 'bp-step', hidden: true});
  const cardStep = el('div', {class: 'bp-step', hidden: true});
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
  root.append(el('h2', {text: 'Опишите задачу бизнеса'}), status, error, reloadWarning, reloadBtn, inputStep, questionStep, cardStep, resetBtn);

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
    if (source.mode === 'mock') box.append(el('span', {class: 'bp-badge bp-badge-mock', text: 'mock: ответ без реального AI'}));
    else if (source.mode) box.append(el('span', {class: 'bp-badge', text: 'AI: ' + source.mode}));
    if (source.synthetic) box.append(el('span', {class: 'bp-badge bp-badge-synthetic', text: 'Синтетика'}));
    return box;
  }

  // Шаг 1 — описание и отрасль.
  const text = el('textarea', {id: 'bp-text', rows: 6, required: true, placeholder: 'Какую проблему нужно решить, для кого и что уже есть'});
  const industry = el('input', {id: 'bp-industry', required: true, placeholder: 'Например: логистика'});
  const clarifyBtn = el('button', {type: 'submit', class: 'bp-primary', text: 'Уточнить задачу'});
  const inputForm = el('form', {class: 'bp-form'},
    el('label', {for: 'bp-text', text: 'Описание задачи'}), text,
    el('label', {for: 'bp-industry', text: 'Отрасль'}), industry,
    el('div', {class: 'bp-actions'}, clarifyBtn));
  inputStep.append(inputForm);

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
      const area = el('textarea', {id, rows: 3});
      answers.set(q.id, area);
      list.append(el('li', {},
        el('label', {for: id, text: q.question}),
        el('span', {class: 'bp-hint', text: 'Поле карточки: ' + (FIELD_LABEL[q.field] || q.field)}),
        area));
    }
    const buildBtn = el('button', {type: 'submit', class: 'bp-primary', text: 'Собрать карточку'});
    const form = el('form', {class: 'bp-form'}, list, el('div', {class: 'bp-actions'}, buildBtn));
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
    questionStep.replaceChildren(el('h3', {text: 'Уточняющие вопросы'}), badges(result),
      el('p', {class: 'bp-hint', text: 'Ответьте на вопросы — ответы станут источниками для полей карточки.'}), form);
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

  function renderCard(previousTotal) {
    const card = state.card;
    const fieldsBox = el('div', {class: 'bp-fields'});
    for (const [key, label] of FIELDS) fieldsBox.append(renderField(card, key, label));

    const saveBtn = el('button', {type: 'button', text: 'Сохранить изменения'});
    const confirmBtn = el('button', {type: 'button', text: 'Подтвердить отмеченные'});
    const publishBtn = el('button', {type: 'button', class: 'bp-primary', text: card.published ? 'Опубликовать изменения' : 'Опубликовать'});
    const published = el('p', {class: 'bp-success', role: 'status', hidden: true});

    saveBtn.addEventListener('click', () => {
      if (!state.dirty.size) { status.textContent = 'Нет несохранённых изменений'; return; }
      run(saveBtn, 'Сохраняем…', saveChanges);
    });

    confirmBtn.addEventListener('click', () => {
      run(confirmBtn, 'Подтверждаем…', async () => {
        if (state.conflict) throw new Error('Сначала загрузите актуальную карточку');
        if (!state.checked.size) throw new Error('Отметьте хотя бы одно заполненное неподтверждённое поле');
        await saveChanges();
        const confirmed = new Set(state.card.confirmed_fields || []);
        const fields = [...state.checked].filter(f => !confirmed.has(f) && (state.card[f] || '').trim());
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
        done.textContent = 'Карточка «' + (card.title || 'без названия') + '» опубликована. Она появилась в каталоге для учебных команд.';
        done.hidden = false;
        onPublished(card);
      });
    });

    cardStep.replaceChildren(...[
      el('h3', {text: 'Карточка задачи'}),
      badges(card),
      card.published ? el('p', {class: 'bp-hint', text: card.has_unpublished_changes ? 'Опубликована, есть неопубликованные изменения.' : 'Опубликована.'}) : null,
      warnings(card),
      el('p', {class: 'bp-hint', text: 'Проверьте каждое поле. После правки поле нужно сохранить и подтвердить заново. Опубликовать можно карточку с названием, где подтверждены все заполненные поля.'}),
      el('div', {class: 'bp-layout'}, fieldsBox, renderRating(card.rating, previousTotal)),
      unconfirmedHint(card),
      el('div', {class: 'bp-actions'}, saveBtn, confirmBtn, publishBtn),
      published].filter(Boolean));
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

  function renderField(card, key, label) {
    const id = 'bp-f-' + key;
    const value = card[key] || '';
    const input = LONG_FIELDS.has(key)
      ? el('textarea', {id, rows: 3, value})
      : el('input', {id, value});
    input.dataset.field = key;
    const confirmedOnServer = (card.confirmed_fields || []).includes(key);
    const check = el('input', {type: 'checkbox', id: id + '-ok', checked: state.checked.has(key), disabled: confirmedOnServer || !value.trim()});
    const confirmationStatus = el('p', {class: 'bp-confirmation', text: confirmedOnServer ? 'Подтверждено бизнесом' : 'Не подтверждено'});
    const row = el('div', {class: 'bp-field' + (confirmedOnServer ? ' bp-confirmed' : '')},
      el('label', {for: id, class: 'bp-field-label', text: label}),
      input,
      evidence(card.evidence && card.evidence[key]),
      confirmationStatus,
      el('label', {class: 'bp-check', for: id + '-ok'}, check, document.createTextNode(' Подтвердить это поле')));

    input.addEventListener('input', () => {
      state.dirty.add(key);
      state.checked.delete(key);
      check.checked = false;
      check.disabled = !input.value.trim();
      row.classList.remove('bp-confirmed');
      row.classList.add('bp-dirty');
      confirmationStatus.textContent = 'Есть несохранённые правки — после сохранения потребуется подтверждение';
    });
    check.addEventListener('change', () => {
      if (check.checked) state.checked.add(key); else state.checked.delete(key);
    });
    return row;
  }

  function evidence(item) {
    if (!item || !item.quote) return el('p', {class: 'bp-evidence bp-evidence-none', text: 'Источник не найден — заполните вручную'});
    const source = String(item.source_id || '').startsWith('manual:') ? 'введено вручную' : 'источник: ' + item.source_id;
    return el('p', {class: 'bp-evidence'},
      el('span', {class: 'bp-source', text: source}),
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
    if (!left.length) return el('p', {class: 'bp-hint', text: 'Все заполненные поля подтверждены — можно публиковать.'});
    return el('p', {class: 'bp-hint', text: 'Перед публикацией: ' + left.join(', ') + '.'});
  }

  function renderRating(rating, previousTotal) {
    const box = el('aside', {class: 'bp-rating', 'aria-label': 'Рейтинг готовности'});
    if (!rating) return box;
    const total = el('div', {class: 'bp-total'},
      el('strong', {text: String(rating.total)}),
      el('span', {text: '/100'}));
    box.append(el('h4', {text: 'Готовность задачи'}), total,
      el('p', {class: 'bp-level bp-level-' + rating.level, text: LEVELS[rating.level] || rating.level}));
    if (previousTotal != null) {
      const diff = rating.total - previousTotal;
      box.append(el('p', {class: 'bp-delta' + (diff > 0 ? ' bp-up' : diff < 0 ? ' bp-down' : ''),
        text: diff === 0 ? 'Баллы не изменились' : (diff > 0 ? '+' : '−') + Math.abs(diff) + ' ' + points(Math.abs(diff))}));
    }
    const items = el('ul', {class: 'bp-items'});
    for (const item of rating.items || []) {
      const bar = el('div', {class: 'bp-bar'}, el('span', {style: 'width:' + (item.maximum ? Math.round(100 * item.earned / item.maximum) : 0) + '%'}));
      items.append(el('li', {},
        el('div', {class: 'bp-item-head'}, el('span', {text: item.label}), el('span', {text: item.earned + '/' + item.maximum})),
        bar,
        el('p', {class: 'bp-hint', text: item.explanation})));
    }
    box.append(items);
    if (rating.missing_fields && rating.missing_fields.length) {
      box.append(el('p', {class: 'bp-missing', text: 'Не хватает: ' + rating.missing_fields.map(f => FIELD_LABEL[f] || f).join(', ')}));
    }
    return box;
  }
}
