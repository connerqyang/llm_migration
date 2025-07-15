import React, { useState, useEffect } from 'react'
import { api } from '../utils/api'
import { Component, MigrationResponse } from '../types/api'

interface MigrationForm {
  component_name: string
  file_path: string
  show: boolean
}

interface MigrationStatus {
  type: 'loading' | 'success' | 'error'
  message: string
  migrationId?: string
}

export default function ComponentsView(): JSX.Element {
  const [components, setComponents] = useState<Component[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [migrationForm, setMigrationForm] = useState<MigrationForm>({
    component_name: '',
    file_path: '',
    show: false
  })
  const [migrationStatus, setMigrationStatus] = useState<MigrationStatus | null>(null)

  useEffect(() => {
    fetchComponents()
  }, [])

  const fetchComponents = async () => {
    try {
      setLoading(true)
      const data = await api.getComponents()
      setComponents(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const handleMigrationSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    try {
      setMigrationStatus({ type: 'loading', message: 'Starting migration...' })
      
      const migrationData = {
        component_name: migrationForm.component_name,
        file_path: migrationForm.file_path,
        target_framework: 'React', // Default for now
        code_style: 'modern'
      }

      const result = await api.triggerMigration(migrationData)
      
      setMigrationStatus({
        type: 'success',
        message: `Migration started successfully! ID: ${result.migration_id}`,
        migrationId: result.migration_id
      })
      
      setMigrationForm({ component_name: '', file_path: '', show: false })
      
    } catch (err) {
      setMigrationStatus({
        type: 'error',
        message: `Migration failed: ${err instanceof Error ? err.message : 'Unknown error'}`
      })
    }
  }

  const openMigrationForm = (componentName: string) => {
    setMigrationForm({
      component_name: componentName,
      file_path: '',
      show: true
    })
    setMigrationStatus(null)
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
            <h3 className="text-sm font-medium text-red-800">Error loading components</h3>
            <div className="mt-2 text-sm text-red-700">{error}</div>
            <button
              onClick={fetchComponents}
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
      {/* Header with actions */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Available Components</h2>
          <p className="text-gray-600">Manage and migrate TUX components</p>
        </div>
        <button
          onClick={fetchComponents}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium"
        >
          🔄 Refresh
        </button>
      </div>

      {/* Migration Status */}
      {migrationStatus && (
        <div className={`rounded-md p-4 ${
          migrationStatus.type === 'success' ? 'bg-green-50 border border-green-200' :
          migrationStatus.type === 'error' ? 'bg-red-50 border border-red-200' :
          'bg-blue-50 border border-blue-200'
        }`}>
          <div className="flex items-center">
            <span className="text-sm font-medium">
              {migrationStatus.type === 'success' ? '✅' : migrationStatus.type === 'error' ? '❌' : '⏳'}
            </span>
            <span className={`ml-2 text-sm ${
              migrationStatus.type === 'success' ? 'text-green-800' :
              migrationStatus.type === 'error' ? 'text-red-800' :
              'text-blue-800'
            }`}>
              {migrationStatus.message}
            </span>
            {migrationStatus.migrationId && (
              <button
                onClick={() => {/* TODO: Navigate to migration details */}}
                className="ml-4 text-green-600 hover:text-green-800 text-sm underline"
              >
                View Details
              </button>
            )}
          </div>
        </div>
      )}

      {/* Components Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {components.map((component) => (
          <div key={component.id} className="bg-white shadow rounded-lg p-6 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  {component.name}
                </h3>
                <p className="text-gray-600 text-sm mb-4">
                  {component.description}
                </p>
                
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="font-medium text-gray-700">From:</span>
                    <span className="ml-1 text-gray-600 font-mono text-xs">
                      {component.old_import_path}
                    </span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">To:</span>
                    <span className="ml-1 text-gray-600 font-mono text-xs">
                      {component.new_import_path}
                    </span>
                  </div>
                </div>
              </div>
              
              <div className="ml-4">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  component.is_active 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-red-100 text-red-800'
                }`}>
                  {component.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>

            <div className="mt-6">
              <button
                onClick={() => openMigrationForm(component.name)}
                disabled={!component.is_active}
                className={`w-full py-2 px-4 rounded-md text-sm font-medium ${
                  component.is_active
                    ? 'bg-blue-600 hover:bg-blue-700 text-white'
                    : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                }`}
              >
                🚀 Start Migration
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Migration Form Modal */}
      {migrationForm.show && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Start Migration: {migrationForm.component_name}
            </h3>
            
            <form onSubmit={handleMigrationSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  File Path *
                </label>
                <input
                  type="text"
                  required
                  value={migrationForm.file_path}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setMigrationForm(prev => ({ ...prev, file_path: e.target.value }))}
                  placeholder="e.g., src/components/Button.tsx"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Relative path to the file you want to migrate
                </p>
              </div>

              <div className="flex space-x-3 pt-4">
                <button
                  type="submit"
                  className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-md text-sm font-medium"
                >
                  Start Migration
                </button>
                <button
                  type="button"
                  onClick={() => setMigrationForm(prev => ({ ...prev, show: false }))}
                  className="flex-1 bg-gray-300 hover:bg-gray-400 text-gray-700 py-2 px-4 rounded-md text-sm font-medium"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Empty State */}
      {components.length === 0 && (
        <div className="text-center py-12">
          <div className="text-gray-400 text-6xl mb-4">🧩</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No components found</h3>
          <p className="text-gray-600">
            No migration components are currently available.
          </p>
        </div>
      )}
    </div>
  )
}