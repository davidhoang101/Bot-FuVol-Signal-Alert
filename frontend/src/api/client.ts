/** API client for backend communication. */

const API_BASE = '/api'

async function fetchAPI(endpoint: string, options?: RequestInit) {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Unknown error' }))
    throw new Error(error.error || error.message || 'Request failed')
  }

  return response.json()
}

export const api = {
  // Health
  health: () => fetchAPI('/health'),

  // Config
  getConfig: () => fetchAPI('/config'),
  reloadConfig: () => fetchAPI('/config/reload', { method: 'POST' }),

  // Markets
  getFundingOpportunities: (params?: {
    min_rate?: number
    max_spread_bps?: number
    quote?: string
    exclude_low_volume?: boolean
  }) => {
    const searchParams = new URLSearchParams()
    if (params?.min_rate !== undefined) searchParams.set('min_rate', params.min_rate.toString())
    if (params?.max_spread_bps !== undefined) searchParams.set('max_spread_bps', params.max_spread_bps.toString())
    if (params?.quote) searchParams.set('quote', params.quote)
    if (params?.exclude_low_volume !== undefined) searchParams.set('exclude_low_volume', params.exclude_low_volume.toString())
    return fetchAPI(`/markets/funding?${searchParams.toString()}`)
  },

  getSymbolSnapshot: (symbol: string) => fetchAPI(`/markets/symbol/${symbol}/snapshot`),

  // Trade
  openDeltaNeutral: (data: {
    symbol: string
    notional: number
    leverage?: number
    client_request_id?: string
  }) => fetchAPI('/trade/open_delta_neutral', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  closeDeltaNeutral: (data: {
    symbol: string
    client_request_id?: string
  }) => fetchAPI('/trade/close_delta_neutral', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  placeOrder: (data: {
    symbol: string
    side: string
    amount: number
    market_type: string
    order_type?: string
    price?: number
    leverage?: number
  }) => fetchAPI('/trade/place_order', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  // Orders
  getOrders: (params?: { symbol?: string; market_type?: string }) => {
    const searchParams = new URLSearchParams()
    if (params?.symbol) searchParams.set('symbol', params.symbol)
    if (params?.market_type) searchParams.set('market_type', params.market_type)
    return fetchAPI(`/orders?${searchParams.toString()}`)
  },

  // Positions
  getPositions: (params?: { symbol?: string }) => {
    const searchParams = new URLSearchParams()
    if (params?.symbol) searchParams.set('symbol', params.symbol)
    return fetchAPI(`/positions?${searchParams.toString()}`)
  },

  // Balances
  getBalances: () => fetchAPI('/balances'),

  // Margin
  getMargin: () => fetchAPI('/margin'),

  // Emergency
  emergencyCloseAll: (symbol?: string) => {
    const searchParams = new URLSearchParams()
    if (symbol) searchParams.set('symbol', symbol)
    return fetchAPI(`/emergency/close_all?${searchParams.toString()}`, { method: 'POST' })
  },

  // Logs
  getLogs: (params?: { limit?: number; level?: string }) => {
    const searchParams = new URLSearchParams()
    if (params?.limit) searchParams.set('limit', params.limit.toString())
    if (params?.level) searchParams.set('level', params.level)
    return fetchAPI(`/logs/tail?${searchParams.toString()}`)
  },
}
