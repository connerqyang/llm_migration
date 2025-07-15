import React, { useState, useEffect } from 'react'
import { api } from '../utils/api'
import { Migration, MigrationDetails } from '../types/api'

interface Filters {
  component_name: string
  status: string
}

export default function MigrationsView(): JSX.Element {
  const [migrations, setMigrations] = useState<Migration[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedMigration, setSelectedMigration] = useState<MigrationDetails | null>(null)
  const [filters, setFilters] = useState<Filters>({
    component_name: '',
    status: ''
  })

  useEffect(() => {
    fetchMigrations()
  }, [filters])

  const fetchMigrations = async () => {
    try {
      setLoading(true)
      const queryParams = {}
      if (filters.component_name) queryParams.component_name = filters.component_name
      if (filters.status) queryParams.status = filters.status
      
      const data = await api.getMigrations(queryParams)
      setMigrations(data.migrations || [])
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const fetchMigrationDetails = async (migrationId: string) => {
    try {
      const details = await api.getMigrationDetails(migrationId)
      setSelectedMigration(details)
    } catch (err) {
      console.error('Failed to fetch migration details:', err)
    }
  }

  const getStatusColor = (status: string | undefined) => {
    switch (status?.toLowerCase()) {
      case 'completed':
        return 'bg-green-100 text-green-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      case 'running':
      case 'started':
        return 'bg-blue-100 text-blue-800'
      case 'pending':
        return 'bg-yellow-100 text-yellow-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const formatDuration = (seconds: number | undefined) => {
    if (!seconds) return 'N/A'
    if (seconds < 60) return `${seconds}s`
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}m ${remainingSeconds}s`
  }

  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleString()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <div className="flex">
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">Error loading migrations</h3>
            <div className="mt-2 text-sm text-red-700">{error}</div>
            <button
              onClick={fetchMigrations}
              className="mt-2 bg-red-100 hover:bg-red-200 text-red-800 px-3 py-1 rounded text-sm"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header and Filters */}
      <div className="bg-white shadow rounded-lg p-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Migration History</h2>
            <p className="text-gray-600">Track and monitor your component migrations</p>
          </div>
          <button
            onClick={fetchMigrations}
            className="mt-4 lg:mt-0 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium"
          >
            🔄 Refresh
          </button>
        </div>

        {/* Filters */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Component
            </label>
            <input
              type="text"
              value={filters.component_name}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFilters(prev => ({ ...prev, component_name: e.target.value }))}
              placeholder="Filter by component..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Status
            </label>
            <select
              value={filters.status}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setFilters(prev => ({ ...prev, status: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            >
              <option value="">All statuses</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
              <option value="running">Running</option>
              <option value="pending">Pending</option>
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={() => setFilters({ component_name: '', status: '' })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 text-sm"
            >
              Clear Filters
            </button>
          </div>
        </div>
      </div>

      {/* Migrations List */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        {migrations.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-gray-400 text-6xl mb-4">🔄</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No migrations found</h3>
            <p className="text-gray-600">
              {Object.values(filters).some(f => f) 
                ? 'No migrations match your current filters.'
                : 'No migrations have been started yet.'
              }
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Component & File
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Duration
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Started
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {migrations.map((migration) => (
                  <tr key={migration.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {migration.component_name}
                        </div>
                        <div className="text-sm text-gray-500 font-mono">
                          {migration.file_path}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(migration.status)}`}>
                        {migration.status}
                      </span>
                      {migration.overall_success !== null && (
                        <div className="text-xs text-gray-500 mt-1">
                          {migration.overall_success ? '✅ Success' : '❌ Failed'}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatDuration(migration.duration_seconds)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatDate(migration.started_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <button
                        onClick={() => fetchMigrationDetails(migration.id)}
                        className="text-blue-600 hover:text-blue-900"
                      >
                        View Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Migration Details Modal */}
      {selectedMigration && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="text-lg font-medium text-gray-900">
                    Migration Details
                  </h3>
                  <p className="text-sm text-gray-600 mt-1">
                    {selectedMigration.component_name} • {selectedMigration.file_path}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedMigration(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>
            </div>
            
            <div className="p-6 space-y-6">
              {/* Migration Summary */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-gray-50 p-3 rounded">
                  <div className="text-xs text-gray-500">Status</div>
                  <div className={`text-sm font-medium ${getStatusColor(selectedMigration.status)} inline-flex px-2 py-1 rounded`}>
                    {selectedMigration.status}
                  </div>
                </div>
                <div className="bg-gray-50 p-3 rounded">
                  <div className="text-xs text-gray-500">Duration</div>
                  <div className="text-sm font-medium">
                    {formatDuration(selectedMigration.duration_seconds)}
                  </div>
                </div>
                <div className="bg-gray-50 p-3 rounded">
                  <div className="text-xs text-gray-500">Validation</div>
                  <div className="text-sm font-medium">
                    {selectedMigration.validation_passed ? '✅ Passed' : '❌ Failed'}
                  </div>
                </div>
                <div className="bg-gray-50 p-3 rounded">
                  <div className="text-xs text-gray-500">Overall</div>
                  <div className="text-sm font-medium">
                    {selectedMigration.overall_success ? '✅ Success' : '❌ Failed'}
                  </div>
                </div>
              </div>

              {/* Migration Steps */}
              {selectedMigration.steps && selectedMigration.steps.length > 0 && (
                <div>
                  <h4 className="text-md font-medium text-gray-900 mb-3">Migration Steps</h4>
                  <div className="space-y-2">
                    {selectedMigration.steps.map((step, index) => (
                      <div key={index} className="flex items-center space-x-3 p-3 bg-gray-50 rounded">
                        <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                          step.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                        }`}>
                          {step.success ? '✓' : '✗'}
                        </div>
                        <div className="flex-1">
                          <div className="text-sm font-medium">{step.step_type}</div>
                          {step.description && (
                            <div className="text-xs text-gray-600">{step.description}</div>
                          )}
                        </div>
                        <div className="text-xs text-gray-500">
                          {formatDuration(step.duration_seconds)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Error Details */}
              {selectedMigration.error_message && (
                <div>
                  <h4 className="text-md font-medium text-gray-900 mb-3">Error Details</h4>
                  <div className="bg-red-50 border border-red-200 rounded p-4">
                    <div className="text-sm text-red-800 font-mono">
                      {selectedMigration.error_message}
                    </div>
                  </div>
                </div>
              )}

              {/* Migration Output */}
              {selectedMigration.result_code && (
                <div>
                  <h4 className="text-md font-medium text-gray-900 mb-3">Generated Code</h4>
                  <div className="bg-gray-900 text-gray-100 p-4 rounded font-mono text-sm overflow-x-auto">
                    <pre>{selectedMigration.result_code}</pre>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}