from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, Numeric, 
    ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime

from database import Base


class Component(Base):
    __tablename__ = "components"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    old_import_path = Column(String(255))
    new_import_path = Column(String(255))
    migration_guide_path = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    migrations = relationship("Migration", back_populates="component")


class Migration(Base):
    __tablename__ = "migrations"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    component_id = Column(String(36), ForeignKey("components.id"), nullable=False)
    component_name = Column(String(100), nullable=False)
    file_path = Column(Text, nullable=False)
    subrepo_path = Column(Text)
    repo_path = Column(Text)
    full_file_path = Column(Text, nullable=False)
    
    # Migration settings
    max_retries = Column(Integer, default=3)
    selected_steps = Column(JSON)
    
    # Status and timing
    status = Column(String(50), nullable=False, default='pending')
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)
    
    # Git information
    branch_name = Column(String(255))
    commit_hash = Column(String(40))
    base_branch = Column(String(100), default='master')
    
    # Code snapshots
    original_code = Column(Text)
    final_code = Column(Text)
    
    # Results
    overall_success = Column(Boolean)
    validation_passed = Column(Boolean)
    migration_notes = Column(Text)
    error_summary = Column(Text)
    
    # Metadata
    created_by = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    component = relationship("Component", back_populates="migrations")
    validation_steps = relationship("ValidationStep", back_populates="migration", cascade="all, delete-orphan")
    error_logs = relationship("ErrorLog", back_populates="migration", cascade="all, delete-orphan")


class ValidationStep(Base):
    __tablename__ = "validation_steps"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    migration_id = Column(String(36), ForeignKey("migrations.id"), nullable=False)
    
    # Step identification
    step_type = Column(String(50), nullable=False)
    step_name = Column(String(100), nullable=False)
    retry_attempt = Column(Integer, nullable=False, default=1)
    step_order = Column(Integer, nullable=False)
    
    # Execution details
    status = Column(String(50), nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)
    
    # Results and metrics
    success = Column(Boolean)
    total_checks = Column(Integer, default=0)
    passed_checks = Column(Integer, default=0)
    failed_checks = Column(Integer, default=0)
    skipped_checks = Column(Integer, default=0)
    success_rate = Column(Numeric(5, 2))
    
    # Code at this step
    input_code = Column(Text)
    output_code = Column(Text)
    code_changes_made = Column(Boolean, default=False)
    
    # Error tracking
    error_count = Column(Integer, default=0)
    errors_before = Column(JSON)
    errors_after = Column(JSON)
    errors_resolved = Column(Integer, default=0)
    errors_introduced = Column(Integer, default=0)
    
    # LLM interaction
    llm_used = Column(Boolean, default=False)
    llm_prompt = Column(Text)
    llm_response = Column(Text)
    llm_fix_successful = Column(Boolean)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    migration = relationship("Migration", back_populates="validation_steps")
    error_logs = relationship("ErrorLog", back_populates="validation_step", cascade="all, delete-orphan")


class ErrorLog(Base):
    __tablename__ = "error_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    migration_id = Column(String(36), ForeignKey("migrations.id"), nullable=False)
    validation_step_id = Column(String(36), ForeignKey("validation_steps.id"))
    
    # Error details
    error_type = Column(String(100), nullable=False)
    error_code = Column(String(100))
    error_message = Column(Text, nullable=False)
    error_severity = Column(Integer, default=2)
    
    # Location information
    file_path = Column(Text)
    line_number = Column(Integer)
    column_number = Column(Integer)
    
    # Context
    surrounding_code = Column(Text)
    suggested_fix = Column(Text)
    was_fixed = Column(Boolean, default=False)
    fix_attempt_count = Column(Integer, default=0)
    
    # Timing
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True))
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    migration = relationship("Migration", back_populates="error_logs")
    validation_step = relationship("ValidationStep", back_populates="error_logs")


class MigrationMetric(Base):
    __tablename__ = "migration_metrics"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Time period
    date_period = Column(DateTime(timezone=True), nullable=False)
    component_name = Column(String(100))
    
    # Counts
    total_attempts = Column(Integer, default=0)
    successful_attempts = Column(Integer, default=0)
    failed_attempts = Column(Integer, default=0)
    
    # Success rates
    overall_success_rate = Column(Numeric(5, 2))
    validation_success_rate = Column(Numeric(5, 2))
    
    # Performance metrics
    avg_duration_seconds = Column(Numeric(8, 2))
    avg_retry_count = Column(Numeric(4, 2))
    
    # Error statistics
    total_errors = Column(Integer, default=0)
    eslint_errors = Column(Integer, default=0)
    typescript_errors = Column(Integer, default=0)
    build_errors = Column(Integer, default=0)
    
    # LLM usage
    llm_fixes_attempted = Column(Integer, default=0)
    llm_fixes_successful = Column(Integer, default=0)
    llm_success_rate = Column(Numeric(5, 2))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())