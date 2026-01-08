import { createContext, useContext, useState, type ReactNode } from 'react'

interface FolderConfig {
  id: string
  name: string
  personIds: Set<number>
  logic: 'any' | 'all'
}

interface ExportContextType {
  folders: FolderConfig[]
  setFolders: React.Dispatch<React.SetStateAction<FolderConfig[]>>
  outputPath: string
  setOutputPath: React.Dispatch<React.SetStateAction<string>>
  previewFolderId: string | null
  setPreviewFolderId: React.Dispatch<React.SetStateAction<string | null>>
}

const ExportContext = createContext<ExportContextType | null>(null)

export function ExportProvider({ children }: { children: ReactNode }) {
  const [folders, setFolders] = useState<FolderConfig[]>([])
  const [outputPath, setOutputPath] = useState('')
  const [previewFolderId, setPreviewFolderId] = useState<string | null>(null)

  return (
    <ExportContext.Provider
      value={{
        folders,
        setFolders,
        outputPath,
        setOutputPath,
        previewFolderId,
        setPreviewFolderId,
      }}
    >
      {children}
    </ExportContext.Provider>
  )
}

export function useExportContext() {
  const context = useContext(ExportContext)
  if (!context) {
    throw new Error('useExportContext must be used within an ExportProvider')
  }
  return context
}

export type { FolderConfig }
