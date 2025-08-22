import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import { Campaign, Lead, CampaignMetrics } from '../types'

interface AppState {
  // UI State
  theme: 'light' | 'dark'
  sidebarOpen: boolean
  
  // Campaign State
  campaigns: Campaign[]
  activeCampaign: Campaign | null
  campaignMetrics: CampaignMetrics | null
  
  // Lead State
  leads: Lead[]
  selectedLeads: string[]
  leadFilters: {
    status?: string
    source?: string
    confidence?: number
    search?: string
  }
  
  // Real-time updates
  isConnected: boolean
  lastUpdate: Date | null
  
  // Actions
  setTheme: (theme: 'light' | 'dark') => void
  toggleSidebar: () => void
  
  setCampaigns: (campaigns: Campaign[]) => void
  setActiveCampaign: (campaign: Campaign | null) => void
  updateCampaign: (id: string, updates: Partial<Campaign>) => void
  setCampaignMetrics: (metrics: CampaignMetrics) => void
  
  setLeads: (leads: Lead[]) => void
  addLead: (lead: Lead) => void
  updateLead: (id: string, updates: Partial<Lead>) => void
  deleteLead: (id: string) => void
  setSelectedLeads: (leadIds: string[]) => void
  toggleLeadSelection: (leadId: string) => void
  clearLeadSelection: () => void
  setLeadFilters: (filters: Partial<AppState['leadFilters']>) => void
  
  setConnectionStatus: (connected: boolean) => void
  updateLastUpdate: () => void
}

export const useAppStore = create<AppState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        theme: 'light',
        sidebarOpen: true,
        campaigns: [],
        activeCampaign: null,
        campaignMetrics: null,
        leads: [],
        selectedLeads: [],
        leadFilters: {},
        isConnected: false,
        lastUpdate: null,

        // UI Actions
        setTheme: (theme) => 
          set({ theme }, false, 'setTheme'),

        toggleSidebar: () => 
          set((state) => ({ sidebarOpen: !state.sidebarOpen }), false, 'toggleSidebar'),

        // Campaign Actions
        setCampaigns: (campaigns) => 
          set({ campaigns }, false, 'setCampaigns'),

        setActiveCampaign: (activeCampaign) => 
          set({ activeCampaign }, false, 'setActiveCampaign'),

        updateCampaign: (id, updates) =>
          set((state) => ({
            campaigns: state.campaigns.map(campaign =>
              campaign.id === id ? { ...campaign, ...updates } : campaign
            ),
            activeCampaign: state.activeCampaign?.id === id 
              ? { ...state.activeCampaign, ...updates }
              : state.activeCampaign
          }), false, 'updateCampaign'),

        setCampaignMetrics: (campaignMetrics) => 
          set({ campaignMetrics }, false, 'setCampaignMetrics'),

        // Lead Actions
        setLeads: (leads) => 
          set({ leads }, false, 'setLeads'),

        addLead: (lead) =>
          set((state) => ({
            leads: [...state.leads, lead]
          }), false, 'addLead'),

        updateLead: (id, updates) =>
          set((state) => ({
            leads: state.leads.map(lead =>
              lead.id === id ? { ...lead, ...updates } : lead
            )
          }), false, 'updateLead'),

        deleteLead: (id) =>
          set((state) => ({
            leads: state.leads.filter(lead => lead.id !== id),
            selectedLeads: state.selectedLeads.filter(leadId => leadId !== id)
          }), false, 'deleteLead'),

        setSelectedLeads: (selectedLeads) => 
          set({ selectedLeads }, false, 'setSelectedLeads'),

        toggleLeadSelection: (leadId) =>
          set((state) => ({
            selectedLeads: state.selectedLeads.includes(leadId)
              ? state.selectedLeads.filter(id => id !== leadId)
              : [...state.selectedLeads, leadId]
          }), false, 'toggleLeadSelection'),

        clearLeadSelection: () => 
          set({ selectedLeads: [] }, false, 'clearLeadSelection'),

        setLeadFilters: (filters) =>
          set((state) => ({
            leadFilters: { ...state.leadFilters, ...filters }
          }), false, 'setLeadFilters'),

        // Connection Actions
        setConnectionStatus: (isConnected) => 
          set({ isConnected }, false, 'setConnectionStatus'),

        updateLastUpdate: () => 
          set({ lastUpdate: new Date() }, false, 'updateLastUpdate'),
      }),
      {
        name: 'vrsen-app-store',
        partialize: (state) => ({
          theme: state.theme,
          sidebarOpen: state.sidebarOpen,
          leadFilters: state.leadFilters,
        }),
      }
    ),
    {
      name: 'vrsen-app-store',
    }
  )
)