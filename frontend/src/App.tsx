import { useState, useEffect } from 'react'
import { Phone, Calendar, Clock, User } from 'lucide-react'
import { VoiceRecorder } from './components/VoiceRecorder'
import { AppointmentCard } from './components/AppointmentCard'
import { ConnectionStatus } from './components/ConnectionStatus'
import { AppointmentModal } from './components/AppointmentModal'
import { Toast } from './components/Toast'
import { ProfileSection } from './components/ProfileSection'
import { ScheduleHistory } from './components/ScheduleHistory'
import { EmergencySection } from './components/EmergencySection'
import { LanguageSwitcher } from './components/LanguageSwitcher'
import { useWebSocket } from './hooks/useWebSocket'
import { Appointment } from './types'

function App() {
  const [isConnected, setIsConnected] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [allAppointments, setAllAppointments] = useState<Appointment[]>([])
  const [currentTranscript, setCurrentTranscript] = useState('')
  const [language, setLanguage] = useState<'en' | 'hi' | 'ta'>('en')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [toast, setToast] = useState({ message: '', type: 'success' as 'success' | 'error', isVisible: false })
  const [activeView, setActiveView] = useState<'voice' | 'profile' | 'schedule'>('voice')
  
  const { sendMessage, lastMessage, connectionStatus } = useWebSocket('ws://localhost:8080')

  useEffect(() => {
    setIsConnected(connectionStatus === 'connected')
  }, [connectionStatus])

  useEffect(() => {
    // Filter upcoming appointments (accepted status)
    const upcoming = allAppointments.filter(apt => apt.status === 'accepted')
    setAppointments(upcoming)
  }, [allAppointments])

  useEffect(() => {
    if (lastMessage) {
      try {
        const data = JSON.parse(lastMessage.data)
        
        if (data.type === 'transcript') {
          setCurrentTranscript(data.text)
          
          // Add voice-triggered appointment booking suggestions
          const transcript = data.text.toLowerCase()
          const bookingKeywords = ['book', 'appointment', 'schedule', 'doctor', 'hospital', 'medical']
          const hasBookingIntent = bookingKeywords.some(keyword => transcript.includes(keyword))
          
          if (hasBookingIntent && !isModalOpen) {
            // Show booking suggestion based on language
            setTimeout(() => {
              const suggestions = {
                'en': 'Would you like me to book an appointment for you?',
                'hi': 'kya main aapke liye appointment book kar sakta hun?',
                'ta': 'naan ungalukku appointment book seithaluda?'
              }
              showToast(suggestions[language] || suggestions['en'], 'success')
            }, 2000)
          }
        }
        
        if (data.type === 'appointment_booked') {
          setAllAppointments(prev => [...prev, data.appointment])
        }
        
        if (data.type === 'tts_audio') {
          // Handle TTS audio playback
          playAudio(data.audio)
        }
      } catch (error) {
        console.error('Error parsing message:', error)
      }
    }
  }, [lastMessage])

  const playAudio = (audioData: string) => {
    // Convert base64 audio data and play
    const audio = new Audio(`data:audio/wav;base64,${audioData}`)
    audio.play()
  }

  const handleRecordingStart = () => {
    setIsRecording(true)
    sendMessage({
      type: 'start_recording',
      language,
      timestamp: Date.now()
    })
  }

  const handleRecordingStop = () => {
    setIsRecording(false)
    sendMessage({
      type: 'stop_recording',
      timestamp: Date.now()
    })
  }

  const handleLanguageChange = (newLanguage: 'en' | 'hi' | 'ta') => {
    console.log(`handleLanguageChange called: ${language} -> ${newLanguage}`)
    setLanguage(newLanguage)
    sendMessage({
      type: 'language_change',
      language: newLanguage,
      timestamp: Date.now()
    })
  }

  const handleAppointmentSubmit = async (data: { name: string; mobile: string }) => {
    setIsLoading(true)
    
    try {
      // Create new appointment
      const newAppointment: Appointment = {
        id: Date.now().toString(),
        name: data.name,
        mobile: data.mobile,
        status: 'pending',
        createdAt: new Date().toISOString()
      }

      // Add to appointments list
      setAllAppointments(prev => [newAppointment, ...prev])
      
      // Show success message
      setToast({
        message: 'Submitted. Our team will contact you shortly.',
        type: 'success',
        isVisible: true
      })
      
      // Close modal
      setIsModalOpen(false)
      
      // Send to backend via WebSocket if connected
      if (isConnected) {
        sendMessage({
          type: 'appointment_request',
          appointment: newAppointment,
          timestamp: Date.now()
        })
      }
      
    } catch (error) {
      setToast({
        message: 'Failed to submit appointment. Please try again.',
        type: 'error',
        isVisible: true
      })
    } finally {
      setIsLoading(false)
    }
  }

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type, isVisible: true })
  }

  const hideToast = () => {
    setToast(prev => ({ ...prev, isVisible: false }))
  }

  const getUserProfile = () => {
    const latestAppointment = allAppointments[0]
    return latestAppointment ? {
      name: latestAppointment.name,
      mobile: latestAppointment.mobile
    } : null
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-green-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-r from-primary-500 to-medical-500 rounded-lg flex items-center justify-center">
                <Phone className="w-5 h-5 text-white" />
              </div>
              <h1 className="text-xl font-bold text-gray-900">
                Voice AI Medical Assistant
              </h1>
            </div>
            
            <div className="flex items-center space-x-4">
              <ConnectionStatus isConnected={isConnected} />
              
              <LanguageSwitcher
                currentLanguage={language}
                onLanguageChange={handleLanguageChange}
                disabled={!isConnected}
              />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Main Content Area */}
          <div className="lg:col-span-2 space-y-6">
            <div className="card">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-gray-900">
                  Voice Assistant
                </h2>
                <div className="flex items-center space-x-2">
                  {isRecording && (
                    <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse" />
                  )}
                  <span className="text-sm text-gray-600">
                    {isRecording ? 'Recording...' : 'Ready'}
                  </span>
                </div>
              </div>

              {/* Current Transcript */}
              {currentTranscript && (
                <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <p className="text-gray-900">{currentTranscript}</p>
                </div>
              )}

              {/* Voice Recorder */}
              <VoiceRecorder
                isRecording={isRecording}
                onStart={handleRecordingStart}
                onStop={handleRecordingStop}
                disabled={!isConnected}
              />

              {/* Navigation Tabs */}
              <div className="mt-6 flex space-x-1 bg-gray-100 rounded-lg p-1">
                <button
                  onClick={() => setActiveView('voice')}
                  className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-colors ${
                    activeView === 'voice'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Voice Assistant
                </button>
                <button
                  onClick={() => setActiveView('profile')}
                  className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-colors ${
                    activeView === 'profile'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  My Profile
                </button>
                <button
                  onClick={() => setActiveView('schedule')}
                  className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-colors ${
                    activeView === 'schedule'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Schedule
                </button>
              </div>

              {/* Quick Actions */}
              <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-3">
                <button
                  onClick={() => setIsModalOpen(true)}
                  className="btn-secondary flex items-center justify-center space-x-2"
                >
                  <Calendar className="w-4 h-4" />
                  <span>Book Appointment</span>
                </button>
                <button
                  onClick={() => setActiveView('schedule')}
                  className="btn-secondary flex items-center justify-center space-x-2"
                >
                  <Clock className="w-4 h-4" />
                  <span>Check Schedule</span>
                </button>
                <button
                  onClick={() => setActiveView('profile')}
                  className="btn-secondary flex items-center justify-center space-x-2"
                >
                  <User className="w-4 h-4" />
                  <span>My Profile</span>
                </button>
                <button
                  onClick={() => showToast('Emergency: Call 108 for immediate assistance', 'success')}
                  className="btn-secondary flex items-center justify-center space-x-2"
                >
                  <Phone className="w-4 h-4" />
                  <span>Emergency</span>
                </button>
              </div>
            </div>

            {/* Dynamic Content based on active view */}
            {activeView === 'voice' && (
              <>
                <div className="card">
                  <div className="flex items-center justify-between mb-6">
                    <h2 className="text-2xl font-bold text-gray-900">
                      Voice Assistant
                    </h2>
                    <div className="flex items-center space-x-2">
                      {isRecording && (
                        <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse" />
                      )}
                      <span className="text-sm text-gray-600">
                        {isRecording ? 'Recording...' : 'Ready'}
                      </span>
                    </div>
                  </div>

                  {/* Current Transcript */}
                  {currentTranscript && (
                    <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                      <p className="text-gray-900">{currentTranscript}</p>
                    </div>
                  )}

                  {/* Voice Recorder */}
                  <VoiceRecorder
                    isRecording={isRecording}
                    onStart={handleRecordingStart}
                    onStop={handleRecordingStop}
                    disabled={!isConnected}
                  />
                </div>

                {/* Instructions */}
                <div className="card">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    How to Use
                  </h3>
                  <ul className="space-y-2 text-gray-600">
                    <li className="flex items-start space-x-2">
                      <span className="w-6 h-6 bg-primary-100 text-primary-600 rounded-full flex items-center justify-center text-sm font-medium">1</span>
                      <span>Click the microphone button to start recording</span>
                    </li>
                    <li className="flex items-start space-x-2">
                      <span className="w-6 h-6 bg-primary-100 text-primary-600 rounded-full flex items-center justify-center text-sm font-medium">2</span>
                      <span>Speak clearly about your medical needs or appointment requirements</span>
                    </li>
                    <li className="flex items-start space-x-2">
                      <span className="w-6 h-6 bg-primary-100 text-primary-600 rounded-full flex items-center justify-center text-sm font-medium">3</span>
                      <span>The AI will understand and help you book appointments</span>
                    </li>
                    <li className="flex items-start space-x-2">
                      <span className="w-6 h-6 bg-primary-100 text-primary-600 rounded-full flex items-center justify-center text-sm font-medium">4</span>
                      <span>Switch between English, Hindi, and Tamil as needed</span>
                    </li>
                  </ul>
                </div>
              </>
            )}

            {activeView === 'profile' && (
              <ProfileSection
                userData={getUserProfile()}
                onEdit={() => setIsModalOpen(true)}
              />
            )}

            {activeView === 'schedule' && (
              <ScheduleHistory appointments={allAppointments} />
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Upcoming Appointments */}
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Upcoming Appointments
              </h3>
              
              {appointments.length === 0 ? (
                <div className="text-center py-8">
                  <Calendar className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                  <p className="text-gray-600">No appointments scheduled</p>
                  <p className="text-sm text-gray-500 mt-1">
                    Book an appointment to see it here
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {appointments.map((appointment) => (
                    <AppointmentCard key={appointment.id} appointment={appointment} />
                  ))}
                </div>
              )}
            </div>

            {/* Emergency Section */}
            <EmergencySection />

            {/* System Status */}
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                System Status
              </h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Voice Recognition</span>
                  <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">AI Assistant</span>
                  <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Speech Synthesis</span>
                  <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
                </div>
              </div>
              <div className="mt-3 text-xs text-gray-500">
                {isConnected ? 'All systems operational' : 'System disconnected'}
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Appointment Modal */}
      <AppointmentModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleAppointmentSubmit}
        isLoading={isLoading}
      />

      {/* Toast Notifications */}
      <Toast
        message={toast.message}
        type={toast.type}
        isVisible={toast.isVisible}
        onClose={hideToast}
      />
    </div>
  )
}

export default App
