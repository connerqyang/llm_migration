#!/usr/bin/env python3
"""
Database setup script for LLM Migration Tool API
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import text

# Add current directory to path to import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, async_session_maker
from db_models import Component, Migration, ValidationStep, ErrorLog


async def setup_sample_data():
    """Insert sample data for testing"""
    
    async with async_session_maker() as session:
        try:
            # Check if components already exist
            existing_components = await session.execute(
                text("SELECT COUNT(*) FROM components")
            )
            count = existing_components.scalar()
            
            if count > 0:
                print("📋 Components already exist, skipping sample data insertion")
                return
            
            print("📋 Inserting sample components...")
            
            # Insert sample components
            components = [
                Component(
                    name="TUXButton",
                    description="Button component migration from old TUX to new TUX",
                    old_import_path="@byted-tiktok/tux-components",
                    new_import_path="@byted-tiktok/tux-web",
                    migration_guide_path="src/prompts/components/TUXButton.md"
                ),
                Component(
                    name="TUXIcon",
                    description="Icon component migration from old TUX to new TUX",
                    old_import_path="@byted-tiktok/tux-components",
                    new_import_path="@byted-tiktok/tux-web",
                    migration_guide_path="src/prompts/components/TUXIcon.md"
                )
            ]
            
            for component in components:
                session.add(component)
            
            await session.commit()
            print("✅ Sample components inserted successfully")
            
            # Insert a sample migration for demonstration
            print("📋 Inserting sample migration data...")
            
            # Get the TUXButton component
            button_component = components[0]
            await session.refresh(button_component)
            
            # Create sample migration
            sample_migration = Migration(
                component_id=button_component.id,
                component_name="TUXButton",
                file_path="src/components/Button.tsx",
                subrepo_path="packages/ui",
                repo_path="/example/repo",
                full_file_path="/example/repo/packages/ui/src/components/Button.tsx",
                max_retries=3,
                selected_steps=["fix-eslint", "fix-tsc"],
                status="completed",
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                duration_seconds=45,
                overall_success=True,
                validation_passed=True,
                migration_notes="Successfully migrated TUXButton import path",
                original_code='import { TUXButton } from "@byted-tiktok/tux-components";',
                final_code='import { TUXButton } from "@byted-tiktok/tux-web";',
                created_by="demo_user"
            )
            
            session.add(sample_migration)
            await session.commit()
            await session.refresh(sample_migration)
            
            # Add sample validation steps
            validation_steps = [
                ValidationStep(
                    migration_id=sample_migration.id,
                    step_type="eslint",
                    step_name="ESLint",
                    retry_attempt=1,
                    step_order=1,
                    status="completed",
                    success=True,
                    total_checks=5,
                    passed_checks=5,
                    failed_checks=0,
                    success_rate=100.0,
                    duration_seconds=15
                ),
                ValidationStep(
                    migration_id=sample_migration.id,
                    step_type="typescript",
                    step_name="TypeScript",
                    retry_attempt=1,
                    step_order=2,
                    status="completed",
                    success=True,
                    total_checks=8,
                    passed_checks=8,
                    failed_checks=0,
                    success_rate=100.0,
                    duration_seconds=20
                )
            ]
            
            for step in validation_steps:
                session.add(step)
            
            await session.commit()
            print("✅ Sample migration and validation steps inserted successfully")
            
        except Exception as e:
            print(f"❌ Error inserting sample data: {e}")
            await session.rollback()
            raise


async def main():
    """Main setup function"""
    print("🚀 Setting up LLM Migration Tool Database\n" + "="*50)
    
    try:
        # Initialize database
        print("🔧 Initializing database...")
        await init_db()
        
        # Insert sample data
        await setup_sample_data()
        
        print("\n" + "="*50)
        print("🎉 Database setup completed successfully!")
        print("\nYou can now start the API server with:")
        print("cd api && python main.py")
        
    except Exception as e:
        print(f"\n❌ Database setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())