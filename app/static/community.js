import {mountProjectLetters} from './project-letters.js';

export const community = {
  actor: null,
  language: 'ru',
  async request(path, {method = 'GET', body, blob = false} = {}) {
    const response = await fetch('/api' + path, {method, credentials: 'same-origin',
      headers: {'Content-Type': 'application/json', 'X-Community-Request': '1'},
      body: body === undefined ? undefined : JSON.stringify(body)});
    if (!response.ok) {
      let message = `HTTP ${response.status}`;
      try { const data = await response.json(); message = typeof data.detail === 'string' ? data.detail : 'Проверьте заполнение полей / Өрістерді тексеріңіз'; } catch { /* retain status */ }
      throw new Error(message);
    }
    return blob ? response.blob() : response.json();
  },
};

export function node(tag, text, className) {
  const result = document.createElement(tag);
  if (text != null) result.textContent = text;
  if (className) result.className = className;
  return result;
}

export function control(text, callback, className = '') {
  const result = node('button', text, className); result.type = 'button';
  result.addEventListener('click', callback); return result;
}

export function field(text, input) {
  input.setAttribute('aria-label', text);
  const label = node('label', null, 'community-field'); label.append(node('span', text), input); return label;
}

export function mountCommunity(root) {
  root.classList.add('community-workspace');
  const header = node('div', null, 'community-header');
  const identity = node('select');
  const language = node('select');
  for (const [value, label] of [['ru', 'Русский'], ['kk', 'Қазақша']]) {
    const option = node('option', label); option.value = value; language.append(option);
  }
  const notice = node('p', '', 'community-notice'); notice.setAttribute('role', 'status');
  const demo = node('p', 'Учебные учётные записи. Это демо, а не производственная авторизация. Уведомления приходят только в этот раздел. / Бұл оқу демосы. Хабарландырулар осы бөлімде көрсетіледі.', 'community-demo');
  header.append(node('h2', 'Сотрудничество / Ынтымақтастық'), demo,
    field('Учётная запись / Пайдаланушы', identity), field('Язык / Тіл', language), notice);
  const inbox = node('section', null, 'community-inbox');
  const projectRoot = node('section');
  root.append(header, inbox, projectRoot);
  const projects = mountProjectLetters(projectRoot, community, {language: community.language});
  let inboxEpoch = 0;
  async function refreshInbox() {
    const generation = ++inboxEpoch;
    inbox.replaceChildren();
    if (!community.actor) return;
    inbox.append(node('h3', community.language === 'kk' ? 'Хабарландырулар' : 'Уведомления'));
    try {
      const notifications = await community.request('/notifications');
      if (generation !== inboxEpoch) return;
      const labels = community.language === 'kk'
        ? {question_digest:'Жаңа сұрақтар', question_reminder:'72 сағат бойы жауап жоқ', question_answered:'Сұраққа жауап берілді', question_declined:'Сұрақ қабылданбады', assessment_reminder:'Сауалнаманы толтырыңыз', letter_issued:'Ұсыным хат берілді', letter_revoked:'Ұсыным хат қайтарылды', letter_complaint:'Деректер туралы шағым'}
        : {question_digest:'Новые вопросы', question_reminder:'Вопрос без ответа 72 часа', question_answered:'Получен ответ', question_declined:'Вопрос отклонён', assessment_reminder:'Заполните опросник', letter_issued:'Выдано рекомендательное письмо', letter_revoked:'Письмо отозвано', letter_complaint:'Жалоба на фактическую ошибку'};
      if (!notifications.length) inbox.append(node('p', community.language === 'kk' ? 'Жаңа хабарландыру жоқ.' : 'Новых уведомлений нет.'));
      for (const item of notifications) {
        const row = node('article', null, 'community-notification');
        row.append(node('strong', labels[item.kind] || item.kind), node('p', new Date(item.delivered_at).toLocaleString()),
          node('p', item.payload?.question_ids ? `${item.payload.question_ids.length}` : item.entity_id));
        if (!item.read) row.append(control(community.language === 'kk' ? 'Оқылды' : 'Прочитано', async () => {
          try { await community.request(`/notifications/${encodeURIComponent(item.id)}/read`, {method:'POST'}); await refreshInbox(); }
          catch (error) { notice.textContent = error.message; }
        }));
        inbox.append(row);
      }
      if (community.actor.role === 'moderator') {
        const complaints = await community.request('/letter-complaints');
        if (generation !== inboxEpoch) return;
        inbox.append(node('h3', community.language === 'kk' ? 'Деректер туралы шағымдар' : 'Жалобы на фактические ошибки'));
        for (const complaint of complaints) {
          const row = node('article', null, 'community-notification');
          row.append(node('strong', complaint.author_user_id), node('p', complaint.text),
            node('small', `${complaint.copy_id} · ${new Date(complaint.created_at).toLocaleString()}`));
          inbox.append(row);
        }
      }
    } catch (error) { if (generation === inboxEpoch) inbox.append(node('p', error.message, 'community-error')); }
  }
  identity.addEventListener('change', async () => {
    identity.disabled = true;
    try {
      const response = await community.request('/community/session', {method:'POST', body:{user_id:identity.value}});
      community.actor = response.actor;
      notice.textContent = community.language === 'kk' ? 'Пайдаланушы таңдалды.' : 'Учётная запись выбрана.';
      dispatchEvent(new CustomEvent('community-change'));
      await projects.refresh(); await refreshInbox();
    } catch (error) { notice.textContent = error.message; }
    finally { identity.disabled = false; }
  });
  language.addEventListener('change', () => {
    community.language = language.value;
    projects.setLanguage(language.value);
    dispatchEvent(new CustomEvent('community-change'));
    void refreshInbox();
  });
  async function refresh() {
    try {
      const info = await community.request('/community');
      community.actor = info.actor;
      dispatchEvent(new CustomEvent('community-change'));
      identity.replaceChildren(node('option', 'Выберите пользователя / Пайдаланушыны таңдаңыз'));
      identity.firstChild.value = '';
      for (const user of info.users) {
        const option = node('option', user.name); option.value = user.id; identity.append(option);
      }
      identity.value = community.actor?.id || '';
      identity.disabled = !info.demo;
      await projects.refresh(); await refreshInbox();
    } catch (error) { notice.textContent = error.message; }
  }
  root.addEventListener('community-project', event => projects.openProposal(event.detail));
  addEventListener('community-open-project', event => { location.hash = '#community'; void projects.openProposal(event.detail); });
  inbox.before(control('Обновить уведомления / Хабарландыруларды жаңарту', refreshInbox));
  void refresh();
  return {refresh, openProposal: id => projects.openProposal(id)};
}
