import {community, node, control, field} from './community.js';

const TEXT = {
  ru: {title:'Вопросы', signin:'Выберите учётную запись в разделе «Сотрудничество», чтобы задавать вопросы и отвечать.', open:'Открыть сотрудничество', all:'Все вопросы', answered:'С ответом', unanswered:'Без ответа', refresh:'Обновить вопросы', ask:'Ваш вопрос', similar:'Найти похожие вопросы', send:'Отправить вопрос', matches:'Похожие вопросы', none:'Похожих вопросов не найдено.', empty:'Вопросов пока нет.', rules:'10–1000 символов. До 5 вопросов на задачу в сутки (UTC). Ответ виден всем командам.', answer:'Ответ бизнеса', answerSend:'Ответить', answerEdit:'Сохранить исправленный ответ', edited:'изменён', edit:'Редактировать вопрос', save:'Сохранить вопрос', decline:'Отклонить', reason:'Причина', duplicate:'Отметить дубликат', original:'ID исходного вопроса', hide:'Скрыть', transfer:'Предложить перенос в карточку', apply:'Перенести в рабочую карточку', field:'Поле карточки', text:'Предлагаемый текст', confirmation:'Перенос снимет подтверждение поля. Опубликованная карточка изменится только после подтверждения и публикации бизнесом.', applied:'Перенесено в рабочую карточку. Загрузите её на экране бизнеса и подтвердите поле заново.', subscribed:'Отписаться от ответов', subscribe:'Подписаться на ответы', working:'Загрузка…', retry:'Не удалось выполнить действие. Повторите попытку.', remaining:'Осталось вопросов сегодня', source:'Исходный вопрос', new:'Новый', hidden:'Скрыт модератором', declined:'Отклонён', duplicateStatus:'Дубликат', cancel:'Отмена', pending:'Вопросы без ответа', mock:'Демонстрационная подсказка (mock), проверьте поле и текст.', live:'AI предлагает поле; текст ответа сохранён дословно.'},
  kk: {title:'Сұрақтар', signin:'Сұрақ қою немесе жауап беру үшін «Ынтымақтастық» бөлімінде пайдаланушыны таңдаңыз.', open:'Ынтымақтастықты ашу', all:'Барлық сұрақтар', answered:'Жауап берілген', unanswered:'Жауапсыз', refresh:'Сұрақтарды жаңарту', ask:'Сіздің сұрағыңыз', similar:'Ұқсас сұрақтарды іздеу', send:'Сұрақты жіберу', matches:'Ұқсас сұрақтар', none:'Ұқсас сұрақтар табылмады.', empty:'Әзірше сұрақ жоқ.', rules:'10–1000 таңба. Бір тапсырмаға тәулігіне 5 сұраққа дейін (UTC). Жауап барлық командаға көрінеді.', answer:'Тапсырыс берушінің жауабы', answerSend:'Жауап беру', answerEdit:'Өзгертілген жауапты сақтау', edited:'өзгертілген', edit:'Сұрақты өңдеу', save:'Сұрақты сақтау', decline:'Қабылдамау', reason:'Себеп', duplicate:'Қайталанған деп белгілеу', original:'Бастапқы сұрақтың ID нөмірі', hide:'Жасыру', transfer:'Карточкаға көшіруді ұсыну', apply:'Жұмыс карточкасына көшіру', field:'Карточка өрісі', text:'Ұсынылған мәтін', confirmation:'Көшіру өрістің растауын алып тастайды. Жарияланған карточка растаудан және жариялаудан кейін ғана өзгереді.', applied:'Жұмыс карточкасына көшірілді. Бизнес экранында карточканы жүктеп, өрісті қайта растаңыз.', subscribed:'Жауаптарға жазылудан бас тарту', subscribe:'Жауаптарға жазылу', working:'Жүктелуде…', retry:'Әрекетті орындау мүмкін болмады. Қайталап көріңіз.', remaining:'Бүгін қалған сұрақ саны', source:'Бастапқы сұрақ', new:'Жаңа', hidden:'Модератор жасырған', declined:'Қабылданбаған', duplicateStatus:'Қайталанған', cancel:'Бас тарту', pending:'Жауапсыз сұрақтар', mock:'Демонстрациялық ұсыныс (mock). Өріс пен мәтінді тексеріңіз.', live:'AI өрісті ұсынады; жауап мәтіні өзгеріссіз сақталған.'},
};
const FIELDS = {title:['Название','Атауы'],context:['Контекст','Мәнмәтін'],need:['Потребность','Қажеттілік'],users:['Пользователи','Пайдаланушылар'],data:['Данные','Деректер'],constraints:['Ограничения','Шектеулер'],expected_result:['Результат','Нәтиже'],success_criteria:['Критерии успеха','Табыс критерийлері'],contact:['Контакт','Байланыс'],interaction_format:['Формат работы','Жұмыс форматы'],feedback_process:['Обратная связь','Кері байланыс']};
const drafts = new Map();

