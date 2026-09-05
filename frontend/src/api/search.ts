export interface SearchHit {
  document_id: number
  document_title: string
  chunk_id: number
  seq: number
  section_path: string
  content: string
  score: number
}

import { http } from '@/api/http'

export async function search(spaceId: number, query: string, topK = 10): Promise<SearchHit[]> {
  const { data } = await http.post(`/spaces/${spaceId}/search`, { query, top_k: topK })
  return data
}