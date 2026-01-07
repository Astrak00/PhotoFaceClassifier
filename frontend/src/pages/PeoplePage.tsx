import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  Check, Merge, X, EyeOff, Eye, ChevronDown, ChevronUp,
  Edit3, Save, Users, Loader2
} from 'lucide-react'
import { 
  fetchPersons, fetchPerson, updatePerson, hidePerson, mergePersons, 
  getThumbnailUrl, type PersonSummary
} from '../api'

export default function PeoplePage() {
  const queryClient = useQueryClient()
  const [selectedPersons, setSelectedPersons] = useState<Set<number>>(new Set())
  const [editingPerson, setEditingPerson] = useState<number | null>(null)
  const [editName, setEditName] = useState('')
  const [expandedPerson, setExpandedPerson] = useState<number | null>(null)
  const [showHidden, setShowHidden] = useState(false)

  const { data: persons, isLoading } = useQuery({
    queryKey: ['persons', showHidden],
    queryFn: () => fetchPersons(showHidden),
  })

  const { data: expandedPersonData, isLoading: isLoadingExpanded } = useQuery({
    queryKey: ['person', expandedPerson],
    queryFn: () => fetchPerson(expandedPerson!),
    enabled: !!expandedPerson,
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) => updatePerson(id, { name }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['persons'] })
      setEditingPerson(null)
    },
  })

  const hideMutation = useMutation({
    mutationFn: hidePerson,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['persons'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
    },
  })

  const unhideMutation = useMutation({
    mutationFn: (id: number) => updatePerson(id, { is_ignored: false }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['persons'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
    },
  })

  const mergeMutation = useMutation({
    mutationFn: ({ keepId, mergeIds }: { keepId: number; mergeIds: number[] }) => 
      mergePersons(keepId, mergeIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['persons'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      setSelectedPersons(new Set())
    },
  })

  const handleSelectPerson = (id: number, e: React.MouseEvent) => {
    e.stopPropagation()
    const newSelected = new Set(selectedPersons)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedPersons(newSelected)
  }

  const handleStartEdit = (person: PersonSummary, e: React.MouseEvent) => {
    e.stopPropagation()
    setEditingPerson(person.id)
    setEditName(person.name || '')
  }

  const handleSaveName = (id: number, e: React.MouseEvent) => {
    e.stopPropagation()
    updateMutation.mutate({ id, name: editName })
  }

  const handleMerge = () => {
    if (selectedPersons.size < 2) return
    const ids = Array.from(selectedPersons)
    const keepId = ids[0]
    const mergeIds = ids.slice(1)
    mergeMutation.mutate({ keepId, mergeIds })
  }

  const handleExpand = (personId: number) => {
    setExpandedPerson(expandedPerson === personId ? null : personId)
  }

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <Loader2 className="w-8 h-8 text-violet-400 animate-spin" />
        <p className="text-zinc-400">Loading people...</p>
      </div>
    )
  }

  if (!persons || persons.length === 0) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">People</h1>
          <p className="text-zinc-400 mt-1 text-sm">Manage detected and identified people</p>
        </div>
        <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-12 text-center">
          <div className="w-16 h-16 rounded-2xl bg-zinc-800 flex items-center justify-center mx-auto mb-5">
            <Users className="w-8 h-8 text-zinc-600" />
          </div>
          <h2 className="text-lg font-semibold text-white mb-2">No People Found</h2>
          <p className="text-zinc-500 max-w-sm mx-auto text-sm">
            Scan a folder with photos to detect and group faces automatically.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">People</h1>
          <p className="text-zinc-400 mt-1 text-sm">{persons.length} people detected</p>
        </div>
        
        <button
          type="button"
          onClick={() => setShowHidden(!showHidden)}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors ${
            showHidden 
              ? 'bg-zinc-800 text-white border border-zinc-700' 
              : 'bg-zinc-900 text-zinc-400 hover:text-white border border-zinc-800 hover:border-zinc-700'
          }`}
        >
          {showHidden ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
          {showHidden ? 'Showing Hidden' : 'Show Hidden'}
        </button>
      </div>

      {/* Selection Actions Bar */}
      {selectedPersons.size > 0 && (
        <div className="sticky top-4 z-40 bg-zinc-900/95 backdrop-blur-sm rounded-2xl border border-zinc-800 p-4 shadow-xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-sm text-zinc-400">
                <span className="font-semibold text-white">{selectedPersons.size}</span> selected
              </span>
              <button
                type="button"
                onClick={() => setSelectedPersons(new Set())}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors"
              >
                <X className="w-3.5 h-3.5" />
                Clear
              </button>
            </div>
            {selectedPersons.size >= 2 && (
              <button
                type="button"
                onClick={handleMerge}
                disabled={mergeMutation.isPending}
                className="flex items-center gap-2 px-5 py-2.5 bg-violet-600 hover:bg-violet-500 rounded-xl text-sm font-medium text-white transition-colors disabled:opacity-50"
              >
                <Merge className="w-4 h-4" />
                Merge Selected
              </button>
            )}
          </div>
        </div>
      )}

      {/* People Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {persons.map((person) => {
          const isExpanded = expandedPerson === person.id
          const isSelected = selectedPersons.has(person.id)
          
          return (
            <div
              key={person.id}
              className={`bg-zinc-900 rounded-2xl border overflow-hidden transition-all duration-200 ${
                isSelected
                  ? 'border-violet-500 ring-2 ring-violet-500/20'
                  : 'border-zinc-800 hover:border-zinc-700'
              }`}
            >
              {/* Card Header */}
              <div className="p-4 flex items-center justify-between">
                <button
                  type="button"
                  onClick={(e) => handleSelectPerson(person.id, e)}
                  className={`w-6 h-6 rounded-lg flex items-center justify-center transition-colors ${
                    isSelected
                      ? 'bg-violet-500 text-white'
                      : 'bg-zinc-800 text-zinc-600 hover:bg-zinc-700 hover:text-zinc-400'
                  }`}
                >
                  {isSelected && <Check className="w-4 h-4" />}
                </button>
                
                <div className="flex items-center gap-2">
                  <span className="text-xs text-zinc-500 bg-zinc-800 px-2.5 py-1 rounded-lg">
                    {person.photo_count} photos
                  </span>
                  {!showHidden && (
                    <button
                      type="button"
                      onClick={() => hideMutation.mutate(person.id)}
                      className="p-1.5 rounded-lg text-zinc-600 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                      title="Hide this person"
                    >
                      <EyeOff className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>

              {/* Face Thumbnails Grid - Clickable */}
              <button
                type="button"
                onClick={() => handleExpand(person.id)}
                className="w-full relative group"
              >
                <div className="grid grid-cols-3 gap-0.5 mx-4 rounded-xl overflow-hidden">
                  {person.sample_thumbnails.slice(0, 6).map((thumb, i) => (
                    <div key={`${person.id}-thumb-${i}`} className="aspect-square bg-zinc-950">
                      <img
                        src={getThumbnailUrl(thumb)}
                        alt=""
                        className="w-full h-full object-cover"
                        loading="lazy"
                      />
                    </div>
                  ))}
                  {person.sample_thumbnails.length < 6 &&
                    Array.from({ length: 6 - person.sample_thumbnails.length }).map((_, i) => (
                      <div key={`${person.id}-empty-${i}`} className="aspect-square bg-zinc-950" />
                    ))}
                </div>
                
                {/* Expand Indicator */}
                <div className="absolute inset-0 bg-gradient-to-t from-zinc-950/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-center pb-3">
                  <span className="flex items-center gap-1 text-xs text-white/80">
                    {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    {isExpanded ? 'Collapse' : 'View all photos'}
                  </span>
                </div>
              </button>

              {/* Name Section */}
              <div className="p-4">
                {editingPerson === person.id ? (
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      onClick={(e) => e.stopPropagation()}
                      className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:border-violet-500/50"
                      placeholder="Enter name..."

                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleSaveName(person.id, e as unknown as React.MouseEvent)
                        if (e.key === 'Escape') setEditingPerson(null)
                      }}
                    />
                    <button
                      type="button"
                      onClick={(e) => handleSaveName(person.id, e)}
                      className="p-2 bg-emerald-500 hover:bg-emerald-400 rounded-lg transition-colors"
                    >
                      <Save className="w-4 h-4 text-white" />
                    </button>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); setEditingPerson(null) }}
                      className="p-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors"
                    >
                      <X className="w-4 h-4 text-zinc-400" />
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={(e) => handleStartEdit(person, e)}
                    className="w-full flex items-center justify-between group"
                  >
                    <span className={`font-medium ${person.name ? 'text-white' : 'text-zinc-600 italic'}`}>
                      {person.name || `Unknown Person`}
                    </span>
                    <Edit3 className="w-4 h-4 text-zinc-700 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </button>
                )}
              </div>

              {/* Expanded View - All Faces */}
              {isExpanded && (
                <div className="border-t border-zinc-800 p-4 bg-zinc-950/50">
                  {isLoadingExpanded ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="w-6 h-6 text-violet-400 animate-spin" />
                    </div>
                  ) : expandedPersonData ? (
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
                          All {expandedPersonData.faces.length} appearances
                        </span>
                      </div>
                      <div className="grid grid-cols-4 gap-2 max-h-64 overflow-y-auto pr-1">
                        {expandedPersonData.faces.map((face) => (
                          <div key={face.id} className="group relative">
                            <div className="aspect-square rounded-lg overflow-hidden bg-zinc-900">
                              <img
                                src={getThumbnailUrl(face.thumbnail_path)}
                                alt=""
                                className="w-full h-full object-cover"
                                loading="lazy"
                              />
                            </div>
                            <div className="absolute inset-0 bg-black/70 opacity-0 group-hover:opacity-100 transition-opacity rounded-lg flex items-end p-1.5">
                              <span className="text-[10px] text-white/90 truncate w-full font-mono">
                                {face.photo.filename}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </div>
              )}

              {/* Unhide button for hidden persons */}
              {showHidden && (
                <div className="px-4 pb-4">
                  <button
                    type="button"
                    onClick={() => unhideMutation.mutate(person.id)}
                    className="w-full flex items-center justify-center gap-2 py-2.5 bg-zinc-800 hover:bg-zinc-700 rounded-xl text-sm text-zinc-300 transition-colors"
                  >
                    <Eye className="w-4 h-4" />
                    Unhide Person
                  </button>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Merge Instructions */}
      {selectedPersons.size === 1 && (
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 text-center">
          <p className="text-zinc-500 text-sm">
            Select another person to merge them together
          </p>
        </div>
      )}
    </div>
  )
}
