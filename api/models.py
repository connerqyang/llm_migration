from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
# from uuid import UUID


# Request Models
class MigrationRequest(BaseModel):
    component_name: str = Field(..., description="Name of the TUX component to migrate")
    file_path: str = Field(..., description="Path to the file containing the component")
    subrepo_path: Optional[str] = Field(None, description="Subrepository path relative to LOCAL_REPO_PATH")
    max_retries: int = Field(3, description="Maximum number of retries for validation steps")
    selected_steps: Optional[List[str]] = Field(None, description="Specific validation steps to run")
    created_by: Optional[str] = Field(None, description="User identifier")


# Response Models
class ComponentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    description: Optional[str]
    old_import_path: Optional[str]
    new_import_path: Optional[str]
    is_active: bool


class MigrationResponse(BaseModel):
    migration_id: str
    status: str
    message: str


class ValidationStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    step_type: str
    step_name: str
    retry_attempt: int
    step_order: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    success: Optional[bool]
    total_checks: int
    passed_checks: int
    failed_checks: int
    skipped_checks: int
    success_rate: Optional[float]
    error_count: int
    errors_resolved: int
    errors_introduced: int
    llm_used: bool
    llm_fix_successful: Optional[bool]


class ErrorLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    error_type: str
    error_code: Optional[str]
    error_message: str
    error_severity: int
    file_path: Optional[str]
    line_number: Optional[int]
    column_number: Optional[int]
    was_fixed: bool
    fix_attempt_count: int
    first_seen_at: datetime
    resolved_at: Optional[datetime]


class MigrationDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    component_name: str
    file_path: str
    subrepo_path: Optional[str]
    full_file_path: str
    max_retries: int
    selected_steps: Optional[List[str]]
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    branch_name: Optional[str]
    commit_hash: Optional[str]
    overall_success: Optional[bool]
    validation_passed: Optional[bool]
    migration_notes: Optional[str]
    error_summary: Optional[str]
    original_code: Optional[str]
    final_code: Optional[str]
    created_by: Optional[str]
    
    # Related data
    validation_steps: List[ValidationStepResponse]
    error_logs: List[ErrorLogResponse]


class MigrationSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    component_name: str
    file_path: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    overall_success: Optional[bool]
    validation_passed: Optional[bool]
    created_by: Optional[str]


class MigrationHistoryResponse(BaseModel):
    migrations: List[MigrationSummaryResponse]
    total_count: int
    has_more: bool


class AnalyticsOverview(BaseModel):
    total_migrations: int
    successful_migrations: int
    failed_migrations: int
    success_rate: float
    avg_duration_seconds: float
    unique_files_migrated: int
    last_migration_date: Optional[datetime]


class ComponentAnalytics(BaseModel):
    component_name: str
    total_migrations: int
    successful_migrations: int
    failed_migrations: int
    success_rate: float
    avg_duration_seconds: float
    avg_validation_steps: float
    unique_files_migrated: int
    last_migration_date: Optional[datetime]


class ValidationAnalytics(BaseModel):
    step_type: str
    total_attempts: int
    successful_attempts: int
    success_rate: float
    avg_duration_seconds: float
    common_errors: List[Dict[str, Any]]


class TrendDataPoint(BaseModel):
    date: datetime
    total_migrations: int
    successful_migrations: int
    success_rate: float
    avg_duration_seconds: float


class ErrorAnalytics(BaseModel):
    error_type: str
    error_count: int
    error_rate: float
    common_messages: List[Dict[str, Any]]
    resolution_rate: float


class AnalyticsResponse(BaseModel):
    overview: AnalyticsOverview
    component_breakdown: List[ComponentAnalytics]
    validation_breakdown: List[ValidationAnalytics]
    recent_trends: List[TrendDataPoint]
    error_summary: List[ErrorAnalytics]
    date_range: Dict[str, datetime]