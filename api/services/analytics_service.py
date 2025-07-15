from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, case
from sqlalchemy.orm import selectinload

from db_models import Migration, ValidationStep, ErrorLog, Component
from models import (
    AnalyticsResponse, 
    AnalyticsOverview, 
    ComponentAnalytics, 
    ValidationAnalytics,
    TrendDataPoint,
    ErrorAnalytics
)


class AnalyticsService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def get_overview_analytics(
        self, 
        component_name: Optional[str] = None, 
        days: int = 30
    ) -> AnalyticsResponse:
        """Get comprehensive analytics overview"""
        
        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Get overview metrics
        overview = await self._get_overview_metrics(component_name, start_date, end_date)
        
        # Get component breakdown
        component_breakdown = await self._get_component_breakdown(start_date, end_date)
        
        # Get validation breakdown
        validation_breakdown = await self._get_validation_breakdown(component_name, start_date, end_date)
        
        # Get recent trends
        recent_trends = await self._get_recent_trends(component_name, days)
        
        # Get error summary
        error_summary = await self._get_error_summary(component_name, start_date, end_date)
        
        return AnalyticsResponse(
            overview=overview,
            component_breakdown=component_breakdown,
            validation_breakdown=validation_breakdown,
            recent_trends=recent_trends,
            error_summary=error_summary,
            date_range={
                "start_date": start_date,
                "end_date": end_date
            }
        )
    
    async def _get_overview_metrics(
        self, 
        component_name: Optional[str], 
        start_date: datetime, 
        end_date: datetime
    ) -> AnalyticsOverview:
        """Get overall migration metrics"""
        
        # Build base query
        base_query = select(Migration).where(
            and_(
                Migration.created_at >= start_date,
                Migration.created_at <= end_date
            )
        )
        
        if component_name:
            base_query = base_query.where(Migration.component_name == component_name)
        
        # Get total migrations
        result = await self.db.execute(base_query)
        all_migrations = result.scalars().all()
        
        total_migrations = len(all_migrations)
        successful_migrations = len([m for m in all_migrations if m.overall_success])
        failed_migrations = total_migrations - successful_migrations
        
        success_rate = (successful_migrations / total_migrations * 100) if total_migrations > 0 else 0
        
        # Calculate average duration
        completed_migrations = [m for m in all_migrations if m.duration_seconds is not None]
        avg_duration = (
            sum(m.duration_seconds for m in completed_migrations) / len(completed_migrations)
        ) if completed_migrations else 0
        
        # Count unique files
        unique_files = len(set(m.file_path for m in all_migrations))
        
        # Get last migration date
        last_migration = max((m.created_at for m in all_migrations), default=None)
        
        return AnalyticsOverview(
            total_migrations=total_migrations,
            successful_migrations=successful_migrations,
            failed_migrations=failed_migrations,
            success_rate=round(success_rate, 2),
            avg_duration_seconds=round(avg_duration, 2),
            unique_files_migrated=unique_files,
            last_migration_date=last_migration
        )
    
    async def _get_component_breakdown(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[ComponentAnalytics]:
        """Get analytics broken down by component"""
        
        # Query for component-level analytics
        query = (
            select(
                Migration.component_name,
                func.count(Migration.id).label('total_migrations'),
                func.count(case((Migration.overall_success == True, 1))).label('successful_migrations'),
                func.count(case((Migration.overall_success == False, 1))).label('failed_migrations'),
                func.avg(Migration.duration_seconds).label('avg_duration'),
                func.count(func.distinct(Migration.file_path)).label('unique_files'),
                func.max(Migration.created_at).label('last_migration_date')
            )
            .where(
                and_(
                    Migration.created_at >= start_date,
                    Migration.created_at <= end_date
                )
            )
            .group_by(Migration.component_name)
            .order_by(desc('total_migrations'))
        )
        
        result = await self.db.execute(query)
        rows = result.all()
        
        component_analytics = []
        for row in rows:
            success_rate = (
                (row.successful_migrations / row.total_migrations * 100) 
                if row.total_migrations > 0 else 0
            )
            
            # Get validation steps count for this component
            validation_query = (
                select(func.avg(
                    select(func.count(ValidationStep.id))
                    .where(ValidationStep.migration_id == Migration.id)
                    .scalar_subquery()
                ))
                .where(
                    and_(
                        Migration.component_name == row.component_name,
                        Migration.created_at >= start_date,
                        Migration.created_at <= end_date
                    )
                )
            )
            validation_result = await self.db.execute(validation_query)
            avg_validation_steps = validation_result.scalar() or 0
            
            component_analytics.append(ComponentAnalytics(
                component_name=row.component_name,
                total_migrations=row.total_migrations,
                successful_migrations=row.successful_migrations,
                failed_migrations=row.failed_migrations,
                success_rate=round(success_rate, 2),
                avg_duration_seconds=round(row.avg_duration or 0, 2),
                avg_validation_steps=round(avg_validation_steps, 2),
                unique_files_migrated=row.unique_files,
                last_migration_date=row.last_migration_date
            ))
        
        return component_analytics
    
    async def _get_validation_breakdown(
        self, 
        component_name: Optional[str], 
        start_date: datetime, 
        end_date: datetime
    ) -> List[ValidationAnalytics]:
        """Get analytics broken down by validation step type"""
        
        # Build query for validation step analytics
        query = (
            select(
                ValidationStep.step_type,
                func.count(ValidationStep.id).label('total_attempts'),
                func.count(case((ValidationStep.success == True, 1))).label('successful_attempts'),
                func.avg(ValidationStep.duration_seconds).label('avg_duration')
            )
            .join(Migration, ValidationStep.migration_id == Migration.id)
            .where(
                and_(
                    Migration.created_at >= start_date,
                    Migration.created_at <= end_date
                )
            )
        )
        
        if component_name:
            query = query.where(Migration.component_name == component_name)
        
        query = query.group_by(ValidationStep.step_type).order_by(ValidationStep.step_type)
        
        result = await self.db.execute(query)
        rows = result.all()
        
        validation_analytics = []
        for row in rows:
            success_rate = (
                (row.successful_attempts / row.total_attempts * 100) 
                if row.total_attempts > 0 else 0
            )
            
            # Get common errors for this step type
            common_errors = await self._get_common_errors_for_step(
                row.step_type, component_name, start_date, end_date
            )
            
            validation_analytics.append(ValidationAnalytics(
                step_type=row.step_type,
                total_attempts=row.total_attempts,
                successful_attempts=row.successful_attempts,
                success_rate=round(success_rate, 2),
                avg_duration_seconds=round(row.avg_duration or 0, 2),
                common_errors=common_errors
            ))
        
        return validation_analytics
    
    async def _get_common_errors_for_step(
        self, 
        step_type: str, 
        component_name: Optional[str], 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get common errors for a specific validation step type"""
        
        query = (
            select(
                ErrorLog.error_message,
                func.count(ErrorLog.id).label('count')
            )
            .join(Migration, ErrorLog.migration_id == Migration.id)
            .where(
                and_(
                    ErrorLog.error_type == step_type,
                    Migration.created_at >= start_date,
                    Migration.created_at <= end_date
                )
            )
        )
        
        if component_name:
            query = query.where(Migration.component_name == component_name)
        
        query = (
            query.group_by(ErrorLog.error_message)
            .order_by(desc('count'))
            .limit(5)
        )
        
        result = await self.db.execute(query)
        rows = result.all()
        
        return [
            {"error_message": row.error_message, "count": row.count}
            for row in rows
        ]
    
    async def _get_recent_trends(
        self, 
        component_name: Optional[str], 
        days: int
    ) -> List[TrendDataPoint]:
        """Get daily trend data for the specified period"""
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Generate daily buckets
        daily_data = {}
        current_date = start_date.date()
        while current_date <= end_date.date():
            daily_data[current_date] = {
                'total_migrations': 0,
                'successful_migrations': 0,
                'durations': []
            }
            current_date += timedelta(days=1)
        
        # Query migrations in the date range
        query = select(Migration).where(
            and_(
                Migration.created_at >= start_date,
                Migration.created_at <= end_date
            )
        )
        
        if component_name:
            query = query.where(Migration.component_name == component_name)
        
        result = await self.db.execute(query)
        migrations = result.scalars().all()
        
        # Aggregate by day
        for migration in migrations:
            migration_date = migration.created_at.date()
            if migration_date in daily_data:
                daily_data[migration_date]['total_migrations'] += 1
                if migration.overall_success:
                    daily_data[migration_date]['successful_migrations'] += 1
                if migration.duration_seconds:
                    daily_data[migration_date]['durations'].append(migration.duration_seconds)
        
        # Convert to trend data points
        trends = []
        for date, data in sorted(daily_data.items()):
            success_rate = (
                (data['successful_migrations'] / data['total_migrations'] * 100)
                if data['total_migrations'] > 0 else 0
            )
            avg_duration = (
                sum(data['durations']) / len(data['durations'])
                if data['durations'] else 0
            )
            
            trends.append(TrendDataPoint(
                date=datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc),
                total_migrations=data['total_migrations'],
                successful_migrations=data['successful_migrations'],
                success_rate=round(success_rate, 2),
                avg_duration_seconds=round(avg_duration, 2)
            ))
        
        return trends
    
    async def _get_error_summary(
        self, 
        component_name: Optional[str], 
        start_date: datetime, 
        end_date: datetime
    ) -> List[ErrorAnalytics]:
        """Get error analytics summary"""
        
        query = (
            select(
                ErrorLog.error_type,
                func.count(ErrorLog.id).label('error_count'),
                func.count(case((ErrorLog.was_fixed == True, 1))).label('resolved_count')
            )
            .join(Migration, ErrorLog.migration_id == Migration.id)
            .where(
                and_(
                    Migration.created_at >= start_date,
                    Migration.created_at <= end_date
                )
            )
        )
        
        if component_name:
            query = query.where(Migration.component_name == component_name)
        
        query = query.group_by(ErrorLog.error_type).order_by(desc('error_count'))
        
        result = await self.db.execute(query)
        rows = result.all()
        
        # Calculate total errors for error rate
        total_errors = sum(row.error_count for row in rows)
        
        error_analytics = []
        for row in rows:
            error_rate = (row.error_count / total_errors * 100) if total_errors > 0 else 0
            resolution_rate = (row.resolved_count / row.error_count * 100) if row.error_count > 0 else 0
            
            # Get common error messages for this type
            messages_query = (
                select(
                    ErrorLog.error_message,
                    func.count(ErrorLog.id).label('count')
                )
                .join(Migration, ErrorLog.migration_id == Migration.id)
                .where(
                    and_(
                        ErrorLog.error_type == row.error_type,
                        Migration.created_at >= start_date,
                        Migration.created_at <= end_date
                    )
                )
            )
            
            if component_name:
                messages_query = messages_query.where(Migration.component_name == component_name)
            
            messages_query = (
                messages_query.group_by(ErrorLog.error_message)
                .order_by(desc('count'))
                .limit(3)
            )
            
            messages_result = await self.db.execute(messages_query)
            common_messages = [
                {"message": row_msg.error_message, "count": row_msg.count}
                for row_msg in messages_result.all()
            ]
            
            error_analytics.append(ErrorAnalytics(
                error_type=row.error_type,
                error_count=row.error_count,
                error_rate=round(error_rate, 2),
                common_messages=common_messages,
                resolution_rate=round(resolution_rate, 2)
            ))
        
        return error_analytics
    
    async def get_trends(
        self, 
        component_name: Optional[str] = None, 
        days: int = 30
    ) -> List[TrendDataPoint]:
        """Get trend data for charts"""
        return await self._get_recent_trends(component_name, days)
    
    async def get_error_analytics(
        self, 
        component_name: Optional[str] = None, 
        days: int = 30
    ) -> List[ErrorAnalytics]:
        """Get error analytics for charts"""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        return await self._get_error_summary(component_name, start_date, end_date)