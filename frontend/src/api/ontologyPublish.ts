/**
 * 本体发布 — 前端 API 客户端
 * 接 backend/app/api/v1/ontology_publish.py 的真实接口
 */
import { get, post } from './client'

export const ontologyPublishApi = {
  previewImpact: (versionId: string) =>
    get<any>(`/ontology-publish/versions/${versionId}/impact`),
  quickPublish: (ontologyId: string, name?: string, description?: string) =>
    post<any>('/ontology-publish/quick-publish', { ontology_id: ontologyId, name, description }),
  listPublishedOntologies: () =>
    get<any>('/ontology-publish/ontologies'),
  listVersions: (status?: string) =>
    get<any>('/ontology-publish/versions', { params: status ? { status } : undefined }),
  getVersion: (versionId: string) =>
    get<any>(`/ontology-publish/versions/${versionId}`),
  listVersionFunctions: (versionId: string) =>
    get<any>(`/ontology-publish/versions/${versionId}/functions`),
  listVersionActions: (versionId: string) =>
    get<any>(`/ontology-publish/versions/${versionId}/actions`),
}
