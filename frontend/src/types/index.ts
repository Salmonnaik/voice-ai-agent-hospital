export interface Appointment {
  id: string
  name: string
  mobile: string
  status: 'pending' | 'accepted' | 'rejected' | 'completed'
  createdAt: string
  scheduledTime?: string
  notes?: string
  department?: string
}

export interface WebSocketMessage {
  type: string
  data?: any
  timestamp: number
}

export interface VoiceEvent {
  type: 'start_recording' | 'stop_recording' | 'audio_chunk' | 'language_change'
  language?: 'en' | 'hi' | 'ta'
  timestamp: number
  audioData?: string
}

export interface TranscriptEvent {
  type: 'transcript'
  text: string
  isFinal: boolean
  language: 'en' | 'hi' | 'ta'
  timestamp: number
}

export interface TTSEvent {
  type: 'tts_audio'
  audio: string
  text: string
  language: 'en' | 'hi' | 'ta'
  timestamp: number
}

export interface AppointmentEvent {
  type: 'appointment_booked' | 'appointment_cancelled' | 'appointment_updated'
  appointment: Appointment
  timestamp: number
}

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error'
