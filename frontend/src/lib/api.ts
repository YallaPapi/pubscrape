import axios, { AxiosInstance, AxiosRequestConfig } from 'axios'
import { 
  Campaign, 
  Lead, 
  CampaignSettings, 
  ApiResponse, 
  PaginatedResponse,
  CampaignMetrics,
  ExportOptions 
} from '../types'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.client.interceptors.request.use(
      (config) => {
        // Add auth token if available
        const token = localStorage.getItem('auth_token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('auth_token')
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    )
  }

  // Campaign Management
  async getCampaigns(page = 1, limit = 10): Promise<PaginatedResponse<Campaign>> {
    const response = await this.client.get(`/campaigns?page=${page}&limit=${limit}`)
    return response.data
  }

  async getCampaign(id: string): Promise<ApiResponse<Campaign>> {
    const response = await this.client.get(`/campaigns/${id}`)
    return response.data
  }

  async createCampaign(campaign: Partial<Campaign>): Promise<ApiResponse<Campaign>> {
    const response = await this.client.post('/campaigns', campaign)
    return response.data
  }

  async updateCampaign(id: string, updates: Partial<Campaign>): Promise<ApiResponse<Campaign>> {
    const response = await this.client.patch(`/campaigns/${id}`, updates)
    return response.data
  }

  async deleteCampaign(id: string): Promise<ApiResponse<void>> {
    const response = await this.client.delete(`/campaigns/${id}`)
    return response.data
  }

  async startCampaign(id: string): Promise<ApiResponse<Campaign>> {
    const response = await this.client.post(`/campaigns/${id}/start`)
    return response.data
  }

  async pauseCampaign(id: string): Promise<ApiResponse<Campaign>> {
    const response = await this.client.post(`/campaigns/${id}/pause`)
    return response.data
  }

  async stopCampaign(id: string): Promise<ApiResponse<Campaign>> {
    const response = await this.client.post(`/campaigns/${id}/stop`)
    return response.data
  }

  // Lead Management
  async getLeads(
    campaignId?: string,
    page = 1,
    limit = 50,
    filters?: Record<string, any>
  ): Promise<PaginatedResponse<Lead>> {
    const params = new URLSearchParams({
      page: page.toString(),
      limit: limit.toString(),
      ...(campaignId && { campaignId }),
      ...(filters && Object.entries(filters).reduce((acc, [key, value]) => {
        if (value !== undefined && value !== '') {
          acc[key] = value.toString()
        }
        return acc
      }, {} as Record<string, string>))
    })
    
    const response = await this.client.get(`/leads?${params}`)
    return response.data
  }

  async getLead(id: string): Promise<ApiResponse<Lead>> {
    const response = await this.client.get(`/leads/${id}`)
    return response.data
  }

  async updateLead(id: string, updates: Partial<Lead>): Promise<ApiResponse<Lead>> {
    const response = await this.client.patch(`/leads/${id}`, updates)
    return response.data
  }

  async deleteLead(id: string): Promise<ApiResponse<void>> {
    const response = await this.client.delete(`/leads/${id}`)
    return response.data
  }

  async bulkUpdateLeads(
    leadIds: string[],
    updates: Partial<Lead>
  ): Promise<ApiResponse<Lead[]>> {
    const response = await this.client.patch('/leads/bulk', {
      leadIds,
      updates
    })
    return response.data
  }

  async bulkDeleteLeads(leadIds: string[]): Promise<ApiResponse<void>> {
    const response = await this.client.delete('/leads/bulk', {
      data: { leadIds }
    })
    return response.data
  }

  // Export functionality
  async exportLeads(
    campaignId: string,
    options: ExportOptions
  ): Promise<ApiResponse<{ downloadUrl: string }>> {
    const response = await this.client.post(`/campaigns/${campaignId}/export`, options)
    return response.data
  }

  async downloadExport(downloadUrl: string): Promise<Blob> {
    const response = await this.client.get(downloadUrl, {
      responseType: 'blob'
    })
    return response.data
  }

  // Metrics and Analytics
  async getMetrics(): Promise<ApiResponse<CampaignMetrics>> {
    const response = await this.client.get('/metrics')
    return response.data
  }

  async getCampaignAnalytics(id: string): Promise<ApiResponse<any>> {
    const response = await this.client.get(`/campaigns/${id}/analytics`)
    return response.data
  }

  // Settings and Configuration
  async getSettings(): Promise<ApiResponse<CampaignSettings>> {
    const response = await this.client.get('/settings')
    return response.data
  }

  async updateSettings(settings: Partial<CampaignSettings>): Promise<ApiResponse<CampaignSettings>> {
    const response = await this.client.patch('/settings', settings)
    return response.data
  }

  // Health check
  async healthCheck(): Promise<ApiResponse<{ status: string; version: string }>> {
    const response = await this.client.get('/health')
    return response.data
  }
}

export const apiClient = new ApiClient()
export default apiClient