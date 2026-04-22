import React from 'react'
import { Phone, AlertTriangle } from 'lucide-react'

export const EmergencySection: React.FC = () => {
  const handleEmergencyCall = () => {
    // In a real app, this would open the phone dialer
    window.open('tel:108')
  }

  return (
    <div className="card border-red-200 bg-red-50">
      <div className="flex items-center space-x-3 mb-4">
        <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
          <AlertTriangle className="w-5 h-5 text-red-600" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-red-900">Emergency</h3>
          <p className="text-sm text-red-700">24/7 Emergency Services</p>
        </div>
      </div>

      <button
        onClick={handleEmergencyCall}
        className="w-full bg-red-600 text-white py-3 px-4 rounded-lg hover:bg-red-700 transition-colors flex items-center justify-center space-x-2 font-medium"
      >
        <Phone className="w-5 h-5" />
        <span>Call: 108</span>
      </button>

      <div className="mt-3 text-xs text-red-700">
        <p>For medical emergencies, dial 108 immediately.</p>
        <p className="mt-1">Available 24 hours a day, 7 days a week.</p>
      </div>
    </div>
  )
}
