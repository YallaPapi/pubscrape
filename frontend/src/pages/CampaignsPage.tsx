import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { 
  Plus, 
  Search, 
  Filter, 
  MoreHorizontal,
  Play,
  Pause,
  Square,
  Eye,
  Edit,
  Trash2
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Badge } from '../components/ui/badge'
import { apiClient } from '../lib/api'
import { useAppStore } from '../store/useAppStore'
import { Campaign } from '../types'
import { formatDate, formatNumber } from '../lib/utils'

const CampaignsPage: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const { setCampaigns } = useAppStore()
  const queryClient = useQueryClient()

  const { data: campaignsResponse, isLoading } = useQuery({
    queryKey: ['campaigns', searchQuery, statusFilter],
    queryFn: async () => {
      const response = await apiClient.getCampaigns(1, 50)
      if (response.data) {
        setCampaigns(response.data)
      }
      return response
    }
  })

  const startCampaignMutation = useMutation({
    mutationFn: (campaignId: string) => apiClient.startCampaign(campaignId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] })
    }
  })

  const pauseCampaignMutation = useMutation({
    mutationFn: (campaignId: string) => apiClient.pauseCampaign(campaignId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] })
    }
  })

  const stopCampaignMutation = useMutation({
    mutationFn: (campaignId: string) => apiClient.stopCampaign(campaignId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] })
    }
  })

  const deleteCampaignMutation = useMutation({
    mutationFn: (campaignId: string) => apiClient.deleteCampaign(campaignId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] })
    }
  })

  const filteredCampaigns = campaignsResponse?.data?.filter((campaign: Campaign) => {
    const matchesSearch = campaign.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         campaign.description.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus = statusFilter === 'all' || campaign.status === statusFilter
    return matchesSearch && matchesStatus
  }) || []

  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'running': return 'success'
      case 'paused': return 'warning'
      case 'completed': return 'info'
      case 'error': return 'destructive'
      default: return 'secondary'
    }
  }

  const getProgressPercentage = (campaign: Campaign) => {
    if (campaign.status === 'completed') return 100
    if (campaign.status === 'draft') return 0
    
    const { progress } = campaign
    const totalSteps = 6
    const currentStepIndex = (() => {
      switch (progress.currentStep) {
        case 'building_queries': return 1
        case 'searching': return 2
        case 'parsing': return 3
        case 'classifying': return 4
        case 'extracting': return 5
        case 'validating': return 6
        default: return 0
      }
    })()
    
    return Math.round((currentStepIndex / totalSteps) * 100)
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">Campaigns</h2>
            <p className="text-muted-foreground">Manage your lead generation campaigns</p>
          </div>
        </div>
        
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <div className="h-4 w-3/4 bg-muted animate-pulse rounded" />
                <div className="h-3 w-1/2 bg-muted animate-pulse rounded" />
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="h-3 w-full bg-muted animate-pulse rounded" />
                  <div className="h-3 w-2/3 bg-muted animate-pulse rounded" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Campaigns</h2>
          <p className="text-muted-foreground">
            Manage your lead generation campaigns
          </p>
        </div>
        <Link to="/campaigns/new">
          <Button size="lg">
            <Plus className="mr-2 h-5 w-5" />
            New Campaign
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center space-x-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search campaigns..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="h-10 px-3 py-2 text-sm border border-input bg-background rounded-md"
              >
                <option value="all">All Status</option>
                <option value="draft">Draft</option>
                <option value="running">Running</option>
                <option value="paused">Paused</option>
                <option value="completed">Completed</option>
                <option value="error">Error</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Campaigns Grid */}
      {filteredCampaigns.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <div className="space-y-4">
              <div className="text-4xl">📊</div>
              <div>
                <h3 className="text-lg font-medium">No campaigns found</h3>
                <p className="text-muted-foreground">
                  {searchQuery || statusFilter !== 'all' 
                    ? 'Try adjusting your search or filters'
                    : 'Create your first campaign to get started'
                  }
                </p>
              </div>
              {!searchQuery && statusFilter === 'all' && (
                <Link to="/campaigns/new">
                  <Button>
                    <Plus className="mr-2 h-4 w-4" />
                    Create Campaign
                  </Button>
                </Link>
              )}
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {filteredCampaigns.map((campaign: Campaign) => (
            <Card key={campaign.id} className="group hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <CardTitle className="text-lg">{campaign.name}</CardTitle>
                    <CardDescription className="line-clamp-2">
                      {campaign.description}
                    </CardDescription>
                  </div>
                  
                  <div className="flex items-center space-x-1">
                    <Badge variant={getStatusVariant(campaign.status)}>
                      {campaign.status}
                    </Badge>
                    
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              </CardHeader>
              
              <CardContent className="space-y-4">
                {/* Progress Bar */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span>Progress</span>
                    <span>{getProgressPercentage(campaign)}%</span>
                  </div>
                  <div className="w-full bg-secondary rounded-full h-2">
                    <div
                      className="bg-primary h-2 rounded-full transition-all duration-300"
                      style={{ width: `${getProgressPercentage(campaign)}%` }}
                    />
                  </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <div className="font-medium">{formatNumber(campaign.progress.leadsFound)}</div>
                    <div className="text-muted-foreground">Leads Found</div>
                  </div>
                  <div>
                    <div className="font-medium">{campaign.searchQueries.length}</div>
                    <div className="text-muted-foreground">Search Queries</div>
                  </div>
                </div>

                {/* Metadata */}
                <div className="text-xs text-muted-foreground space-y-1">
                  <div>Location: {campaign.location}</div>
                  <div>Created: {formatDate(new Date(campaign.createdAt))}</div>
                  {campaign.completedAt && (
                    <div>Completed: {formatDate(new Date(campaign.completedAt))}</div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex items-center justify-between pt-2 border-t">
                  <div className="flex items-center space-x-1">
                    {campaign.status === 'draft' && (
                      <Button
                        size="sm"
                        onClick={() => startCampaignMutation.mutate(campaign.id)}
                        disabled={startCampaignMutation.isPending}
                      >
                        <Play className="h-3 w-3 mr-1" />
                        Start
                      </Button>
                    )}
                    
                    {campaign.status === 'running' && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => pauseCampaignMutation.mutate(campaign.id)}
                        disabled={pauseCampaignMutation.isPending}
                      >
                        <Pause className="h-3 w-3 mr-1" />
                        Pause
                      </Button>
                    )}
                    
                    {campaign.status === 'paused' && (
                      <>
                        <Button
                          size="sm"
                          onClick={() => startCampaignMutation.mutate(campaign.id)}
                          disabled={startCampaignMutation.isPending}
                        >
                          <Play className="h-3 w-3 mr-1" />
                          Resume
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => stopCampaignMutation.mutate(campaign.id)}
                          disabled={stopCampaignMutation.isPending}
                        >
                          <Square className="h-3 w-3 mr-1" />
                          Stop
                        </Button>
                      </>
                    )}
                  </div>
                  
                  <div className="flex items-center space-x-1">
                    <Link to={`/campaigns/${campaign.id}`}>
                      <Button size="sm" variant="ghost">
                        <Eye className="h-3 w-3" />
                      </Button>
                    </Link>
                    
                    {campaign.status === 'draft' && (
                      <>
                        <Button size="sm" variant="ghost">
                          <Edit className="h-3 w-3" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => deleteCampaignMutation.mutate(campaign.id)}
                          disabled={deleteCampaignMutation.isPending}
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

export default CampaignsPage