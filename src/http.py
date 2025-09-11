
import logging
from fastapi import FastAPI, HTTPException
from typing import List

from .container import get_use_case, LinkRequest,LinkResponse
from .domain.entity.link import Link  # Import Link for OpenAPI schema

logger = logging.getLogger(__name__)


app = FastAPI(
    title="DOU Data Collection API", 
    version="1.0.0",
    description="API for collecting and reading DOU (Diário Oficial da União) links"
)


async def run_link(command_str:str, request: LinkRequest)->LinkResponse:        
        logger.info(f"Getting use case for command: {command_str.upper()}")
        use_case = await get_use_case(command_str.upper())
        logger.info(f"Got use case: {type(use_case).__name__}")
        
        logger.info(f"Executing with params: entity={request.entity.upper()}, group={request.group.upper()}, start={request.start_date}, end={request.end_date}, commit={request.commit}, status={request.status}")
        
        result = await use_case.execute(
            entity_name=request.entity.upper(),
            group=request.group.upper(),
            start=request.start_date,
            end=request.end_date,
            commit=request.commit,
            status_filter=request.status
        )
        
        logger.info(f"Use case execution completed. Result type: {type(result)}, keys: {list(result.keys()) if result else 'None'}")
        
        total_links = sum(len(links_list) for links_list in result.values()) if result else 0
        logger.info(f"Total links collected: {total_links}")
        if result:
            for date_key, links_list in result.items():
                logger.info(f"Date {date_key}: {len(links_list)} links")
        
        response = LinkResponse(
            request=request,
            links=result
        )
        
        logger.info(f"Returning response to client with {total_links} total links")
        return response

@app.post("/collect-links", response_model=LinkResponse)
async def collect_links(request: LinkRequest):
    try:
        logger.info(f"Collecting links for: {request}")
        result = await run_link("INSERT", request)
        logger.info(f"Collection result: {result}")
        return result
    except ValueError as e:
        logger.error(f"ValueError: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Exception: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/read-links", response_model=LinkResponse)
async def read_links(request: LinkRequest):
    """
    Read existing DOU links from the database.
    """
    try:
        result = await run_link("READ", request)
        return result        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "DOU Data Collection API"}

@app.get("/schema-helper", response_model=Link, include_in_schema=False)
async def schema_helper():
    """Hidden endpoint to include Link in OpenAPI schema"""
    # This endpoint will never be called, it just forces Link into the schema
    pass



if __name__ == "__main__":
    
    #Run REST server
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
    #Run MCP server
    # mcp.run()