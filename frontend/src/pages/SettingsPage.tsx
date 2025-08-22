import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'

const SettingsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Settings</h2>
        <p className="text-muted-foreground">
          Application settings and configuration
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Application Settings</CardTitle>
          <CardDescription>
            Settings panel coming soon
          </CardDescription>
        </CardHeader>
        <CardContent className="p-12 text-center">
          <div className="space-y-4">
            <div className="text-4xl">⚙️</div>
            <div>
              <h3 className="text-lg font-medium">Settings Coming Soon</h3>
              <p className="text-muted-foreground">
                Configuration options and preferences will be available in the next version
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default SettingsPage