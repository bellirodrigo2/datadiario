#!/usr/bin/env python3
"""
Simple clients for DOU API - both REST and MCP examples
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
import httpx
import json

# Reduce verbose MCP logging
logging.getLogger("mcp").setLevel(logging.WARNING)

# --------------------------- REST CLIENT --------------------------------------

class DOURestClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    async def collect_links(self, entity: str, group: str, start_date: str, commit: bool = False):
        """Collect links via REST API"""
        async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minutes timeout
            response = await client.post(
                f"{self.base_url}/collect-links",
                json={
                    "entity": entity,
                    "group": group, 
                    "start_date": start_date,
                    "commit": commit
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def read_links(self, entity: str, group: str, start_date: str):
        """Read links via REST API"""
        async with httpx.AsyncClient(timeout=60.0) as client:  # 1 minute timeout
            response = await client.post(
                f"{self.base_url}/read-links",
                json={
                    "entity": entity,
                    "group": group,
                    "start_date": start_date
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def health_check(self):
        """Check API health"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()


async def main(entity: str, group: str , start_date: str):
    """Example using REST client"""
    print("=== REST Client Example ===")
    
    client = DOURestClient()
    
    try:
        # Health check
        health = await client.health_check()
        print(f"Health: {health}")
        
        # Collect links
        result = await client.collect_links(
            entity=entity,
            group=group,
            start_date=start_date,
            commit=True
        )
        print(f"Collected: {json.dumps(result, indent=2)}")
        
        # Read links
        links = await client.read_links(
            entity=entity,
            group=group,
            start_date=start_date
        )
        print(f"Read: {json.dumps(links, indent=2)}")
        
    except Exception as e:
        print(f"REST Error: {str(e)}")



if __name__ == "__main__":
    entity = "br"
    group = "dou1"
    start_date = "03/09/2025"
    asyncio.run(main(entity=entity, group=group, start_date=start_date))