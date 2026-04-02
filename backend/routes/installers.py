"""
Installer routes.
"""
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, Depends

from database import sb_find_many, sb_find_one, sb_update
from security import get_current_user, require_role
from models.user import User, UserRole, Installer

router = APIRouter()


@router.get("/installers", response_model=List[Installer])
async def list_installers(current_user: User = Depends(get_current_user)):
    """List all installers."""
    installers = await sb_find_many('installers')

    for installer in installers:
        if isinstance(installer.get('created_at'), str):
            installer['created_at'] = datetime.fromisoformat(installer['created_at'])

    return installers


@router.put("/installers/{installer_id}", response_model=Installer)
async def update_installer(installer_id: str, installer_data: dict, current_user: User = Depends(get_current_user)):
    """Update installer data."""
    await require_role(current_user, [UserRole.ADMIN])

    update_data = {k: v for k, v in installer_data.items() if k not in ['id', 'user_id', 'created_at']}

    result = await sb_update('installers', installer_id, update_data)

    if not result:
        raise HTTPException(status_code=404, detail="Installer not found")

    if isinstance(result.get('created_at'), str):
        result['created_at'] = datetime.fromisoformat(result['created_at'])

    return Installer(**result)
