#!/usr/bin/env python3
"""
Simple test script for the LLM Migration API
"""

import asyncio
import httpx
import json
from typing import Dict, Any


class APITester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def test_health(self) -> Dict[str, Any]:
        """Test health endpoint"""
        print("🏥 Testing health endpoint...")
        try:
            response = await self.client.get(f"{self.base_url}/health")
            result = response.json()
            print(f"✅ Health check: {result}")
            return result
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return {"error": str(e)}
    
    async def test_get_components(self) -> Dict[str, Any]:
        """Test get components endpoint"""
        print("\n🧩 Testing get components endpoint...")
        try:
            response = await self.client.get(f"{self.base_url}/api/components")
            result = response.json()
            print(f"✅ Components: {json.dumps(result, indent=2, default=str)}")
            return result
        except Exception as e:
            print(f"❌ Get components failed: {e}")
            return {"error": str(e)}
    
    async def test_trigger_migration(self) -> Dict[str, Any]:
        """Test trigger migration endpoint"""
        print("\n🚀 Testing trigger migration endpoint...")
        
        # Test migration request
        migration_request = {
            "component_name": "TUXButton",
            "file_path": "src/test/component.tsx",
            "subrepo_path": "packages/test",
            "max_retries": 2,
            "selected_steps": ["fix-eslint"],
            "created_by": "test_user"
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/migrate",
                json=migration_request
            )
            result = response.json()
            print(f"✅ Migration triggered: {json.dumps(result, indent=2, default=str)}")
            return result
        except Exception as e:
            print(f"❌ Trigger migration failed: {e}")
            return {"error": str(e)}
    
    async def test_get_migration_history(self) -> Dict[str, Any]:
        """Test get migration history endpoint"""
        print("\n📊 Testing get migration history endpoint...")
        try:
            response = await self.client.get(f"{self.base_url}/api/migrations")
            result = response.json()
            print(f"✅ Migration history: {json.dumps(result, indent=2, default=str)}")
            return result
        except Exception as e:
            print(f"❌ Get migration history failed: {e}")
            return {"error": str(e)}
    
    async def test_get_analytics(self) -> Dict[str, Any]:
        """Test get analytics endpoint"""
        print("\n📈 Testing get analytics endpoint...")
        try:
            response = await self.client.get(f"{self.base_url}/api/analytics/overview")
            result = response.json()
            print(f"✅ Analytics: {json.dumps(result, indent=2, default=str)}")
            return result
        except Exception as e:
            print(f"❌ Get analytics failed: {e}")
            return {"error": str(e)}
    
    async def run_all_tests(self):
        """Run all API tests"""
        print("🧪 Starting API Tests\n" + "="*50)
        
        # Test health
        await self.test_health()
        
        # Test components
        await self.test_get_components()
        
        # Test migration history
        await self.test_get_migration_history()
        
        # Test analytics
        await self.test_get_analytics()
        
        # Note: We're not testing trigger migration in automated tests
        # as it requires actual file system setup
        print("\n📝 Note: Skipping migration trigger test - requires file system setup")
        
        print("\n" + "="*50)
        print("🎉 API Tests Completed!")
        
        await self.client.aclose()


async def main():
    """Main test function"""
    tester = APITester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())