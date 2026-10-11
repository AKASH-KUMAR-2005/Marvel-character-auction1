const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000/api').replace(/\/$/, '');

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error || `Request failed (${response.status})`);
  return body;
}

export const api = {
  health: () => request('/health'),
  createMatch: (payload) => request('/matches', { method: 'POST', body: JSON.stringify(payload) }),
  getMatch: (id) => request(`/matches/${encodeURIComponent(id)}`),
  nextCharacter: (id) => request(`/matches/${encodeURIComponent(id)}/next-character`, { method: 'POST', body: '{}' }),
  bid: (auctionId, teamId) => request(`/auctions/${encodeURIComponent(auctionId)}/bid`, { method: 'POST', body: JSON.stringify({ team_id: teamId }) }),
  skip: (auctionId, teamId) => request(`/auctions/${encodeURIComponent(auctionId)}/skip`, { method: 'POST', body: JSON.stringify({ team_id: teamId }) }),
  resolve: (auctionId) => request(`/auctions/${encodeURIComponent(auctionId)}/resolve`, { method: 'POST', body: '{}' }),
  endMatch: (id) => request(`/matches/${encodeURIComponent(id)}/end`, { method: 'POST', body: '{}' }),
  analyze: (id) => request(`/matches/${encodeURIComponent(id)}/analyze`, { method: 'POST', body: '{}' }),
  history: () => request('/results'),
  result: (id) => request(`/results/${encodeURIComponent(id)}`),
};
