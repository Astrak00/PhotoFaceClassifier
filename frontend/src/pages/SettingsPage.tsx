import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Settings, Cpu, Users, Loader2, CheckCircle, AlertCircle, RefreshCw } from 'lucide-react'
import { getConfig, updateConfig } from '../api'

export default function SettingsPage() {
  const queryClient = useQueryClient()
  const [localDevice, setLocalDevice] = useState<string>('auto')
  const [localMinFaces, setLocalMinFaces] = useState<number>(3)
  const [hasChanges, setHasChanges] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)

  // Fetch config
  const { data: config, isLoading, error, refetch } = useQuery({
    queryKey: ['config'],
    queryFn: getConfig,
  })

  // Initialize local state when config loads
  useEffect(() => {
    if (config) {
      setLocalDevice(config.device)
      setLocalMinFaces(config.min_faces_per_person)
      setHasChanges(false)
    }
  }, [config])

  // Check for changes
  useEffect(() => {
    if (config) {
      const changed = localDevice !== config.device || localMinFaces !== config.min_faces_per_person
      setHasChanges(changed)
      if (changed) setSaveSuccess(false)
    }
  }, [localDevice, localMinFaces, config])

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: () => updateConfig({
      device: localDevice,
      min_faces_per_person: localMinFaces,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      setSaveSuccess(true)
      setHasChanges(false)
      setTimeout(() => setSaveSuccess(false), 3000)
    },
  })

  const deviceLabels: Record<string, string> = {
    auto: 'Auto (Best Available)',
    mps: 'Apple Silicon GPU (MPS)',
    cuda: 'NVIDIA GPU (CUDA)',
    cpu: 'CPU Only',
  }

  const deviceDescriptions: Record<string, string> = {
    auto: 'Automatically select the best available device',
    mps: 'Use Apple Silicon GPU acceleration',
    cuda: 'Use NVIDIA GPU acceleration',
    cpu: 'Run on CPU (slower but always available)',
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-violet-400" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Settings</h1>
          <p className="text-zinc-400 mt-1 text-sm">Configure face detection and clustering parameters</p>
        </div>
        <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-6 text-center">
          <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-3" />
          <p className="text-red-300 mb-4">Failed to load settings</p>
          <button
            type="button"
            onClick={() => refetch()}
            className="px-4 py-2 rounded-xl bg-red-500/20 hover:bg-red-500/30 text-red-300 text-sm font-medium transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Settings</h1>
        <p className="text-zinc-400 mt-1 text-sm">Configure face detection and clustering parameters</p>
      </div>

      {/* Device Selection Card */}
      <div className="bg-zinc-900 rounded-2xl border border-zinc-800 overflow-hidden">
        <div className="p-5 border-b border-zinc-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center">
              <Cpu className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <h3 className="font-semibold text-white">Compute Device</h3>
              <p className="text-xs text-zinc-500">Select hardware for face embedding computation</p>
            </div>
          </div>
        </div>

        <div className="p-5">
          {/* Current Device Info */}
          {config?.current_device && (
            <div className="mb-5 px-4 py-3 bg-zinc-800 rounded-xl flex items-center justify-between">
              <span className="text-sm text-zinc-400">Currently using:</span>
              <span className="text-sm font-medium text-emerald-400">{config.current_device.device_name}</span>
            </div>
          )}

          {/* Device Options */}
          <fieldset>
            <legend className="sr-only">Compute Device</legend>
            <div className="space-y-2">
              {config?.available_devices.map((device) => (
                <label
                  key={device}
                  className={`flex items-center gap-4 p-4 rounded-xl cursor-pointer transition-all border ${
                    localDevice === device
                      ? 'border-violet-500/50 bg-violet-500/10'
                      : 'border-zinc-800 hover:border-zinc-700 hover:bg-zinc-800/50'
                  }`}
                >
                  <input
                    type="radio"
                    name="device"
                    value={device}
                    checked={localDevice === device}
                    onChange={(e) => setLocalDevice(e.target.value)}
                    className="sr-only"
                  />
                  <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all ${
                    localDevice === device
                      ? 'border-violet-500 bg-violet-500'
                      : 'border-zinc-600'
                  }`}>
                    {localDevice === device && (
                      <div className="w-2 h-2 rounded-full bg-white" />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="font-medium text-white text-sm">{deviceLabels[device] || device.toUpperCase()}</div>
                    <div className="text-xs text-zinc-500">{deviceDescriptions[device]}</div>
                  </div>
                </label>
              ))}
            </div>
          </fieldset>

          <p className="mt-4 text-xs text-zinc-600">
            Note: Face detection (MTCNN) uses MPS when available with image size normalization for stability.
          </p>
        </div>
      </div>

      {/* Clustering Settings Card */}
      <div className="bg-zinc-900 rounded-2xl border border-zinc-800 overflow-hidden">
        <div className="p-5 border-b border-zinc-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-violet-500/10 flex items-center justify-center">
              <Users className="w-5 h-5 text-violet-400" />
            </div>
            <div>
              <h3 className="font-semibold text-white">Clustering Settings</h3>
              <p className="text-xs text-zinc-500">Configure how faces are grouped into people</p>
            </div>
          </div>
        </div>

        <div className="p-5">
          {/* Min Faces Slider */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <label htmlFor="min-faces-slider" className="text-sm font-medium text-zinc-300">
                Minimum faces per person
              </label>
              <span className="text-xl font-bold text-white tabular-nums">{localMinFaces}</span>
            </div>

            <input
              id="min-faces-slider"
              type="range"
              min="1"
              max="10"
              value={localMinFaces}
              onChange={(e) => setLocalMinFaces(parseInt(e.target.value))}
              className="w-full h-2 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-violet-500"
            />

            <div className="flex justify-between text-xs text-zinc-600">
              <span>1 (more people)</span>
              <span>10 (fewer people)</span>
            </div>

            <p className="text-xs text-zinc-500 mt-2">
              People with fewer than {localMinFaces} face{localMinFaces !== 1 ? 's' : ''} detected will not be shown as identified persons.
              Lower values will detect more people but may include false matches.
            </p>
          </div>
        </div>
      </div>

      {/* Save Button Bar */}
      <div className="flex items-center justify-between bg-zinc-900 rounded-2xl border border-zinc-800 p-5">
        <div className="flex items-center gap-3">
          {saveSuccess && (
            <>
              <CheckCircle className="w-5 h-5 text-emerald-400" />
              <span className="text-emerald-400 text-sm font-medium">Settings saved successfully</span>
            </>
          )}
          {hasChanges && !saveSuccess && (
            <>
              <RefreshCw className="w-5 h-5 text-amber-400" />
              <span className="text-amber-400 text-sm font-medium">You have unsaved changes</span>
            </>
          )}
        </div>

        <button
          type="button"
          onClick={() => saveMutation.mutate()}
          disabled={!hasChanges || saveMutation.isPending}
          className={`flex items-center gap-2 px-6 py-3 rounded-xl font-medium text-sm transition-colors ${
            hasChanges
              ? 'bg-violet-600 hover:bg-violet-500 text-white'
              : 'bg-zinc-800 text-zinc-600 cursor-not-allowed'
          }`}
        >
          {saveMutation.isPending ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <Settings className="w-4 h-4" />
              Save Settings
            </>
          )}
        </button>
      </div>

      {/* Error Message */}
      {saveMutation.isError && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
          <p className="text-red-300 text-sm">Failed to save settings. Please try again.</p>
        </div>
      )}
    </div>
  )
}
