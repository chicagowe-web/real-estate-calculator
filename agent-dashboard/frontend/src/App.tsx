import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Sidebar } from './components/Sidebar'
import { Dashboard } from './pages/Dashboard'
import { Agents } from './pages/Agents'
import { Devices } from './pages/Devices'
import { Alerts } from './pages/Alerts'
import { Deployments } from './pages/Deployments'
import { GPU } from './pages/GPU'
import { Settings } from './pages/Settings'

export function App() {
  return (
    <Router>
      <div className="flex h-screen bg-slate-950 text-slate-50">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/agents" element={<Agents />} />
            <Route path="/devices" element={<Devices />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/deployments" element={<Deployments />} />
            <Route path="/gpu" element={<GPU />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}
