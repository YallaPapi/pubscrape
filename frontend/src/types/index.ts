export interface Lead {
  id: string
  name: string
  email: string
  phone?: string
  company?: string
  website?: string
  address?: string
  specialty?: string
  source: string
  confidence: number
  status: 'pending' | 'contacted' | 'qualified' | 'disqualified'
  notes?: string
  createdAt: Date
  updatedAt: Date
}

export interface Campaign {
  id: string
  name: string
  description: string
  businessTypes: string[]
  location: string
  searchQueries: string[]
  maxLeads: number
  status: 'draft' | 'running' | 'paused' | 'completed' | 'error'
  progress: {
    currentStep: string
    queriesProcessed: number
    totalQueries: number
    leadsFound: number
    pagesScraped: number
    totalPages: number
    emailsExtracted: number
    emailsValidated: number
  }
  settings: CampaignSettings
  createdAt: Date
  updatedAt: Date
  completedAt?: Date
}

export interface CampaignSettings {
  searchEngine: 'bing' | 'google'
  language: string
  countryCode: string
  maxPagesPerQuery: number
  maxLeadsPerQuery: number
  requestDelaySeconds: number
  timeoutSeconds: number
  headlessMode: boolean
  useRotatingUserAgents: boolean
  useResidentialProxies: boolean
  enableEmailValidation: boolean
  enableDnsChecking: boolean
  minEmailConfidence: number
  minBusinessScore: number
  maxConcurrentExtractions: number
  includeReport: boolean
  excludeKeywords: string[]
  outputDirectory: string
  csvFilename: string
}

export interface ProgressUpdate {
  campaignId: string
  step: string
  message: string
  progress: number
  timestamp: Date
  data?: any
}

export interface ExportOptions {
  format: 'csv' | 'json' | 'xlsx'
  includeNotes: boolean
  includeMetadata: boolean
  selectedFields: string[]
}

export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  limit: number
  totalPages: number
}

export interface CampaignMetrics {
  totalCampaigns: number
  activeCampaigns: number
  totalLeads: number
  qualifiedLeads: number
  successRate: number
  averageLeadsPerCampaign: number
  recentActivity: Array<{
    type: 'campaign_started' | 'campaign_completed' | 'leads_found'
    message: string
    timestamp: Date
  }>
}