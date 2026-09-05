export interface Document {
  id: number
  space_id: number
  title: string
  source_type: string
  status: string
  summary: string | null
  tags: string[] | null
  content_text: string
  created_by: number
  created_at: string
  updated_at: string
}

export interface DocumentDetail extends Document {
  content_json: any | null
}

export interface DocumentVersion {
  id: number
  document_id: number
  version_no: number
  content_md: string
  created_by: number
  created_at: string
}

export interface Job {
  id: number
  space_id: number
  document_id: number | null
  job_type: string
  status: string
  error: string | null
  created_at: string
  updated_at: string
}

import { http } from '@/api/http'

export async function listDocuments(spaceId: number): Promise<Document[]> {
  const { data } = await http.get(`/spaces/${spaceId}/documents`)
  return data
}

export async function getDocument(id: number): Promise<DocumentDetail> {
  const { data } = await http.get(`/documents/${id}`)
  return data
}

export async function createDocument(spaceId: number, title: string): Promise<Document> {
  const { data } = await http.post(`/spaces/${spaceId}/documents`, { title })
  return data
}

export async function updateDocument(id: number, title: string): Promise<Document> {
  const { data } = await http.patch(`/documents/${id}`, { title })
  return data
}

export async function saveContent(id: number, content_text: string, content_json?: any): Promise<Document> {
  const { data } = await http.put(`/documents/${id}/content`, { content_text, content_json })
  return data
}

export async function deleteDocument(id: number): Promise<void> {
  await http.delete(`/documents/${id}`)
}

export async function getVersions(id: number): Promise<DocumentVersion[]> {
  const { data } = await http.get(`/documents/${id}/versions`)
  return data
}

export async function restoreVersion(id: number, versionNo: number): Promise<Document> {
  const { data } = await http.post(`/documents/${id}/restore/${versionNo}`)
  return data
}

export async function uploadFiles(spaceId: number, files: File[]): Promise<Document[]> {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  const { data } = await http.post(`/spaces/${spaceId}/documents/upload`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function getJobs(id: number): Promise<Job[]> {
  const { data } = await http.get(`/documents/${id}/jobs`)
  return data
}