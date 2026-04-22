import React from 'react'
import { Calendar, Clock, User, Phone } from 'lucide-react'
import { Appointment } from '../types'

interface AppointmentCardProps {
  appointment: Appointment
}

export const AppointmentCard: React.FC<AppointmentCardProps> = ({ appointment }) => {
  const getStatusColor = (status: Appointment['status']) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800'
      case 'accepted':
        return 'bg-green-100 text-green-800'
      case 'rejected':
        return 'bg-red-100 text-red-800'
      case 'completed':
        return 'bg-gray-100 text-gray-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric'
    })
  }

  const formatDateTime = (dateTimeString?: string) => {
    if (!dateTimeString) return 'Not scheduled'
    return new Date(dateTimeString).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-2">
            <User className="w-4 h-4 text-gray-600" />
            <h4 className="font-semibold text-gray-900">{appointment.name}</h4>
          </div>
          
          <div className="flex items-center space-x-2 text-sm text-gray-600">
            <Phone className="w-3 h-3" />
            <span>{appointment.mobile}</span>
          </div>
          
          {appointment.department && (
            <p className="text-sm text-gray-600 mt-1">{appointment.department}</p>
          )}
        </div>
        
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(appointment.status)}`}>
          {appointment.status.charAt(0).toUpperCase() + appointment.status.slice(1)}
        </span>
      </div>

      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center space-x-1 text-gray-600">
          <Calendar className="w-3 h-3" />
          <span>{formatDate(appointment.createdAt)}</span>
        </div>
        
        {appointment.scheduledTime && (
          <div className="flex items-center space-x-1 text-gray-600">
            <Clock className="w-3 h-3" />
            <span>{formatDateTime(appointment.scheduledTime)}</span>
          </div>
        )}
      </div>

      {appointment.notes && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <p className="text-xs text-gray-500">{appointment.notes}</p>
        </div>
      )}
    </div>
  )
}
