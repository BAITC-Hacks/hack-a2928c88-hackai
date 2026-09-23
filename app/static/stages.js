// Separate from the teammate-owned catalogue. Demo roles are labelled, not authentication.
export function mountStages(root, api, cardId) {
  let proposals = [], selected = '', stage = null, published = null, busy = false, dirty = false;
  const node = (tag, text, cls) => {
    const el = document.createElement(tag);
    if (text != null) el.textContent = text;
    if (cls) el.className = cls;
    return el;
  };
  const heading = node('h3', 'Первый проверяемый этап');
  const note = node('p', 'Учебные роли: бизнес задаёт условия и принимает результат; выбранная команда отправляет работу. Ссылка не является независимым доказательством качества.', 'bp-hint');
  const status = node('p'); status.setAttribute('role', 'status');
  const content = node('div');
  const refresh = node('button', 'Обновить этапы'); refresh.type = 'button';
  root.className = 'bp-stages bp-review';
  root.replaceChildren(heading, note, refresh, status, content);
  async function run(fn) {
    if (busy) return;
    busy = true;
    const controls = [...root.querySelectorAll('button, input, select, textarea')];
    const previous = controls.map(el => el.disabled);
    controls.forEach(el => { el.disabled = true; });
    status.textContent = 'Загружаем…';
    try { await fn(); status.textContent = ''; }
    catch (error) { status.textContent = 'Ошибка: ' + error.message + '. Ввод сохранён. При конфликте обновите этапы.'; }
    finally { controls.forEach((el, i) => { el.disabled = previous[i]; }); busy = false; }
  }
  function mayDiscard() { return !dirty || window.confirm('Обновление заменит несохранённый ввод этапа. Продолжить?'); }
  async function load() {
    const [cards, items] = await Promise.all([api.listCards({}), api.listProposals(cardId)]);
    published = cards.find(c => c.id === cardId);
    proposals = items.filter(p => p.status === 'selected');
    if (!proposals.some(p => p.id === selected)) selected = proposals[0]?.id || '';
    stage = selected ? await api.getStage(selected) : null;
    dirty = false;
    render();
  }
  refresh.addEventListener('click', () => { if (mayDiscard()) void run(load); });
  function form(fields, label, action) {
    const form = node('form', null, 'bp-stage-form');
    const inputs = {};
    for (const [key, title, initial, type] of fields) {
      const lab = node('label', title);
      const input = node(type === 'url' ? 'input' : 'textarea');
      input.name = key; input.required = true; input.maxLength = 3000;
      input.setAttribute('aria-label', title);
      if (type === 'url') input.type = 'url'; else input.rows = 3;
      input.value = initial || '';
      input.addEventListener('input', () => { dirty = true; });
      lab.append(input); form.append(lab); inputs[key] = input;
    }
    const submit = node('button', label); submit.type = 'submit'; form.append(submit);
    form.addEventListener('submit', event => {
      event.preventDefault();
      if (!form.reportValidity()) return;
      void run(async () => {
        const values = Object.fromEntries(Object.entries(inputs).map(([k,v]) => [k,v.value.trim()]));
        if (Object.values(values).some(v => !v)) throw new Error('Заполните все поля');
        stage = await action(values);
        dirty = false;
        render();
      });
    });
    return form;
  }
  function render() {
    content.replaceChildren();
    if (!published) { content.append(node('p', 'Сначала опубликуйте карточку и выберите команду по её отклику.')); return; }
    if (!proposals.length) { content.append(node('p', 'Выберите команду в каталоге, затем нажмите «Обновить этапы».')); return; }
    const choice = node('select'); choice.setAttribute('aria-label', 'Выбранный отклик для этапа');
    for (const p of proposals) {
      const option = node('option', `${p.team_name}: ${p.idea.slice(0, 60)}`);
      option.value = p.id; choice.append(option);
    }
    choice.value = selected;
    choice.addEventListener('change', () => {
      const target = choice.value;
      choice.value = selected;
      if (!mayDiscard()) return;
      void run(async () => { const next = await api.getStage(target); selected = target; stage = next; dirty = false; render(); });
    });
    content.append(choice);
    if (!stage) {
      content.append(node('h4', 'Роль бизнеса: определить этап'),
        node('p', `Условия фиксируются по опубликованной версии ${published.revision}. После создания они не редактируются; будущие правки карточки их не подменяют.`, 'bp-hint'),
        form([
          ['expected_result', 'Результат первого этапа', published.expected_result],
          ['input_example', 'Входной пример или материалы', published.data],
          ['verification_method', 'Как бизнес проверит результат', published.success_criteria],
        ], 'Зафиксировать условия этапа', values => api.defineStage(selected, {...values, card_revision: published.revision})));
      return;
    }
    content.append(node('p', `Условия версии задачи ${stage.card_revision}. Версия этапа ${stage.version}.`));
    for (const [key,label] of [['expected_result','Ожидаемый результат'],['input_example','Входные материалы'],['verification_method','Способ приёмки']]) {
      content.append(node('h4', label), node('p', stage[key]));
    }
    if (stage.submission) {
      content.append(node('h4', 'Результат команды'), node('p', stage.submission.note));
      try {
        const url = new URL(stage.submission.url);
        if (['https:','http:'].includes(url.protocol)) {
          const link = node('a', 'Открыть результат команды'); link.href = url.href; link.target = '_blank'; link.rel = 'noopener noreferrer'; content.append(link);
        }
      } catch {}
    }
    if (stage.decision_note) content.append(node('p', 'Основание решения бизнеса: ' + stage.decision_note));
    if (stage.status === 'accepted') {
      content.append(node('p', 'Этап принят бизнесом. Баллы прогресса: 10. Повторного начисления нет.', 'bp-stage-accepted'));
    } else if (['defined','needs_changes'].includes(stage.status)) {
      content.append(node('h4', stage.status === 'needs_changes' ? 'Роль команды: доработать результат' : 'Роль команды: отправить результат'),
        form([['url','Ссылка на результат',stage.submission?.url,'url'], ['note','Что выполнено и как проверить',stage.submission?.note]],
          'Отправить результат этапа', values => api.submitStage(selected, {...values, version: stage.version})));
    } else {
      content.append(node('h4', 'Роль бизнеса: проверить результат'));
      const decisionForm = form([['note','Что проверено или что нужно доработать','']], 'Принять результат и начислить +10',
        values => api.decideStage(selected, {...values, version: stage.version, action:'accept'}));
      const revise = node('button', 'Вернуть на доработку'); revise.type = 'button';
      revise.addEventListener('click', () => {
        if (!decisionForm.reportValidity()) return;
        const text = decisionForm.querySelector('textarea').value.trim();
        if (!text) return;
        void run(async () => { stage = await api.decideStage(selected, {version:stage.version,action:'request_changes',note:text}); dirty=false; render(); });
      });
      decisionForm.append(revise); content.append(decisionForm);
    }
    if (stage.history?.length) {
      const history = node('details'); history.append(node('summary', 'История отправок и решений'));
      const names = {submitted:'Команда отправила результат',needs_changes:'Бизнес запросил доработку',accepted:'Бизнес принял результат'};
      for (const row of stage.history) history.append(node('p', `${names[row.event] || row.event}: ${row.note}`));
      content.append(history);
    }
  }
  void run(load);
  return {hasUnsaved: () => dirty};
}
