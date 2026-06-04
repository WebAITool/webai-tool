from fastapi import APIRouter
from app.schemas import SettingsData
from app import models

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("", response_model=SettingsData)
async def get_settings():
    """Get current settings (API key is masked)."""
    settings = models.get_settings()
    # Mask the API key for security — only show last 4 chars
    masked = settings.model_copy(update={
        "api_key": "****" + settings.api_key[-4:] if len(settings.api_key) > 4 else ("****" if settings.api_key else "")
    })
    return masked

@router.put("", response_model=SettingsData)
async def update_settings(data: SettingsData):
    """Save settings. If api_key is '****...' (masked), keep the existing one."""
    existing = models.get_settings()
    # If the client sent a masked key, preserve the real one
    if data.api_key.startswith("****"):
        data.api_key = existing.api_key
    saved = models.save_settings(data)
    # Return masked version
    return saved.model_copy(update={
        "api_key": "****" + saved.api_key[-4:] if len(saved.api_key) > 4 else ("****" if saved.api_key else "")
    })

@router.post("/test-connection")
async def test_connection(data: SettingsData):
    """Test LLM API connection with the provided settings."""
    from openai import OpenAI
    api_key = data.api_key
    if api_key.startswith("****"):
        api_key = models.get_settings().api_key
    try:
        client = OpenAI(base_url=data.api_base_url, api_key=api_key)
        client.models.list()
        return {"success": True, "message": "Connection successful!"}
    except Exception as e:
        return {"success": False, "message": str(e)}
