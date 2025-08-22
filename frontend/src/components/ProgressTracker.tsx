import React, { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { 
  Clock, 
  Search, 
  Globe, 
  Mail, 
  CheckCircle, 
  AlertCircle,
  Pause,
  Play,
  BarChart3
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Badge } from './ui/badge'
import { Campaign } from '../types'
import { apiClient } from '../lib/api'
import { useAppStore } from '../store/useAppStore'
import { formatNumber } from '../lib/utils'

interface ProgressTrackerProps {
  campaign: Campaign
  onPause?: () => void
  onResume?: () => void
  onStop?: () => void
}

const ProgressTracker: React.FC<ProgressTrackerProps> = ({
  campaign,
  onPause,
  onResume,
  onStop
}) => {
  const { updateCampaign } = useAppStore()

  // Poll for campaign updates
  const { data: currentCampaign } = useQuery({
    queryKey: ['campaign', campaign.id],
    queryFn: async () => {
      const response = await apiClient.getCampaign(campaign.id)
      if (response.success && response.data) {
        updateCampaign(campaign.id, response.data)
        return response.data
      }
      return campaign
    },
    refetchInterval: campaign.status === 'running' ? 2000 : 10000,
    initialData: campaign
  })

  const progress = currentCampaign.progress
  const isActive = currentCampaign.status === 'running'
  const isPaused = currentCampaign.status === 'paused'
  const isCompleted = currentCampaign.status === 'completed'
  const hasError = currentCampaign.status === 'error'

  // Calculate overall progress percentage
  const totalSteps = 6 // Query building, searching, parsing, classifying, extracting, validating
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

  const stepProgress = (() => {
    switch (progress.currentStep) {
      case 'searching':
        return progress.totalQueries > 0 
          ? (progress.queriesProcessed / progress.totalQueries) * 100 
          : 0
      case 'parsing':
      case 'extracting':
        return progress.totalPages > 0 
          ? (progress.pagesScraped / progress.totalPages) * 100 
          : 0
      default:
        return 100
    }
  })()

  const overallProgress = isCompleted 
    ? 100 
    : ((currentStepIndex - 1) / totalSteps) * 100 + (stepProgress / totalSteps)

  const getStatusColor = () => {
    if (hasError) return 'text-red-500'
    if (isCompleted) return 'text-green-500'
    if (isPaused) return 'text-yellow-500'
    if (isActive) return 'text-blue-500'
    return 'text-gray-500'
  }

  const getStatusIcon = () => {
    if (hasError) return <AlertCircle className="h-5 w-5 text-red-500" />
    if (isCompleted) return <CheckCircle className="h-5 w-5 text-green-500" />
    if (isPaused) return <Pause className="h-5 w-5 text-yellow-500" />
    if (isActive) return <Play className="h-5 w-5 text-blue-500" />
    return <Clock className="h-5 w-5 text-gray-500" />
  }

  const steps = [
    {
      name: 'Building Queries',
      key: 'building_queries',
      icon: Search,
      description: 'Generating search queries from campaign settings'
    },
    {
      name: 'Searching',
      key: 'searching',
      icon: Globe,
      description: `Processing ${progress.queriesProcessed}/${progress.totalQueries} queries`,
      progress: progress.totalQueries > 0 ? (progress.queriesProcessed / progress.totalQueries) * 100 : 0
    },
    {
      name: 'Parsing Results',
      key: 'parsing',
      icon: BarChart3,
      description: `Extracted ${progress.pagesScraped} pages from search results`
    },
    {
      name: 'Classifying Domains',
      key: 'classifying',
      icon: CheckCircle,
      description: 'Prioritizing business domains by relevance'
    },
    {
      name: 'Extracting Emails',
      key: 'extracting',
      icon: Mail,
      description: `Found ${progress.emailsExtracted} email addresses`,
      progress: progress.totalPages > 0 ? (progress.pagesScraped / progress.totalPages) * 100 : 0
    },
    {
      name: 'Validating Results',
      key: 'validating',
      icon: CheckCircle,
      description: `Validated ${progress.emailsValidated}/${progress.emailsExtracted} emails`
    }
  ]

  return (
    <div className="space-y-6">
      {/* Campaign Status Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              {getStatusIcon()}
              <div>
                <CardTitle className={getStatusColor()}>
                  {currentCampaign.name}
                </CardTitle>
                <CardDescription>
                  Status: {currentCampaign.status.charAt(0).toUpperCase() + currentCampaign.status.slice(1)}
                </CardDescription>
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              {isActive && onPause && (
                <Button variant="outline" onClick={onPause}>
                  <Pause className="h-4 w-4 mr-2" />
                  Pause
                </Button>
              )}
              
              {isPaused && onResume && (
                <Button onClick={onResume}>
                  <Play className="h-4 w-4 mr-2" />
                  Resume
                </Button>
              )}
              
              {(isActive || isPaused) && onStop && (
                <Button variant="destructive" onClick={onStop}>
                  Stop Campaign
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        
        <CardContent>
          {/* Overall Progress Bar */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span>Overall Progress</span>
              <span>{Math.round(overallProgress)}%</span>
            </div>
            <div className="w-full bg-secondary rounded-full h-2">
              <div
                className="bg-primary h-2 rounded-full transition-all duration-300"
                style={{ width: `${Math.min(overallProgress, 100)}%` }}
              />
            </div>
          </div>

          {/* Current Step */}
          {!isCompleted && !hasError && (
            <div className="mt-4 p-3 bg-muted rounded-lg">
              <div className="flex items-center space-x-2">
                <div className="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full" />
                <span className="font-medium">Current Step: {progress.currentStep.replace('_', ' ')}</span>
              </div>
              {stepProgress > 0 && (
                <div className="mt-2">
                  <div className="w-full bg-background rounded-full h-1">
                    <div
                      className="bg-primary h-1 rounded-full transition-all duration-300"
                      style={{ width: `${stepProgress}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Detailed Steps */}
      <Card>
        <CardHeader>
          <CardTitle>Progress Details</CardTitle>
          <CardDescription>
            Step-by-step breakdown of campaign execution
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {steps.map((step, index) => {
              const isCurrentStep = progress.currentStep === step.key
              const isCompleted = currentStepIndex > index + 1
              const isActive = isCurrentStep && currentCampaign.status === 'running'
              
              return (
                <div
                  key={step.key}
                  className={`flex items-start space-x-3 p-3 rounded-lg transition-colors ${
                    isCurrentStep 
                      ? 'bg-primary/5 border border-primary/20' 
                      : isCompleted 
                        ? 'bg-green-50 dark:bg-green-900/10' 
                        : 'bg-muted/50'
                  }`}
                >
                  <div className="flex-shrink-0 mt-0.5">
                    {isActive ? (
                      <div className="animate-spin h-5 w-5 border-2 border-primary border-t-transparent rounded-full" />
                    ) : isCompleted ? (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    ) : (
                      <step.icon 
                        className={`h-5 w-5 ${
                          isCurrentStep ? 'text-primary' : 'text-muted-foreground'
                        }`} 
                      />
                    )}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <h4 className={`font-medium ${
                        isCurrentStep ? 'text-primary' : isCompleted ? 'text-green-600' : ''
                      }`}>
                        {step.name}
                      </h4>
                      
                      {isCurrentStep && (
                        <Badge variant="outline">
                          In Progress
                        </Badge>
                      )}
                      
                      {isCompleted && (
                        <Badge variant="success">
                          Complete
                        </Badge>
                      )}
                    </div>
                    
                    <p className="text-sm text-muted-foreground mt-1">
                      {step.description}
                    </p>
                    
                    {/* Step-specific progress */}
                    {step.progress !== undefined && step.progress > 0 && (
                      <div className="mt-2">
                        <div className="w-full bg-background rounded-full h-1">
                          <div
                            className="bg-primary h-1 rounded-full transition-all duration-300"
                            style={{ width: `${step.progress}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Stats Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-primary">
                {formatNumber(progress.leadsFound)}
              </div>
              <div className="text-sm text-muted-foreground">Leads Found</div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-500">
                {formatNumber(progress.queriesProcessed)}
              </div>
              <div className="text-sm text-muted-foreground">Queries Processed</div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-500">
                {formatNumber(progress.emailsExtracted)}
              </div>
              <div className="text-sm text-muted-foreground">Emails Extracted</div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-500">
                {formatNumber(progress.emailsValidated)}
              </div>
              <div className="text-sm text-muted-foreground">Emails Validated</div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default ProgressTracker