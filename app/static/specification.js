const SECTIONS = {summary:'Цель и результат', requirements:'Функциональные требования',
  architecture:'Технический подход и ограничения', acceptance:'Критерии приёмки',
  plan:'Этапы и результаты работы', risks:'Риски и границы задачи', questions:'Открытые вопросы заказчику'};
const IDEA_FIELDS = {title:'Название идеи', description:'Описание идеи', rationale:'Польза',
  implementation:'Как реализовать', acceptance:'Как проверить результат'};
const STATUS = {empty:'ТЗ ещё не сформировано', draft:'Черновик — требуется проверка',
  approved:'ТЗ утверждено бизнесом', stale:'Данные карточки изменились — сформируйте ТЗ заново'};
function node(tag, text, className) {
  const n = document.createElement(tag);
  if (text != null) n.textContent = text;
  if (className) n.className = className;
  return n;
}
function modeText(doc) { return doc.mode === 'mock' ? 'Шаблон без реального AI (mock)' : 'Подготовлено AI: ' + (doc.provider || ''); }
const SOURCE_LABELS = {title:'Название', industry:'Отрасль', context:'Контекст', need:'Потребность', users:'Пользователи', data:'Данные', constraints:'Ограничения', expected_result:'Ожидаемый результат', success_criteria:'Критерии успеха', contact:'Контакт', interaction_format:'Формат взаимодействия', feedback_process:'Обратная связь'};

export function specificationPreview(doc) {
  const box = node('article', null, 'spec-preview');
  box.append(node('h4', doc.title), node('p', modeText(doc), 'muted'));
  if (doc.source) {
    const source = node('details'); source.append(node('summary','Исходные сведения заказчика'));
    for (const [key,label] of Object.entries(SOURCE_LABELS)) source.append(node('p',label+': '+(doc.source[key] || 'Не указано')));
    box.append(source);
  }
  for (const [key, label] of Object.entries(SECTIONS)) box.append(node('h5', label), node('p', doc[key]));
  box.append(node('h5', 'Идеи, выбранные заказчиком'));
  if (!doc.ideas.length) box.append(node('p', 'Дополнительные идеи не выбраны. Выполняется базовое ТЗ.'));
  for (const idea of doc.ideas) {
    box.append(node('h5', idea.title));
    for (const [key, label] of Object.entries(IDEA_FIELDS)) if (key !== 'title') box.append(node('p', label + ': ' + idea[key]));
  }
  return box;
}

