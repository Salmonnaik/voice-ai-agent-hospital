import React, { useState, useRef, useEffect } from 'react'
import { Mic, MicOff, Volume2 } from 'lucide-react'

interface VoiceRecorderProps {
  isRecording: boolean
  onStart: () => void
  onStop: () => void
  disabled?: boolean
}

export const VoiceRecorder: React.FC<VoiceRecorderProps> = ({
  isRecording,
  onStart,
  onStop,
  disabled = false
}) => {
  const [audioLevel, setAudioLevel] = useState(0)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const animationFrameRef = useRef<number | null>(null)

  useEffect(() => {
    if (isRecording) {
      startAudioCapture()
    } else {
      stopAudioCapture()
    }

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
      if (audioContextRef.current) {
        audioContextRef.current.close()
      }
    }
  }, [isRecording])

  const startAudioCapture = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000
        } 
      })

      // Set up audio context for level monitoring
      audioContextRef.current = new AudioContext()
      analyserRef.current = audioContextRef.current.createAnalyser()
      const source = audioContextRef.current.createMediaStreamSource(stream)
      source.connect(analyserRef.current)
      analyserRef.current.fftSize = 256

      // Set up media recorder
      mediaRecorderRef.current = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      })

      // Start monitoring audio levels
      monitorAudioLevel()

      mediaRecorderRef.current.start(100) // Collect data every 100ms

    } catch (error) {
      console.error('Error accessing microphone:', error)
    }
  }

  const stopAudioCapture = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop()
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop())
    }

    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current)
      animationFrameRef.current = null
    }

    setAudioLevel(0)
  }

  const monitorAudioLevel = () => {
    if (!analyserRef.current) return

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount)
    analyserRef.current.getByteFrequencyData(dataArray)

    // Calculate average level
    const average = dataArray.reduce((sum, value) => sum + value, 0) / dataArray.length
    const normalizedLevel = Math.min(100, (average / 128) * 100)
    setAudioLevel(normalizedLevel)

    animationFrameRef.current = requestAnimationFrame(monitorAudioLevel)
  }

  const handleClick = () => {
    if (disabled) return

    if (isRecording) {
      onStop()
    } else {
      onStart()
    }
  }

  const getButtonColor = () => {
    if (disabled) return 'bg-gray-300 cursor-not-allowed'
    if (isRecording) return 'bg-red-500 hover:bg-red-600 animate-pulse'
    return 'bg-primary-500 hover:bg-primary-600'
  }

  return (
    <div className="flex flex-col items-center space-y-6">
      {/* Microphone Button */}
      <button
        onClick={handleClick}
        disabled={disabled}
        className={`
          relative w-24 h-24 rounded-full flex items-center justify-center
          transition-all duration-200 transform hover:scale-105
          ${getButtonColor()}
          ${disabled ? 'transform-none' : ''}
        `}
      >
        <div className="absolute inset-0 rounded-full bg-white opacity-20" />
        {isRecording ? (
          <MicOff className="w-10 h-10 text-white relative z-10" />
        ) : (
          <Mic className="w-10 h-10 text-white relative z-10" />
        )}
      </button>

      {/* Audio Level Indicator */}
      {isRecording && (
        <div className="w-full max-w-xs">
          <div className="flex items-center space-x-2 mb-2">
            <Volume2 className="w-4 h-4 text-gray-600" />
            <span className="text-sm text-gray-600">Audio Level</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-green-400 to-green-600 transition-all duration-100 ease-out"
              style={{ width: `${audioLevel}%` }}
            />
          </div>
        </div>
      )}

      {/* Status Text */}
      <div className="text-center">
        <p className="text-sm font-medium text-gray-900">
          {disabled ? 'Microphone unavailable' : 
           isRecording ? 'Recording... Click to stop' : 
           'Click to start recording'}
        </p>
        {isRecording && (
          <p className="text-xs text-gray-500 mt-1">
            Speak clearly into your microphone
          </p>
        )}
      </div>

      {/* Recording Indicator */}
      {isRecording && (
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
          <span className="text-sm text-red-600 font-medium">LIVE</span>
        </div>
      )}
    </div>
  )
}
