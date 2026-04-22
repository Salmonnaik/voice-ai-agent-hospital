import React from 'react'
import { Calendar, Clock, User, Phone, CheckCircle, AlertCircle } from 'lucide-react'
import { Appointment } from '../types'


interface ScheduleHistoryProps {
  appointments: Appointment[]
}

export const ScheduleHistory: React.FC<ScheduleHistoryProps> = ({
  appointments
}) => {
  const sortedAppointments = [...appointments].sort((a, b) => 
    new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
  )

  const getStatusIcon = (status: string) => {
    return status === 'accepted' ? (
      <CheckCircle className="w-4 h-4 text-green-600" />
    ) : (
      <AlertCircle className="w-4 h-4 text-yellow-600" />
    )
  }

  const getStatusText = (status: string) => {
    return status === 'accepted' ? 'Accepted' : 'Pending'
  }

  const getStatusColor = (status: string) => {
    return status === 'accepted' 
      ? 'bg-green-100 text-green-800' 
      : 'bg-yellow-100 text-yellow-800'
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (sortedAppointments.length === 0) {
    return (
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Check Schedule</h3>
        </div>
        <div className="text-center py-8">
          <Calendar className="w-12 h-12 text-gray-400 mx-auto mb-3" />
          <p className="text-gray-600">No appointments found</p>
          <p className="text-sm text-gray-500 mt-1">
            Book your first appointment to see it here
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Check Schedule</h3>
        <span className="text-sm text-gray-600">
          {sortedAppointments.length} appointment{sortedAppointments.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div className="space-y-3">
        {sortedAppointments.map((appointment) => (
          <div
            key={appointment.id}
            className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors"
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center space-x-2">
                {getStatusIcon(appointment.status)}
                <span className={`text-xs font-medium px-2 py-1 rounded-full ${getStatusColor(appointment.status)}`}>
                  {getStatusText(appointment.status)}
                </span>
              </div>
              <span className="text-xs text-gray-500">
                {formatDate(appointment.createdAt)}
              </span>
            </div>

            {/* Appointment details */}
            <div className="space-y-2">
              {/* Name */}
              <div className="flex items-center space-x-2">
                <User className="w-4 h-4 text-gray-400" />
                <span className="text-sm font-medium text-gray-900">{appointment.name}</span>
              </div>

              {/* Mobile */}
              <div className="flex items-center space-x-2">
                <Phone className="w-4 h-4 text-gray-400" />
                <span className="text-sm text-gray-600">{appointment.mobile}</span>
              </div>

              {/* Scheduled time (if accepted) */}
              {appointment.scheduledTime && (
                <div className="flex items-center space-x-2">
                  <Clock className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-600">
                    Scheduled: {formatDate(appointment.scheduledTime)}
                  </span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Summary */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">
            Accepted: {appointments.filter(a => a.status === 'accepted').length}
          </span>
          <span className="text-gray-600">
            Pending: {appointments.filter(a => a.status === 'pending').length}
          </span>
        </div>
      </div>
    </div>
  )
}