export function mountSpecification(root, api, hooks) {
  let card = null, draft = null, dirty = false;
  root.classList.add('spec-panel');
  root.hidden = true;
  function accept(result) {
    draft = result;
    dirty = false;
    card = {...card, revision:result.revision, review:result.review,
      has_unpublished_changes:!!card.published && (card.has_unpublished_changes || result.revision !== card.revision),
      specification:{enabled:result.enabled, status:result.status, stale:result.stale}};
    hooks.onChange(card);
    render();
  }
  function guard() {
    if (hooks.blocked()) throw new Error('Сначала сохраните правки карточки и разрешите конфликт версии');
  }
  function action(label, work) {
    const b = node('button', label); b.type = 'button';
    b.addEventListener('click', () => hooks.run(b, 'Подождите…', async () => {guard(); await work();}));
    return b;
  }
  function markDirty() {
    dirty = true;
    const status = root.querySelector('.spec-state');
    if (status) status.textContent = 'Есть несохранённые правки ТЗ — перед публикацией сохраните и утвердите их';
  }
  function edit(label, value, update, maxLength=8000) {
    const wrap = node('label', null, 'spec-edit'); wrap.append(node('span', label));
    const input = node('textarea'); input.rows = maxLength === 300 ? 2 : 4;
    input.value = value; input.maxLength = maxLength;
    input.addEventListener('input', () => {update(input.value); markDirty();});
    wrap.append(input); return wrap;
  }
  async function save() {
    for (const [key,label] of Object.entries({title:'Название ТЗ',...SECTIONS})) {
      if (!draft.content[key].trim()) throw new Error('Заполните раздел «'+label+'» или укажите, что вопрос требует уточнения');
    }
    for (const idea of draft.content.ideas) for (const [key,label] of Object.entries(IDEA_FIELDS)) {
      if (!idea[key].trim()) throw new Error('Заполните поле «'+label+'» в предложении идеи');
    }
    accept(await api.saveSpecification(card.id, {content:draft.content, selected_idea_ids:draft.selected_idea_ids}));
  }
  function render() {
    root.replaceChildren(); root.hidden = !card;
    if (!card) return;
    const meta = card.specification || {enabled:false, status:'empty'};
    const toggle = node('input'); toggle.type='checkbox'; toggle.id='spec-enabled'; toggle.checked=meta.enabled;
    toggle.setAttribute('role','switch');
    const toggleLabel = node('label', null, 'spec-toggle'); toggleLabel.htmlFor=toggle.id;
    toggleLabel.append(toggle, node('span','Составить техническое задание для студентов'));
    root.append(node('h3','Техническое задание'), toggleLabel,
      node('p','Необязательно. AI подготовит черновик по данным карточки. Вы сможете изменить текст, выбрать идеи и утвердить ТЗ. Студенты получат только опубликованную утверждённую версию.', 'muted'));
    toggle.addEventListener('change', () => {
      const enabled=toggle.checked; toggle.checked=meta.enabled;
      hooks.run(toggle, 'Сохраняем…', async () => {
        guard();
        if (dirty) throw new Error('Сохраните правки ТЗ перед переключением');
        accept(await api.setSpecificationEnabled(card.id, enabled));
      });
    });
    if (!meta.enabled) {hooks.lock(); return;}
    root.append(node('p', dirty ? 'Есть несохранённые правки ТЗ' : STATUS[meta.status] || STATUS.empty, 'spec-state'));
    const actions=node('div',null,'spec-actions');
    if (!draft && meta.status !== 'empty') actions.append(action('Открыть редактор ТЗ',async()=>accept(await api.getSpecificationDraft(card.id))));
    const generate=action(draft?.content || meta.status!=='empty' ? 'Сформировать ТЗ заново' : 'Сформировать ТЗ с AI', async()=>{
      if(dirty) throw new Error('Сохраните правки ТЗ перед повторной генерацией');
      accept(await api.generateSpecification(card.id));
    });
    actions.append(generate); root.append(actions);
    if (draft?.content || meta.status!=='empty') root.append(node('p','Повторная генерация заменит черновик, правки и выбранные идеи. Потребуется новое утверждение.', 'muted'));
    if(!draft?.content) {hooks.lock(); return;}
    root.append(node('p',modeText(draft),draft.mode==='mock'?'tag tag-mock':'tag'));
    if (draft.mode==='mock' && draft.warnings?.length) root.append(node('p','AI сейчас недоступен. Подготовлен шаблон по вашим данным: отредактируйте его или повторите генерацию позже.', 'muted'));
    if(meta.stale) {root.append(node('p','Старый черновик сохранён, но его нельзя утвердить или опубликовать. Сначала подтвердите обновлённые поля карточки и сформируйте ТЗ заново.')); hooks.lock(); return;}
    root.append(edit('Название ТЗ',draft.content.title,v=>draft.content.title=v,300));
    for(const [key,label] of Object.entries(SECTIONS)) root.append(edit(label,draft.content[key],v=>draft.content[key]=v));
    root.append(node('h4','Предложения AI — выберите нужные идеи'),
      node('p','Все идеи изначально выключены. Можно изменить каждую и выбрать несколько или ни одной. Они добавляются к базовым разделам ТЗ.', 'muted'));
    for(const idea of draft.content.ideas) {
      const box=node('fieldset',null,'spec-idea'); box.append(node('legend',idea.title));
      const label=node('label',null,'spec-toggle'), check=node('input'); check.type='checkbox';
      check.checked=draft.selected_idea_ids.includes(idea.id);
      label.append(check,node('span','Включить идею: '+idea.title)); box.append(label);
      check.addEventListener('change',()=>{
        draft.selected_idea_ids=draft.selected_idea_ids.filter(id=>id!==idea.id);
        if(check.checked) draft.selected_idea_ids.push(idea.id);
        markDirty();
      });
      for(const [key,title] of Object.entries(IDEA_FIELDS)) box.append(edit(title,idea[key],v=>idea[key]=v,key==='title'?300:8000));
      root.append(box);
    }
    const buttons=node('div',null,'spec-actions');
    buttons.append(action('Сохранить правки ТЗ',save),action('Утвердить ТЗ для студентов',async()=>{
      if(dirty) await save();
      accept(await api.approveSpecification(card.id));
    }),action('Предпросмотр выбранного ТЗ',async()=>{
      const doc={...draft.content, source:draft.source, mode:draft.mode, provider:draft.provider,
        ideas:draft.content.ideas.filter(i=>draft.selected_idea_ids.includes(i.id))};
      preview.replaceChildren(node('h4','Студенты получат после утверждения и публикации'),specificationPreview(doc)); preview.hidden=false;
    }),action('Скачать PDF ТЗ',async()=>{
      if(dirty) throw new Error('Сохраните правки ТЗ перед скачиванием PDF');
      const blob=await api.downloadSpecificationDraft(card.id);
      const url=URL.createObjectURL(blob), a=node('a'); a.href=url; a.download='sana-specification.pdf';
      root.append(a); a.click(); a.remove(); setTimeout(()=>URL.revokeObjectURL(url),10000);
    }));
    const preview=node('div',null,'spec-preview-wrap'); preview.hidden=true;
    root.append(buttons,node('p','После утверждения нажмите «Опубликовать» в карточке. До публикации студенты не увидят новое ТЗ.', 'muted'),preview);
    hooks.lock();
  }
  return {
    setCard(value) {if(card?.id!==value.id){draft=null;dirty=false;} card=value;render();},
    reset() {draft=null;dirty=false;},
    hasUnsaved() {return dirty;},
  };
}
