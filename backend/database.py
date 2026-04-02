"""
Supabase database connection.
Replaces the previous MongoDB/Motor connection.
"""
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_SERVICE_KEY = os.environ['SUPABASE_SERVICE_KEY']

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Alias para compatibilidade com código existente
db = supabase


# ============ HELPERS ASYNC ============
# O SDK Supabase Python é síncrono. Usamos asyncio.to_thread para não bloquear o event loop.

async def sb_find_one(table: str, filters: dict):
    """Busca um único registro por filtros. Retorna dict ou None."""
    def _run():
        query = supabase.table(table).select('*')
        for key, value in filters.items():
            query = query.eq(key, value)
        result = query.maybe_single().execute()
        return result.data
    return await asyncio.to_thread(_run)


async def sb_find_many(table: str, filters: dict = None, order_by: str = None, limit: int = None):
    """Busca múltiplos registros. Retorna lista de dicts."""
    def _run():
        query = supabase.table(table).select('*')
        if filters:
            for key, value in filters.items():
                if isinstance(value, list):
                    query = query.in_(key, value)
                else:
                    query = query.eq(key, value)
        if order_by:
            desc = order_by.startswith('-')
            col = order_by.lstrip('-')
            query = query.order(col, desc=desc)
        if limit:
            query = query.limit(limit)
        result = query.execute()
        return result.data or []
    return await asyncio.to_thread(_run)


async def sb_insert(table: str, data: dict):
    """Insere um registro. Retorna o registro inserido."""
    def _run():
        result = supabase.table(table).insert(data).execute()
        return result.data[0] if result.data else None
    return await asyncio.to_thread(_run)


async def sb_update(table: str, record_id: str, data: dict, id_field: str = 'id'):
    """Atualiza um registro pelo id. Retorna o registro atualizado."""
    def _run():
        result = supabase.table(table).update(data).eq(id_field, record_id).execute()
        return result.data[0] if result.data else None
    return await asyncio.to_thread(_run)


async def sb_delete(table: str, record_id: str, id_field: str = 'id'):
    """Deleta um registro pelo id."""
    def _run():
        supabase.table(table).delete().eq(id_field, record_id).execute()
    return await asyncio.to_thread(_run)


async def sb_delete_many(table: str, filters: dict):
    """Deleta múltiplos registros por filtros."""
    def _run():
        query = supabase.table(table).delete()
        for key, value in filters.items():
            query = query.eq(key, value)
        query.execute()
    return await asyncio.to_thread(_run)


async def sb_count(table: str, filters: dict = None):
    """Conta registros. Retorna inteiro."""
    def _run():
        query = supabase.table(table).select('id', count='exact')
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        result = query.execute()
        return result.count or 0
    return await asyncio.to_thread(_run)


async def sb_upsert(table: str, data: dict, on_conflict: str = 'id'):
    """Upsert (insert or update). Retorna o registro."""
    def _run():
        result = supabase.table(table).upsert(data, on_conflict=on_conflict).execute()
        return result.data[0] if result.data else None
    return await asyncio.to_thread(_run)
