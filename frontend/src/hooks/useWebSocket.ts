import { useState, useEffect, useRef, useCallback } from 'react'
import { ConnectionStatus } from '../types'

interface UseWebSocketReturn {
  sendMessage: (message: any) => void
  lastMessage: MessageEvent | null
  connectionStatus: ConnectionStatus
  error: string | null
}

export const useWebSocket = (url: string): UseWebSocketReturn => {
  const [lastMessage, setLastMessage] = useState<MessageEvent | null>(null)
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected')
  const [error, setError] = useState<string | null>(null)
  const ws = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)
  const maxReconnectAttempts = 5
  const reconnectAttempts = useRef(0)

  const connect = useCallback(() => {
    try {
      setConnectionStatus('connecting')
      setError(null)
      
      console.log('Attempting WebSocket connection to:', url)
      ws.current = new WebSocket(url)
      
      ws.current.onopen = () => {
        setConnectionStatus('connected')
        reconnectAttempts.current = 0
        console.log('WebSocket connected')
      }
      
      ws.current.onmessage = (event: MessageEvent) => {
        setLastMessage(event)
      }
      
      ws.current.onclose = (event: CloseEvent) => {
        setConnectionStatus('disconnected')
        console.log('WebSocket disconnected', event.code, event.reason)
        
        // Attempt to reconnect if not explicitly closed
        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current++
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000)
          
          console.log(`Attempting to reconnect in ${delay}ms (attempt ${reconnectAttempts.current}/${maxReconnectAttempts})`)
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, delay)
        } else if (reconnectAttempts.current >= maxReconnectAttempts) {
          setError('Failed to reconnect after maximum attempts')
        }
      }
      
      ws.current.onerror = (error: Event) => {
        console.error('WebSocket error:', error)
        setError('Connection error')
        setConnectionStatus('error')
      }
      
      ws.current.onclose = (event: CloseEvent) => {
        console.log('WebSocket closed:', event.code, event.reason)
        setConnectionStatus('disconnected')
      }
      
    } catch (err) {
      console.error('Failed to create WebSocket connection:', err)
      setError('Failed to create connection')
      setConnectionStatus('error')
    }
  }, [url])

  const sendMessage = useCallback((message: any) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      try {
        const messageString = typeof message === 'string' ? message : JSON.stringify(message)
        ws.current.send(messageString)
      } catch (err) {
        console.error('Failed to send message:', err)
        setError('Failed to send message')
      }
    } else {
      console.warn('WebSocket is not connected')
      setError('Cannot send message - not connected')
    }
  }, [])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    
    if (ws.current) {
      ws.current.close(1000, 'Disconnected by user')
      ws.current = null
    }
    
    setConnectionStatus('disconnected')
    reconnectAttempts.current = 0
  }, [])

  useEffect(() => {
    connect()
    
    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  return {
    sendMessage,
    lastMessage,
    connectionStatus,
    error
  }
}
