import React from 'react'
import { useForm, useFieldArray } from 'react-hook-form'
import { Plus, Minus, Save, Play } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Badge } from './ui/badge'
import { Campaign, CampaignSettings } from '../types'

interface CampaignFormProps {
  initialData?: Partial<Campaign>
  onSubmit: (data: Partial<Campaign>) => void
  onSave?: (data: Partial<Campaign>) => void
  isLoading?: boolean
}

interface FormData {
  name: string
  description: string
  businessTypes: string[]
  location: string
  searchQueries: string[]
  maxLeads: number
  settings: CampaignSettings
}

const defaultSettings: CampaignSettings = {
  searchEngine: 'bing',
  language: 'en',
  countryCode: 'US',
  maxPagesPerQuery: 3,
  maxLeadsPerQuery: 25,
  requestDelaySeconds: 2.5,
  timeoutSeconds: 20,
  headlessMode: true,
  useRotatingUserAgents: true,
  useResidentialProxies: false,
  enableEmailValidation: true,
  enableDnsChecking: false,
  minEmailConfidence: 0.6,
  minBusinessScore: 0.5,
  maxConcurrentExtractions: 3,
  includeReport: true,
  excludeKeywords: ['yelp', 'reviews', 'directory', 'wikipedia'],
  outputDirectory: 'campaign_output',
  csvFilename: ''
}

