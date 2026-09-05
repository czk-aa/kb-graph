export interface ChatSession {
  id: number
  space_id: number
  title: string
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  citations: Citation[] | null
  meta: any | null
}

export interface Citation {
  doc_id: number
  doc_title: string
  chunk_id: number
  seq: number
  section_path: string
  quote: string
  score: number
}

export interface SSEEvent {
  type: 'citations' | 'delta' | 'done'
  data: any
}

import { http } from '@/api/http'

export async function createSession(spaceId: number): Promise<ChatSession> {
  const { data } = await http.post('/chat/sessions', { space_id: spaceId })
  return data
}

export async function listSessions(spaceId: number): Promise<ChatSession[]> {
  const { data } = await http.get('/chat/sessions', { params: { space_id: spaceId } })
  return data
}

export async function getMessages(sessionId: number): Promise<ChatMessage[]> {
  const { data } = await http.get(`/chat/sessions/${sessionId}/messages`)
  return data
}

export async function deleteSession(sessionId: number): Promise<void> {
  await http.delete(`/chat/sessions/${sessionId}`)
}

export async function* askStream(sessionId: number, question: string): AsyncGenerator<SSEEvent> {
  const token = localStorage.getItem('token')
  const response = await fetch('/api/v1/chat/ask', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ session_id: sessionId, question }),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({ message: '请求失败' }))
    throw new Error(err.message || `HTTP ${response.status}`)
  }

  const reader = response.body?.getReader()
  if (!reader) throw new Error('无法读取响应流')

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    let eventType = ''
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        eventType = line.slice(7).trim()
      } else if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6))
          yield { type: eventType as SSEEvent['type'], data }
        } catch {
          // skip parse errors
        }
      }
    }
  }
}