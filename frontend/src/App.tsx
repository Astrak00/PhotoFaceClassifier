import { Routes, Route, Link, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { 
  Scan, Users, FolderOutput, Settings, 
  Images, Focus, UserCircle, Zap
} from 'lucide-react'
import ScanPage from './pages/ScanPage'
import PeoplePage from './pages/PeoplePage'
import ExportPage from './pages/ExportPage'
import SettingsPage from './pages/SettingsPage'
import { fetchStats } from './api'

function App() {
  const location = useLocation()
  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: fetchStats,
    refetchInterval: 5000,
  })

  const navItems = [
    { path: '/', icon: Scan, label: 'Scan' },
    { path: '/people', icon: Users, label: 'People' },
    { path: '/export', icon: FolderOutput, label: 'Export' },
    { path: '/settings', icon: Settings, label: 'Settings' },
  ]

  return (
    <div className="min-h-screen bg-zinc-950 flex">
      {/* Sidebar */}
      <aside className="w-64 border-r border-zinc-800 flex flex-col fixed h-full bg-zinc-950/80 backdrop-blur-xl z-50">
        {/* Logo */}
        <div className="p-6 border-b border-zinc-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center shadow-lg shadow-violet-500/20">
              <Focus className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-semibold text-white tracking-tight">FaceSort</h1>
              <p className="text-[11px] text-zinc-500 font-medium">Photo Organizer</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map(({ path, icon: Icon, label }) => {
            const isActive = location.pathname === path
            return (
              <Link
                key={path}
                to={path}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl font-medium text-sm transition-all duration-200 group ${
                  isActive
                    ? 'bg-zinc-800 text-white'
                    : 'text-zinc-400 hover:text-white hover:bg-zinc-800/50'
                }`}
              >
                <Icon className={`w-[18px] h-[18px] transition-colors ${
                  isActive ? 'text-violet-400' : 'text-zinc-500 group-hover:text-zinc-300'
                }`} />
                {label}
                {isActive && (
                  <div className="ml-auto w-1.5 h-1.5 rounded-full bg-violet-400" />
                )}
              </Link>
            )
          })}
        </nav>

        {/* Stats */}
        {stats && (
          <div className="p-4 border-t border-zinc-800">
            <div className="bg-zinc-900 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Zap className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-xs font-medium text-zinc-400">Device</span>
                </div>
                <span className="text-xs font-semibold text-emerald-400 uppercase">{stats.device}</span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1 mb-0.5">
                    <Images className="w-3 h-3 text-blue-400" />
                    <span className="text-sm font-bold text-white">{stats.total_photos}</span>
                  </div>
                  <span className="text-[10px] text-zinc-500">Photos</span>
                </div>
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1 mb-0.5">
                    <Focus className="w-3 h-3 text-amber-400" />
                    <span className="text-sm font-bold text-white">{stats.total_faces}</span>
                  </div>
                  <span className="text-[10px] text-zinc-500">Faces</span>
                </div>
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1 mb-0.5">
                    <UserCircle className="w-3 h-3 text-violet-400" />
                    <span className="text-sm font-bold text-white">{stats.total_persons}</span>
                  </div>
                  <span className="text-[10px] text-zinc-500">People</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </aside>

      {/* Main Content */}
      <main className="flex-1 ml-64">
        <div className="max-w-6xl mx-auto p-8">
          <Routes>
            <Route path="/" element={<ScanPage />} />
            <Route path="/people" element={<PeoplePage />} />
            <Route path="/export" element={<ExportPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </div>
      </main>
    </div>
  )
}

export default App
