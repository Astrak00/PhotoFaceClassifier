import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  Folder, ChevronUp, ChevronRight, Play, Loader2, CheckCircle2, 
  XCircle, Trash2, AlertTriangle, Images, Users, Sparkles, RotateCcw
} from 'lucide-react'
import { browseDirectory, startScan, getLatestScan, resetDatabase, type ScanProgress } from '../api'

export default function ScanPage() {
  const queryClient = useQueryClient()
  const [selectedPath, setSelectedPath] = useState<string>('')
  const [recursive, setRecursive] = useState(true)
  const [useThumbnails, setUseThumbnails] = useState(true)
  const [currentScanId, setCurrentScanId] = useState<number | null>(null)
  const [showResetConfirm, setShowResetConfirm] = useState(false)

  const { data: dirData, isLoading: isDirLoading } = useQuery({
    queryKey: ['browse', selectedPath],
    queryFn: () => browseDirectory(selectedPath || undefined),
  })

  const { data: latestScan } = useQuery({
    queryKey: ['latestScan'],
    queryFn: getLatestScan,
    retry: false,
  })

  const { data: scanProgress } = useQuery({
    queryKey: ['scanProgress', currentScanId],
    queryFn: () => getLatestScan(),
    enabled: !!currentScanId,
    refetchInterval: (query) => {
      const data = query.state.data as ScanProgress | undefined
      if (data?.status === 'running') return 500
      return false
    },
  })

  useEffect(() => {
    if (latestScan && latestScan.status === 'running') {
      setCurrentScanId(latestScan.scan_id)
    }
  }, [latestScan])

  const scanMutation = useMutation({
    mutationFn: startScan,
    onSuccess: (data) => {
      setCurrentScanId(data.scan_id)
      queryClient.invalidateQueries({ queryKey: ['stats'] })
    },
  })

  const resetMutation = useMutation({
    mutationFn: resetDatabase,
    onSuccess: () => {
      queryClient.invalidateQueries()
      setShowResetConfirm(false)
      setCurrentScanId(null)
    },
  })

  const handleStartScan = () => {
    if (!selectedPath) return
    scanMutation.mutate({
      directory: selectedPath,
      recursive,
      use_thumbnails: useThumbnails,
    })
  }

  const activeScan = currentScanId ? (scanProgress || latestScan) : null
  const isScanning = scanMutation.isPending || (activeScan?.status === 'running')
  const progress = activeScan?.total_photos 
    ? Math.round((activeScan.processed_photos / activeScan.total_photos) * 100)
    : 0

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Scan Photos</h1>
          <p className="text-zinc-400 mt-1 text-sm">Select a folder to detect and identify faces</p>
        </div>
        <button
          type="button"
          onClick={() => setShowResetConfirm(true)}
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-zinc-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
        >
          <RotateCcw className="w-4 h-4" />
          Reset Data
        </button>
      </div>

      {/* Reset Modal */}
      {showResetConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="bg-zinc-900 rounded-2xl p-6 max-w-md w-full mx-4 border border-zinc-800 shadow-2xl">
            <div className="flex items-center gap-4 mb-4">
              <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-red-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">Reset All Data?</h3>
                <p className="text-sm text-zinc-500">This cannot be undone</p>
              </div>
            </div>
            <p className="text-zinc-400 text-sm mb-6">
              All scanned photos, detected faces, and identified people will be deleted. Your original files are safe.
            </p>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setShowResetConfirm(false)}
                className="flex-1 px-4 py-2.5 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-white text-sm font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => resetMutation.mutate()}
                disabled={resetMutation.isPending}
                className="flex-1 px-4 py-2.5 rounded-xl bg-red-500 hover:bg-red-600 text-white text-sm font-medium transition-colors disabled:opacity-50"
              >
                {resetMutation.isPending ? 'Resetting...' : 'Reset Everything'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Directory Browser */}
      <div className="bg-zinc-900 rounded-2xl border border-zinc-800 overflow-hidden">
        {/* Path Input */}
        <div className="p-5 border-b border-zinc-800">
          <label className="block text-xs font-medium text-zinc-500 uppercase tracking-wider mb-3">
            Directory Path
          </label>
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <Folder className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
              <input
                type="text"
                value={selectedPath || dirData?.current_path || ''}
                onChange={(e) => setSelectedPath(e.target.value)}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-xl pl-11 pr-4 py-3 text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:border-violet-500/50 transition-all"
                placeholder="Enter or browse to select a folder..."
              />
            </div>
            {dirData?.parent_path && (
              <button
                type="button"
                onClick={() => setSelectedPath(dirData.parent_path!)}
                className="px-4 bg-zinc-800 hover:bg-zinc-700 rounded-xl transition-colors border border-zinc-700"
                title="Parent directory"
              >
                <ChevronUp className="w-4 h-4 text-zinc-400" />
              </button>
            )}
          </div>
        </div>

        {/* Directory List */}
        <div className="max-h-64 overflow-y-auto">
          {isDirLoading ? (
            <div className="p-8 text-center">
              <Loader2 className="w-5 h-5 animate-spin text-zinc-500 mx-auto" />
            </div>
          ) : (
            <div>
              {dirData?.entries
                .filter(e => e.is_dir)
                .map((entry) => (
                  <button
                    key={entry.path}
                    type="button"
                    onClick={() => setSelectedPath(entry.path)}
                    className="w-full px-5 py-3 text-left hover:bg-zinc-800/50 flex items-center gap-3 transition-colors group border-b border-zinc-800/50 last:border-0"
                  >
                    <Folder className="w-4 h-4 text-amber-400/70 group-hover:text-amber-400" />
                    <span className="text-sm text-zinc-300 group-hover:text-white flex-1">{entry.name}</span>
                    <ChevronRight className="w-4 h-4 text-zinc-600 group-hover:text-zinc-400" />
                  </button>
                ))}
              {dirData?.entries.filter(e => e.is_dir).length === 0 && (
                <div className="p-8 text-center text-zinc-500 text-sm">
                  No subdirectories
                </div>
              )}
            </div>
          )}
        </div>

        {/* Options & Start */}
        <div className="p-5 bg-zinc-800/30 border-t border-zinc-800">
          <div className="flex items-center gap-6 mb-4">
            <label className="flex items-center gap-2.5 cursor-pointer group">
              <input
                type="checkbox"
                checked={recursive}
                onChange={(e) => setRecursive(e.target.checked)}
                className="w-4 h-4 rounded border-zinc-600 bg-zinc-800 text-violet-500 focus:ring-violet-500/50 focus:ring-offset-0"
              />
              <span className="text-sm text-zinc-400 group-hover:text-zinc-300">Include subfolders</span>
            </label>
            <label className="flex items-center gap-2.5 cursor-pointer group">
              <input
                type="checkbox"
                checked={useThumbnails}
                onChange={(e) => setUseThumbnails(e.target.checked)}
                className="w-4 h-4 rounded border-zinc-600 bg-zinc-800 text-violet-500 focus:ring-violet-500/50 focus:ring-offset-0"
              />
              <span className="text-sm text-zinc-400 group-hover:text-zinc-300">Use thumbnails (faster)</span>
            </label>
          </div>

          <button
            type="button"
            onClick={handleStartScan}
            disabled={!selectedPath || isScanning}
            className="w-full flex items-center justify-center gap-2.5 px-6 py-3.5 bg-violet-600 hover:bg-violet-500 disabled:bg-zinc-700 disabled:cursor-not-allowed rounded-xl font-medium text-white text-sm transition-colors"
          >
            {isScanning ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Scanning...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Start Scan
              </>
            )}
          </button>
        </div>
      </div>

      {/* Active Scan Progress */}
      {activeScan && (
        <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-6">
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-3">
              {activeScan.status === 'completed' && (
                <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                </div>
              )}
              {activeScan.status === 'failed' && (
                <div className="w-10 h-10 rounded-xl bg-red-500/10 flex items-center justify-center">
                  <XCircle className="w-5 h-5 text-red-400" />
                </div>
              )}
              {activeScan.status === 'running' && (
                <div className="w-10 h-10 rounded-xl bg-violet-500/10 flex items-center justify-center">
                  <Loader2 className="w-5 h-5 text-violet-400 animate-spin" />
                </div>
              )}
              <div>
                <h3 className="font-medium text-white">
                  {activeScan.status === 'completed' ? 'Scan Complete' : 
                   activeScan.status === 'failed' ? 'Scan Failed' : 'Scanning...'}
                </h3>
                {activeScan.current_file && (
                  <p className="text-xs text-zinc-500 font-mono truncate max-w-md">{activeScan.current_file}</p>
                )}
              </div>
            </div>
            <span className="text-2xl font-bold text-white tabular-nums">{progress}%</span>
          </div>

          {/* Progress Bar */}
          <div className="h-2 bg-zinc-800 rounded-full overflow-hidden mb-5">
            <div
              className={`h-full rounded-full transition-all duration-300 ${
                activeScan.status === 'completed' ? 'bg-emerald-500' :
                activeScan.status === 'failed' ? 'bg-red-500' : 'bg-violet-500'
              }`}
              style={{ width: `${progress}%` }}
            />
          </div>

          {/* Stats */}
          <div className="grid grid-cols-4 gap-3">
            <div className="bg-zinc-800/50 rounded-xl p-3 text-center">
              <div className="flex items-center justify-center gap-1.5 mb-1">
                <Images className="w-3.5 h-3.5 text-blue-400" />
                <span className="text-lg font-bold text-white tabular-nums">{activeScan.processed_photos}</span>
              </div>
              <span className="text-[11px] text-zinc-500">of {activeScan.total_photos}</span>
            </div>
            <div className="bg-zinc-800/50 rounded-xl p-3 text-center">
              <div className="flex items-center justify-center gap-1.5 mb-1">
                <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                <span className="text-lg font-bold text-white tabular-nums">{activeScan.total_faces}</span>
              </div>
              <span className="text-[11px] text-zinc-500">Faces</span>
            </div>
            <div className="bg-zinc-800/50 rounded-xl p-3 text-center">
              <div className="flex items-center justify-center gap-1.5 mb-1">
                <Users className="w-3.5 h-3.5 text-violet-400" />
                <span className="text-lg font-bold text-white tabular-nums">{activeScan.total_persons}</span>
              </div>
              <span className="text-[11px] text-zinc-500">People</span>
            </div>
            <div className="bg-zinc-800/50 rounded-xl p-3 text-center">
              <span className="text-lg font-bold text-white tabular-nums">{progress}%</span>
              <span className="text-[11px] text-zinc-500 block">Complete</span>
            </div>
          </div>

          {activeScan.error_message && (
            <div className="mt-4 p-4 bg-red-500/10 border border-red-500/20 rounded-xl">
              <p className="text-sm text-red-400">{activeScan.error_message}</p>
            </div>
          )}
        </div>
      )}

      {/* Last Scan Summary */}
      {!activeScan && latestScan && latestScan.status !== 'running' && (
        <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
              latestScan.status === 'completed' ? 'bg-emerald-500/10' : 'bg-red-500/10'
            }`}>
              {latestScan.status === 'completed' 
                ? <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                : <XCircle className="w-5 h-5 text-red-400" />
              }
            </div>
            <div>
              <h3 className="font-medium text-white">Previous Scan</h3>
              <p className="text-xs text-zinc-500 capitalize">{latestScan.status}</p>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-zinc-800/50 rounded-xl p-3 text-center">
              <span className="text-lg font-bold text-white">{latestScan.total_photos}</span>
              <span className="text-[11px] text-zinc-500 block">Photos</span>
            </div>
            <div className="bg-zinc-800/50 rounded-xl p-3 text-center">
              <span className="text-lg font-bold text-white">{latestScan.total_faces}</span>
              <span className="text-[11px] text-zinc-500 block">Faces</span>
            </div>
            <div className="bg-zinc-800/50 rounded-xl p-3 text-center">
              <span className="text-lg font-bold text-white">{latestScan.total_persons}</span>
              <span className="text-[11px] text-zinc-500 block">People</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
