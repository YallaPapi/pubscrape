import React from 'react'
import { Menu, Sun, Moon, Bell, Settings, User } from 'lucide-react'
import { Button } from './ui/button'
import { Badge } from './ui/badge'
import { useAppStore } from '../store/useAppStore'

const Header: React.FC = () => {
  const { 
    toggleSidebar, 
    theme, 
    setTheme, 
    isConnected, 
    activeCampaign,
    lastUpdate 
  } = useAppStore()

  const formatLastUpdate = () => {
    if (!lastUpdate) return 'Never'
    const diff = Date.now() - lastUpdate.getTime()
    const seconds = Math.floor(diff / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    
    if (hours > 0) return `${hours}h ago`
    if (minutes > 0) return `${minutes}m ago`
    return `${seconds}s ago`
  }

  return (
    <header className="flex items-center justify-between h-16 px-6 bg-card border-b">
      {/* Left Section */}
      <div className="flex items-center space-x-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleSidebar}
          className="lg:hidden"
        >
          <Menu className="h-5 w-5" />
        </Button>
        
        <div className="hidden lg:block">
          <h1 className="text-xl font-semibold">VRSEN Lead Generation</h1>
          {activeCampaign && (
            <p className="text-sm text-muted-foreground">
              Campaign: {activeCampaign.name}
            </p>
          )}
        </div>
      </div>

      {/* Center Section - Status */}
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <div
            className={`h-2 w-2 rounded-full ${
              isConnected ? 'bg-green-500' : 'bg-red-500'
            }`}
          />
          <span className="text-sm text-muted-foreground">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
        
        {lastUpdate && (
          <div className="text-sm text-muted-foreground">
            Last update: {formatLastUpdate()}
          </div>
        )}
      </div>

      {/* Right Section */}
      <div className="flex items-center space-x-2">
        {/* Notifications */}
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-5 w-5" />
          <Badge
            variant="destructive"
            className="absolute -top-1 -right-1 h-5 w-5 text-xs p-0 flex items-center justify-center"
          >
            3
          </Badge>
        </Button>

        {/* Theme Toggle */}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
        >
          {theme === 'light' ? (
            <Moon className="h-5 w-5" />
          ) : (
            <Sun className="h-5 w-5" />
          )}
        </Button>

        {/* Settings */}
        <Button variant="ghost" size="icon">
          <Settings className="h-5 w-5" />
        </Button>

        {/* User Menu */}
        <Button variant="ghost" size="icon">
          <User className="h-5 w-5" />
        </Button>
      </div>
    </header>
  )
}

export default Header