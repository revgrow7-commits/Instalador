"""
User management routes.
"""
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, Depends

from database import sb_find_many, sb_find_one, sb_update, sb_delete
from security import get_current_user, get_password_hash, verify_password, require_role
from models.user import User, UserRole, AdminResetPasswordRequest, PasswordChangeRequest

router = APIRouter()


@router.get("/users", response_model=List[User])
async def list_users(current_user: User = Depends(get_current_user)):
    await require_role(current_user, [UserRole.ADMIN])
    users = await sb_find_many('users')

    for user in users:
        user.pop('password_hash', None)
        if isinstance(user.get('created_at'), str):
            user['created_at'] = datetime.fromisoformat(user['created_at'])

    return users


@router.put("/users/{user_id}", response_model=User)
async def update_user(user_id: str, user_data: dict, current_user: User = Depends(get_current_user)):
    await require_role(current_user, [UserRole.ADMIN])

    update_data = {k: v for k, v in user_data.items() if k not in ['id', 'created_at', 'password', 'phone', 'branch']}

    if user_data.get('password'):
        update_data['password_hash'] = get_password_hash(user_data['password'])

    result = await sb_update('users', user_id, update_data)

    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    if user_data.get('role') == 'installer':
        installer_update = {}
        if 'phone' in user_data:
            installer_update['phone'] = user_data['phone']
        if 'branch' in user_data:
            installer_update['branch'] = user_data['branch']
        if 'name' in user_data:
            installer_update['full_name'] = user_data['name']

        if installer_update:
            installer = await sb_find_one('installers', {"user_id": user_id})
            if installer:
                await sb_update('installers', installer['id'], installer_update)

    result.pop('password_hash', None)
    if isinstance(result.get('created_at'), str):
        result['created_at'] = datetime.fromisoformat(result['created_at'])

    return User(**result)


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: User = Depends(get_current_user)):
    await require_role(current_user, [UserRole.ADMIN])
    user = await sb_find_one('users', {"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await sb_delete('users', user_id)
    return {"message": "User deleted"}


@router.post("/users/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user)
):
    """Change the current user's password"""
    user_doc = await sb_find_one('users', {"id": current_user.id})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(password_data.current_password, user_doc['password_hash']):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")

    if len(password_data.new_password) < 6:
        raise HTTPException(status_code=400, detail="A nova senha deve ter pelo menos 6 caracteres")

    new_password_hash = get_password_hash(password_data.new_password)
    await sb_update('users', current_user.id, {"password_hash": new_password_hash})

    return {"message": "Senha alterada com sucesso"}


@router.put("/users/{user_id}/reset-password")
async def admin_reset_password(
    user_id: str,
    request: AdminResetPasswordRequest,
    current_user: User = Depends(get_current_user)
):
    """Admin can reset any user's password"""
    await require_role(current_user, [UserRole.ADMIN])

    user = await sb_find_one('users', {"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    new_hash = get_password_hash(request.new_password)
    await sb_update('users', user_id, {"password_hash": new_hash})

    return {"message": f"Senha do usuário {user.get('name')} redefinida com sucesso"}
