"""
Supabase authentication service for installer module.
"""
import os
import logging
import asyncio
import httpx
from datetime import datetime, timezone
from fastapi import HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://otyrrvkixegiqsthmaaj.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
SUPABASE_TABLE = 'gateway_users'


class InstallerLogin(BaseModel):
    """Login request for installers"""
    email: EmailStr
    password: str


class InstallerResponse(BaseModel):
    """Installer user response"""
    id: str
    email: str
    name: str
    role: str
    department: Optional[str] = None
    is_active: bool
    permissions: Dict[str, Any] = {}


async def login_installer(email: str, password: str) -> Dict[str, Any]:
    """
    Login installer using email and password.
    Verifies against Supabase gateway_users table.
    """
    if not SUPABASE_KEY:
        logger.error("SUPABASE_KEY not configured")
        raise HTTPException(status_code=500, detail="Sistema de autenticação não configurado")

    try:
        async with httpx.AsyncClient() as client:
            # Query to get user by email
            url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json"
            }

            # RLS bypass with service role - fetch by email
            params = f'email=eq.{email}'
            response = await client.get(
                f"{url}?{params}",
                headers=headers,
                timeout=10
            )

            if response.status_code != 200:
                logger.error(f"Supabase query failed: {response.status_code} - {response.text}")
                raise HTTPException(status_code=401, detail="Credenciais inválidas")

            users = response.json()

            if not users:
                logger.warning(f"User not found: {email}")
                raise HTTPException(status_code=401, detail="Credenciais inválidas")

            user = users[0]

            # Check if user is active
            if not user.get('is_active', False):
                logger.warning(f"User account inactive: {email}")
                raise HTTPException(status_code=401, detail="Conta desativada. Entre em contato com o gerente.")

            # Verify password using bcrypt
            password_hash = user.get('password_hash', '')
            if not password_hash:
                logger.error(f"User has no password hash: {email}")
                raise HTTPException(status_code=401, detail="Credenciais inválidas")

            from passlib.context import CryptContext
            _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            if not _pwd_context.verify(password, password_hash):
                logger.warning(f"Invalid password for user: {email}")
                raise HTTPException(status_code=401, detail="Credenciais inválidas")

            # Update last login timestamp
            await update_last_login(user['id'])

            return {
                "user": {
                    "id": user['id'],
                    "email": user['email'],
                    "name": user['name'],
                    "role": user['role'],
                    "department": user.get('department'),
                    "permissions": user.get('permissions', {})
                },
                "message": "Login realizado com sucesso"
            }

    except httpx.RequestError as e:
        logger.error(f"Supabase connection error: {str(e)}")
        raise HTTPException(status_code=503, detail="Serviço de autenticação indisponível")
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao processar login")


async def update_last_login(user_id: str) -> None:
    """Update last_login_at timestamp for user"""
    if not SUPABASE_KEY:
        return

    try:
        async with httpx.AsyncClient() as client:
            url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            }

            data = {
                "last_login_at": datetime.now(timezone.utc).isoformat()
            }

            await client.patch(
                f"{url}?id=eq.{user_id}",
                json=data,
                headers=headers,
                timeout=10
            )
    except Exception as e:
        logger.warning(f"Failed to update last login: {str(e)}")


async def verify_installer_token(token: str) -> Dict[str, Any]:
    """
    Verify JWT token from Supabase Auth.
    Returns user data if token is valid.
    """
    if not SUPABASE_KEY:
        raise HTTPException(status_code=500, detail="Sistema de autenticação não configurado")

    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {token}"
            }

            # Verify token with Supabase
            response = await client.get(
                f"{SUPABASE_URL}/auth/v1/user",
                headers=headers,
                timeout=10
            )

            if response.status_code != 200:
                raise HTTPException(status_code=401, detail="Token inválido")

            auth_user = response.json()

            # Get user details from gateway_users table
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json"
            }

            params = f'email=eq.{auth_user["email"]}'
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}?{params}",
                headers=headers,
                timeout=10
            )

            if response.status_code != 200 or not response.json():
                raise HTTPException(status_code=401, detail="Usuário não encontrado")

            user = response.json()[0]

            return {
                "id": user['id'],
                "email": user['email'],
                "name": user['name'],
                "role": user['role'],
                "department": user.get('department'),
                "permissions": user.get('permissions', {})
            }

    except httpx.RequestError as e:
        logger.error(f"Supabase connection error: {str(e)}")
        raise HTTPException(status_code=503, detail="Serviço de autenticação indisponível")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        raise HTTPException(status_code=401, detail="Token inválido")


async def create_installer_user(
    email: str,
    password: str,
    name: str,
    role: str,
    department: Optional[str] = None,
    permissions: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create new installer user in Supabase.
    Should be called only by admins.
    """
    if not SUPABASE_KEY:
        raise HTTPException(status_code=500, detail="Sistema de autenticação não configurado")

    try:
        async with httpx.AsyncClient() as client:
            # First create auth user in Supabase Auth
            auth_response = await client.post(
                f"{SUPABASE_URL}/auth/v1/signup",
                json={
                    "email": email,
                    "password": password,
                    "user_metadata": {
                        "name": name,
                        "role": role
                    }
                },
                headers={"apikey": SUPABASE_KEY},
                timeout=10
            )

            if auth_response.status_code != 200:
                logger.error(f"Failed to create auth user: {auth_response.text}")
                raise HTTPException(
                    status_code=400,
                    detail="Erro ao criar usuário. Email pode já estar registrado."
                )

            auth_user = auth_response.json()
            user_id = auth_user['user']['id']

            # Create entry in gateway_users table
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json"
            }

            user_data = {
                "id": user_id,
                "email": email,
                "name": name,
                "role": role,
                "department": department,
                "permissions": permissions or {"roles": [role]},
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            response = await client.post(
                f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}",
                json=user_data,
                headers=headers,
                timeout=10
            )

            if response.status_code not in [200, 201]:
                logger.error(f"Failed to create user record: {response.text}")
                raise HTTPException(status_code=400, detail="Erro ao criar usuário")

            return {
                "id": user_id,
                "email": email,
                "name": name,
                "role": role,
                "department": department,
                "is_active": True
            }

    except httpx.RequestError as e:
        logger.error(f"Supabase connection error: {str(e)}")
        raise HTTPException(status_code=503, detail="Serviço de autenticação indisponível")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao criar usuário")
