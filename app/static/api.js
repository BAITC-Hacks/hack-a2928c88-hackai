// Shared contract from docs/TEAM.md. Screens never calculate scores themselves.
const revisions = new Map();
async function request(path, {method = 'GET', body, role, cardId} = {}) {
  const headers = {'Content-Type': 'application/json'};
  if (role) headers['X-Demo-Role'] = role;
  if (cardId) {
    if (!revisions.has(cardId)) throw new Error('Откройте актуальную карточку перед изменением');
    headers['If-Match'] = String(revisions.get(cardId));
  }
  let response;
  try {
    response = await fetch('/api' + path, {method, headers, body: body === undefined ? undefined : JSON.stringify(body)});
  } catch {
    throw new Error('Нет связи с сервером. Повторите запрос.');
  }
  let data;
  try { data = await response.json(); }
  catch {
    throw new Error(response.ok
      ? 'Сервер вернул некорректный ответ. Повторите запрос.'
      : `Сервер временно недоступен (HTTP ${response.status}). Повторите запрос.`);
  }
  if (!response.ok) {
    const invalidUrl = Array.isArray(data.detail) && data.detail.some(item => item.loc?.includes('prototype_url'));
    const message = typeof data.detail === 'string' ? data.detail : invalidUrl
      ? 'Укажите корректную ссылку на прототип (http:// или https://).'
      : 'Проверьте заполнение обязательных полей';
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  if (data.id && data.revision) revisions.set(data.id, data.revision);
  return data;
}
const id = encodeURIComponent;
export const api = {
  createDraft: body => request('/drafts', {method:'POST', body, role:'business'}),
  clarifyDraft: draftId => request(`/drafts/${id(draftId)}/clarify`, {method:'POST', role:'business'}),
  buildCard: (draftId, body) => request(`/drafts/${id(draftId)}/card`, {method:'POST', body, role:'business'}),
  getCard: cardId => request(`/cards/${id(cardId)}`),
  updateCard: (cardId, body) => request(`/cards/${id(cardId)}`, {method:'PATCH', body, role:'business', cardId}),
  confirmCard: (cardId, body) => request(`/cards/${id(cardId)}/confirm`, {method:'POST', body, role:'business', cardId}),
  publishCard: cardId => request(`/cards/${id(cardId)}/publish`, {method:'POST', role:'business', cardId}),
  listCards: (filters = {}) => request('/cards?' + new URLSearchParams(filters)),
  listTeams: () => request('/teams'),
  createProposal: (cardId, body) => request(`/cards/${id(cardId)}/proposals`, {method:'POST', body, role:'team'}),
  listProposals: cardId => request(`/cards/${id(cardId)}/proposals`),
  decideProposal: (proposalId, body) => request(`/proposals/${id(proposalId)}/decision`, {method:'POST', body, role:'business'}),
  confirmMilestone: proposalId => request(`/proposals/${id(proposalId)}/milestone`, {method:'POST', role:'business'}),
};
