"""
Mock authentication service for local development.
Uses in-memory test users instead of Supabase.
Set USE_MOCK_AUTH=true in .env to enable this.
"""

import logging
from fastapi import HTTPException
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Test users data (in-memory)
TEST_USERS = {
    "instalador.teste1@company.com": {
        "id": "test-installer-1",
        "email": "instalador.teste1@company.com",
        "name": "João Silva - Instalador",
        "password": "teste123",  # In production, use bcrypt hash
        "role": "instalador_visual",
        "department": "Instalação",
        "permissions": {"roles": ["instalador_visual"], "permissions": ["view_jobs", "checkin", "checkout"]},
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    "gerente.instalacao@company.com": {
        "id": "test-manager-1",
        "email": "gerente.instalacao@company.com",
        "name": "Maria Santos - Gerente",
        "password": "teste123",
        "role": "gerente_instalacao",
        "department": "Gestão",
        "permissions": {"roles": ["gerente_instalacao"], "permissions": ["view_all_jobs", "assign_jobs", "manage_installers"]},
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
}


async def login_installer(email: str, password: str) -> dict:
    """
    Mock login for local development.
    Uses in-memory test users.
    In production, this should use real Supabase.

    Test credentials:
    - email: instalador.teste1@company.com
    - password: teste123

    OR

    - email: gerente.instalacao@company.com
    - password: teste123
    """
    user = TEST_USERS.get(email)

    if not user:
        logger.warning(f"Mock login attempt with unknown email: {email}")
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    # Simple password check (in production, use bcrypt)
    if user["password"] != password:
        logger.warning(f"Mock login attempt with wrong password: {email}")
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    if not user["is_active"]:
        logger.warning(f"Mock login attempt with inactive account: {email}")
        raise HTTPException(status_code=401, detail="Conta desativada. Entre em contato com o gerente.")

    logger.info(f"Mock login successful: {email} ({user['role']})")

    return {
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "department": user.get("department"),
            "permissions": user.get("permissions", {})
        },
        "message": "Login realizado com sucesso"
    }


async def update_last_login(user_id: str) -> None:
    """Mock update last login - does nothing in development"""
    logger.debug(f"Mock update_last_login called for user: {user_id}")
    pass


async def verify_installer_token(token: str) -> dict:
    """
    Mock token verification.
    In production, this should verify against Supabase auth.
    """
    # For mock, just return a valid user
    # In production, decode JWT and verify against Supabase
    logger.info("Mock token verification (mock always returns valid)")

    return {
        "id": "test-installer-1",
        "email": "instalador.teste1@company.com",
        "name": "João Silva - Instalador",
        "role": "instalador_visual",
        "department": "Instalação",
        "permissions": {"roles": ["instalador_visual"]}
    }


async def create_installer_user(
    email: str,
    password: str,
    name: str,
    role: str,
    department: str = None,
    permissions: dict = None
) -> dict:
    """
    Mock create user.
    In production, this should create a user in Supabase.
    """
    if email in TEST_USERS:
        raise HTTPException(status_code=400, detail="Email já registrado")

    user_id = f"test-user-{len(TEST_USERS)}"

    new_user = {
        "id": user_id,
        "email": email,
        "name": name,
        "password": password,  # In production, hash this!
        "role": role,
        "department": department,
        "permissions": permissions or {"roles": [role]},
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    TEST_USERS[email] = new_user

    logger.info(f"Mock user created: {email} ({role})")

    return {
        "id": user_id,
        "email": email,
        "name": name,
        "role": role,
        "department": department,
        "is_active": True
    }


def get_test_users():
    """Get all test users (for debugging/testing)"""
    return {
        email: {
            "id": user["id"],
            "name": user["name"],
            "role": user["role"],
            "is_active": user["is_active"]
        }
        for email, user in TEST_USERS.items()
    }
