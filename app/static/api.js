// Shared contract from docs/TEAM.md. Screens never calculate scores themselves.
const revisions = new Map();
async function request(path, {method = 'GET', body, role, cardId, withTotal = false, blob = false} = {}) {
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
  if (response.ok && blob) return response.blob();
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
  if (data.id && data.revision) revisions.set(data.id, Math.max(revisions.get(data.id) || 0, data.revision));
  if (withTotal) return {items: data, total: Number(response.headers.get('X-Total-Count') ?? data.length)};
  return data;
}
// Drops empty filters so the query string stays readable.
const query = params => new URLSearchParams(Object.entries(params).filter(([, v]) => v !== '' && v != null));
const id = encodeURIComponent;
export const api = {
  createDraft: body => request('/drafts', {method:'POST', body, role:'business'}),
  clarifyDraft: draftId => request(`/drafts/${id(draftId)}/clarify`, {method:'POST', role:'business'}),
  buildCard: (draftId, body) => request(`/drafts/${id(draftId)}/card`, {method:'POST', body, role:'business'}),
  getCard: cardId => request(`/cards/${id(cardId)}`),
  getSpecificationDraft: cardId => request(`/cards/${id(cardId)}/specification/draft`, {role:'business'}),
  setSpecificationEnabled: (cardId, enabled) => request(`/cards/${id(cardId)}/specification/settings`, {method:'PATCH', body:{enabled}, role:'business', cardId}),
  generateSpecification: cardId => request(`/cards/${id(cardId)}/specification/generate`, {method:'POST', role:'business', cardId}),
  saveSpecification: (cardId, body) => request(`/cards/${id(cardId)}/specification/draft`, {method:'PUT', body, role:'business', cardId}),
  approveSpecification: cardId => request(`/cards/${id(cardId)}/specification/approve`, {method:'POST', role:'business', cardId}),
  downloadSpecificationDraft: cardId => request(`/cards/${id(cardId)}/specification/draft.pdf`, {role:'business', cardId, blob:true}),
  reviewCard: cardId => request(`/cards/${id(cardId)}/review`, {method:'POST', role:'business', cardId}),
  updateCard: (cardId, body) => request(`/cards/${id(cardId)}`, {method:'PATCH', body, role:'business', cardId}),
  confirmCard: (cardId, body) => request(`/cards/${id(cardId)}/confirm`, {method:'POST', body, role:'business', cardId}),
  publishCard: cardId => request(`/cards/${id(cardId)}/publish`, {method:'POST', role:'business', cardId}),
  listCards: (filters = {}) => request('/cards?' + new URLSearchParams(filters)),
  /** One catalog page: {items, total}. Ranking stays on the server. */
  listCardsPage: ({q = '', industry = '', level = '', limit = 20, offset = 0} = {}) =>
    request('/cards?' + query({q, industry, level, limit, offset}), {withTotal: true}),
  catalogFacets: () => request('/catalog/facets'),
  teamRecommendations: (teamId, limit = 5) => request(`/teams/${id(teamId)}/recommendations?limit=${limit}`),
  listTeams: () => request('/teams'),
  createProposal: (cardId, body) => request(`/cards/${id(cardId)}/proposals`, {method:'POST', body, role:'team'}),
  listProposals: cardId => request(`/cards/${id(cardId)}/proposals`),
  decideProposal: (proposalId, body) => request(`/proposals/${id(proposalId)}/decision`, {method:'POST', body, role:'business'}),
  confirmMilestone: proposalId => request(`/proposals/${id(proposalId)}/milestone`, {method:'POST', role:'business'}),
};
