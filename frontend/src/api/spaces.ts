export interface Space {
  id: number
  name: string
  description: string
  owner_id: number
  my_role: 'owner' | 'admin' | 'member'
  created_at: string
  updated_at: string
}

export interface SpaceMember {
  user: { id: number; email: string; nickname: string; avatar_url: string | null }
  role: 'owner' | 'admin' | 'member'
  created_at: string
}

import { http } from '@/api/http'

export async function listSpaces(): Promise<Space[]> {
  const { data } = await http.get('/spaces')
  return data
}

export async function createSpace(name: string, description: string): Promise<Space> {
  const { data } = await http.post('/spaces', { name, description })
  return data
}

export async function listMembers(spaceId: number): Promise<SpaceMember[]> {
  const { data } = await http.get(`/spaces/${spaceId}/members`)
  return data
}

export async function addMember(spaceId: number, email: string, role: string) {
  await http.post(`/spaces/${spaceId}/members`, { email, role })
}

export async function removeMember(spaceId: number, userId: number) {
  await http.delete(`/spaces/${spaceId}/members/${userId}`)
}
