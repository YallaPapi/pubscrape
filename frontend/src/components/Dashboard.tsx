import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { 
  Target, 
  Users, 
  TrendingUp, 
  Clock,
  Play,
  Pause,
  CheckCircle,
  AlertCircle
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Badge } from './ui/badge'
import { apiClient } from '../lib/api'
import { useAppStore } from '../store/useAppStore'
import { formatNumber } from '../lib/utils'

const Dashboard: React.FC = () => {
  const { setCampaignMetrics, campaignMetrics } = useAppStore()

  const { data: metrics, isLoading } = useQuery({
    queryKey: ['metrics'],
    queryFn: async () => {
      const response = await apiClient.getMetrics()
      if (response.success && response.data) {
        setCampaignMetrics(response.data)
        return response.data
      }
      throw new Error(response.error || 'Failed to fetch metrics')
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  const { data: campaigns } = useQuery({
    queryKey: ['campaigns-recent'],
    queryFn: async () => {
      const response = await apiClient.getCampaigns(1, 5)
      return response.data
    },
  })

  const statsCards = [
    {
      title: "Total Campaigns",
      value: metrics?.totalCampaigns || 0,
      description: `${metrics?.activeCampaigns || 0} active`,
      icon: Target,
      color: "blue"
    },
    {
      title: "Total Leads",
      value: metrics?.totalLeads || 0,
      description: `${metrics?.qualifiedLeads || 0} qualified`,
      icon: Users,
      color: "green"
    },
    {
      title: "Success Rate",
      value: `${((metrics?.successRate || 0) * 100).toFixed(1)}%`,
      description: "Average conversion",
      icon: TrendingUp,
      color: "purple"
    },
    {
      title: "Avg. Leads/Campaign",
      value: metrics?.averageLeadsPerCampaign || 0,
      description: "Per campaign",
      icon: Clock,
      color: "orange"
    }
  ]

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <Play className="h-4 w-4 text-green-500" />
      case 'paused':
        return <Pause className="h-4 w-4 text-yellow-500" />
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-blue-500" />
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />
      default:
        return <Clock className="h-4 w-4 text-gray-500" />
    }
  }

  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'running':
        return 'success'
      case 'paused':
        return 'warning'
      case 'completed':
        return 'info'
      case 'error':
        return 'destructive'
      default:
        return 'secondary'
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <div className="h-4 w-20 bg-muted animate-pulse rounded" />
                <div className="h-4 w-4 bg-muted animate-pulse rounded" />
              </CardHeader>
              <CardContent>
                <div className="h-8 w-16 bg-muted animate-pulse rounded mb-1" />
                <div className="h-3 w-24 bg-muted animate-pulse rounded" />
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
          <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
          <p className="text-muted-foreground">
            Overview of your lead generation campaigns and performance
          </p>
        </div>
        <Button size="lg">
          <Target className="mr-2 h-5 w-5" />
          New Campaign
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {statsCards.map((stat, index) => (
          <Card key={index}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {stat.title}
              </CardTitle>
              <stat.icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {typeof stat.value === 'number' ? formatNumber(stat.value) : stat.value}
              </div>
              <p className="text-xs text-muted-foreground">
                {stat.description}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Recent Campaigns */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Campaigns</CardTitle>
            <CardDescription>
              Your latest lead generation campaigns
            </CardDescription>
          </CardHeader>
          <CardContent>
            {campaigns && campaigns.length > 0 ? (
              <div className="space-y-4">
                {campaigns.map((campaign) => (
                  <div
                    key={campaign.id}
                    className="flex items-center justify-between p-3 border rounded-lg"
                  >
                    <div className="flex items-center space-x-3">
                      {getStatusIcon(campaign.status)}
                      <div>
                        <div className="font-medium">{campaign.name}</div>
                        <div className="text-sm text-muted-foreground">
                          {campaign.progress.leadsFound} leads found
                        </div>
                      </div>
                    </div>
                    <Badge variant={getStatusVariant(campaign.status)}>
                      {campaign.status}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-6 text-muted-foreground">
                No campaigns found. Create your first campaign to get started.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>
              Latest updates from your campaigns
            </CardDescription>
          </CardHeader>
          <CardContent>
            {metrics?.recentActivity && metrics.recentActivity.length > 0 ? (
              <div className="space-y-4">
                {metrics.recentActivity.map((activity, index) => (
                  <div key={index} className="flex items-start space-x-3">
                    <div className="flex-shrink-0">
                      {activity.type === 'campaign_started' && (
                        <Play className="h-4 w-4 text-green-500 mt-0.5" />
                      )}
                      {activity.type === 'campaign_completed' && (
                        <CheckCircle className="h-4 w-4 text-blue-500 mt-0.5" />
                      )}
                      {activity.type === 'leads_found' && (
                        <Users className="h-4 w-4 text-purple-500 mt-0.5" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium">{activity.message}</p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(activity.timestamp).toLocaleString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-6 text-muted-foreground">
                No recent activity
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default Dashboard