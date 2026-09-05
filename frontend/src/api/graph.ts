export interface GraphNode {
  id: number
  name: string
  type: string
  mention_count: number
  description: string | null
}

export interface GraphEdge {
  id: number
  src_id: number
  dst_id: number
  relation: string
  weight: number
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface EntityDetail {
  id: number
  name: string
  type: string
  description: string | null
  aliases: string[] | null
  mention_count: number
  documents: { id: number; title: string }[]
}

import { http } from '@/api/http'

export async function getGraphOverview(
  spaceId: number,
  params?: { limit?: number; type_filter?: string; search?: string },
): Promise<GraphData> {
  const { data } = await http.get(`/spaces/${spaceId}/graph/overview`, { params })
  return data
}

export async function getSubgraph(spaceId: number, entityId: number, hops = 2): Promise<GraphData> {
  const { data } = await http.get(`/spaces/${spaceId}/graph/subgraph`, {
    params: { entity_id: entityId, hops },
  })
  return data
}

export async function getDocumentGraph(documentId: number): Promise<GraphData> {
  const { data } = await http.get(`/documents/${documentId}/graph`)
  return data
}

export async function getEntityDetail(entityId: number): Promise<EntityDetail> {
  const { data } = await http.get(`/entities/${entityId}`)
  return data
}