export function mountQuestions(root, card, {business = false, onCount} = {}) {
  root.classList.add('community-questions');
  let data = null, filter = business ? 'unanswered' : 'all', offset = 0, busy = false, alive = true, epoch = 0, reloadPending = false;
  const localDrafts = new Map();
  const key = () => `${community.actor?.id || 'anonymous'}:${card.id}`;
  const t = key => (TEXT[community.language] || TEXT.ru)[key];
  const status = node('p', '', 'community-notice'); status.setAttribute('role','status');
  const content = node('div');
  root.append(status, content);
  async function request(message, work) {
    if (busy) return;
    busy = true; status.textContent = message;
    const controls = [...root.querySelectorAll('button,input,select,textarea')];
    const disabled = controls.map(item => item.disabled);
    controls.forEach(item => { item.disabled = true; });
    try { await work(); if (alive) status.textContent = ''; }
    catch (error) { if (alive) status.textContent = error.message || t('retry'); }
    finally {
      busy = false;
      controls.forEach((item,i) => { if (item.isConnected) item.disabled = disabled[i]; });
      if (alive && reloadPending) { reloadPending = false; void refresh(); }
    }
  }
  async function load() {
    const requestEpoch = ++epoch;
    if (!community.actor) { data = null; render(); return; }
    const value = await community.request(`/cards/${encodeURIComponent(card.id)}/questions?filter=${filter}&limit=20&offset=${offset}`);
    if (!alive || requestEpoch !== epoch) return;
    data = value; onCount?.(value.total); render();
  }
  function refresh() { return request(t('working'), load); }
  function editor(parent, title, value, save, {max=3000,min=1} = {}) {
    const box = node('form'); const input = node('textarea'); input.rows=4; input.required=true; input.minLength=min; input.maxLength=max; input.value=value;
    const draftKey=`${key()}:${parent.dataset.questionId}:${title}`; input.value=localDrafts.get(draftKey) ?? value;
    input.addEventListener('input',()=>localDrafts.set(draftKey,input.value));
    const send=node('button',title); send.type='submit';
    box.append(field(title,input),send,control(t('cancel'),()=>box.remove()));
    box.addEventListener('submit',event=>{event.preventDefault(); if (!box.reportValidity() || !input.value.trim()) return;
      void request(t('working'),async()=>{await save(input.value);localDrafts.delete(draftKey);await load();});});
    parent.append(box); input.focus(); return box;
  }
  function render() {
    content.replaceChildren();
    if (!community.actor) {
      content.append(node('p',t('signin')),control(t('open'),()=>{location.hash='#community';})); return;
    }
    const toolbar=node('div',null,'community-actions');
    const select=node('select');
    for(const [value,label] of [['all','all'],['answered','answered'],['unanswered','unanswered']]){const option=node('option',t(label));option.value=value;select.append(option);}
    select.value=filter; select.addEventListener('change',()=>{filter=select.value;offset=0;void refresh();});
    toolbar.append(field(t('title'),select),control(t('refresh'),refresh));
    if(data && community.actor.role === 'student') toolbar.append(control(t(data.subscribed?'subscribed':'subscribe'),()=>request(t('working'),async()=>{
      await community.request(`/cards/${encodeURIComponent(card.id)}/subscribe`,{method:'POST',body:{subscribed:!data.subscribed}});await load();
    })));
    content.append(node('h4',t(business?'pending':'title')),toolbar);
    if (!data) return;
    if (community.actor.role === 'student' && !data.can_ask) content.append(node('p',`${t('remaining')}: ${data.remaining_today}. ${t('rules')}`));
    if (data.can_ask) {
      const form=node('form',null,'community-ask'), input=node('textarea');input.rows=3;input.minLength=10;input.maxLength=1000;input.required=true;input.value=drafts.get(key()) || '';
      let checkedText=null;
      const results=node('div'), send=node('button',t('send'));send.type='submit';send.disabled=true;
      input.addEventListener('input',()=>{drafts.set(key(),input.value);checkedText=null;send.disabled=true;results.replaceChildren();});
      const similar=control(t('similar'),()=>request(t('working'),async()=>{
        if (!form.reportValidity()) return;
        const value=input.value.trim();
        const match=await community.request(`/cards/${encodeURIComponent(card.id)}/questions/similar?q=${encodeURIComponent(value)}`);
        checkedText=value;results.replaceChildren(node('h5',t('matches')));
        if (!match.items.length) results.append(node('p',t('none')));
        for(const item of match.items) results.append(node('p',item.text),...(item.answer?.text?[node('blockquote',item.answer.text)]:[]));
      }).then(()=>{send.disabled=checkedText!==input.value.trim();}));
      form.append(node('p',t('rules')),node('p',`${t('remaining')}: ${data.remaining_today}`),field(t('ask'),input),similar,results,send);
      form.addEventListener('submit',event=>{event.preventDefault();if(!form.reportValidity()||checkedText!==input.value.trim())return;
        void request(t('working'),async()=>{await community.request(`/cards/${encodeURIComponent(card.id)}/questions`,{method:'POST',body:{text:input.value}});drafts.delete(key());await load();});});
      content.append(form);
    }
    if(!data.items.length)content.append(node('p',t('empty')));
    for(const question of data.items){
      const item=node('article',null,'community-question');item.dataset.questionId=question.id;
      item.append(node('p',`${question.author_name || question.author_user_id} · ${t(question.status==='duplicate'?'duplicateStatus':question.status) || question.status}`, 'community-question-meta'),node('p',question.text));
      if(question.duplicate_of_id)item.append(control(t('source'),()=>request(t('working'),async()=>{
        const original=await community.request(`/questions/${encodeURIComponent(question.duplicate_of_id)}`);
        const panel=node('section',null,'community-original');panel.tabIndex=-1;
        panel.append(node('h5',t('source')),node('p',original.text));
        if(original.answer)panel.append(node('blockquote',original.answer.text));
        item.querySelector('.community-original')?.remove();item.append(panel);panel.focus();
      })));
      if(question.decline_reason)item.append(node('p',question.decline_reason));
      if(question.hide_reason)item.append(node('p',question.hide_reason));
      if(question.answer){item.append(node('strong',`${t('answer')}${question.answer.is_edited?' · '+t('edited'):''}`),node('blockquote',question.answer.text));}
      const actions=node('div',null,'community-actions');
      if(question.can_edit)actions.append(control(t('edit'),()=>editor(item,t('save'),question.text,text=>community.request(`/questions/${question.id}`,{method:'PATCH',body:{text,version:question.version}}),{min:10,max:1000})));
      if(question.can_answer||(question.can_manage&&question.answer))actions.append(control(t(question.answer?'answerEdit':'answerSend'),()=>editor(item,t(question.answer?'answerEdit':'answerSend'),question.answer?.text||'',text=>community.request(`/questions/${question.id}/answer`,{method:question.answer?'PATCH':'POST',body:question.answer?{text,version:question.answer.version}:{text}}))));
      if(question.can_manage&&!question.answer){
        actions.append(control(t('decline'),()=>editor(item,t('reason'),'',reason=>community.request(`/questions/${question.id}/decline`,{method:'POST',body:{reason,version:question.version}}),{max:1000})));
        actions.append(control(t('duplicate'),()=>request(t('working'),async()=>{
          const all={items:[]}; let page;
          do {
            page=await community.request(`/cards/${encodeURIComponent(card.id)}/questions?filter=all&limit=200&offset=${all.items.length}`);
            all.items.push(...page.items);
          } while(page.items.length && all.items.length<page.filtered_count);
          const form=node('form'),original=node('select');original.required=true;
          for(const candidate of all.items.filter(q=>q.id!==question.id&&['new','answered'].includes(q.status))){const option=node('option',candidate.text);option.value=candidate.id;original.append(option);}
          const submit=node('button',t('duplicate'));submit.type='submit';submit.disabled=!original.options.length;
          form.append(field(t('source'),original),submit,control(t('cancel'),()=>form.remove()));
          form.addEventListener('submit',event=>{event.preventDefault();if(!form.reportValidity())return;void request(t('working'),async()=>{
            await community.request(`/questions/${question.id}/merge`,{method:'POST',body:{duplicate_of_id:original.value,version:question.version}});await load();
          });});item.append(form);
        })));
      }
      if(question.can_hide)actions.append(control(t('hide'),()=>editor(item,t('reason'),'',reason=>community.request(`/questions/${question.id}/hide`,{method:'POST',body:{reason,version:question.version}}),{max:1000})));
      if(question.answer&&question.can_manage)actions.append(control(t('transfer'),()=>request(t('working'),async()=>{
        const suggestion=await community.request(`/questions/${question.id}/suggest-field`,{method:'POST'});
        const form=node('form'), target=node('select'), text=node('textarea'); text.value=suggestion.text;text.rows=4;text.required=true;
        for(const [value,labels]of Object.entries(FIELDS)){const option=node('option',labels[community.language==='kk'?1:0]);option.value=value;target.append(option);}target.value=suggestion.field;
        const save=node('button',t('apply'));save.type='submit';
        form.append(node('p',t(suggestion.mode==='mock'?'mock':'live')),field(t('field'),target),field(t('text'),text),node('p',t('confirmation')),save);
        form.addEventListener('submit',event=>{event.preventDefault();void request(t('working'),async()=>{
          await community.request(`/questions/${question.id}/apply-field`,{method:'POST',body:{field:target.value,text:text.value,card_revision:suggestion.card_revision,answer_version:suggestion.answer_version}});
          form.replaceChildren(node('p',t('applied')));
          dispatchEvent(new CustomEvent('community-card-changed',{detail:{cardId:card.id}}));
        });});item.append(form);
      })));
      item.append(actions);content.append(item);
    }
    if(data.filtered_count>20){
      const pagination=node('nav',null,'community-actions');pagination.setAttribute('aria-label',t('title'));
      const previous=control('←',()=>{offset=Math.max(0,offset-20);void refresh();});previous.disabled=offset===0;
      const next=control('→',()=>{offset+=20;void refresh();});next.disabled=offset+20>=data.filtered_count;
      previous.setAttribute('aria-label',community.language==='kk'?'Алдыңғы бет':'Предыдущая страница');
      next.setAttribute('aria-label',community.language==='kk'?'Келесі бет':'Следующая страница');
      pagination.append(previous,node('span',`${Math.floor(offset/20)+1} / ${Math.ceil(data.filtered_count/20)}`),next);content.append(pagination);
    }
  }
  const changed=()=>{
    epoch++;data=null;offset=0;status.textContent='';render();
    if(busy)reloadPending=true;else void refresh();
  };
  addEventListener('community-change',changed);
  void refresh();
  return {refresh,destroy(){alive=false;epoch++;removeEventListener('community-change',changed);}};
}
