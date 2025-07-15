from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import os
from typing import List, Optional

from database import init_db, get_db_session
from models import (
    MigrationRequest,
    MigrationResponse,
    ComponentResponse,
    AnalyticsResponse,
    MigrationDetailResponse,
    MigrationHistoryResponse
)
from services.migration_service import MigrationService
from services.analytics_service import AnalyticsService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    
    yield
    
    # Shutdown


app = FastAPI(
    title="LLM Migration Tool API",
    description="API for managing TUX component migrations with LLM assistance",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "llm-migration-api"}


# Component endpoints
@app.get("/api/components", response_model=List[ComponentResponse])
async def get_supported_components(db=Depends(get_db_session)):
    """Get list of supported TUX components for migration"""
    try:
        from services.component_service import ComponentService
        component_service = ComponentService(db)
        components = await component_service.get_all_components()
        return components
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch components: {str(e)}")


@app.post("/api/components/discover")
async def discover_components(db=Depends(get_db_session)):
    """Manually trigger component discovery from markdown files"""
    try:
        from services.component_discovery_service import ComponentDiscoveryService
        from pathlib import Path
        
        prompts_dir = os.getenv("PROMPTS_DIR", "../src/prompts")
        components_dir = Path(prompts_dir) / "components"
        
        discovery_service = ComponentDiscoveryService(db, prompts_dir)
        
        # Find all .md files in the components directory
        md_files = list(components_dir.glob("**/*.md"))
        
        discovered_components = []
        for md_file in md_files:
            if not md_file.name.startswith('.'):  # Skip hidden files
                component = await discovery_service.discover_and_register_component(md_file)
                if component:
                    discovered_components.append(component.name)
        
        return {
            "message": "Component discovery completed",
            "discovered_components": discovered_components,
            "total_discovered": len(discovered_components)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to discover components: {str(e)}")


# Migration endpoints
@app.post("/api/migrate", response_model=MigrationResponse)
async def trigger_migration(
    request: MigrationRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db_session)
):
    """Trigger a new component migration"""
    try:
        migration_service = MigrationService(db)
        
        # Start the migration in the background
        migration_id = await migration_service.create_migration_record(request)
        
        # Add the actual migration work to background tasks
        background_tasks.add_task(
            migration_service.execute_migration,
            migration_id,
            request
        )
        
        return MigrationResponse(
            migration_id=migration_id,
            status="started",
            message="Migration started successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start migration: {str(e)}")


@app.get("/api/migrations/{migration_id}", response_model=MigrationDetailResponse)
async def get_migration_details(migration_id: str, db=Depends(get_db_session)):
    """Get detailed information about a specific migration"""
    try:
        migration_service = MigrationService(db)
        migration_details = await migration_service.get_migration_details(migration_id)
        
        if not migration_details:
            raise HTTPException(status_code=404, detail="Migration not found")
            
        return migration_details
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch migration details: {str(e)}")


@app.get("/api/migrations", response_model=MigrationHistoryResponse)
async def get_migration_history(
    component_name: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db=Depends(get_db_session)
):
    """Get migration history with optional filtering"""
    try:
        migration_service = MigrationService(db)
        history = await migration_service.get_migration_history(
            component_name=component_name,
            status=status,
            limit=limit,
            offset=offset
        )
        return history
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch migration history: {str(e)}")


# Analytics endpoints
@app.get("/api/analytics/overview", response_model=AnalyticsResponse)
async def get_analytics_overview(
    component_name: Optional[str] = None,
    days: int = 30,
    db=Depends(get_db_session)
):
    """Get analytics overview with success rates and metrics"""
    try:
        analytics_service = AnalyticsService(db)
        analytics = await analytics_service.get_overview_analytics(
            component_name=component_name,
            days=days
        )
        return analytics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch analytics: {str(e)}")


@app.get("/api/analytics/trends")
async def get_analytics_trends(
    component_name: Optional[str] = None,
    days: int = 30,
    db=Depends(get_db_session)
):
    """Get analytics trends over time"""
    try:
        analytics_service = AnalyticsService(db)
        trends = await analytics_service.get_trends(
            component_name=component_name,
            days=days
        )
        return {"trends": trends}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch trends: {str(e)}")


@app.get("/api/analytics/errors")
async def get_error_analytics(
    component_name: Optional[str] = None,
    days: int = 30,
    db=Depends(get_db_session)
):
    """Get error analytics and common failure patterns"""
    try:
        analytics_service = AnalyticsService(db)
        error_analytics = await analytics_service.get_error_analytics(
            component_name=component_name,
            days=days
        )
        return {"error_analytics": error_analytics}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch error analytics: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )