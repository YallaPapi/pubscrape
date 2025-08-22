import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'

const ReportsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Reports</h2>
        <p className="text-muted-foreground">
          Campaign reports and exports
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Report Generation</CardTitle>
          <CardDescription>
            Advanced reporting features coming soon
          </CardDescription>
        </CardHeader>
        <CardContent className="p-12 text-center">
          <div className="space-y-4">
            <div className="text-4xl">📄</div>
            <div>
              <h3 className="text-lg font-medium">Reports Coming Soon</h3>
              <p className="text-muted-foreground">
                Detailed reporting and export features will be available in the next version
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default ReportsPage