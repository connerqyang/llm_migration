import os
import re
from pathlib import Path
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from db_models import Component

logger = logging.getLogger(__name__)


class ComponentDiscoveryService:
    """Service for auto-discovering component migration guides from markdown files"""
    
    def __init__(self, db_session: AsyncSession, prompts_dir: str):
        self.db = db_session
        self.prompts_dir = Path(prompts_dir)
        self.components_dir = self.prompts_dir / "components"
    
    async def discover_and_register_component(self, md_file_path: Path) -> Optional[Component]:
        """
        Parse a markdown file and register the component in the database
        Returns the created/updated Component or None if parsing failed
        """
        try:
            logger.info(f"Discovering component from: {md_file_path}")
            
            # Extract component metadata from the markdown file
            component_data = self._parse_markdown_file(md_file_path)
            if not component_data:
                logger.warning(f"Failed to parse component data from {md_file_path}")
                return None
            
            # Check if component already exists
            existing_component = await self._get_component_by_name(component_data["name"])
            
            if existing_component:
                # Update existing component
                logger.info(f"Updating existing component: {component_data['name']}")
                await self._update_component(existing_component, component_data, md_file_path)
                return existing_component
            else:
                # Create new component
                logger.info(f"Creating new component: {component_data['name']}")
                return await self._create_component(component_data, md_file_path)
                
        except Exception as e:
            logger.error(f"Error discovering component from {md_file_path}: {e}")
            return None
    
    def _parse_markdown_file(self, md_file_path: Path) -> Optional[Dict[str, Any]]:
        """Parse a markdown file to extract component metadata"""
        try:
            with open(md_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract component name from filename
            component_name = md_file_path.stem
            
            # Extract title from H1 heading if available
            title_match = re.search(r'^#\s+(.+?)(?:\s+Migration Guide)?$', content, re.MULTILINE)
            title = title_match.group(1) if title_match else component_name
            
            # Extract old import path
            old_import_path = self._extract_import_path(content, "old")
            
            # Extract new import path  
            new_import_path = self._extract_import_path(content, "new")
            
            if not old_import_path or not new_import_path:
                logger.warning(f"Could not extract import paths from {md_file_path}")
                return None
            
            return {
                "name": component_name,
                "description": f"{title} migration from old TUX to new TUX",
                "old_import_path": old_import_path,
                "new_import_path": new_import_path,
                "migration_guide_path": str(md_file_path.relative_to(self.prompts_dir.parent))
            }
            
        except Exception as e:
            logger.error(f"Error parsing markdown file {md_file_path}: {e}")
            return None
    
    def _extract_import_path(self, content: str, import_type: str) -> Optional[str]:
        """Extract import path from markdown content"""
        # Look for sections containing "Old" or "New" 
        if import_type.lower() == "old":
            # Find old import patterns
            patterns = [
                r'##\s+Old.*?```(?:tsx?|javascript)\s*\n.*?from\s+["\']([^"\']+)["\']',
                r'##\s+Old.*?```(?:tsx?|javascript)\s*\n.*?import.*?from\s+["\']([^"\']+)["\']'
            ]
        else:
            # Find new import patterns  
            patterns = [
                r'##\s+New.*?```(?:tsx?|javascript)\s*\n.*?from\s+["\']([^"\']+)["\']',
                r'##\s+New.*?```(?:tsx?|javascript)\s*\n.*?import.*?from\s+["\']([^"\']+)["\']'
            ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Fallback: look for any import in code blocks
        import_matches = re.findall(
            r'```(?:tsx?|javascript)\s*\n.*?import.*?from\s+["\']([^"\']+)["\']', 
            content, 
            re.DOTALL
        )
        
        if import_matches:
            if import_type.lower() == "old":
                return import_matches[0]  # First import is usually old
            elif len(import_matches) > 1:
                return import_matches[1]  # Second import is usually new
        
        return None
    
    async def _get_component_by_name(self, name: str) -> Optional[Component]:
        """Get existing component by name"""
        query = select(Component).where(Component.name == name)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _create_component(self, component_data: Dict[str, Any], md_file_path: Path) -> Component:
        """Create a new component in the database"""
        component = Component(
            name=component_data["name"],
            description=component_data["description"],
            old_import_path=component_data["old_import_path"],
            new_import_path=component_data["new_import_path"],
            migration_guide_path=component_data["migration_guide_path"],
            is_active=True
        )
        
        self.db.add(component)
        await self.db.commit()
        await self.db.refresh(component)
        
        logger.info(f"✅ Created component: {component.name}")
        return component
    
    async def _update_component(self, component: Component, component_data: Dict[str, Any], md_file_path: Path):
        """Update an existing component with new data"""
        component.description = component_data["description"]
        component.old_import_path = component_data["old_import_path"]
        component.new_import_path = component_data["new_import_path"]
        component.migration_guide_path = component_data["migration_guide_path"]
        component.is_active = True
        
        await self.db.commit()
        logger.info(f"✅ Updated component: {component.name}")
    
    async def remove_component_by_file(self, md_file_path: Path):
        """Mark component as inactive when its markdown file is deleted"""
        try:
            component_name = md_file_path.stem
            component = await self._get_component_by_name(component_name)
            
            if component:
                component.is_active = False
                await self.db.commit()
                logger.info(f"🗑️ Deactivated component: {component_name}")
                
        except Exception as e:
            logger.error(f"Error removing component for {md_file_path}: {e}")