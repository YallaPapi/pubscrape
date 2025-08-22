import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'

const AnalyticsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Analytics</h2>
        <p className="text-muted-foreground">
          Campaign performance and insights
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Analytics Dashboard</CardTitle>
          <CardDescription>
            Detailed analytics and reporting coming soon
          </CardDescription>
        </CardHeader>
        <CardContent className="p-12 text-center">
          <div className="space-y-4">
            <div className="text-4xl">📊</div>
            <div>
              <h3 className="text-lg font-medium">Analytics Coming Soon</h3>
              <p className="text-muted-foreground">
                Advanced analytics and insights will be available in the next version
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default AnalyticsPage