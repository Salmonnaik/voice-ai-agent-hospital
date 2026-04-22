import React from 'react'
import { Wifi, WifiOff } from 'lucide-react'

interface ConnectionStatusProps {
  isConnected: boolean
}

export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ isConnected }) => {
  const getStatusColor = () => {
    if (isConnected) return 'text-green-600'
    return 'text-red-600'
  }

  const getStatusIcon = () => {
    if (isConnected) return <Wifi className="w-4 h-4" />
    return <WifiOff className="w-4 h-4" />
  }

  const getStatusText = () => {
    if (isConnected) return 'Connected'
    return 'Disconnected'
  }

  return (
    <div className={`flex items-center space-x-2 ${getStatusColor()}`}>
      {getStatusIcon()}
      <span className="text-sm font-medium">{getStatusText()}</span>
    </div>
  )
}
