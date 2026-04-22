import React from 'react'
import { User, Phone, Edit2 } from 'lucide-react'

interface ProfileSectionProps {
  userData: {
    name: string
    mobile: string
  } | null
  onEdit?: () => void
}

export const ProfileSection: React.FC<ProfileSectionProps> = ({
  userData,
  onEdit
}) => {
  if (!userData) {
    return (
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">My Profile</h3>
        </div>
        <div className="text-center py-8">
          <User className="w-12 h-12 text-gray-400 mx-auto mb-3" />
          <p className="text-gray-600">No profile information</p>
          <p className="text-sm text-gray-500 mt-1">
            Book an appointment to create your profile
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">My Profile</h3>
        {onEdit && (
          <button
            onClick={onEdit}
            className="text-primary-600 hover:text-primary-700 transition-colors"
          >
            <Edit2 className="w-4 h-4" />
          </button>
        )}
      </div>

      <div className="space-y-4">
        {/* Name */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center">
            <User className="w-5 h-5 text-primary-600" />
          </div>
          <div>
            <p className="text-sm text-gray-600">Name</p>
            <p className="font-medium text-gray-900">{userData.name}</p>
          </div>
        </div>

        {/* Mobile */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
            <Phone className="w-5 h-5 text-green-600" />
          </div>
          <div>
            <p className="text-sm text-gray-600">Mobile Number</p>
            <p className="font-medium text-gray-900">{userData.mobile}</p>
          </div>
        </div>
      </div>

      {/* Auto-fill note */}
      <div className="mt-4 p-3 bg-gray-50 rounded-lg">
        <p className="text-xs text-gray-600">
          Profile information auto-filled from your last appointment
        </p>
      </div>
    </div>
  )
}
