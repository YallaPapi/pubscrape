import React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Download, Settings, Play, Pause, Square } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import ProgressTracker from '../components/ProgressTracker'
import { apiClient } from '../lib/api'
import { useAppStore } from '../store/useAppStore'
import { formatDate } from '../lib/utils'

const CampaignDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { setActiveCampaign } = useAppStore()

  const { data: campaign, isLoading, error } = useQuery({
    queryKey: ['campaign', id],
    queryFn: async () => {
      if (!id) throw new Error('Campaign ID is required')
      const response = await apiClient.getCampaign(id)
      if (response.success && response.data) {
        setActiveCampaign(response.data)
        return response.data
      }
      throw new Error(response.error || 'Failed to fetch campaign')
    },
    enabled: !!id
  })

  const startCampaignMutation = useMutation({
    mutationFn: () => {
      if (!id) throw new Error('Campaign ID is required')
      return apiClient.startCampaign(id)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaign', id] })
    }
  })

  const pauseCampaignMutation = useMutation({
    mutationFn: () => {
      if (!id) throw new Error('Campaign ID is required')
      return apiClient.pauseCampaign(id)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaign', id] })
    }
  })

  const stopCampaignMutation = useMutation({
    mutationFn: () => {
      if (!id) throw new Error('Campaign ID is required')
      return apiClient.stopCampaign(id)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaign', id] })
    }
  })

  const exportMutation = useMutation({
    mutationFn: () => {
      if (!id) throw new Error('Campaign ID is required')
      return apiClient.exportLeads(id, {
        format: 'csv',
        includeNotes: true,
        includeMetadata: true,
        selectedFields: ['name', 'email', 'phone', 'company', 'website', 'address']
      })
    },
    onSuccess: async (response) => {
      if (response.success && response.data?.downloadUrl) {
        try {
          const blob = await apiClient.downloadExport(response.data.downloadUrl)
          const url = window.URL.createObjectURL(blob)
          const link = document.createElement('a')
          link.href = url
          link.setAttribute('download', `${campaign?.name || 'campaign'}_leads.csv`)
          document.body.appendChild(link)
          link.click()
          document.body.removeChild(link)
          window.URL.revokeObjectURL(url)
        } catch (error) {
          console.error('Failed to download export:', error)
        }
      }
    }
  })

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center space-x-4">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="space-y-2">
            <div className="h-8 w-64 bg-muted animate-pulse rounded" />
            <div className="h-4 w-48 bg-muted animate-pulse rounded" />
          </div>
        </div>
        
        <div className="grid gap-6 md:grid-cols-3">
          {[...Array(3)].map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <div className="h-4 w-3/4 bg-muted animate-pulse rounded" />
                <div className="h-3 w-1/2 bg-muted animate-pulse rounded" />
              </CardHeader>
              <CardContent>
                <div className="h-8 w-16 bg-muted animate-pulse rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (error || !campaign) {
    return (
      <div className="space-y-6">
        <div className="flex items-center space-x-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/campaigns')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Campaign Not Found</h1>
            <p className="text-muted-foreground">
              The requested campaign could not be found.
            </p>
          </div>
        </div>
        
        <Card>
          <CardContent className="p-12 text-center">
            <div className="space-y-4">
              <div className="text-4xl">😕</div>
              <div>
                <h3 className="text-lg font-medium">Campaign not found</h3>
                <p className="text-muted-foreground">
                  This campaign may have been deleted or you may not have access to it.
                </p>
              </div>
              <Button onClick={() => navigate('/campaigns')}>
                Back to Campaigns
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'running': return 'success'
      case 'paused': return 'warning'
      case 'completed': return 'info'
      case 'error': return 'destructive'
      default: return 'secondary'
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate('/campaigns')}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          
          <div>
            <div className="flex items-center space-x-3">
              <h1 className="text-3xl font-bold tracking-tight">{campaign.name}</h1>
              <Badge variant={getStatusVariant(campaign.status)}>
                {campaign.status}
              </Badge>
            </div>
            <p className="text-muted-foreground">
              {campaign.description}
            </p>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            onClick={() => exportMutation.mutate()}
            disabled={exportMutation.isPending || campaign.progress.leadsFound === 0}
          >
            <Download className="mr-2 h-4 w-4" />
            {exportMutation.isPending ? 'Exporting...' : 'Export Leads'}
          </Button>
          
          <Button variant="outline">
            <Settings className="mr-2 h-4 w-4" />
            Settings
          </Button>
        </div>
      </div>

      {/* Campaign Overview */}
      <div className="grid gap-6 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Campaign Info</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Location:</span>
              <span>{campaign.location}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Max Leads:</span>
              <span>{campaign.maxLeads.toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Created:</span>
              <span>{formatDate(new Date(campaign.createdAt))}</span>
            </div>
            {campaign.completedAt && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Completed:</span>
                <span>{formatDate(new Date(campaign.completedAt))}</span>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Business Types</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-1">
              {campaign.businessTypes.map((type, index) => (
                <Badge key={index} variant="outline">
                  {type}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Search Queries</CardTitle>
            <CardDescription>
              {campaign.searchQueries.length} queries defined
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {campaign.searchQueries.slice(0, 5).map((query, index) => (
                <div key={index} className="text-sm text-muted-foreground">
                  • {query}
                </div>
              ))}
              {campaign.searchQueries.length > 5 && (
                <div className="text-sm text-muted-foreground">
                  ... and {campaign.searchQueries.length - 5} more
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Progress Tracker */}
      <ProgressTracker
        campaign={campaign}
        onPause={() => pauseCampaignMutation.mutate()}
        onResume={() => startCampaignMutation.mutate()}
        onStop={() => stopCampaignMutation.mutate()}
      />

      {/* Campaign Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Campaign Settings</CardTitle>
          <CardDescription>
            Configuration details for this campaign
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <div className="font-medium">Search Engine</div>
              <div className="text-muted-foreground capitalize">{campaign.settings.searchEngine}</div>
            </div>
            <div>
              <div className="font-medium">Max Pages/Query</div>
              <div className="text-muted-foreground">{campaign.settings.maxPagesPerQuery}</div>
            </div>
            <div>
              <div className="font-medium">Request Delay</div>
              <div className="text-muted-foreground">{campaign.settings.requestDelaySeconds}s</div>
            </div>
            <div>
              <div className="font-medium">Email Validation</div>
              <div className="text-muted-foreground">
                {campaign.settings.enableEmailValidation ? 'Enabled' : 'Disabled'}
              </div>
            </div>
            <div>
              <div className="font-medium">Min Confidence</div>
              <div className="text-muted-foreground">{(campaign.settings.minEmailConfidence * 100).toFixed(0)}%</div>
            </div>
            <div>
              <div className="font-medium">Concurrent Extractions</div>
              <div className="text-muted-foreground">{campaign.settings.maxConcurrentExtractions}</div>
            </div>
            <div>
              <div className="font-medium">User Agent Rotation</div>
              <div className="text-muted-foreground">
                {campaign.settings.useRotatingUserAgents ? 'Enabled' : 'Disabled'}
              </div>
            </div>
            <div>
              <div className="font-medium">Headless Mode</div>
              <div className="text-muted-foreground">
                {campaign.settings.headlessMode ? 'Enabled' : 'Disabled'}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default CampaignDetailPage