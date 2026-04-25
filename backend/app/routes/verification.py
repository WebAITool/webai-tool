from fastapi import APIRouter, HTTPException, status
from typing import List, Optional

from app.schemas import VerificationResult
from app import models

router = APIRouter(prefix="/verification", tags=["verification"])

@router.get("/{task_id}/results", response_model=List[VerificationResult])
async def get_verification_results(task_id: str):
    """
    Get all verification results (screenshots + VLM analysis) for a task.
    """
    results = models.get_verification_results(task_id)
    return results

@router.get("/{task_id}/screenshot/{route:path}")
async def get_screenshot(task_id: str, route: str):
    """
    Get specific screenshot as base64 PNG.
    """
    result = models.get_verification_result(task_id, route)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Screenshot for route '{route}' not found"
        )
    
    # Return the base64 string. 
    # Note: The client will need to prepend "data:image/png;base64," to display it.
    return {
        "route": result.route,
        "image_base64": result.screenshot_base64
    }
