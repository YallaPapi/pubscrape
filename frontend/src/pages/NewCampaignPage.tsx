import React from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { Button } from '../components/ui/button'
import CampaignForm from '../components/CampaignForm'
import { apiClient } from '../lib/api'
import { Campaign } from '../types'

const NewCampaignPage: React.FC = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const createCampaignMutation = useMutation({
    mutationFn: (campaignData: Partial<Campaign>) => 
      apiClient.createCampaign(campaignData),
    onSuccess: (response) => {
      if (response.success && response.data) {
        queryClient.invalidateQueries({ queryKey: ['campaigns'] })
        navigate(`/campaigns/${response.data.id}`)
      }
    },
    onError: (error) => {
      console.error('Failed to create campaign:', error)
      // TODO: Show error toast
    }
  })

  const saveDraftMutation = useMutation({
    mutationFn: (campaignData: Partial<Campaign>) => 
      apiClient.createCampaign({ ...campaignData, status: 'draft' }),
    onSuccess: (response) => {
      if (response.success && response.data) {
        queryClient.invalidateQueries({ queryKey: ['campaigns'] })
        // TODO: Show success toast
      }
    },
    onError: (error) => {
      console.error('Failed to save draft:', error)
      // TODO: Show error toast
    }
  })

  const handleSubmit = (data: Partial<Campaign>) => {
    createCampaignMutation.mutate({
      ...data,
      status: 'draft' // Will be started immediately after creation
    })
  }

  const handleSaveDraft = (data: Partial<Campaign>) => {
    saveDraftMutation.mutate({
      ...data,
      status: 'draft'
    })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center space-x-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => navigate('/campaigns')}
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        
        <div>
          <h1 className="text-3xl font-bold tracking-tight">New Campaign</h1>
          <p className="text-muted-foreground">
            Create a new lead generation campaign
          </p>
        </div>
      </div>

      {/* Campaign Form */}
      <CampaignForm
        onSubmit={handleSubmit}
        onSave={handleSaveDraft}
        isLoading={createCampaignMutation.isPending || saveDraftMutation.isPending}
      />
    </div>
  )
}

export default NewCampaignPage