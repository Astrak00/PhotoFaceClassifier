// API functions for the face classifier backend

const API_BASE = '/api'

export interface Stats {
  total_photos: number
  processed_photos: number
  total_faces: number
  total_persons: number
  device: string
}

export interface DirectoryEntry {
  name: string
  path: string
  is_dir: boolean
}

export interface DirectoryListResponse {
  current_path: string
  parent_path: string | null
  entries: DirectoryEntry[]
}

export interface ScanRequest {
  directory: string
  recursive: boolean
  use_thumbnails: boolean
}

export interface ScanResponse {
  scan_id: number
  status: string
  message: string
}

export interface ScanProgress {
  scan_id: number
  status: string
  total_photos: number
  processed_photos: number
  total_faces: number
  total_persons: number
  current_file: string | null
  error_message: string | null
}

export interface PersonSummary {
  id: number
  name: string | null
  photo_count: number
  thumbnail_path: string | null
  sample_thumbnails: string[]
}

export interface Photo {
  id: number
  filepath: string
  filename: string
  directory: string
  exif_date: string | null
  processed: boolean
  created_at: string
}

export interface Face {
  id: number
  photo_id: number
  person_id: number | null
  box: number[]
  confidence: number
  thumbnail_path: string | null
  photo: Photo
}

export interface PersonWithFaces {
  id: number
  name: string | null
  cluster_id: number
  is_ignored: boolean
  photo_count: number
  representative_face_id: number | null
  created_at: string
  faces: Face[]
}

export interface FolderSpec {
  name: string
  person_ids: number[]
  logic: 'any' | 'all'
}

export interface CreateFoldersRequest {
  output_directory: string
  folders: FolderSpec[]
  overwrite: boolean
}

export interface FolderResult {
  folder_name: string
  folder_path: string
  created_count: number
  error_count: number
  errors: Array<{ filepath: string; error: string }>
}

export interface CreateFoldersResponse {
  success: boolean
  results: FolderResult[]
}

export interface ExportPreview {
  photo_count: number
  photos: Array<{
    id: number
    filename: string
    filepath: string
    exif_date: string | null
  }>
}

// Fetch functions
export async function fetchStats(): Promise<Stats> {
  const res = await fetch(`${API_BASE}/stats`)
  if (!res.ok) throw new Error('Failed to fetch stats')
  return res.json()
}

export async function browseDirectory(path?: string): Promise<DirectoryListResponse> {
  const url = path 
    ? `${API_BASE}/browse?path=${encodeURIComponent(path)}`
    : `${API_BASE}/browse`
  const res = await fetch(url)
  if (!res.ok) throw new Error('Failed to browse directory')
  return res.json()
}

export async function startScan(request: ScanRequest): Promise<ScanResponse> {
  const res = await fetch(`${API_BASE}/scan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (!res.ok) throw new Error('Failed to start scan')
  return res.json()
}

export async function getScanProgress(scanId: number): Promise<ScanProgress> {
  const res = await fetch(`${API_BASE}/scan/${scanId}/progress`)
  if (!res.ok) throw new Error('Failed to get scan progress')
  return res.json()
}

export async function getLatestScan(): Promise<ScanProgress> {
  const res = await fetch(`${API_BASE}/scan/latest`)
  if (!res.ok) throw new Error('No scans found')
  return res.json()
}

export async function fetchPersons(includeIgnored = false): Promise<PersonSummary[]> {
  const res = await fetch(`${API_BASE}/persons?include_ignored=${includeIgnored}`)
  if (!res.ok) throw new Error('Failed to fetch persons')
  return res.json()
}

export async function fetchPerson(personId: number): Promise<PersonWithFaces> {
  const res = await fetch(`${API_BASE}/persons/${personId}`)
  if (!res.ok) throw new Error('Failed to fetch person')
  return res.json()
}

export async function updatePerson(personId: number, data: { name?: string; is_ignored?: boolean }): Promise<void> {
  const res = await fetch(`${API_BASE}/persons/${personId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to update person')
}

export async function hidePerson(personId: number): Promise<void> {
  return updatePerson(personId, { is_ignored: true })
}

export async function unhidePerson(personId: number): Promise<void> {
  return updatePerson(personId, { is_ignored: false })
}

export async function mergePersons(keepPersonId: number, mergePersonIds: number[]): Promise<void> {
  const res = await fetch(`${API_BASE}/persons/merge`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      keep_person_id: keepPersonId,
      merge_person_ids: mergePersonIds,
    }),
  })
  if (!res.ok) throw new Error('Failed to merge persons')
}

export async function createExportFolders(request: CreateFoldersRequest): Promise<CreateFoldersResponse> {
  const res = await fetch(`${API_BASE}/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (!res.ok) throw new Error('Failed to create folders')
  return res.json()
}

export async function previewExport(personIds: number[], logic: 'any' | 'all'): Promise<ExportPreview> {
  const res = await fetch(
    `${API_BASE}/export/preview?person_ids=${personIds.join(',')}&logic=${logic}`
  )
  if (!res.ok) throw new Error('Failed to preview export')
  return res.json()
}

export async function resetDatabase(): Promise<void> {
  const res = await fetch(`${API_BASE}/reset`, {
    method: 'POST',
  })
  if (!res.ok) throw new Error('Failed to reset database')
}

export interface AppConfig {
  min_faces_per_person: number
  device: string
  available_devices: string[]
  current_device: {
    device: string
    device_name: string
  }
}

export interface UpdateConfigRequest {
  min_faces_per_person?: number
  device?: string
}

export async function getConfig(): Promise<AppConfig> {
  const res = await fetch(`${API_BASE}/config`)
  if (!res.ok) throw new Error('Failed to fetch config')
  return res.json()
}

export async function updateConfig(config: UpdateConfigRequest): Promise<{ status: string; config: { min_faces_per_person: number; device: string } }> {
  const res = await fetch(`${API_BASE}/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
  if (!res.ok) throw new Error('Failed to update config')
  return res.json()
}

export function getThumbnailUrl(thumbnailPath: string | null): string {
  if (!thumbnailPath) return ''
  // Extract just the filename from the path
  const filename = thumbnailPath.split('/').pop()
  return `/api/thumbnail/${filename}`
}