const CampaignForm: React.FC<CampaignFormProps> = ({
  initialData,
  onSubmit,
  onSave,
  isLoading = false
}) => {
  const {
    register,
    control,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isDirty }
  } = useForm<FormData>({
    defaultValues: {
      name: initialData?.name || '',
      description: initialData?.description || '',
      businessTypes: initialData?.businessTypes || [''],
      location: initialData?.location || '',
      searchQueries: initialData?.searchQueries || [''],
      maxLeads: initialData?.maxLeads || 100,
      settings: { ...defaultSettings, ...initialData?.settings }
    }
  })

  const {
    fields: businessTypeFields,
    append: appendBusinessType,
    remove: removeBusinessType
  } = useFieldArray({
    control,
    name: 'businessTypes' as const
  })

  const {
    fields: queryFields,
    append: appendQuery,
    remove: removeQuery
  } = useFieldArray({
    control,
    name: 'searchQueries' as const
  })

  const {
    fields: excludeKeywordFields,
    append: appendExcludeKeyword,
    remove: removeExcludeKeyword
  } = useFieldArray({
    control,
    name: 'settings.excludeKeywords' as const
  })

  const watchedValues = watch()

  const handleFormSubmit = (data: FormData) => {
    // Clean up empty values
    const cleanData = {
      ...data,
      businessTypes: data.businessTypes.filter(type => type.trim() !== ''),
      searchQueries: data.searchQueries.filter(query => query.trim() !== ''),
      settings: {
        ...data.settings,
        excludeKeywords: data.settings.excludeKeywords?.filter(keyword => keyword.trim() !== '') || []
      }
    }
    onSubmit(cleanData)
  }

  const handleSave = () => {
    if (onSave && isDirty) {
      const data = watchedValues
      const cleanData = {
        ...data,
        businessTypes: data.businessTypes.filter(type => type.trim() !== ''),
        searchQueries: data.searchQueries.filter(query => query.trim() !== ''),
        settings: {
          ...data.settings,
          excludeKeywords: data.settings.excludeKeywords?.filter(keyword => keyword.trim() !== '') || []
        }
      }
      onSave(cleanData)
    }
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-6">
      {/* Basic Information */}
      <Card>
        <CardHeader>
          <CardTitle>Campaign Details</CardTitle>
          <CardDescription>
            Basic information about your lead generation campaign
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">
              Campaign Name *
            </label>
            <Input
              {...register('name', { required: 'Campaign name is required' })}
              placeholder="e.g., Atlanta Optometrists Campaign"
            />
            {errors.name && (
              <p className="text-sm text-red-500 mt-1">{errors.name.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              Description
            </label>
            <Input
              {...register('description')}
              placeholder="Brief description of the campaign goals"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              Target Location *
            </label>
            <Input
              {...register('location', { required: 'Location is required' })}
              placeholder="e.g., Atlanta, GA"
            />
            {errors.location && (
              <p className="text-sm text-red-500 mt-1">{errors.location.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              Maximum Leads
            </label>
            <Input
              type="number"
              {...register('maxLeads', { 
                required: 'Maximum leads is required',
                min: { value: 1, message: 'Must be at least 1' },
                max: { value: 10000, message: 'Must be less than 10,000' }
              })}
              placeholder="100"
            />
            {errors.maxLeads && (
              <p className="text-sm text-red-500 mt-1">{errors.maxLeads.message}</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Business Types */}
      <Card>
        <CardHeader>
          <CardTitle>Business Types</CardTitle>
          <CardDescription>
            Specify the types of businesses you want to target
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {businessTypeFields.map((field, index) => (
              <div key={field.id} className="flex items-center space-x-2">
                <Input
                  {...register(`businessTypes.${index}` as const)}
                  placeholder="e.g., optometry, eye care, vision"
                />
                {businessTypeFields.length > 1 && (
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={() => removeBusinessType(index)}
                  >
                    <Minus className="h-4 w-4" />
                  </Button>
                )}
              </div>
            ))}
            <Button
              type="button"
              variant="outline"
              onClick={() => appendBusinessType('')}
              className="w-full"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Business Type
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Search Queries */}
      <Card>
        <CardHeader>
          <CardTitle>Search Queries</CardTitle>
          <CardDescription>
            Define the search terms that will be used to find leads
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {queryFields.map((field, index) => (
              <div key={field.id} className="flex items-center space-x-2">
                <Input
                  {...register(`searchQueries.${index}` as const)}
                  placeholder="e.g., optometrist Atlanta"
                />
                {queryFields.length > 1 && (
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={() => removeQuery(index)}
                  >
                    <Minus className="h-4 w-4" />
                  </Button>
                )}
              </div>
            ))}
            <Button
              type="button"
              variant="outline"
              onClick={() => appendQuery('')}
              className="w-full"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Search Query
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Advanced Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Advanced Settings</CardTitle>
          <CardDescription>
            Fine-tune the campaign behavior and performance
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">
                Search Engine
              </label>
              <select
                {...register('settings.searchEngine')}
                className="w-full h-10 px-3 py-2 text-sm border border-input bg-background rounded-md"
              >
                <option value="bing">Bing</option>
                <option value="google">Google</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Max Pages per Query
              </label>
              <Input
                type="number"
                {...register('settings.maxPagesPerQuery', {
                  min: { value: 1, message: 'Must be at least 1' },
                  max: { value: 10, message: 'Must be less than 10' }
                })}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Max Leads per Query
              </label>
              <Input
                type="number"
                {...register('settings.maxLeadsPerQuery', {
                  min: { value: 1, message: 'Must be at least 1' },
                  max: { value: 100, message: 'Must be less than 100' }
                })}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Request Delay (seconds)
              </label>
              <Input
                type="number"
                step="0.5"
                {...register('settings.requestDelaySeconds', {
                  min: { value: 0.5, message: 'Must be at least 0.5' },
                  max: { value: 10, message: 'Must be less than 10' }
                })}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Min Email Confidence
              </label>
              <Input
                type="number"
                step="0.1"
                {...register('settings.minEmailConfidence', {
                  min: { value: 0, message: 'Must be between 0 and 1' },
                  max: { value: 1, message: 'Must be between 0 and 1' }
                })}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Max Concurrent Extractions
              </label>
              <Input
                type="number"
                {...register('settings.maxConcurrentExtractions', {
                  min: { value: 1, message: 'Must be at least 1' },
                  max: { value: 10, message: 'Must be less than 10' }
                })}
              />
            </div>
          </div>

          {/* Checkboxes */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                {...register('settings.enableEmailValidation')}
                className="rounded border-gray-300"
              />
              <span className="text-sm">Email Validation</span>
            </label>

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                {...register('settings.useRotatingUserAgents')}
                className="rounded border-gray-300"
              />
              <span className="text-sm">Rotating User Agents</span>
            </label>

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                {...register('settings.headlessMode')}
                className="rounded border-gray-300"
              />
              <span className="text-sm">Headless Mode</span>
            </label>

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                {...register('settings.includeReport')}
                className="rounded border-gray-300"
              />
              <span className="text-sm">Include Report</span>
            </label>

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                {...register('settings.enableDnsChecking')}
                className="rounded border-gray-300"
              />
              <span className="text-sm">DNS Checking</span>
            </label>

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                {...register('settings.useResidentialProxies')}
                className="rounded border-gray-300"
              />
              <span className="text-sm">Residential Proxies</span>
            </label>
          </div>
        </CardContent>
      </Card>

      {/* Exclude Keywords */}
      <Card>
        <CardHeader>
          <CardTitle>Exclude Keywords</CardTitle>
          <CardDescription>
            Keywords to filter out from search results
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {excludeKeywordFields.map((field, index) => (
              <div key={field.id} className="flex items-center space-x-2">
                <Input
                  {...register(`settings.excludeKeywords.${index}` as const)}
                  placeholder="e.g., yelp, reviews"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={() => removeExcludeKeyword(index)}
                >
                  <Minus className="h-4 w-4" />
                </Button>
              </div>
            ))}
            <Button
              type="button"
              variant="outline"
              onClick={() => appendExcludeKeyword('')}
              className="w-full"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Exclude Keyword
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Form Actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          {isDirty && (
            <Badge variant="warning">Unsaved changes</Badge>
          )}
        </div>
        
        <div className="flex items-center space-x-2">
          {onSave && (
            <Button
              type="button"
              variant="outline"
              onClick={handleSave}
              disabled={!isDirty || isLoading}
            >
              <Save className="h-4 w-4 mr-2" />
              Save Draft
            </Button>
          )}
          
          <Button
            type="submit"
            disabled={isLoading}
          >
            <Play className="h-4 w-4 mr-2" />
            {isLoading ? 'Starting...' : 'Start Campaign'}
          </Button>
        </div>
      </div>
    </form>
  )
}

export default CampaignForm