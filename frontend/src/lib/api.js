const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
const TOKEN_KEY = 'irr_token'
const USER_KEY = 'irr_user'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function getStoredUser() {
  const raw = localStorage.getItem(USER_KEY)
  return raw ? JSON.parse(raw) : null
}

export function storeSession(accessToken, user) {
  localStorage.setItem(TOKEN_KEY, accessToken)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `Erreur API (${status})`)
    this.status = status
  }
}

async function request(path, options = {}) {
  const token = getToken()
  const isFormData = options.body instanceof FormData
  const headers = { ...(isFormData ? {} : { 'Content-Type': 'application/json' }), ...options.headers }
  if (token) headers.Authorization = `Bearer ${token}`

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })

  if (!res.ok) {
    let detail
    try {
      detail = (await res.json()).detail
    } catch {
      detail = undefined
    }
    if (res.status === 401) clearSession()
    throw new ApiError(res.status, detail)
  }

  if (res.status === 204) return null
  return res.json()
}

export function login(username, password) {
  return request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

export function sso(token) {
  return request('/auth/sso', {
    method: 'POST',
    body: JSON.stringify({ token }),
  })
}

export function getRaffineriesJobs() {
  return request('/raffineries/jobs')
}

export function confirmRaffineriesJob(jobId, body) {
  return request(`/raffineries/jobs/${jobId}/confirm`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function cancelRaffineriesJob(jobId) {
  return request(`/raffineries/jobs/${jobId}`, { method: 'DELETE' })
}

export function getRaffineriesReferenceData() {
  return request('/raffineries/reference-data')
}

export function estimateRaffineriesJob(body) {
  return request('/raffineries/estimate', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function createRaffineriesJob(body) {
  return request('/raffineries/jobs', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function getSessions() {
  return request('/raffineries/sessions')
}

export function getMembers() {
  return request('/raffineries/sessions/members')
}

export function createSession(starSystem) {
  return request('/raffineries/sessions', {
    method: 'POST',
    body: JSON.stringify({ star_system: starSystem }),
  })
}

export function getSessionDetail(sessionId) {
  return request(`/raffineries/sessions/${sessionId}`)
}

export function renameSession(sessionId, numero) {
  return request(`/raffineries/sessions/${sessionId}/rename`, {
    method: 'PUT',
    body: JSON.stringify({ numero }),
  })
}

export function closeSession(sessionId) {
  return request(`/raffineries/sessions/${sessionId}/close`, { method: 'POST' })
}

export function addSessionShip(sessionId, shipName, shipRole) {
  return request(`/raffineries/sessions/${sessionId}/ships`, {
    method: 'POST',
    body: JSON.stringify({ ship_name: shipName, ship_role: shipRole }),
  })
}

export function removeSessionShip(shipId) {
  return request(`/raffineries/sessions/ships/${shipId}`, { method: 'DELETE' })
}

export function addCrewMember(shipId, username) {
  return request(`/raffineries/sessions/ships/${shipId}/crew`, {
    method: 'POST',
    body: JSON.stringify({ username }),
  })
}

export function removeCrewMember(crewId) {
  return request(`/raffineries/sessions/crew/${crewId}`, { method: 'DELETE' })
}

export function addSessionExpense(sessionId, description, amountAuec) {
  return request(`/raffineries/sessions/${sessionId}/expenses`, {
    method: 'POST',
    body: JSON.stringify({ description, amount_auec: amountAuec }),
  })
}

export function removeSessionExpense(expenseId) {
  return request(`/raffineries/sessions/expenses/${expenseId}`, { method: 'DELETE' })
}

export function getSessionFinancialSummary(sessionId) {
  return request(`/raffineries/sessions/${sessionId}/financial-summary`)
}

export function getRaffineriesLots() {
  return request('/raffineries/lots')
}

export function toggleRaffineryLotBlocked(lotId, isBlocked) {
  return request(`/raffineries/lots/${lotId}/toggle-block`, {
    method: 'POST',
    body: JSON.stringify({ is_blocked: isBlocked }),
  })
}

export function getPersonalStock() {
  return request('/raffineries/personal-stock')
}

export function relocatePersonalStock(stockId, location) {
  return request(`/raffineries/personal-stock/${stockId}/relocate`, {
    method: 'POST',
    body: JSON.stringify({ location }),
  })
}

export function consumePersonalStock(stockId, reason) {
  return request(`/raffineries/personal-stock/${stockId}/consume`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  })
}

export function getAllTerminals() {
  return request('/raffineries/all-terminals')
}

export function analyzeScreenshot(file) {
  const formData = new FormData()
  formData.append('screenshot', file)
  return request('/raffineries/analyze-screenshot', { method: 'POST', body: formData })
}

export function getCommodities() {
  return request('/commerce/commodities')
}

export function getCommodityPrices(commodityId) {
  return request(`/commerce/prices?commodity_id=${commodityId}`)
}

export function getStockCategories() {
  return request('/gestion-stock/categories')
}

export function getStockItems(categoryIds) {
  return request(`/gestion-stock/items?category_ids=${categoryIds.join(',')}`)
}

export function getItemPrices(itemId) {
  return request(`/gestion-stock/items/${itemId}/prices`)
}

export function addToStock(body) {
  return request('/gestion-stock/stock', { method: 'POST', body: JSON.stringify(body) })
}

export function getInventory() {
  return request('/gestion-stock/inventory')
}

export function setItemVisibility(itemId, isHidden) {
  return request(`/gestion-stock/items/${itemId}/visibility`, {
    method: 'POST',
    body: JSON.stringify({ is_hidden: isHidden }),
  })
}

export function getStockLogs() {
  return request('/gestion-stock/logs')
}

export function getFedStockSummary() {
  return request('/stock-federation/summary')
}

export function getFedInventory() {
  return request('/stock-federation/inventory')
}

export function getFedLots() {
  return request('/stock-federation/lots')
}

export function getFedLogs() {
  return request('/stock-federation/logs')
}

export function getFedPrices() {
  return request('/commerce-federation/fed-prices')
}

export function setFedPrice(commodityId, price) {
  return request('/commerce-federation/fed-prices', {
    method: 'POST',
    body: JSON.stringify({ commodity_id: commodityId, price }),
  })
}

export function getBestMarketPrice(commodityId) {
  return request(`/commerce-federation/best-price?commodity_id=${commodityId}`)
}

export function getTransportOrders(status) {
  return request(`/transport/orders?status=${status}`)
}

export function takeTransportOrder(orderId) {
  return request(`/transport/orders/${orderId}/take`, { method: 'POST' })
}

export function deliverTransportOrder(orderId) {
  return request(`/transport/orders/${orderId}/deliver`, { method: 'POST' })
}

export function searchBlueprints(search) {
  return request(`/crafting/blueprints?search=${encodeURIComponent(search)}`)
}

export function getLotsForIngredient(name) {
  return request(`/crafting/lots-for-ingredient?name=${encodeURIComponent(name)}`)
}

export function toggleLotBlocked(lotId, isBlocked) {
  return request(`/crafting/lots/${lotId}/toggle-block`, {
    method: 'POST',
    body: JSON.stringify({ is_blocked: isBlocked }),
  })
}

export function getBlockedLots() {
  return request('/crafting/blocked-lots')
}
