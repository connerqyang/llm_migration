import asyncio
import os
import sys
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, desc
from sqlalchemy.orm import selectinload

from db_models import Migration, ValidationStep, ErrorLog, Component
from models import (
    MigrationRequest, 
    MigrationDetailResponse, 
    MigrationHistoryResponse,
    MigrationSummaryResponse
)

# Import the existing migration functionality
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.utils.git_operations import GitOperations
from src.utils.llm_client import LLMClient
from src.utils.validation import ValidationOperations


class MigrationService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def create_migration_record(self, request: MigrationRequest) -> UUID:
        """Create initial migration record in database"""
        try:
            # Get component from database
            component_query = select(Component).where(Component.name == request.component_name)
            result = await self.db.execute(component_query)
            component = result.scalar_one_or_none()
            
            if not component:
                raise ValueError(f"Component {request.component_name} not found")
            
            # Create migration record
            migration = Migration(
                component_id=component.id,
                component_name=request.component_name,
                file_path=request.file_path,
                subrepo_path=request.subrepo_path,
                repo_path=os.getenv("LOCAL_REPO_PATH"),
                full_file_path=self._build_full_path(request),
                max_retries=request.max_retries,
                selected_steps=request.selected_steps,
                status='pending',
                created_by=request.created_by
            )
            
            self.db.add(migration)
            await self.db.commit()
            await self.db.refresh(migration)
            
            return migration.id
            
        except Exception as e:
            await self.db.rollback()
            raise Exception(f"Failed to create migration record: {str(e)}")
    
    def _build_full_path(self, request: MigrationRequest) -> str:
        """Build the full file path from request components"""
        repo_path = os.getenv("LOCAL_REPO_PATH", "")
        
        if request.subrepo_path:
            return os.path.join(repo_path, request.subrepo_path, request.file_path)
        else:
            return os.path.join(repo_path, request.file_path)
    
    async def execute_migration(self, migration_id: UUID, request: MigrationRequest):
        """Execute the actual migration process with database logging"""
        try:
            # Update migration status to running
            await self._update_migration_status(migration_id, 'running', started_at=datetime.now(timezone.utc))
            
            # Initialize GitOperations and LLMClient
            git_ops = GitOperations(
                repo_path=os.getenv("LOCAL_REPO_PATH"),
                subrepo_path=request.subrepo_path,
                file_path=request.file_path
            )
            llm_client = LLMClient()
            
            # Read original code
            original_code = git_ops.read_file()
            await self._update_migration_field(migration_id, {'original_code': original_code})
            
            # Perform LLM migration
            migration_result = llm_client.migrate_component(request.component_name, original_code)
            migrated_code = migration_result.get('migrated_code', '')
            migration_notes = migration_result.get('migration_notes', '')
            
            await self._update_migration_field(migration_id, {
                'migration_notes': migration_notes
            })
            
            # Run validation pipeline with database logging
            final_code, validation_success = await self._run_validation_pipeline_with_logging(
                migration_id, git_ops, llm_client, migrated_code, request
            )
            
            # Determine overall success
            overall_success = bool(final_code and validation_success)
            
            # Update final migration status
            await self._complete_migration(
                migration_id,
                final_code=final_code,
                overall_success=overall_success,
                validation_passed=validation_success
            )
            
            # If successful and user wants to commit, handle Git operations
            if overall_success:
                await self._handle_git_operations(migration_id, git_ops, final_code, request)
            
        except Exception as e:
            await self._update_migration_status(
                migration_id, 
                'failed', 
                error_summary=str(e),
                completed_at=datetime.now(timezone.utc)
            )
            print(f"Migration {migration_id} failed: {str(e)}")
    
    async def _run_validation_pipeline_with_logging(
        self, 
        migration_id: UUID, 
        git_ops: GitOperations, 
        llm_client: LLMClient, 
        code: str, 
        request: MigrationRequest
    ) -> tuple[str, bool]:
        """Run validation pipeline with comprehensive database logging"""
        
        validation_ops = ValidationOperations(git_ops=git_ops, max_retries=request.max_retries)
        
        # Define validation steps
        validation_steps = {
            'fix-eslint': {'type': 'eslint', 'name': 'ESLint'},
            'fix-build': {'type': 'build', 'name': 'Build'},
            'fix-tsc': {'type': 'typescript', 'name': 'TypeScript'}
        }
        
        steps_to_run = request.selected_steps or ['fix-eslint', 'fix-build', 'fix-tsc']
        
        updated_code = code
        overall_success = True
        
        for step_order, step_key in enumerate(steps_to_run, 1):
            if step_key not in validation_steps:
                continue
                
            step_info = validation_steps[step_key]
            
            # Create validation step record
            validation_step = ValidationStep(
                migration_id=migration_id,
                step_type=step_info['type'],
                step_name=step_info['name'],
                retry_attempt=1,
                step_order=step_order,
                status='pending',
                input_code=updated_code
            )
            
            self.db.add(validation_step)
            await self.db.commit()
            await self.db.refresh(validation_step)
            
            # Run validation step with retries
            step_success, final_step_code = await self._run_single_validation_step(
                validation_step.id, validation_ops, llm_client, updated_code, step_info
            )
            
            if step_success:
                updated_code = final_step_code
            else:
                overall_success = False
                break
        
        return updated_code, overall_success
    
    async def _run_single_validation_step(
        self, 
        step_id: UUID, 
        validation_ops: ValidationOperations, 
        llm_client: LLMClient, 
        code: str, 
        step_info: Dict[str, str]
    ) -> tuple[bool, str]:
        """Run a single validation step with retry logic and logging"""
        
        config = validation_ops._get_validation_config(step_info['type'])
        check_method = config['check_method']
        pre_check_method = config.get('pre_check_method')
        
        updated_code = code
        
        for retry in range(validation_ops.max_retries):
            # Update step status
            await self._update_validation_step(step_id, {
                'status': 'in_progress',
                'retry_attempt': retry + 1,
                'started_at': datetime.now(timezone.utc)
            })
            
            # Write current code to file
            validation_ops.git_ops.write_file(updated_code)
            
            # Run pre-check if available (e.g., eslint --fix)
            if pre_check_method:
                try:
                    pre_check_success, pre_check_output = pre_check_method()
                    if pre_check_success:
                        updated_code = validation_ops.git_ops.read_file()
                except Exception as e:
                    await self._log_error(step_id, 'system', f"Pre-check failed: {str(e)}")
            
            # Check for errors
            try:
                has_errors, errors = check_method()
                
                # Log errors to database
                await self._log_validation_errors(step_id, errors, step_info['type'])
                
                # Update step metrics
                await self._update_validation_step(step_id, {
                    'error_count': len(errors),
                    'errors_before': json.dumps(errors) if errors else None,
                    'total_checks': len(errors) + 10,  # Estimate
                    'failed_checks': len(errors),
                    'passed_checks': 10,  # Estimate
                    'success_rate': (10 / (len(errors) + 10)) * 100 if errors else 100
                })
                
                if not has_errors:
                    # Success!
                    await self._update_validation_step(step_id, {
                        'status': 'completed',
                        'success': True,
                        'completed_at': datetime.now(timezone.utc),
                        'output_code': updated_code
                    })
                    return True, updated_code
                
                # Try to fix with LLM
                if llm_client and retry < validation_ops.max_retries - 1:
                    llm_success, llm_code = await self._attempt_llm_fix(
                        step_id, llm_client, updated_code, errors, step_info
                    )
                    
                    if llm_success and llm_code:
                        updated_code = llm_code
                        continue
                
            except Exception as e:
                await self._log_error(step_id, 'system', f"Validation check failed: {str(e)}")
        
        # All retries exhausted
        await self._update_validation_step(step_id, {
            'status': 'failed',
            'success': False,
            'completed_at': datetime.now(timezone.utc),
            'output_code': updated_code
        })
        
        return False, updated_code
    
    async def _attempt_llm_fix(
        self, 
        step_id: UUID, 
        llm_client: LLMClient, 
        code: str, 
        errors: List[Dict], 
        step_info: Dict[str, str]
    ) -> tuple[bool, Optional[str]]:
        """Attempt to fix errors using LLM"""
        
        try:
            # Mark LLM usage
            await self._update_validation_step(step_id, {'llm_used': True})
            
            # Create fix prompt
            fix_prompt = f"""# {step_info['name']} Error Fix Request

## File with {step_info['name']} Errors

```tsx
{code}
```

## Current {step_info['name']} Errors

```json
{json.dumps(errors, indent=2)}
```

Please fix ONLY these specific {step_info['type']} errors in the code while preserving the functionality.
Do not introduce new issues or change unrelated code."""
            
            # Store prompt in database
            await self._update_validation_step(step_id, {'llm_prompt': fix_prompt})
            
            # Call LLM
            fix_response = llm_client._call_llm_api(fix_prompt)
            
            # Store response
            await self._update_validation_step(step_id, {'llm_response': fix_response})
            
            # Extract fixed code
            import re
            code_pattern = r'```tsx\n(.*?)\n```'
            code_match = re.search(code_pattern, fix_response, re.DOTALL)
            
            if code_match:
                fixed_code = code_match.group(1).strip()
                await self._update_validation_step(step_id, {
                    'llm_fix_successful': True,
                    'code_changes_made': True
                })
                return True, fixed_code
            else:
                await self._update_validation_step(step_id, {'llm_fix_successful': False})
                return False, None
                
        except Exception as e:
            await self._log_error(step_id, 'llm', f"LLM fix failed: {str(e)}")
            await self._update_validation_step(step_id, {'llm_fix_successful': False})
            return False, None
    
    async def _log_validation_errors(self, step_id: UUID, errors: List[Dict], error_type: str):
        """Log validation errors to database"""
        
        # Get migration_id from step
        step_query = select(ValidationStep.migration_id).where(ValidationStep.id == step_id)
        result = await self.db.execute(step_query)
        migration_id = result.scalar()
        
        for error in errors:
            error_log = ErrorLog(
                migration_id=migration_id,
                validation_step_id=step_id,
                error_type=error_type,
                error_message=error.get('message', 'Unknown error'),
                error_severity=error.get('severity', 2),
                line_number=error.get('line'),
                column_number=error.get('column'),
                file_path=error.get('filePath')
            )
            self.db.add(error_log)
        
        await self.db.commit()
    
    async def _log_error(self, step_id: UUID, error_type: str, message: str):
        """Log a single error to database"""
        
        # Get migration_id from step
        step_query = select(ValidationStep.migration_id).where(ValidationStep.id == step_id)
        result = await self.db.execute(step_query)
        migration_id = result.scalar()
        
        error_log = ErrorLog(
            migration_id=migration_id,
            validation_step_id=step_id,
            error_type=error_type,
            error_message=message,
            error_severity=3  # Fatal
        )
        
        self.db.add(error_log)
        await self.db.commit()
    
    async def _update_migration_status(self, migration_id: UUID, status: str, **kwargs):
        """Update migration status and other fields"""
        update_data = {'status': status, 'updated_at': datetime.now(timezone.utc)}
        update_data.update(kwargs)
        
        stmt = update(Migration).where(Migration.id == migration_id).values(**update_data)
        await self.db.execute(stmt)
        await self.db.commit()
    
    async def _update_migration_field(self, migration_id: UUID, fields: Dict[str, Any]):
        """Update specific migration fields"""
        fields['updated_at'] = datetime.now(timezone.utc)
        
        stmt = update(Migration).where(Migration.id == migration_id).values(**fields)
        await self.db.execute(stmt)
        await self.db.commit()
    
    async def _update_validation_step(self, step_id: UUID, fields: Dict[str, Any]):
        """Update validation step fields"""
        fields['updated_at'] = datetime.now(timezone.utc)
        
        stmt = update(ValidationStep).where(ValidationStep.id == step_id).values(**fields)
        await self.db.execute(stmt)
        await self.db.commit()
    
    async def _complete_migration(
        self, 
        migration_id: UUID, 
        final_code: str, 
        overall_success: bool, 
        validation_passed: bool
    ):
        """Complete migration with final status"""
        
        # Calculate duration
        migration_query = select(Migration.started_at).where(Migration.id == migration_id)
        result = await self.db.execute(migration_query)
        started_at = result.scalar()
        
        completed_at = datetime.now(timezone.utc)
        duration_seconds = int((completed_at - started_at).total_seconds()) if started_at else None
        
        await self._update_migration_status(
            migration_id,
            'completed' if overall_success else 'failed',
            final_code=final_code,
            overall_success=overall_success,
            validation_passed=validation_passed,
            completed_at=completed_at,
            duration_seconds=duration_seconds
        )
    
    async def _handle_git_operations(
        self, 
        migration_id: UUID, 
        git_ops: GitOperations, 
        final_code: str, 
        request: MigrationRequest
    ):
        """Handle Git operations (branching, committing, pushing)"""
        try:
            # This would integrate with user input in a real implementation
            # For now, we'll just update the record with Git info
            
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            branch_name = f"migration/{request.component_name}-{timestamp}"
            
            await self._update_migration_field(migration_id, {
                'branch_name': branch_name
            })
            
        except Exception as e:
            await self._log_error(None, 'git', f"Git operations failed: {str(e)}")
    
    async def get_migration_details(self, migration_id: str) -> Optional[MigrationDetailResponse]:
        """Get detailed migration information including validation steps and errors"""
        try:
            query = (
                select(Migration)
                .options(
                    selectinload(Migration.validation_steps),
                    selectinload(Migration.error_logs)
                )
                .where(Migration.id == UUID(migration_id))
            )
            
            result = await self.db.execute(query)
            migration = result.scalar_one_or_none()
            
            if not migration:
                return None
            
            return MigrationDetailResponse.model_validate(migration)
            
        except Exception as e:
            raise Exception(f"Failed to fetch migration details: {str(e)}")
    
    async def get_migration_history(
        self, 
        component_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> MigrationHistoryResponse:
        """Get migration history with filtering and pagination"""
        try:
            # Build query with filters
            query = select(Migration)
            
            conditions = []
            if component_name:
                conditions.append(Migration.component_name == component_name)
            if status:
                conditions.append(Migration.status == status)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Get total count
            count_query = select(Migration.id)
            if conditions:
                count_query = count_query.where(and_(*conditions))
            count_result = await self.db.execute(count_query)
            total_count = len(count_result.all())
            
            # Get paginated results
            query = query.order_by(desc(Migration.created_at)).limit(limit).offset(offset)
            result = await self.db.execute(query)
            migrations = result.scalars().all()
            
            migration_summaries = [
                MigrationSummaryResponse.model_validate(migration) 
                for migration in migrations
            ]
            
            return MigrationHistoryResponse(
                migrations=migration_summaries,
                total_count=total_count,
                has_more=(offset + limit) < total_count
            )
            
        except Exception as e:
            raise Exception(f"Failed to fetch migration history: {str(e)}")