import React from 'react'
import { Languages } from 'lucide-react'

interface LanguageSwitcherProps {
  currentLanguage: 'en' | 'hi' | 'ta'
  onLanguageChange: (language: 'en' | 'hi' | 'ta') => void
  disabled?: boolean
}

export const LanguageSwitcher: React.FC<LanguageSwitcherProps> = ({
  currentLanguage,
  onLanguageChange,
  disabled = false
}) => {
  const languages = [
    { code: 'en' as const, name: 'EN', fullName: 'English' },
    { code: 'hi' as const, name: 'HI', fullName: 'Hindi' },
    { code: 'ta' as const, name: 'TA', fullName: 'Tamil' }
  ]

  return (
    <div className="flex items-center space-x-2">
      <div className="flex items-center space-x-1 text-gray-600">
        <Languages className="w-4 h-4" />
        <span className="text-xs font-medium">Language:</span>
      </div>
      
      <div className="flex items-center space-x-1 bg-gray-100 rounded-lg p-1">
        {languages.map((lang) => (
          <button
            key={lang.code}
            onClick={() => {
              console.log(`Language clicked: ${lang.code} (current: ${currentLanguage})`)
              onLanguageChange(lang.code)
            }}
            disabled={disabled}
            className={`
              px-3 py-1.5 rounded-md text-sm font-medium transition-all duration-200
              ${currentLanguage === lang.code 
                ? 'bg-white text-gray-900 shadow-sm transform scale-105' 
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              }
              ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
            `}
            title={lang.fullName}
          >
            {lang.name}
          </button>
        ))}
      </div>
    </div>
  )
}
