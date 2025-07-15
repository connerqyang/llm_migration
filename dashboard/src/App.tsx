import React, { useState } from 'react'
import ComponentsView from './components/ComponentsView'
import MigrationsView from './components/MigrationsView'

interface Tab {
  id: string
  label: string
  icon: string
}

function App(): JSX.Element {
  const [activeTab, setActiveTab] = useState<string>('components')

  const tabs: Tab[] = [
    { id: 'components', label: 'Components', icon: '🧩' },
    { id: 'migrations', label: 'Migrations', icon: '🔄' },
    { id: 'analytics', label: 'Analytics', icon: '📊' }
  ]

  const renderContent = () => {
    switch (activeTab) {
      case 'components':
        return <ComponentsView />
      case 'migrations':
        return <MigrationsView />
      case 'analytics':
        return <AnalyticsView />
      default:
        return <ComponentsView />
    }
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-gray-900">
                🚀 LLM Migration Dashboard
              </h1>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2 bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span>API Connected</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        {renderContent()}
      </main>
    </div>
  )
}

// Analytics View
function AnalyticsView(): JSX.Element {
  return (
    <div className="space-y-6">
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Analytics & Metrics</h2>
        <p className="text-gray-600">Analytics dashboard will be implemented here.</p>
      </div>
    </div>
  )
}

export default App