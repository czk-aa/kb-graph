export interface Notification {
  id: number
  space_id: number
  type: string
  title: string
  body: string
  ref_id: number | null
  is_read: boolean
  created_at: string
}

import { http } from '@/api/http'

export async function listNotifications(unreadOnly = false, limit = 50): Promise<Notification[]> {
  const { data } = await http.get('/notifications', { params: { unread_only: unreadOnly, limit } })
  return data
}

export async function markAllRead(): Promise<void> {
  await http.post('/notifications/read-all')
}

export async function markRead(id: number): Promise<void> {
  await http.post(`/notifications/${id}/read`)
}