from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db_models import Component
from models import ComponentResponse


class ComponentService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def get_all_components(self) -> List[ComponentResponse]:
        """Get all active components available for migration"""
        try:
            query = select(Component).where(Component.is_active == True).order_by(Component.name)
            result = await self.db.execute(query)
            components = result.scalars().all()
            
            return [ComponentResponse.model_validate(component) for component in components]
            
        except Exception as e:
            raise Exception(f"Failed to fetch components: {str(e)}")
    
    async def get_component_by_name(self, name: str) -> Optional[ComponentResponse]:
        """Get a specific component by name"""
        try:
            query = select(Component).where(Component.name == name, Component.is_active == True)
            result = await self.db.execute(query)
            component = result.scalar_one_or_none()
            
            if component:
                return ComponentResponse.model_validate(component)
            return None
            
        except Exception as e:
            raise Exception(f"Failed to fetch component {name}: {str(e)}")