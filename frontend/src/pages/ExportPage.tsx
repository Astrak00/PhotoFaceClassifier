import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { 
  FolderPlus, Trash2, Download, Check, ChevronUp, ChevronRight,
  FolderOpen, AlertCircle, CheckCircle, Users, Loader2
} from 'lucide-react'
import { 
  fetchPersons, 
  browseDirectory, 
  createExportFolders, 
  previewExport,
  getThumbnailUrl,
  isElectron,
  selectDirectoryNative,
  type FolderSpec 
} from '../api'
import { useExportContext, type FolderConfig } from '../contexts/ExportContext'

export default function ExportPage() {
  const { folders, setFolders, outputPath, setOutputPath, previewFolderId, setPreviewFolderId } = useExportContext()
  const [showBrowser, setShowBrowser] = useState(false)

  // Only fetch named persons for export
  const { data: allPersons } = useQuery({
    queryKey: ['persons', false],
    queryFn: () => fetchPersons(false),
  })

  // Filter to only show persons with names
  const persons = allPersons?.filter(p => p.name && p.name.trim() !== '')

  const { data: dirData } = useQuery({
    queryKey: ['browse', outputPath],
    queryFn: () => browseDirectory(outputPath || undefined),
    enabled: showBrowser || !outputPath,
  })

  const { data: preview } = useQuery({
    queryKey: ['exportPreview', previewFolderId, folders],
    queryFn: () => {
      const folder = folders.find(f => f.id === previewFolderId)
      if (!folder || folder.personIds.size === 0) return null
      return previewExport(Array.from(folder.personIds), folder.logic)
    },
    enabled: !!previewFolderId,
  })

  const exportMutation = useMutation({
    mutationFn: createExportFolders,
  })

  const handleBrowseNative = async () => {
    const dir = await selectDirectoryNative()
    if (dir) {
      setOutputPath(dir)
      setShowBrowser(false)
    }
  }

  const addFolder = () => {
    const newFolder: FolderConfig = {
      id: crypto.randomUUID(),
      name: `Export ${folders.length + 1}`,
      personIds: new Set(),
      logic: 'any',
    }
    setFolders([...folders, newFolder])
  }

  const removeFolder = (id: string) => {
    setFolders(folders.filter(f => f.id !== id))
    if (previewFolderId === id) setPreviewFolderId(null)
  }

  const updateFolder = (id: string, updates: Partial<FolderConfig>) => {
    setFolders(folders.map(f => 
      f.id === id ? { ...f, ...updates } : f
    ))
  }

  const togglePerson = (folderId: string, personId: number) => {
    const folder = folders.find(f => f.id === folderId)
    if (!folder) return

    const newPersonIds = new Set(folder.personIds)
    if (newPersonIds.has(personId)) {
      newPersonIds.delete(personId)
    } else {
      newPersonIds.add(personId)
    }
    updateFolder(folderId, { personIds: newPersonIds })
  }

  const handleExport = () => {
    if (!outputPath) return
    if (folders.length === 0) return

    const validFolders = folders.filter(f => f.personIds.size > 0)
    if (validFolders.length === 0) return

    const folderSpecs: FolderSpec[] = validFolders.map(f => ({
      name: f.name,
      person_ids: Array.from(f.personIds),
      logic: f.logic,
    }))

    exportMutation.mutate({
      output_directory: outputPath,
      folders: folderSpecs,
      overwrite: false,
    })
  }

  // Count of unnamed persons
  const unnamedCount = allPersons ? allPersons.filter(p => !p.name || p.name.trim() === '').length : 0

  if (!persons || persons.length === 0) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Export Photos</h1>
          <p className="text-zinc-400 mt-1 text-sm">Create folders with photos grouped by person</p>
        </div>

        <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-12 text-center">
          <div className="w-16 h-16 rounded-2xl bg-amber-500/10 flex items-center justify-center mx-auto mb-5">
            <AlertCircle className="w-8 h-8 text-amber-400" />
          </div>
          <h2 className="text-lg font-semibold text-white mb-2">No Named People</h2>
          <p className="text-zinc-500 max-w-sm mx-auto text-sm mb-4">
            You need to name at least one person before you can export photos.
            Go to the People tab and give names to the people you want to export.
          </p>
          {unnamedCount > 0 && (
            <p className="text-xs text-zinc-600">
              You have {unnamedCount} unnamed {unnamedCount === 1 ? 'person' : 'people'} that can be named.
            </p>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Export Photos</h1>
        <p className="text-zinc-400 mt-1 text-sm">Create folders with photos grouped by person</p>
      </div>

      {/* Success Message */}
      {exportMutation.isSuccess && (
        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-2xl p-5">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
              <CheckCircle className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <h3 className="font-semibold text-emerald-400 mb-1">Export Complete</h3>
              <p className="text-sm text-emerald-300/70">
                Successfully created {exportMutation.data?.results.length} folder(s) with{' '}
                {exportMutation.data?.results.reduce((sum, r) => sum + r.created_count, 0)} symlinks.
              </p>
              <div className="mt-3 space-y-1">
                {exportMutation.data?.results.map((result) => (
                  <div key={result.folder_name} className="text-xs text-emerald-400/50 font-mono">
                    {result.folder_path} ({result.created_count} files)
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Error Message */}
      {exportMutation.isError && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-5">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-xl bg-red-500/20 flex items-center justify-center flex-shrink-0">
              <AlertCircle className="w-5 h-5 text-red-400" />
            </div>
            <div>
              <h3 className="font-semibold text-red-400 mb-1">Export Failed</h3>
              <p className="text-sm text-red-300/70">{exportMutation.error?.message}</p>
            </div>
          </div>
        </div>
      )}

      {/* Output Directory Card */}
      <div className="bg-zinc-900 rounded-2xl border border-zinc-800 overflow-hidden">
        <div className="p-5 border-b border-zinc-800">
          <label htmlFor="output-directory" className="block text-xs font-medium text-zinc-500 uppercase tracking-wider mb-3">
            Output Directory
          </label>
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <FolderOpen className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
              <input
                id="output-directory"
                type="text"
                value={outputPath || dirData?.current_path || ''}
                onChange={(e) => setOutputPath(e.target.value)}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-xl pl-11 pr-4 py-3 text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:border-violet-500/50 transition-all"
                placeholder="Select output directory..."
              />
            </div>
            {isElectron() ? (
              <button
                type="button"
                onClick={handleBrowseNative}
                className="px-4 rounded-xl font-medium text-sm transition-colors border bg-violet-600 border-violet-600 text-white hover:bg-violet-500"
              >
                Browse
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setShowBrowser(!showBrowser)}
                className={`px-4 rounded-xl font-medium text-sm transition-colors border ${
                  showBrowser 
                    ? 'bg-violet-600 border-violet-600 text-white' 
                    : 'bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700'
                }`}
              >
                Browse
              </button>
            )}
          </div>
        </div>

        {showBrowser && dirData && (
          <div className="max-h-48 overflow-y-auto">
            {dirData.parent_path && (
              <button
                type="button"
                onClick={() => setOutputPath(dirData.parent_path!)}
                className="w-full px-5 py-3 text-left hover:bg-zinc-800/50 flex items-center gap-3 border-b border-zinc-800/50 transition-colors"
              >
                <ChevronUp className="w-4 h-4 text-zinc-500" />
                <span className="text-zinc-400">..</span>
              </button>
            )}
            {dirData.entries
              .filter(e => e.is_dir)
              .map((entry) => (
                <button
                  key={entry.path}
                  type="button"
                  onClick={() => setOutputPath(entry.path)}
                  className="w-full px-5 py-3 text-left hover:bg-zinc-800/50 flex items-center gap-3 transition-colors group border-b border-zinc-800/50 last:border-0"
                >
                  <FolderOpen className="w-4 h-4 text-amber-400/70 group-hover:text-amber-400" />
                  <span className="text-zinc-300 group-hover:text-white flex-1">{entry.name}</span>
                  <ChevronRight className="w-4 h-4 text-zinc-600 group-hover:text-zinc-400" />
                </button>
              ))}
          </div>
        )}
      </div>

      {/* Folder Builder */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-medium text-white">Export Folders</h3>
            <p className="text-xs text-zinc-500 mt-0.5">Create folders and assign people to them</p>
          </div>
          <button
            type="button"
            onClick={addFolder}
            className="flex items-center gap-2 px-4 py-2.5 bg-violet-600 hover:bg-violet-500 rounded-xl font-medium text-white text-sm transition-colors"
          >
            <FolderPlus className="w-4 h-4" />
            Add Folder
          </button>
        </div>

        {folders.length === 0 ? (
          <div className="bg-zinc-900 rounded-2xl border-2 border-dashed border-zinc-800 p-10 text-center">
            <FolderPlus className="w-10 h-10 text-zinc-700 mx-auto mb-3" />
            <p className="text-zinc-500 text-sm">
              Click "Add Folder" to create your first export folder
            </p>
          </div>
        ) : (
          folders.map((folder) => (
            <div key={folder.id} className="bg-zinc-900 rounded-2xl border border-zinc-800 overflow-hidden">
              {/* Folder Header */}
              <div className="p-4 flex flex-wrap items-center gap-3 border-b border-zinc-800">
                <input
                  type="text"
                  value={folder.name}
                  onChange={(e) => updateFolder(folder.id, { name: e.target.value })}
                  className="flex-1 min-w-[180px] bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-2.5 text-sm text-white font-medium focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:border-violet-500/50"
                  placeholder="Folder name..."
                />
                <select
                  value={folder.logic}
                  onChange={(e) => updateFolder(folder.id, { logic: e.target.value as 'any' | 'all' })}
                  className="bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-2.5 text-sm text-zinc-300 focus:outline-none focus:ring-2 focus:ring-violet-500/50 appearance-none cursor-pointer"
                >
                  <option value="any">ANY of these people</option>
                  <option value="all">ALL of these people</option>
                </select>
                <button
                  type="button"
                  onClick={() => setPreviewFolderId(previewFolderId === folder.id ? null : folder.id)}
                  className={`px-4 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                    previewFolderId === folder.id
                      ? 'bg-violet-600 text-white'
                      : 'bg-zinc-800 text-zinc-400 hover:text-white border border-zinc-700'
                  }`}
                >
                  Preview
                </button>
                <button
                  type="button"
                  onClick={() => removeFolder(folder.id)}
                  className="p-2.5 text-zinc-600 hover:text-red-400 hover:bg-red-500/10 rounded-xl transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              {/* Person Selection */}
              <div className="p-4">
                <p className="text-xs text-zinc-500 mb-3 flex items-center gap-2">
                  <Users className="w-3.5 h-3.5" />
                  Select people to include ({persons.length} named people available)
                </p>
                <div className="flex flex-wrap gap-2">
                  {persons.map((person) => (
                    <button
                      key={person.id}
                      type="button"
                      onClick={() => togglePerson(folder.id, person.id)}
                      className={`flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-all ${
                        folder.personIds.has(person.id)
                          ? 'bg-violet-600 text-white'
                          : 'bg-zinc-800 text-zinc-400 hover:text-white border border-zinc-700 hover:border-zinc-600'
                      }`}
                    >
                      {folder.personIds.has(person.id) && <Check className="w-3.5 h-3.5" />}
                      {person.thumbnail_path && (
                        <img
                          src={getThumbnailUrl(person.thumbnail_path)}
                          alt=""
                          className="w-5 h-5 rounded-full object-cover"
                        />
                      )}
                      <span>{person.name}</span>
                      <span className="text-xs opacity-60">({person.photo_count})</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Preview */}
              {previewFolderId === folder.id && preview && (
                <div className="p-4 bg-zinc-950/50 border-t border-zinc-800">
                  <div className="flex items-center gap-2 mb-3">
                    <CheckCircle className="w-4 h-4 text-emerald-400" />
                    <span className="text-sm text-zinc-400">
                      <span className="font-medium text-white">{preview.photo_count}</span> photos will be exported
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1.5 max-h-32 overflow-y-auto">
                    {preview.photos.slice(0, 30).map((photo) => (
                      <div
                        key={photo.id}
                        className="px-2.5 py-1 bg-zinc-800 rounded-lg text-xs text-zinc-400 font-mono"
                      >
                        {photo.filename}
                      </div>
                    ))}
                    {preview.photo_count > 30 && (
                      <div className="px-2.5 py-1 text-xs text-zinc-600">
                        +{preview.photo_count - 30} more files
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Export Button */}
      {folders.length > 0 && (
        <div className="flex justify-end">
          <button
            type="button"
            onClick={handleExport}
            disabled={exportMutation.isPending || !outputPath || folders.every(f => f.personIds.size === 0)}
            className="flex items-center gap-2.5 px-6 py-3.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-700 disabled:cursor-not-allowed rounded-xl font-medium text-white text-sm transition-colors"
          >
            {exportMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Creating Folders...
              </>
            ) : (
              <>
                <Download className="w-4 h-4" />
                Create Export Folders
              </>
            )}
          </button>
        </div>
      )}

      {/* Unnamed People Hint */}
      {unnamedCount > 0 && (
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 text-center">
          <p className="text-xs text-zinc-600">
            {unnamedCount} unnamed {unnamedCount === 1 ? 'person is' : 'people are'} hidden from export.
            Name them in the People tab to include them here.
          </p>
        </div>
      )}
    </div>
  )
}
