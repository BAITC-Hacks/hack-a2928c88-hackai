// The server owns permissions, assessment phrases, lifecycle and PDF verification.
// This component never computes a recommendation or inserts user text as HTML.
const COPY = {
  ru: {
    title: 'Проекты и рекомендации', intro: 'Подтвердите роли в команде. После завершения проекта заказчик сможет выдать проверяемое рекомендательное письмо.',
    refresh: 'Обновить', loading: 'Загружаем…', saving: 'Сохраняем…', retry: 'Повторить загрузку', signIn: 'Выберите учётную запись вверху раздела, чтобы открыть свои проекты и рекомендации.', projects: 'Ваши проекты', empty: 'Здесь появятся проекты по выбранным откликам.', select: 'Выберите проект, чтобы открыть состав команды и рекомендации.',
    active: 'В работе', completed: 'Завершён', closed_early: 'Закрыт досрочно', draft: 'Предпросмотр', issued: 'Действительно', valid: 'Действительно', replaced: 'Заменено', revoked: 'Отозвано',
    project: 'Проект', company: 'Компания', team: 'Команда', started: 'Начало', closed: 'Завершение', dateUnknown: 'Не указано', acceptedStages: 'Подтверждённые этапы', noStages: 'Подтверждённых этапов нет.', roster: 'Состав и роли', rosterHelp: 'Роли указывает команда. В письмо попадут только участники, подтвердившие свою роль.',
    rosterClosed: 'Проект закрыт: состав команды зафиксирован.', rosterEmpty: 'Капитан ещё не указал участников проекта.', include: 'Участвует в проекте', role: 'Роль', analyst: 'Аналитик', developer: 'Разработчик', designer: 'Дизайнер', manager: 'Менеджер проекта', project_manager: 'Менеджер проекта', other: 'Другое',
    confirmed: 'Роль подтверждена', pending: 'Ожидает подтверждения', saveRoles: 'Сохранить состав и роли', rolesSaved: 'Состав сохранён. Каждый участник подтверждает свою роль самостоятельно.', confirmRole: 'Подтвердить мою роль', roleConfirmed: 'Ваша роль подтверждена.',
    closeTitle: 'Завершите проект', closeHelp: 'После закрытия откроется опросник на 30 дней. До закрытия проверьте состав команды и подтверждения ролей.', closeMode: 'Как завершился проект?', completeOption: 'Все этапы приняты заказчиком', earlyOption: 'Проект закрыт досрочно', completeHint: 'Завершение проверяется по принятым этапам на сервере.', closeButton: 'Зафиксировать завершение', closeConfirm: 'Состав команды проверен; подтверждаю закрытие проекта', closedSaved: 'Проект закрыт. Опросник доступен заказчику.',
    assessment: 'Опросник заказчика', assessmentIntro: 'Девять вопросов о работе команды — около трёх минут. Письмо собирается из выбранных ответов; комментарии включаются дословно.', unavailable: 'Опросник откроется после завершения или досрочного закрытия проекта.', expired: 'Срок заполнения опросника истёк.', deadline: 'Доступен до', template: 'Шаблон', choose: 'Выберите ответ', optional: 'Комментарий — необязательно', example: 'Конкретный результат — от 50 до 500 символов', exampleHint: 'Опишите, что именно команда подготовила и как вы это проверили.', count: 'символов', maxChoices: 'Можно выбрать не более', nobody: 'Никого не выделять — оставьте список пустым.', noMembers: 'Пока нет участников с подтверждённой ролью.', extra: 'Дополнительный комментарий — до 1000 символов', savePreview: 'Сохранить и посмотреть письмо', dirty: 'Есть несохранённые ответы. Сохраните их, чтобы обновить предпросмотр.', saved: 'Ответы сохранены.', noRecommendation: 'Ответы сохранены. При ответе «нет» на вопрос 6 рекомендательное письмо не формируется.',
    preview: 'Предпросмотр письма', previewHelp: 'Нажмите на предложение, чтобы перейти к исходному ответу. Текст письма напрямую не редактируется.', source: 'Изменить ответ на вопрос', sourceComment: 'Изменить комментарий к вопросу', systemSource: 'Сведения проекта', templateMode: 'Фразы из версионируемого шаблона; комментарии заказчика — дословно.', language: 'Язык письма', ru: 'Русский', kk: 'Қазақша', en: 'English', newVersion: 'Будет выпущена новая версия. Предыдущая останется в истории со статусом «Заменено».',
    signer: 'ФИО подписанта', position: 'Должность подписанта', issue: 'Выдать письмо', reissue: 'Выдать новую версию', issuedSaved: 'Письмо выдано. Участникам доступны личные копии.', history: 'Выданные письма', version: 'Версия', issuedAt: 'Выдано', revoke: 'Отозвать письмо', revokeHelp: 'После отзыва проверка каждой копии будет показывать «Отозвано».', revokeReason: 'Причина отзыва', revokeAction: 'Подтвердить отзыв', revokedSaved: 'Письмо отозвано.',
    ownCopies: 'Мои рекомендации', ownPublicProfile: 'Открыть мой публичный профиль', teamPublicProfile: 'Открыть публичный профиль команды', noCopies: 'После выдачи письма здесь появится ваша личная копия с PDF и ссылкой проверки.', pdf: 'Скачать PDF с QR-кодом', verify: 'Проверить письмо', portfolio: 'Показывать в моём портфолио', visibilityHelp: 'Скрытая копия остаётся действительной. Публичная ссылка проверки работает независимо от видимости в портфолио.', visibilitySaved: 'Видимость копии обновлена.', complaint: 'Сообщить об ошибке в фактах', complaintLabel: 'Что нужно проверить?', complaintHelp: 'Сообщение увидит модератор. Укажите конкретную ошибку и правильные сведения.', complaintSend: 'Отправить модератору', complaintSent: 'Жалоба отправлена модератору.',
    consent: 'Публичный отзыв о команде', consentLabel: 'Разрешить публикацию судьбы прототипа и комментария к вопросу 1', consentHelp: 'С согласия команды публично показываются только эти два пункта. Остальные ответы опросника не публикуются.', consentSaved: 'Согласие команды обновлено.', publicReviews: 'Публичные отзывы о команде', noPublicReviews: 'Опубликованных отзывов с согласием команды пока нет.', prototypeFate: 'Что будет с прототипом', resultComment: 'Комментарий заказчика о результате', implementing: 'Внедряем', testing: 'Тестируем', not_planned: 'Пока не планируем', error: 'Не удалось выполнить действие.', retained: 'Введённые данные сохранены в этом окне.', required: 'Заполните обязательные поля.', chooseMember: 'Выберите хотя бы одного участника.', stale: 'Сохраните изменённые ответы и обновите предпросмотр перед выдачей.', copied: 'Ссылка скопирована.', copyLink: 'Скопировать ссылку', clipboardFailed: 'Не удалось скопировать ссылку. Откройте страницу проверки и скопируйте адрес.',
  },
  kk: {
    title: 'Жобалар мен ұсынымдар', intro: 'Командадағы рөлдерді растаңыз. Жоба аяқталған соң тапсырыс беруші тексерілетін ұсыным хат бере алады.',
    refresh: 'Жаңарту', loading: 'Жүктелуде…', saving: 'Сақталуда…', retry: 'Қайта жүктеу', signIn: 'Жобалар мен ұсынымдарды ашу үшін бөлімнің жоғарғы жағынан тіркелгіні таңдаңыз.', projects: 'Сіздің жобаларыңыз', empty: 'Таңдалған өтінімдер бойынша жобалар осында көрсетіледі.', select: 'Команда құрамы мен ұсынымдарды көру үшін жобаны таңдаңыз.',
    active: 'Орындалуда', completed: 'Аяқталды', closed_early: 'Мерзімінен бұрын жабылды', draft: 'Алдын ала қарау', issued: 'Жарамды', valid: 'Жарамды', replaced: 'Ауыстырылды', revoked: 'Кері қайтарылды',
    project: 'Жоба', company: 'Компания', team: 'Команда', started: 'Басталуы', closed: 'Аяқталуы', dateUnknown: 'Көрсетілмеген', acceptedStages: 'Расталған кезеңдер', noStages: 'Расталған кезеңдер жоқ.', roster: 'Құрам және рөлдер', rosterHelp: 'Рөлдерді команда көрсетеді. Хатқа өз рөлін растаған қатысушылар ғана енгізіледі.',
    rosterClosed: 'Жоба жабылды: команда құрамы бекітілді.', rosterEmpty: 'Капитан жоба қатысушыларын әлі көрсетпеді.', include: 'Жобаға қатысады', role: 'Рөл', analyst: 'Талдаушы', developer: 'Әзірлеуші', designer: 'Дизайнер', manager: 'Жоба менеджері', project_manager: 'Жоба менеджері', other: 'Басқа',
    confirmed: 'Рөлі расталды', pending: 'Растау күтілуде', saveRoles: 'Құрам мен рөлдерді сақтау', rolesSaved: 'Құрам сақталды. Әр қатысушы өз рөлін өзі растайды.', confirmRole: 'Өз рөлімді растау', roleConfirmed: 'Сіздің рөліңіз расталды.',
    closeTitle: 'Жобаны аяқтаңыз', closeHelp: 'Жабылғаннан кейін сауалнама 30 күнге ашылады. Алдымен команда құрамы мен рөлдердің расталуын тексеріңіз.', closeMode: 'Жоба қалай аяқталды?', completeOption: 'Барлық кезеңді тапсырыс беруші қабылдады', earlyOption: 'Жоба мерзімінен бұрын жабылды', completeHint: 'Аяқталу серверде қабылданған кезеңдер бойынша тексеріледі.', closeButton: 'Аяқталуды бекіту', closeConfirm: 'Команда құрамы тексерілді; жобаны жабуды растаймын', closedSaved: 'Жоба жабылды. Тапсырыс беруші сауалнаманы толтыра алады.',
    assessment: 'Тапсырыс берушінің сауалнамасы', assessmentIntro: 'Команда жұмысы туралы тоғыз сұрақ — шамамен үш минут. Хат таңдалған жауаптардан құралады; түсініктемелер сөзбе-сөз енгізіледі.', unavailable: 'Сауалнама жоба аяқталғанда немесе мерзімінен бұрын жабылғанда ашылады.', expired: 'Сауалнаманы толтыру мерзімі аяқталды.', deadline: 'Қолжетімді мерзімі', template: 'Үлгі', choose: 'Жауапты таңдаңыз', optional: 'Түсініктеме — міндетті емес', example: 'Нақты нәтиже — 50–500 таңба', exampleHint: 'Команда не дайындағанын және оны қалай тексергеніңізді сипаттаңыз.', count: 'таңба', maxChoices: 'Таңдаудың ең көп саны', nobody: 'Ешкімді ерекшелеу қажет болмаса, тізімді бос қалдырыңыз.', noMembers: 'Рөлін растаған қатысушылар әлі жоқ.', extra: 'Қосымша түсініктеме — 1000 таңбаға дейін', savePreview: 'Сақтау және хатты қарау', dirty: 'Сақталмаған жауаптар бар. Алдын ала қарауды жаңарту үшін сақтаңыз.', saved: 'Жауаптар сақталды.', noRecommendation: 'Жауаптар сақталды. 6-сұраққа «жоқ» деп жауап берілсе, ұсыным хат жасалмайды.',
    preview: 'Хатты алдын ала қарау', previewHelp: 'Бастапқы жауапқа өту үшін сөйлемді басыңыз. Хат мәтінін тікелей өзгерту мүмкін емес.', source: 'Сұрақтың жауабын өзгерту', sourceComment: 'Сұрақтың түсініктемесін өзгерту', systemSource: 'Жоба деректері', templateMode: 'Нұсқаланған үлгінің сөйлемдері; тапсырыс берушінің түсініктемелері — сөзбе-сөз.', language: 'Хат тілі', ru: 'Русский', kk: 'Қазақша', en: 'English', newVersion: 'Жаңа нұсқа шығарылады. Алдыңғысы тарихта «Ауыстырылды» мәртебесімен сақталады.',
    signer: 'Қол қоюшының аты-жөні', position: 'Қол қоюшының лауазымы', issue: 'Хат беру', reissue: 'Жаңа нұсқаны беру', issuedSaved: 'Хат берілді. Қатысушыларға жеке көшірмелері қолжетімді.', history: 'Берілген хаттар', version: 'Нұсқа', issuedAt: 'Берілген күні', revoke: 'Хатты кері қайтару', revokeHelp: 'Кері қайтарылған соң әр көшірмені тексеру бетінде «Кері қайтарылды» көрсетіледі.', revokeReason: 'Кері қайтару себебі', revokeAction: 'Кері қайтаруды растау', revokedSaved: 'Хат кері қайтарылды.',
    ownCopies: 'Менің ұсынымдарым', ownPublicProfile: 'Менің жария профилімді ашу', teamPublicProfile: 'Команданың жария профилін ашу', noCopies: 'Хат берілгеннен кейін PDF және тексеру сілтемесі бар жеке көшірмеңіз осында пайда болады.', pdf: 'QR-коды бар PDF жүктеу', verify: 'Хатты тексеру', portfolio: 'Менің портфолиомда көрсету', visibilityHelp: 'Жасырылған көшірме жарамды болып қалады. Тексеру сілтемесі портфолиодағы көрініске тәуелсіз жұмыс істейді.', visibilitySaved: 'Көшірменің көрінісі жаңартылды.', complaint: 'Деректердегі қате туралы хабарлау', complaintLabel: 'Нені тексеру керек?', complaintHelp: 'Хабарламаны модератор көреді. Нақты қатені және дұрыс деректерді көрсетіңіз.', complaintSend: 'Модераторға жіберу', complaintSent: 'Шағым модераторға жіберілді.',
    consent: 'Команда туралы жария пікір', consentLabel: 'Прототиптің келешегі мен 1-сұрақ түсініктемесін жариялауға келісемін', consentHelp: 'Команданың келісімімен тек осы екі тармақ жарияланады. Сауалнаманың басқа жауаптары жарияланбайды.', consentSaved: 'Команданың келісімі жаңартылды.', publicReviews: 'Команда туралы жария пікірлер', noPublicReviews: 'Команда келісім берген жария пікірлер әлі жоқ.', prototypeFate: 'Прототиптің келешегі', resultComment: 'Тапсырыс берушінің нәтиже туралы түсініктемесі', implementing: 'Енгізіп жатырмыз', testing: 'Сынап жатырмыз', not_planned: 'Әзірге жоспар жоқ', error: 'Әрекетті орындау мүмкін болмады.', retained: 'Енгізілген деректер осы терезеде сақталды.', required: 'Міндетті өрістерді толтырыңыз.', chooseMember: 'Кемінде бір қатысушыны таңдаңыз.', stale: 'Хатты бермес бұрын өзгерген жауаптарды сақтап, алдын ала қарауды жаңартыңыз.', copied: 'Сілтеме көшірілді.', copyLink: 'Сілтемені көшіру', clipboardFailed: 'Сілтемені көшіру мүмкін болмады. Тексеру бетін ашып, мекенжайды көшіріңіз.',
  },
};

