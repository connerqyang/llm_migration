// Component types
export interface Component {
  id: string
  name: string
  description: string
  old_import_path: string
  new_import_path: string
  is_active: boolean
}

// Migration types
export interface Migration {
  id: string
  component_name: string
  file_path: string
  status: string
  started_at: string
  completed_at?: string
  duration_seconds?: number
  overall_success?: boolean
  validation_passed?: boolean
  created_by?: string
}

export interface MigrationStep {
  step_type: string
  description?: string
  success: boolean
  duration_seconds?: number
  error_message?: string
}

export interface MigrationDetails extends Migration {
  steps?: MigrationStep[]
  error_message?: string
  result_code?: string
}

export interface MigrationRequest {
  component_name: string
  file_path: string
  target_framework?: string
  code_style?: string
}

export interface MigrationResponse {
  migration_id: string
  status: string
  message: string
}

export interface MigrationHistory {
  migrations: Migration[]
  total_count: number
  has_more: boolean
}

// Analytics types
export interface ComponentBreakdown {
  component_name: string
  total_migrations: number
  successful_migrations: number
  failed_migrations: number
  success_rate: number
  avg_duration_seconds: number
  avg_validation_steps: number
  unique_files_migrated: number
  last_migration_date: string
}

export interface ValidationBreakdown {
  step_type: string
  total_attempts: number
  successful_attempts: number
  success_rate: number
  avg_duration_seconds: number
  common_errors: string[]
}

export interface TrendPoint {
  date: string
  total_migrations: number
  successful_migrations: number
  success_rate: number
  avg_duration_seconds: number
}

export interface AnalyticsOverview {
  overview: {
    total_migrations: number
    successful_migrations: number
    failed_migrations: number
    success_rate: number
    avg_duration_seconds: number
    unique_files_migrated: number
    last_migration_date: string
  }
  component_breakdown: ComponentBreakdown[]
  validation_breakdown: ValidationBreakdown[]
  recent_trends: TrendPoint[]
  error_summary: string[]
  date_range: {
    start_date: string
    end_date: string
  }
}

export interface AnalyticsTrends {
  trends: TrendPoint[]
}

export interface AnalyticsErrors {
  error_analytics: string[]
}

// API Error type
export interface ApiError {
  message: string
  status: number
}