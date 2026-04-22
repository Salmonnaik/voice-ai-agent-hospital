import React, { useEffect } from 'react'
import { CheckCircle, XCircle, X } from 'lucide-react'

interface ToastProps {
  message: string
  type: 'success' | 'error'
  isVisible: boolean
  onClose: () => void
}

export const Toast: React.FC<ToastProps> = ({
  message,
  type,
  isVisible,
  onClose
}) => {
  useEffect(() => {
    if (isVisible) {
      const timer = setTimeout(() => {
        onClose()
      }, 3000)
      return () => clearTimeout(timer)
    }
  }, [isVisible, onClose])

  if (!isVisible) return null

  const icon = type === 'success' ? (
    <CheckCircle className="w-5 h-5 text-green-500" />
  ) : (
    <XCircle className="w-5 h-5 text-red-500" />
  )

  const bgColor = type === 'success' ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
  const textColor = type === 'success' ? 'text-green-800' : 'text-red-800'

  return (
    <div className="fixed top-4 right-4 z-50 animate-in slide-in-from-right">
      <div className={`flex items-center p-4 rounded-lg border ${bgColor} shadow-lg max-w-sm`}>
        {icon}
        <p className={`ml-3 text-sm font-medium ${textColor}`}>
          {message}
        </p>
        <button
          onClick={onClose}
          className="ml-auto -mr-1.5 -mt-1.5 p-1.5 rounded-lg hover:bg-black hover:bg-opacity-10 transition-colors"
        >
          <X className="w-4 h-4 text-gray-500" />
        </button>
      </div>
    </div>
  )
}