const QUESTION_LABELS = {
  ru: ['Насколько результат соответствует ожидаемому из карточки?', 'Что сделала команда?', 'Сильные стороны команды — до трёх', 'Как команда соблюдала договорённости?', 'Что будет с прототипом?', 'Готовы рекомендовать команду?', 'Готовы рассмотреть участников на стажировку или работу?', 'Хотите отметить кого-то отдельно — до двух участников?', 'Что ещё хотите сказать?'],
  kk: ['Нәтиже карточкадағы күтілген нәтижеге қаншалықты сәйкес келеді?', 'Команда не істеді?', 'Команданың мықты жақтары — үшеуге дейін', 'Команда келісімдерді қалай орындады?', 'Прототиптің келешегі қандай?', 'Команданы ұсынуға дайынсыз ба?', 'Қатысушыларды тағылымдамаға немесе жұмысқа қарастыруға дайынсыз ба?', 'Кімді ерекше атап өткіңіз келеді — екі қатысушыға дейін?', 'Тағы не айтқыңыз келеді?'],
};

function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text != null) element.textContent = String(text);
  if (className) element.className = className;
  return element;
}
const clone = value => JSON.parse(JSON.stringify(value));
const identifier = value => encodeURIComponent(String(value));
let mountCounter = 0;

/** transport.request uses API-relative paths and the current server-verified actor. */
export function mountProjectLetters(root, transport, context = {}) {
  const prefix = `project-letters-${++mountCounter}`;
  const drafts = new Map();
  let language = context.language === 'kk' ? 'kk' : 'ru';
  let projects = [], project = null, questionnaire = null, preview = null, copies = [], publicReviews = [];
  let busy = false, destroyed = false, hasLoaded = false, pendingRefresh = false, errorText = '', notice = '';
  let selectedId = '', activeActor = actorId();
  let statusNode, contentNode, refreshButton;
  const t = key => COPY[language][key] || key;
  const request = async (path, options) => {
    const requestActor = actorId();
    const result = await transport.request(path, options);
    if (destroyed || requestActor !== actorId()) {
      const stale = new Error('Actor changed'); stale.staleActor = true; throw stale;
    }
    return result;
  };
  const actor = () => transport.actor || {};
  function actorId() { const person = transport.actor || {}; return person.user_id || person.id || ''; }
  const can = permission => !!project?.permissions?.[permission];
  const date = value => {
    if (!value) return t('dateUnknown');
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleDateString(language === 'kk' ? 'kk-KZ' : 'ru-RU', {day: 'numeric', month: 'long', year: 'numeric'});
  };
  function labelOf(item) { return item?.label?.[language] || item?.[`label_${language}`] || item?.label?.ru || (typeof item?.label === 'string' ? item.label : item?.value || ''); }
  function currentDraft() {
    if (!project) return null;
    const key = `${activeActor}:${project.id}`;
    if (!drafts.has(key)) {
      const saved = questionnaire?.assessment || project.assessment || {};
      drafts.set(key, {
        answers: {q2: [], q3: [], ...clone(saved.answers || {})}, comments: clone(saved.comments || {}),
        highlighted_user_ids: [...(saved.highlighted_user_ids || [])], dirty: false,
        roles: (project.members || []).map(member => ({user_id: member.user_id, role: member.role})),
        rolesDirty: false, signer_name: '', signer_position: '', letterLanguage: language,
        closeStatus: 'completed', closeConfirmed: false, revokeReasons: {}, complaints: {},
      });
    }
    return drafts.get(key);
  }
  function setMessage(message, isError = false) {
    if (!statusNode || destroyed) return;
    statusNode.textContent = message;
    statusNode.className = `pl-status${isError ? ' pl-error' : ''}`;
    statusNode.setAttribute('role', isError ? 'alert' : 'status');
    statusNode.hidden = !message;
  }
  function updateBusy() {
    root.setAttribute('aria-busy', String(busy));
    for (const control of root.querySelectorAll('button, input, select, textarea')) {
      if (busy && !control.disabled) { control.dataset.plBusy = 'true'; control.disabled = true; }
      else if (!busy && control.dataset.plBusy === 'true') { control.disabled = false; delete control.dataset.plBusy; }
    }
  }
  async function run(work, message = 'saving') {
    if (busy || destroyed) return;
    busy = true; errorText = ''; notice = ''; updateBusy(); setMessage(t(message));
    try { await work(); if (!destroyed) setMessage(notice); }
    catch (error) {
      if (!destroyed && !error?.staleActor) {
        errorText = `${error?.message || t('error')} ${t('retained')}`;
        setMessage(errorText, true);
      }
    } finally {
      busy = false;
      if (!destroyed) {
        updateBusy();
        if (pendingRefresh) { pendingRefresh = false; void run(load, 'loading'); }
      }
    }
  }
  function button(text, handler, kind = '') {
    const element = node('button', text, `pl-button ${kind}`.trim());
    element.type = 'button';
    element.addEventListener('click', () => void run(handler));
    return element;
  }
  function section(title, help) {
    const result = node('section', null, 'pl-section');
    result.append(node('h3', title));
    if (help) result.append(node('p', help, 'pl-help'));
    return result;
  }
  function field(label, value, onInput, options = {}) {
    const wrap = node('label', null, 'pl-field'); wrap.append(node('span', label));
    const control = node(options.multiline ? 'textarea' : 'input');
    if (options.multiline) control.rows = options.rows || 3;
    else control.type = 'text';
    control.value = value || ''; control.maxLength = options.max || 500;
    if (options.required) control.required = true;
    if (options.min) control.minLength = options.min;
    if (options.id) control.id = options.id;
    control.addEventListener('input', () => { control.setCustomValidity(''); onInput(control.value); });
    wrap.append(control);
    if (options.help) wrap.append(node('span', options.help, 'pl-help'));
    return {wrap, control};
  }
  function submitForm(form, work) {
    form.addEventListener('submit', event => {
      event.preventDefault();
      if (form.reportValidity()) void run(work);
    });
  }
  function submit(label, kind = 'pl-primary') { const b = node('button', label, `pl-button ${kind}`); b.type = 'submit'; return b; }
  function tag(status) { return node('span', t(status), `pl-badge pl-badge-${['active', 'completed', 'closed_early', 'issued', 'valid', 'revoked', 'replaced', 'draft'].includes(status) ? status : 'draft'}`); }
  function metadata(entries) {
    const list = node('dl', null, 'pl-meta');
    for (const [term, value] of entries) { if (value) list.append(node('dt', term), node('dd', value)); }
    return list;
  }
  async function loadProject(projectId) {
    const loadingActor = actorId();
    const next = await request(`/projects/${identifier(projectId)}`);
    if (destroyed || loadingActor !== actorId()) return;
    let nextQuestionnaire = null;
    if (next.permissions?.can_assess) {
      nextQuestionnaire = await request(`/projects/${identifier(projectId)}/questionnaire`);
    }
    const nextPublicReviews = await request(`/teams/${identifier(next.team_id)}/project-recommendations`);
    if (destroyed || loadingActor !== actorId()) return;
    project = next; selectedId = next.id; questionnaire = nextQuestionnaire; preview = null; publicReviews = nextPublicReviews;
    const draft = currentDraft();
    if (!draft.rolesDirty) draft.roles = (next.members || []).map(member => ({user_id: member.user_id, role: member.role}));
    if (!draft.dirty && (nextQuestionnaire?.assessment || next.assessment)) {
      const saved = nextQuestionnaire?.assessment || next.assessment;
      draft.answers = {q2: [], q3: [], ...clone(saved.answers || {})}; draft.comments = clone(saved.comments || {});
      draft.highlighted_user_ids = [...(saved.highlighted_user_ids || [])];
    }
  }
  async function load() {
    const loadingActor = actorId();
    if (!loadingActor) { projects = []; copies = []; project = null; questionnaire = null; preview = null; hasLoaded = true; notice = t('signIn'); render(); return; }
    const actorChanged = activeActor !== actorId();
    if (actorChanged) { activeActor = actorId(); selectedId = ''; project = null; questionnaire = null; preview = null; }
    const [projectItems, ownCopies] = await Promise.all([request('/projects'), request('/me/letter-copies')]);
    if (destroyed || loadingActor !== actorId()) return;
    projects = projectItems; copies = ownCopies;
    if (selectedId && projects.some(item => item.id === selectedId)) await loadProject(selectedId);
    else { project = null; selectedId = ''; questionnaire = null; preview = null; }
    if (destroyed || loadingActor !== actorId()) return;
    hasLoaded = true; render();
  }
  async function refreshProject() {
    if (!selectedId) { await load(); return; }
    const loadingActor = actorId();
    await loadProject(selectedId);
    const [projectItems, ownCopies] = await Promise.all([request('/projects'), request('/me/letter-copies')]);
    if (destroyed || loadingActor !== actorId()) return;
    projects = projectItems; copies = ownCopies; render();
  }
  function render() {
    if (destroyed) return;
    root.classList.add('project-letters'); root.lang = language;
    const head = node('div', null, 'pl-head');
    const titles = node('div'); titles.append(node('h2', t('title')), node('p', t('intro'), 'pl-help'));
    refreshButton = button(t('refresh'), load); head.append(titles, refreshButton);
    statusNode = node('p', null, 'pl-status'); statusNode.setAttribute('aria-live', 'polite');
    contentNode = node('div', null, 'pl-workspace');
    root.replaceChildren(head, statusNode, contentNode);
    const menu = section(t('projects'));
    menu.classList.add('pl-projects');
    if (!projects.length) menu.append(node('p', hasLoaded ? t('empty') : t('loading'), 'pl-empty'));
    for (const item of projects) {
      const choice = button('', async () => { await loadProject(item.id); render(); });
      choice.classList.add('pl-project-choice'); choice.setAttribute('aria-pressed', String(item.id === selectedId));
      choice.append(node('strong', item.title || item.task_title || t('project')), node('span', item.team_name || item.team_id, 'pl-help'), tag(item.status));
      menu.append(choice);
    }
    const detail = node('div', null, 'pl-detail');
    contentNode.append(menu, detail);
    if (project) renderProject(detail);
    else detail.append(node('p', t('select'), 'pl-empty'));
    renderCopies();
    setMessage(errorText || notice, !!errorText); updateBusy();
  }
  function renderProject(target) {
    const header = section(project.title || t('project'));
    header.append(tag(project.status), metadata([[t('company'), project.company_name], [t('team'), project.team_name || project.team_id], [t('started'), date(project.started_at)], ...(project.closed_at ? [[t('closed'), date(project.closed_at)]] : [])]));
    target.append(header); renderRoster(target);
    if (project.status === 'active' && can('can_close')) renderClose(target);
    if (can('can_assess') || questionnaire || (actor().role === 'business' && project.assessment_deadline)) renderAssessment(target);
    else if (project.status === 'active') target.append(node('p', t('unavailable'), 'pl-help pl-callout'));
    if (preview) renderPreview(target);
    renderLetterHistory(target);
    if (can('can_consent')) renderConsent(target);
    renderPublicReviews(target);
  }
  function renderRoster(target) {
    const box = section(t('roster'), t('rosterHelp'));
    const draft = currentDraft();
    if (can('can_manage_roles') && project.status === 'active') {
      const form = node('form', null, 'pl-form');
      const available = project.available_members || [];
      for (const member of available) {
        const memberId = member.id || member.user_id;
        const selected = draft.roles.find(entry => entry.user_id === memberId);
        const row = node('div', null, 'pl-member-edit');
        const label = node('label', null, 'pl-check');
        const include = node('input'); include.type = 'checkbox'; include.checked = !!selected;
        include.setAttribute('aria-label', `${member.name}: ${t('include')}`);
        label.append(include, node('span', member.name || memberId));
        const roleLabel = node('label', null, 'pl-field'); roleLabel.append(node('span', t('role')));
        const role = node('select');
        for (const value of ['analyst', 'developer', 'designer', 'project_manager', 'other']) { const option = node('option', t(value)); option.value = value; role.append(option); }
        role.value = selected?.role === 'manager' ? 'project_manager' : selected?.role || 'developer';
        if (!role.value) role.value = 'other';
        role.disabled = !selected; role.setAttribute('aria-label', `${member.name}: ${t('role')}`);
        const update = () => {
          draft.roles = draft.roles.filter(entry => entry.user_id !== memberId);
          if (include.checked) draft.roles.push({user_id: memberId, role: role.value});
          role.disabled = !include.checked; draft.rolesDirty = true;
        };
        include.addEventListener('change', update); role.addEventListener('change', update);
        roleLabel.append(role); row.append(label, roleLabel);
        const current = (project.members || []).find(entry => entry.user_id === memberId);
        if (current) row.append(node('span', current.confirmed_at ? t('confirmed') : t('pending'), 'pl-help'));
        form.append(row);
      }
      if (!available.length) form.append(node('p', t('rosterEmpty'), 'pl-empty'));
      const save = submit(t('saveRoles')); save.disabled = !available.length; form.append(save);
      submitForm(form, async () => {
        if (!draft.roles.length) throw new Error(t('chooseMember'));
        await request(`/projects/${identifier(project.id)}/roles`, {method: 'PUT', body: {members: draft.roles}});
        draft.rolesDirty = false; await refreshProject(); notice = t('rolesSaved');
      });
      box.append(form);
    } else {
      const list = node('ul', null, 'pl-members');
      for (const member of project.members || []) {
        const row = node('li'); row.append(node('strong', member.name || member.user_id), node('span', t(member.role)), node('span', member.confirmed_at ? t('confirmed') : t('pending'), 'pl-help'));
        list.append(row);
      }
      box.append(list.childElementCount ? list : node('p', t('rosterEmpty'), 'pl-empty'));
      if (project.status !== 'active') box.append(node('p', t('rosterClosed'), 'pl-help'));
    }
    const ownRole = (project.members || []).find(member => member.user_id === actorId());
    if (can('can_confirm_role') && ownRole) box.append(button(t('confirmRole'), async () => {
      await request(`/projects/${identifier(project.id)}/roles/confirm`, {method: 'POST', body: {expected_role: ownRole.role}});
      await refreshProject(); notice = t('roleConfirmed');
    }, 'pl-primary'));
    target.append(box);
  }
  function renderClose(target) {
    const box = section(t('closeTitle'), t('closeHelp'));
    const draft = currentDraft(), form = node('form', null, 'pl-form');
    const modes = node('fieldset', null, 'pl-choices'); modes.append(node('legend', t('closeMode')));
    for (const [value, text] of [['completed', 'completeOption'], ['closed_early', 'earlyOption']]) {
      const label = node('label', null, 'pl-check'); const input = node('input'); input.type = 'radio'; input.name = `${prefix}-close`; input.value = value; input.checked = draft.closeStatus === value;
      input.addEventListener('change', () => { draft.closeStatus = value; }); label.append(input, node('span', t(text))); modes.append(label);
    }
    const confirmation = node('label', null, 'pl-check'); const check = node('input'); check.type = 'checkbox'; check.required = true; check.checked = draft.closeConfirmed;
    check.addEventListener('change', () => { draft.closeConfirmed = check.checked; }); confirmation.append(check, node('span', t('closeConfirm')));
    form.append(modes, node('p', t('completeHint'), 'pl-help'), confirmation, submit(t('closeButton')));
    submitForm(form, async () => { await request(`/projects/${identifier(project.id)}/close`, {method: 'POST', body: {status: draft.closeStatus}}); await refreshProject(); notice = t('closedSaved'); });
    box.append(form); target.append(box);
  }
  function markDirty(draft) {
    draft.dirty = true; preview = null;
    root.querySelector('.pl-preview')?.remove();
    const state = root.querySelector('.pl-draft-state'); if (state) { state.textContent = t('dirty'); state.hidden = false; }
  }
  function renderAssessment(target) {
    const box = section(t('assessment'), t('assessmentIntro'));
    if (!questionnaire || !questionnaire.available) {
      box.append(node('p', project.status === 'active' ? t('unavailable') : t('expired'), 'pl-callout'));
      target.append(box); return;
    }
    box.append(node('p', `${t('template')} ${questionnaire.template.version} · ${t('deadline')}: ${date(questionnaire.deadline)}`, 'pl-help'));
    const draft = currentDraft(), form = node('form', null, 'pl-form pl-assessment-form');
    for (let number = 1; number <= 9; number++) {
      const questionId = `q${number}`;
      const question = questionnaire.template.questions.find(item => item.id === questionId) || {id: questionId};
      const group = node('fieldset', null, 'pl-question'); group.id = `${prefix}-${questionId}`;
      group.append(node('legend', `${number}. ${labelOf(question) || QUESTION_LABELS[language][number - 1]}`));
      if (number === 8) {
        const confirmedMembers = (questionnaire.members || project.members || []).filter(member => member.confirmed_at);
        renderMultiple(group, confirmedMembers.map(member => ({value: member.user_id, label: member.name || member.user_id})), draft.highlighted_user_ids, 2, values => { draft.highlighted_user_ids = values; markDirty(draft); }, questionId);
        group.append(node('p', confirmedMembers.length ? t('nobody') : t('noMembers'), 'pl-help'));
      } else if (number !== 9) {
        const options = question.options || [];
        if (question.multiple || question.type === 'multiple' || number === 2 || number === 3) {
          renderMultiple(group, options, draft.answers[questionId] || [], question.max_choices || (number === 3 ? 3 : options.length), values => { draft.answers[questionId] = values; markDirty(draft); }, questionId);
        } else {
          const select = node('select'); select.id = `${prefix}-${questionId}-answer`; select.required = true;
          select.setAttribute('aria-label', labelOf(question) || QUESTION_LABELS[language][number - 1]);
          const placeholder = node('option', t('choose')); placeholder.value = ''; select.append(placeholder);
          for (const option of options) { const item = node('option', labelOf(option)); item.value = option.value; select.append(item); }
          select.value = draft.answers[questionId] || '';
          select.addEventListener('change', () => { draft.answers[questionId] = select.value; markDirty(draft); }); group.append(select);
        }
      }
      const comment = field(number === 2 ? t('example') : number === 9 ? t('extra') : t('optional'), draft.comments[questionId], value => { draft.comments[questionId] = value; markDirty(draft); }, {multiline: true, max: number === 9 ? 1000 : 500, required: number === 2, min: number === 2 ? 50 : undefined, id: `${prefix}-${questionId}-comment`, help: number === 2 ? t('exampleHint') : ''});
      const counter = node('span', `${comment.control.value.length} / ${number === 9 ? 1000 : 500} ${t('count')}`, 'pl-counter');
      comment.control.addEventListener('input', () => { counter.textContent = `${comment.control.value.length} / ${number === 9 ? 1000 : 500} ${t('count')}`; });
      comment.wrap.append(counter); group.append(comment.wrap); form.append(group);
    }
    const languageLabel = node('label', null, 'pl-field'); languageLabel.append(node('span', t('language')));
    const languageSelect = node('select');
    for (const value of ['ru', 'kk', 'en']) { const option = node('option', t(value)); option.value = value; languageSelect.append(option); }
    languageSelect.value = draft.letterLanguage;
    languageSelect.addEventListener('change', () => { draft.letterLanguage = languageSelect.value; preview = null; root.querySelector('.pl-preview')?.remove(); });
    languageLabel.append(languageSelect);
    const draftState = node('p', draft.dirty ? t('dirty') : '', 'pl-draft-state pl-help'); draftState.hidden = !draft.dirty;
    form.append(languageLabel, draftState, submit(t('savePreview')));
    submitForm(form, async () => {
      if (!(draft.answers.q2 || []).length) {
        const control = root.querySelector(`#${prefix}-q2-answer`);
        control?.focus();
        throw new Error(`${QUESTION_LABELS[language][1]} ${t('required')}`);
      }
      const result = await request(`/projects/${identifier(project.id)}/assessment`, {method: 'PUT', body: {answers: draft.answers, comments: draft.comments, highlighted_user_ids: draft.highlighted_user_ids}});
      questionnaire.assessment = result.assessment || result; draft.dirty = false;
      draft.answers = {q2: [], q3: [], ...clone(questionnaire.assessment.answers)};
      draft.comments = clone(questionnaire.assessment.comments || {});
      preview = draft.answers.q6 === 'no' ? null : await request(`/projects/${identifier(project.id)}/letter/preview?language=${identifier(draft.letterLanguage)}`);
      notice = t(draft.answers.q6 === 'no' ? 'noRecommendation' : 'saved'); render();
      root.querySelector('.pl-preview')?.scrollIntoView({behavior: 'smooth', block: 'start'});
    });
    box.append(form); target.append(box);
  }
  function renderMultiple(parent, options, values, maximum, onChange, questionId) {
    const choices = node('div', null, 'pl-options'); const selected = new Set(values);
    const localError = node('p', null, 'pl-inline-error'); localError.setAttribute('role', 'alert'); localError.hidden = true;
    for (const [index, option] of options.entries()) {
      const label = node('label', null, 'pl-check'); const input = node('input'); input.type = 'checkbox'; input.checked = selected.has(option.value);
      input.id = `${prefix}-${questionId}-answer${index ? `-${index}` : ''}`;
      input.addEventListener('change', () => {
        if (input.checked && selected.size >= maximum) { input.checked = false; localError.textContent = `${t('maxChoices')} ${maximum}.`; localError.hidden = false; return; }
        if (input.checked) selected.add(option.value); else selected.delete(option.value);
        localError.hidden = true; onChange([...selected]);
      });
      label.append(input, node('span', labelOf(option))); choices.append(label);
    }
    parent.append(choices, localError);
  }
  function renderPreview(target) {
    const box = section(t('preview'), t('previewHelp')); box.classList.add('pl-preview'); box.tabIndex = -1;
    const draft = currentDraft(), document = preview;
    box.append(node('p', t('templateMode'), 'pl-help'));
    if (document.header) box.append(metadata([[t('company'), document.header.company_name], [t('project'), document.header.title], [t('started'), date(document.header.started_at)], [t('closed'), date(document.header.closed_at)]]));
    const recipients = node('div', null, 'pl-preview-recipients');
    recipients.append(node('h4', t('roster')), node('p', t('rosterHelp'), 'pl-help'));
    for (const member of document.members || []) recipients.append(node('p', `${member.name || member.user_id} · ${t(member.role)}`));
    const stages = node('div', null, 'pl-preview-stages'); stages.append(node('h4', t('acceptedStages')));
    for (const stage of document.header?.stages || []) stages.append(node('p', `${stage.expected_result || stage.name} · ${date(stage.accepted_at)}`));
    if (!document.header?.stages?.length) stages.append(node('p', t('noStages'), 'pl-help'));
    box.append(recipients, stages);
    const body = node('div', null, 'pl-letter-body'); body.lang = document.language || draft.letterLanguage;
    for (const sentence of document.sentences || []) {
      const source = sentence.source || {};
      if (/^q[1-9]$/.test(source.question_id)) {
        const editable = node('button', sentence.text, 'pl-sentence'); editable.type = 'button';
        editable.title = `${t(source.kind === 'comment' ? 'sourceComment' : 'source')} ${source.question_id.slice(1)}`;
        editable.addEventListener('click', () => {
          const control = root.querySelector(`#${prefix}-${source.question_id}-${source.kind === 'comment' || source.question_id === 'q9' ? 'comment' : 'answer'}`);
          if (control) { control.scrollIntoView({behavior: 'smooth', block: 'center'}); control.focus({preventScroll: true}); }
        });
        body.append(editable);
      } else body.append(node('p', sentence.text));
    }
    if (!(document.sentences || []).length) body.append(node('p', document.body_text));
    box.append(body);
    const existing = [...(project.letters || [])].sort((a, b) => b.version - a.version).find(letter => ['issued', 'valid', 'revoked'].includes(letter.status));
    if (existing) box.append(node('p', t('newVersion'), 'pl-callout'));
    const form = node('form', null, 'pl-form');
    const signer = field(t('signer'), draft.signer_name, value => { draft.signer_name = value; }, {required: true, max: 160});
    const position = field(t('position'), draft.signer_position, value => { draft.signer_position = value; }, {required: true, max: 160});
    form.append(signer.wrap, position.wrap, submit(t(existing ? 'reissue' : 'issue')));
    submitForm(form, async () => {
      if (draft.dirty || preview !== document) throw new Error(t('stale'));
      const name = draft.signer_name.trim(), title = draft.signer_position.trim();
      if (!name || !title) throw new Error(t('required'));
      await request(`/letters/${identifier(existing ? existing.id : document.id)}/${existing ? 'reissue' : 'issue'}`, {method: 'POST', body: {signer_name: name, signer_position: title, ...(existing ? {language: document.language, draft_id: document.id} : {})}});
      preview = null; await refreshProject(); notice = t('issuedSaved');
    });
    box.append(form); target.append(box);
  }
  function renderLetterHistory(target) {
    const issued = (project.letters || []).filter(letter => letter.status !== 'draft');
    if (!issued.length) return;
    const box = section(t('history')); const draft = currentDraft();
    for (const letter of [...issued].sort((a, b) => b.version - a.version)) {
      const entry = node('article', null, 'pl-letter-entry');
      const top = node('div', null, 'pl-row'); top.append(node('h4', `${t('version')} ${letter.version} · ${t(letter.language)}`), tag(letter.status));
      entry.append(top, node('p', `${t('issuedAt')}: ${date(letter.issued_at)}`, 'pl-help'));
      if (letter.body_text) { const details = node('details'); details.append(node('summary', t('preview')), node('p', letter.body_text, 'pl-letter-text')); entry.append(details); }
      if (letter.signer_name) entry.append(node('p', [letter.signer_name, letter.signer_position].filter(Boolean).join(' · '), 'pl-help'));
      if ((can('can_revoke') || can('can_assess')) && ['issued', 'valid'].includes(letter.status)) {
        const details = node('details', null, 'pl-revoke'); details.append(node('summary', t('revoke')), node('p', t('revokeHelp'), 'pl-help'));
        const form = node('form', null, 'pl-form');
        const reason = field(t('revokeReason'), draft.revokeReasons[letter.id], value => { draft.revokeReasons[letter.id] = value; }, {multiline: true, required: true, min: 10, max: 1000});
        form.append(reason.wrap, submit(t('revokeAction'), 'pl-danger'));
        submitForm(form, async () => { await request(`/letters/${identifier(letter.id)}/revoke`, {method: 'POST', body: {reason: reason.control.value.trim()}}); await refreshProject(); notice = t('revokedSaved'); });
        details.append(form); entry.append(details);
      }
      box.append(entry);
    }
    target.append(box);
  }
  function renderConsent(target) {
    const box = section(t('consent'), t('consentHelp')); box.classList.add('pl-consent');
    const label = node('label', null, 'pl-check'); const check = node('input'); check.type = 'checkbox'; check.checked = !!(project.public_consent ?? project.assessment?.public_consent);
    check.addEventListener('change', () => { const desired = check.checked; void run(async () => {
      try { await request(`/projects/${identifier(project.id)}/public-consent`, {method: 'PUT', body: {public_consent: desired}}); await refreshProject(); notice = t('consentSaved'); }
      catch (error) { if (check.isConnected) check.checked = !desired; throw error; }
    }); });
    label.append(check, node('span', t('consentLabel'))); box.append(label); target.append(box);
  }
  function renderPublicReviews(target) {
    const box = section(t('publicReviews'), t('consentHelp')); box.classList.add('pl-public-reviews');
    const profile = node('a', t('teamPublicProfile'), 'pl-button pl-public-profile');
    profile.href = `/profiles/teams/${identifier(project.team_id)}?lang=${language}`; profile.target = '_blank'; profile.rel = 'noopener noreferrer'; box.append(profile);
    if (!publicReviews.length) box.append(node('p', t('noPublicReviews'), 'pl-help'));
    for (const review of publicReviews) {
      const entry = node('article', null, 'pl-letter-entry');
      entry.append(node('h4', t('prototypeFate')), node('p', t(review.prototype_fate)));
      if (review.result_comment) entry.append(node('h4', t('resultComment')), node('p', review.result_comment));
      box.append(entry);
    }
    target.append(box);
  }
  function renderCopies() {
    if (actor().role === 'business' && !copies.length) return;
    const box = section(t('ownCopies'), t('visibilityHelp')); box.classList.add('pl-copies');
    if (actor().role === 'student' && actorId()) {
      const profile = node('a', t('ownPublicProfile'), 'pl-button pl-public-profile');
      profile.href = `/profiles/users/${identifier(actorId())}?lang=${language}`; profile.target = '_blank'; profile.rel = 'noopener noreferrer'; box.append(profile);
    }
    if (!copies.length) box.append(node('p', t('noCopies'), 'pl-empty'));
    for (const copy of copies) {
      const article = node('article', null, 'pl-copy');
      const top = node('div', null, 'pl-row'); top.append(node('h4', copy.project_title || copy.title || t('project')), tag(copy.letter_status || copy.status || 'issued'));
      article.append(top);
      if (copy.student_name || copy.name) article.append(node('p', [copy.student_name || copy.name, t(copy.role || '')].filter(Boolean).join(' · ')));
      if (copy.version || copy.letter_version) article.append(node('p', `${t('version')} ${copy.version || copy.letter_version}`, 'pl-help'));
      const actions = node('div', null, 'pl-actions');
      actions.append(button(t('pdf'), async () => {
        const blob = await request(`/letter-copies/${identifier(copy.id)}/pdf`, {blob: true});
        const url = URL.createObjectURL(blob); const anchor = node('a'); anchor.href = url; anchor.download = `Sana-Hub-${copy.id}.pdf`; anchor.hidden = true;
        root.append(anchor); anchor.click(); anchor.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
      }));
      if (copy.verify_code) {
        const path = `/verify/${identifier(copy.verify_code)}`;
        const verify = node('a', t('verify'), 'pl-button'); verify.href = path; verify.target = '_blank'; verify.rel = 'noopener noreferrer';
        actions.append(verify, button(t('copyLink'), async () => { try { await navigator.clipboard.writeText(new URL(path, window.location.origin).href); notice = t('copied'); } catch { throw new Error(t('clipboardFailed')); } }));
      }
      article.append(actions);
      const visibility = node('label', null, 'pl-check'); const check = node('input'); check.type = 'checkbox'; check.checked = !!copy.show_in_portfolio;
      check.addEventListener('change', () => { const desired = check.checked; void run(async () => {
        try { await request(`/letter-copies/${identifier(copy.id)}/visibility`, {method: 'PATCH', body: {show_in_portfolio: desired}}); copies = await request('/me/letter-copies'); render(); notice = t('visibilitySaved'); }
        catch (error) { if (check.isConnected) check.checked = !desired; throw error; }
      }); });
      visibility.append(check, node('span', t('portfolio'))); article.append(visibility);
      const details = node('details'); details.append(node('summary', t('complaint')), node('p', t('complaintHelp'), 'pl-help'));
      const key = `${activeActor}:copy:${copy.id}`; if (!drafts.has(key)) drafts.set(key, {complaint: ''}); const draft = drafts.get(key);
      const form = node('form', null, 'pl-form'); const complaint = field(t('complaintLabel'), draft.complaint, value => { draft.complaint = value; }, {multiline: true, required: true, min: 10, max: 2000});
      form.append(complaint.wrap, submit(t('complaintSend')));
      submitForm(form, async () => { await request(`/letter-copies/${identifier(copy.id)}/complaint`, {method: 'POST', body: {text: draft.complaint.trim()}}); draft.complaint = ''; render(); notice = t('complaintSent'); });
      details.append(form); article.append(details); box.append(article);
    }
    root.append(box);
  }
  async function openProposal(proposalId) {
    return run(async () => {
      const next = await request(`/proposals/${identifier(proposalId)}/project`, {method: 'POST', body: {}});
      selectedId = next.id; await load();
      root.scrollIntoView({behavior: 'smooth', block: 'start'});
    }, 'loading');
  }
  render();
  if (context.proposalId) void openProposal(context.proposalId); else void run(load, 'loading');
  return {
    refresh: () => {
      if (activeActor !== actorId()) {
        activeActor = actorId(); selectedId = ''; project = null; questionnaire = null; preview = null;
        projects = []; copies = []; hasLoaded = false; errorText = ''; notice = ''; render();
      }
      if (busy) { pendingRefresh = true; return; }
      return run(load, 'loading');
    },
    openProposal,
    setLanguage(value) { language = value === 'kk' ? 'kk' : 'ru'; render(); },
    destroy() { destroyed = true; root.replaceChildren(); root.classList.remove('project-letters'); drafts.clear(); },
  };
}
