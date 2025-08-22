import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, Filter, Download, Eye, Edit, Trash2, Mail, Phone, Globe } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Badge } from '../components/ui/badge'
import { apiClient } from '../lib/api'
import { Lead } from '../types'
import { formatDate } from '../lib/utils'

const LeadsPage: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [selectedLeads, setSelectedLeads] = useState<string[]>([])

  const { data: leadsResponse, isLoading } = useQuery({
    queryKey: ['leads', searchQuery, statusFilter],
    queryFn: async () => {
      const filters: Record<string, any> = {}
      if (statusFilter !== 'all') filters.status = statusFilter
      if (searchQuery) filters.search = searchQuery
      
      return await apiClient.getLeads(undefined, 1, 50, filters)
    }
  })

  const leads = leadsResponse?.data || []

  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'contacted': return 'success'
      case 'qualified': return 'info'
      case 'disqualified': return 'destructive'
      default: return 'secondary'
    }
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600'
    if (confidence >= 0.6) return 'text-yellow-600'
    return 'text-red-600'
  }

  const toggleLeadSelection = (leadId: string) => {
    setSelectedLeads(prev => 
      prev.includes(leadId) 
        ? prev.filter(id => id !== leadId)
        : [...prev, leadId]
    )
  }

  const selectAllLeads = () => {
    setSelectedLeads(selectedLeads.length === leads.length ? [] : leads.map(lead => lead.id))
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">Leads</h2>
            <p className="text-muted-foreground">Manage your generated leads</p>
          </div>
        </div>
        
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <div className="flex items-center space-x-4">
                  <div className="h-4 w-4 bg-muted animate-pulse rounded" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-1/4 bg-muted animate-pulse rounded" />
                    <div className="h-3 w-1/3 bg-muted animate-pulse rounded" />
                  </div>
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
          <h2 className="text-3xl font-bold tracking-tight">Leads</h2>
          <p className="text-muted-foreground">
            Manage your generated leads ({leads.length} total)
          </p>
        </div>
        
        {selectedLeads.length > 0 && (
          <div className="flex items-center space-x-2">
            <Badge variant="outline">
              {selectedLeads.length} selected
            </Badge>
            <Button variant="outline" size="sm">
              <Download className="mr-2 h-4 w-4" />
              Export Selected
            </Button>
            <Button variant="outline" size="sm">
              Bulk Actions
            </Button>
          </div>
        )}
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center space-x-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search leads by name, email, or company..."
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
                <option value="pending">Pending</option>
                <option value="contacted">Contacted</option>
                <option value="qualified">Qualified</option>
                <option value="disqualified">Disqualified</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Leads List */}
      {leads.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <div className="space-y-4">
              <div className="text-4xl">👥</div>
              <div>
                <h3 className="text-lg font-medium">No leads found</h3>
                <p className="text-muted-foreground">
                  {searchQuery || statusFilter !== 'all' 
                    ? 'Try adjusting your search or filters'
                    : 'Start a campaign to generate leads'
                  }
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Lead List</CardTitle>
                <CardDescription>
                  {leads.length} leads from your campaigns
                </CardDescription>
              </div>
              
              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={selectAllLeads}
                >
                  {selectedLeads.length === leads.length ? 'Deselect All' : 'Select All'}
                </Button>
                <Button size="sm">
                  <Download className="mr-2 h-4 w-4" />
                  Export All
                </Button>
              </div>
            </div>
          </CardHeader>
          
          <CardContent className="p-0">
            <div className="space-y-0">
              {leads.map((lead: Lead) => (
                <div
                  key={lead.id}
                  className={`flex items-center space-x-4 p-4 border-b hover:bg-muted/50 transition-colors ${
                    selectedLeads.includes(lead.id) ? 'bg-muted/25' : ''
                  }`}
                >
                  {/* Checkbox */}
                  <input
                    type="checkbox"
                    checked={selectedLeads.includes(lead.id)}
                    onChange={() => toggleLeadSelection(lead.id)}
                    className="rounded border-gray-300"
                  />
                  
                  {/* Lead Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-3">
                      <div>
                        <div className="font-medium">{lead.name}</div>
                        <div className="text-sm text-muted-foreground flex items-center space-x-4">
                          <span className="flex items-center">
                            <Mail className="h-3 w-3 mr-1" />
                            {lead.email}
                          </span>
                          {lead.phone && (
                            <span className="flex items-center">
                              <Phone className="h-3 w-3 mr-1" />
                              {lead.phone}
                            </span>
                          )}
                          {lead.company && (
                            <span>{lead.company}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Confidence Score */}
                  <div className="text-center">
                    <div className={`font-medium ${getConfidenceColor(lead.confidence)}`}>
                      {(lead.confidence * 100).toFixed(0)}%
                    </div>
                    <div className="text-xs text-muted-foreground">Confidence</div>
                  </div>
                  
                  {/* Status */}
                  <div>
                    <Badge variant={getStatusVariant(lead.status)}>
                      {lead.status}
                    </Badge>
                  </div>
                  
                  {/* Source & Date */}
                  <div className="text-right min-w-0">
                    <div className="text-sm font-medium">{lead.source}</div>
                    <div className="text-xs text-muted-foreground">
                      {formatDate(new Date(lead.createdAt))}
                    </div>
                  </div>
                  
                  {/* Actions */}
                  <div className="flex items-center space-x-1">
                    {lead.website && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => window.open(lead.website, '_blank')}
                      >
                        <Globe className="h-3 w-3" />
                      </Button>
                    )}
                    
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                      <Eye className="h-3 w-3" />
                    </Button>
                    
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                      <Edit className="h-3 w-3" />
                    </Button>
                    
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default LeadsPage