export interface Comment {
  id: number
  document_id: number
  user_id: number
  parent_id: number | null
  content: string
  anchor: string | null
  created_at: string
  updated_at: string
  user: { id: number; nickname: string; avatar_url: string | null }
  replies: Comment[]
}

import { http } from '@/api/http'

export async function listComments(docId: number): Promise<Comment[]> {
  const { data } = await http.get(`/documents/${docId}/comments`)
  return data
}

export async function createComment(
  docId: number,
  content: string,
  parentId?: number,
  anchor?: string,
): Promise<Comment> {
  const { data } = await http.post(`/documents/${docId}/comments`, {
    content,
    parent_id: parentId || null,
    anchor: anchor || null,
  })
  return data
}

export async function deleteComment(commentId: number): Promise<void> {
  await http.delete(`/comments/${commentId}`)
}