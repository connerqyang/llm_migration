import {
  Component,
  Migration,
  MigrationDetails,
  MigrationRequest,
  MigrationResponse,
  MigrationHistory,
  AnalyticsOverview,
  AnalyticsTrends,
  AnalyticsErrors
} from '../types/api'

const API_BASE_URL = 'http://localhost:8000'

class ApiError extends Error {
  status: number
  
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function apiRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`
  
  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    })

    if (!response.ok) {
      throw new ApiError(`HTTP ${response.status}: ${response.statusText}`, response.status)
    }

    return await response.json()
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    throw new ApiError(`Network error: ${error.message}`, 0)
  }
}

export const api = {
  // Health check
  health: (): Promise<{ status: string; service: string }> => 
    apiRequest('/health'),

  // Components
  getComponents: (): Promise<Component[]> => 
    apiRequest('/api/components'),
  discoverComponents: (): Promise<{ message: string; discovered_components: string[]; total_discovered: number }> => 
    apiRequest('/api/components/discover', { method: 'POST' }),

  // Migrations
  getMigrations: (params: Record<string, string> = {}): Promise<MigrationHistory> => {
    const query = new URLSearchParams(params).toString()
    return apiRequest(`/api/migrations${query ? `?${query}` : ''}`)
  },
  getMigrationDetails: (migrationId: string): Promise<MigrationDetails> => 
    apiRequest(`/api/migrations/${migrationId}`),
  triggerMigration: (migrationData: MigrationRequest): Promise<MigrationResponse> => 
    apiRequest('/api/migrate', {
      method: 'POST',
      body: JSON.stringify(migrationData),
    }),

  // Analytics
  getAnalyticsOverview: (params: Record<string, string> = {}): Promise<AnalyticsOverview> => {
    const query = new URLSearchParams(params).toString()
    return apiRequest(`/api/analytics/overview${query ? `?${query}` : ''}`)
  },
  getAnalyticsTrends: (params: Record<string, string> = {}): Promise<AnalyticsTrends> => {
    const query = new URLSearchParams(params).toString()
    return apiRequest(`/api/analytics/trends${query ? `?${query}` : ''}`)
  },
  getAnalyticsErrors: (params: Record<string, string> = {}): Promise<AnalyticsErrors> => {
    const query = new URLSearchParams(params).toString()
    return apiRequest(`/api/analytics/errors${query ? `?${query}` : ''}`)
  },
}