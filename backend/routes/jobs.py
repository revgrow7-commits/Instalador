"""
Jobs routes - Migrated to Supabase
Handles all job-related endpoints including Holdprint integration,
scheduling, assignments, and justifications.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field, ConfigDict
import logging
import uuid
import asyncio
import requests

import resend

from database import supabase, sb_find_one, sb_find_many, sb_insert, sb_update, sb_delete, sb_upsert
from security import get_current_user, require_role
from models.user import User, UserRole
from config import (
    HOLDPRINT_API_KEY_POA, HOLDPRINT_API_KEY_SP, HOLDPRINT_API_URL,
    SENDER_EMAIL
)
from services.holdprint import extract_product_dimensions

router = APIRouter()
logger = logging.getLogger(__name__)


# ============ MODELS ============

class Job(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    holdprint_job_id: str
    title: str
    client_name: str
    client_address: Optional[str] = None
    status: str = "aguardando"
    area_m2: Optional[float] = None
    branch: str
    assigned_installers: List[str] = []
    scheduled_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[str] = None
    items: List[dict] = []
    holdprint_data: dict = {}
    products_with_area: List[dict] = []
    total_products: int = 0
    total_quantity: float = 0
    item_assignments: List[dict] = []
    archived_items: List[dict] = []


class JobCreate(BaseModel):
    holdprint_job_id: str
    branch: str


class JobAssign(BaseModel):
    installer_ids: List[str]


class JobSchedule(BaseModel):
    scheduled_date: datetime
    installer_ids: Optional[List[str]] = None


class ItemAssignment(BaseModel):
    item_indices: List[int]
    installer_ids: List[str]
    difficulty_level: Optional[int] = None
    scenario_category: Optional[str] = None
    apply_to_all: bool = True


class BatchImportRequest(BaseModel):
    branch: str


class SyncResult(BaseModel):
    branch: str
    month: int
    year: int
    imported: int
    skipped: int
    total: int
    errors: List[str] = []


class JobJustificationRequest(BaseModel):
    reason: str
    type: str
    job_title: str
    job_code: str


class ArchiveJobRequest(BaseModel):
    exclude_from_metrics: bool = False


class ArchiveItemsRequest(BaseModel):
    item_indices: List[int]
    exclude_from_metrics: bool = False


class ImportMonthRequest(BaseModel):
    month: int
    year: int


# Emails to notify when job is justified
NOTIFICATION_EMAILS = ["bruno@industriavisual.com.br", "marcelo@industriavisual.com.br"]


# ============ HELPER FUNCTIONS ============

def classify_product_family(product_name: str) -> str:
    if not product_name:
        return "Outros"
    name_lower = product_name.lower()
    mappings = [
        (["adesivo", "vinil"], "Adesivos"),
        (["lona", "banner", "faixa"], "Lonas e Banners"),
        (["chapa", "placa", "acm", "acrílico"], "Chapas e Placas"),
        (["totem"], "Totens"),
        (["letra caixa"], "Letras Caixa"),
        (["tecido", "bandeira"], "Tecidos"),
        (["envelopamento"], "Envelopamento"),
        (["painel", "backlight"], "Painéis Luminosos"),
        (["serviço", "instalação", "entrega"], "Serviços"),
    ]
    for keywords, family in mappings:
        for keyword in keywords:
            if keyword in name_lower:
                return family
    return "Outros"


def _parse_job_dates(job: dict) -> dict:
    if isinstance(job.get('created_at'), str):
        job['created_at'] = datetime.fromisoformat(job['created_at'])
    if job.get('scheduled_date') and isinstance(job['scheduled_date'], str):
        job['scheduled_date'] = datetime.fromisoformat(job['scheduled_date'])
    return job


def _build_job_dict(job: 'Job') -> dict:
    job_dict = job.model_dump()
    job_dict['created_at'] = job_dict['created_at'].isoformat()
    if job_dict.get('scheduled_date'):
        job_dict['scheduled_date'] = job_dict['scheduled_date'].isoformat()
    return job_dict


def _build_product_list(holdprint_job: dict) -> tuple:
    products = holdprint_job.get('production', {}).get('products', [])
    products_with_area = []
    total_area_m2 = 0.0
    total_quantity = 0
    for product in products:
        product_info = extract_product_dimensions(product)
        qty = product.get('quantity', 1)
        unit_area = product_info.get('area_m2', 0)
        pw = {
            "name": product.get('name', ''),
            "quantity": qty,
            "copies": product_info.get('copies', 1),
            "width_m": product_info.get('width_m', 0),
            "height_m": product_info.get('height_m', 0),
            "unit_area_m2": unit_area,
            "total_area_m2": unit_area * qty
        }
        products_with_area.append(pw)
        total_area_m2 += pw['total_area_m2']
        total_quantity += qty
    return products_with_area, round(total_area_m2, 2), len(products), total_quantity


async def fetch_holdprint_jobs(branch: str, month: int = None, year: int = None, include_finalized: bool = True):
    """Fetch ALL jobs from Holdprint API with pagination"""
    api_key = HOLDPRINT_API_KEY_POA if branch == "POA" else HOLDPRINT_API_KEY_SP
    if not api_key:
        raise HTTPException(status_code=500, detail=f"Chave de API não configurada para a filial {branch}")

    headers = {"x-api-key": api_key, "Accept": "application/json"}
    api_url = "https://api.holdworks.ai/api-key/jobs/data"
    all_jobs = []
    page = 1

    try:
        while True:
            response = requests.get(f"{api_url}?page={page}", headers=headers, timeout=60)
            if response.status_code == 401:
                raise HTTPException(status_code=401, detail=f"Chave de API inválida para {branch}")
            response.raise_for_status()
            data = response.json()
            jobs = data.get('data', []) if isinstance(data, dict) else data
            has_next = data.get('hasNextPage', False) if isinstance(data, dict) else False
            if not jobs:
                break
            all_jobs.extend(jobs)
            if not has_next or page > 50:
                break
            page += 1

        if not include_finalized:
            all_jobs = [j for j in all_jobs if not j.get('isFinalized', False)]

        logger.info(f"Holdprint {branch}: {len(all_jobs)} jobs encontrados")
        return all_jobs
    except requests.RequestException as e:
        logger.error(f"Erro Holdprint {branch}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao conectar com Holdprint: {e}")


async def _import_job_list(holdprint_jobs: list, branch: str) -> tuple:
    """Import a list of holdprint jobs. Returns (imported, skipped, errors)."""
    imported = 0
    skipped = 0
    errors = []

    for holdprint_job in holdprint_jobs:
        holdprint_job_id = str(holdprint_job.get('id', ''))
        existing = await sb_find_one('jobs', {"holdprint_job_id": holdprint_job_id})
        if existing:
            skipped += 1
            continue
        try:
            products_with_area, total_area_m2, total_products, total_quantity = _build_product_list(holdprint_job)
            job = Job(
                holdprint_job_id=holdprint_job_id,
                title=holdprint_job.get('title', 'Sem título'),
                client_name=holdprint_job.get('customerName', 'Cliente não informado'),
                client_address='',
                branch=branch,
                items=holdprint_job.get('production', {}).get('items', []),
                holdprint_data=holdprint_job,
                area_m2=total_area_m2,
                products_with_area=products_with_area,
                total_products=total_products,
                total_quantity=total_quantity
            )
            await sb_insert('jobs', _build_job_dict(job))
            imported += 1
        except Exception as e:
            errors.append(f"{holdprint_job.get('title', 'Unknown')}: {str(e)}")

    return imported, skipped, errors


# ============ HOLDPRINT ROUTES ============

@router.get("/holdprint/jobs/{branch}")
async def get_holdprint_jobs(
    branch: str,
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2020, le=2030),
    current_user: User = Depends(get_current_user)
):
    if branch not in ["POA", "SP"]:
        raise HTTPException(status_code=400, detail="Branch must be POA or SP")
    jobs = await fetch_holdprint_jobs(branch, month, year)
    return {"success": True, "jobs": jobs}


# ============ JOB CRUD ROUTES ============

@router.post("/jobs", response_model=Job)
async def create_job(job_data: JobCreate, current_user: User = Depends(get_current_user)):
    await require_role(current_user, [UserRole.ADMIN, UserRole.MANAGER])
    existing = await sb_find_one('jobs', {"holdprint_job_id": job_data.holdprint_job_id})
    if existing:
        raise HTTPException(status_code=400, detail="Job already imported")

    holdprint_jobs = await fetch_holdprint_jobs(job_data.branch)
    holdprint_job = next((j for j in holdprint_jobs if str(j.get('id')) == job_data.holdprint_job_id), None)
    if not holdprint_job:
        raise HTTPException(status_code=404, detail="Job not found in Holdprint")

    products_with_area, total_area_m2, total_products, total_quantity = _build_product_list(holdprint_job)
    job = Job(
        holdprint_job_id=job_data.holdprint_job_id,
        title=holdprint_job.get('title', 'Sem título'),
        client_name=holdprint_job.get('customerName', 'Cliente não informado'),
        client_address='',
        branch=job_data.branch,
        items=holdprint_job.get('production', {}).get('items', []),
        holdprint_data=holdprint_job,
        area_m2=total_area_m2,
        products_with_area=products_with_area,
        total_products=total_products,
        total_quantity=total_quantity
    )
    await sb_insert('jobs', _build_job_dict(job))
    return job


@router.get("/jobs", response_model=List[Job])
async def list_jobs(current_user: User = Depends(get_current_user)):
    if current_user.role == UserRole.INSTALLER:
        installer = await sb_find_one('installers', {"user_id": current_user.id})
        if not installer:
            return []

        def _query():
            result = supabase.table('jobs').select('*').execute()
            return result.data or []

        all_jobs = await asyncio.to_thread(_query)
        installer_id = installer['id']
        jobs = [j for j in all_jobs if installer_id in (j.get('assigned_installers') or [])]
    else:
        jobs = await sb_find_many('jobs')

    job_ids = [j.get('id') for j in jobs if j.get('id')]

    def _get_checkins():
        if not job_ids:
            return []
        result = supabase.table('item_checkins').select('job_id,checkin_at').eq('status', 'in_progress').in_('job_id', job_ids).execute()
        return result.data or []

    active_checkins = await asyncio.to_thread(_get_checkins)

    job_start_times = {}
    for checkin in active_checkins:
        job_id = checkin.get("job_id")
        checkin_at = checkin.get("checkin_at")
        if job_id and checkin_at:
            if isinstance(checkin_at, str):
                checkin_at = datetime.fromisoformat(checkin_at.replace('Z', '+00:00'))
            if job_id not in job_start_times or checkin_at < job_start_times[job_id]:
                job_start_times[job_id] = checkin_at

    for job in jobs:
        _parse_job_dates(job)
        job_id = job.get('id')
        if job_id in job_start_times:
            job['started_at'] = job_start_times[job_id].isoformat()

    return jobs


@router.get("/jobs/team-calendar")
async def get_team_calendar_jobs(current_user: User = Depends(get_current_user)):
    def _query():
        result = supabase.table('jobs').select('id,title,status,branch,scheduled_date,created_at,assigned_installers,holdprint_data,client_name').not_.is_('scheduled_date', 'null').execute()
        return result.data or []

    jobs = await asyncio.to_thread(_query)
    return jobs


@router.get("/jobs/sync-status")
async def get_sync_status(current_user: User = Depends(get_current_user)):
    await require_role(current_user, [UserRole.ADMIN, UserRole.MANAGER])
    config = await sb_find_one('system_config', {"key": "last_holdprint_sync"})
    if not config:
        return {"last_sync": None, "message": "Nenhuma sincronização realizada ainda"}
    return {
        "last_sync": config.get("value"),
        "total_imported": config.get("total_imported", 0),
        "total_skipped": config.get("total_skipped", 0)
    }


@router.get("/jobs/check-inconsistent")
async def check_inconsistent_jobs(current_user: User = Depends(get_current_user)):
    await require_role(current_user, [UserRole.ADMIN, UserRole.MANAGER])

    def _query():
        result = supabase.table('jobs').select('id,title,status,holdprint_data').in_('status', ['instalando', 'in_progress']).execute()
        return result.data or []

    all_jobs = await asyncio.to_thread(_query)
    inconsistent = [j for j in all_jobs if not j.get('assigned_installers')]
    jobs_list = [{"id": j["id"], "code": j.get("holdprint_data", {}).get("code", j["id"][:8]), "title": j.get("title"), "status": j.get("status")} for j in inconsistent]
    return {"inconsistent_count": len(jobs_list), "jobs": jobs_list}


@router.post("/jobs/fix-inconsistent")
async def fix_inconsistent_jobs(current_user: User = Depends(get_current_user)):
    await require_role(current_user, [UserRole.ADMIN, UserRole.MANAGER])

    def _query():
        result = supabase.table('jobs').select('id,title,holdprint_data').in_('status', ['instalando', 'in_progress']).execute()
        return result.data or []

    all_jobs = await asyncio.to_thread(_query)
    inconsistent = [j for j in all_jobs if not j.get('assigned_installers')]

    if not inconsistent:
        return {"message": "Nenhum job inconsistente encontrado", "fixed_count": 0, "jobs": []}

    fixed_jobs = []
    for job in inconsistent:
        await sb_update('jobs', job['id'], {"status": "aguardando"})
        fixed_jobs.append({"id": job["id"], "code": job.get("holdprint_data", {}).get("code", job["id"][:8]), "title": job.get("title")})

    return {"message": f"Corrigidos {len(fixed_jobs)} jobs inconsistentes", "fixed_count": len(fixed_jobs), "jobs": fixed_jobs}


@router.get("/jobs/{job_id}", response_model=Job)
async def get_job(job_id: str, current_user: User = Depends(get_current_user)):
    job_doc = await sb_find_one('jobs', {"id": job_id})
    if not job_doc:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job_doc.get('products_with_area'):
        products_with_area = []
        total_area_m2 = 0.0
        source = job_doc.get('items') or job_doc.get('holdprint_data', {}).get('products', [])
        for item in source:
            product_info = extract_product_dimensions(item)
            quantity = item.get('quantity', 1)
            unit_area = product_info.get('area_m2', 0)
            total_area = unit_area * quantity
            products_with_area.append({"name": item.get('name', 'Item'), "quantity": quantity, "width_m": product_info.get('width_m'), "height_m": product_info.get('height_m'), "unit_area_m2": unit_area, "total_area_m2": total_area})
            total_area_m2 += total_area
        if products_with_area:
            await sb_update('jobs', job_id, {"products_with_area": products_with_area, "area_m2": total_area_m2, "total_products": len(products_with_area)})
            job_doc['products_with_area'] = products_with_area
            job_doc['area_m2'] = total_area_m2
            job_doc['total_products'] = len(products_with_area)

    if current_user.role == UserRole.INSTALLER:
        installer = await sb_find_one('installers', {"user_id": current_user.id})
        if not installer:
            raise HTTPException(status_code=403, detail="Instalador não encontrado")
        installer_id = installer['id']
        assigned = job_doc.get('assigned_installers') or []
        assignments = job_doc.get('item_assignments') or []
        has_access = installer_id in assigned or any(a.get('installer_id') == installer_id or installer_id in a.get('installer_ids', []) for a in assignments)
        if not has_access:
            raise HTTPException(status_code=403, detail="Você não tem acesso a este job")

    return Job(**_parse_job_dates(job_doc))


@router.put("/jobs/{job_id}/assign", response_model=Job)
async def assign_job(job_id: str, assign_data: JobAssign, current_user: User = Depends(get_current_user)):
    await require_role(current_user, [UserRole.ADMIN, UserRole.MANAGER])
    result = await sb_update('jobs', job_id, {"assigned_installers": assign_data.installer_ids})
    if not result:
        raise HTTPException(status_code=404, detail="Job not found")
    return Job(**_parse_job_dates(result))


@router.put("/jobs/{job_id}/schedule", response_model=Job)
async def schedule_job(job_id: str, schedule_data: JobSchedule, current_user: User = Depends(get_current_user)):
    await require_role(current_user, [UserRole.ADMIN, UserRole.MANAGER])
    update_data = {"scheduled_date": schedule_data.scheduled_date.isoformat()}
    if schedule_data.installer_ids:
        update_data["assigned_installers"] = schedule_data.installer_ids
    result = await sb_update('jobs', job_id, update_data)
    if not result:
        raise HTTPException(status_code=404, detail="Job not found")
    return Job(**_parse_job_dates(result))


@router.put("/jobs/{job_id}", response_model=Job)
async def update_job(job_id: str, job_update: dict, current_user: User = Depends(get_current_user)):
    await require_role(current_user, [UserRole.ADMIN, UserRole.MANAGER])
    current_job = await sb_find_one('jobs', {"id": job_id})
    if not current_job:
        raise HTTPException(status_code=404, detail="Job not found")

    allowed_fields = ["status", "scheduled_date", "assigned_installers", "client_name", "client_address", "title", "area_m2", "no_installation", "notes", "cancelled_at", "exclude_from_metrics", "item_assignments"]
    update_data = {}
    for field in allowed_fields:
        if field in job_update:
            if field == "scheduled_date" and not isinstance(job_update[field], str):
                update_data[field] = job_update[field].isoformat()
            else:
                update_data[field] = job_update[field]

    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    new_status = update_data.get("status")
    if new_status in ["instalando", "in_progress"]:
        installers = update_data.get("assigned_installers", current_job.get("assigned_installers", []))
        if not installers:
            raise HTTPException(status_code=400, detail="Não é possível definir status 'Instalando' sem instaladores atribuídos.")

    result = await sb_update('jobs', job_id, update_data)
    if not result:
        raise HTTPException(status_code=404, detail="Job not found")
    return Job(**_parse_job_dates(result))


@router.post("/jobs/{job_id}/finalize")
async def finalize_job(job_id: str, current_user: User = Depends(get_current_user)):
    job = await sb_find_one('jobs', {"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    archived_indices = set(a.get("item_index") for a in job.get("archived_items", []))
    item_checkins = await sb_find_many('item_checkins', {"job_id": job_id})
    item_assignments = job.get("item_assignments", [])
    assigned_indices = set()
    for a in item_assignments:
        if "item_index" in a:
            assigned_indices.add(a["item_index"])
        for idx in a.get("item_indices", []):
            assigned_indices.add(idx)

    if not assigned_indices:
        assigned_indices = set(range(len(job.get("products_with_area", []))))

    required_indices = assigned_indices - archived_indices
    completed_indices = set(c["item_index"] for c in item_checkins if c.get("status") == "completed")

    if not required_indices.issubset(completed_indices):
        missing = required_indices - completed_indices
        raise HTTPException(status_code=400, detail=f"Nem todos os itens foram concluídos. Faltam: {list(missing)}")

    await sb_update('jobs', job_id, {"status": "finalizado", "completed_at": datetime.now(timezone.utc).isoformat()})
    return {"message": "Job finalizado com sucesso", "status": "finalizado"}


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, current_user: User = Depends(get_current_user)):
    await require_role(current_user, [UserRole.ADMIN, UserRole.MANAGER])
    job = await sb_find_one('jobs', {"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    from database import sb_delete_many
    await sb_delete_many('item_checkins', {"job_id": job_id})
    await sb_delete('jobs', job_id)
    return {"message": "Job and all related data deleted successfully"}


@router.post("/jobs/{job_id}/reprocess-products")
async def reprocess_job_products(job_id: str, current_user: User = Depends(get_current_user)):
    await require_role(current_user, [UserRole.ADMIN, UserRole.MANAGER])
    job = await sb_find_one('jobs', {"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    products = job.get('holdprint_data', {}).get('products', []) or job.get('items', [])
    if not products:
        return {"message": "Job não possui produtos para reprocessar", "products_count": 0, "total_area_m2": 0}

    products_with_area = []
    total_area_m2 = 0.0
    total_quantity = 0

    for product in products:
        product_info = extract_product_dimensions(product)
        quantity = product.get('quantity', 1)
        unit_area = product_info.get('area_m2', 0)
        total_area = unit_area * quantity
        pw = {"name": product.get('name', 'Produto sem nome'), "family_name": classify_product_family(product.get('name', '')), "quantity": quantity, "width_m": product_info.get('width_m'), "height_m": product_info.get('height_m'), "copies": product_info.get('copies', 1), "unit_area_m2": unit_area, "total_area_m2": total_area}
        products_with_area.append(pw)
        total_area_m2 += total_area
        total_quantity += quantity

    await sb_update('jobs', job_id, {"products_with_area": products_with_area, "area_m2": round(total_area_m2, 2), "total_products": len(products_with_area), "total_quantity": total_quantity})
    return {"message": "Produtos reprocessados com sucesso", "products_count": len(products_with_area), "total_area_m2": round(total_area_m2, 2), "products": products_with_area}


# ============ ARCHIVE ROUTES ============

@router.post("/jobs/{job_id}/archive")
async def archive_job(job_id: str, request: ArchiveJobRequest, current_user: User = Depends(get_current_user)):
    await require_role(current_user, [UserRole.ADMIN, UserRole.MANAGER])
    job = await sb_find_one('jobs', {"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    now = datetime.now(timezone.utc).isoformat()
    await sb_update('jobs', job_id, {"status": "arquivado", "archived": True, "archived_at": now, "archived_by": current_user.id, "archived_by_name": current_user.name, "exclude_from_metrics": request.exclude_from_metrics})
    return {"message": "Job arquivado com sucesso", "job_id": job_id, "exclude_from_metrics": request.exclude_from_metrics}


@router.post("/jobs/{job_id}/unarchive")
async def unarchive_job(job_id: str, current_user: User = Depends(get_current_user)):
    await require_role(current_user, [UserRole.ADMIN, UserRole.MANAGER])
    job = await sb_find_one('jobs', {"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    await sb_update('jobs', job_id, {"status": "aguardando", "archived": False, "exclude_from_metrics": False, "archived_at": None, "archived_by": None, "archived_by_name": None})
    return {"message": "Job desarquivado com sucesso"}


@router.post("/jobs/{job_id}/archive-items")
async def archive_job_items(job_id: str, request: ArchiveItemsRequest, current_user: User = Depends(get_current_user)):
    await require_role(current_user, [UserRole.ADMIN, UserRole.MANAGER])
    job = await sb_find_one('jobs', {"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    products = job.get("products_with_area") or job.get("holdprint_data", {}).get("products", [])
    for idx in request.item_indices:
        if idx < 0 or idx >= len(products):
            raise HTTPException(status_code=400, detail=f"Índice de item inválido: {idx}")

    now = datetime.now(timezone.utc).isoformat()
    archived_items = job.get("archived_items", [])
    for idx in request.item_indices:
        if idx not in [a.get("item_index") for a in archived_items]:
            product = products[idx] if idx < len(products) else {}
            archived_items.append({"item_index": idx, "item_name": product.get("name", f"Item {idx}"), "archived_at": now, "archived_by": current_user.id, "archived_by_name": current_user.name, "exclude_from_metrics": request.exclude_from_metrics})

    await sb_update('jobs', job_id, {"archived_items": archived_items})
    return {"message": f"{len(request.item_indices)} item(s) arquivado(s) com sucesso", "archived_items": archived_items}


@router.post("/jobs/{job_id}/unarchive-items")
async def unarchive_job_items(job_id: str, item_indices: List[int], current_user: User = Depends(get_current_user)):
    await require_role(current_user, [UserRole.ADMIN, UserRole.MANAGER])
    job = await sb_find_one('jobs', {"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    archived_items = [a for a in job.get("archived_items", []) if a.get("item_index") not in item_indices]
    await sb_update('jobs', job_id, {"archived_items": archived_items})
    return {"message": f"{len(item_indices)} item(s) desarquivado(s) com sucesso", "archived_items": archived_items}


# ============ ITEM ASSIGNMENT ROUTES ============

@router.post("/jobs/{job_id}/assign-items")
async def assign_items_to_installers(job_id: str, assignment: ItemAssignment, current_user: User = Depends(get_current_user)):
    await require_role(current_user, [UserRole.ADMIN, UserRole.MANAGER])
    job = await sb_find_one('jobs', {"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    def _get_installers():
        result = supabase.table('installers').select('*').in_('id', assignment.installer_ids).execute()
        return result.data or []

    installers = await asyncio.to_thread(_get_installers)
    installer_map = {i["id"]: i for i in installers}
    if len(installers) != len(assignment.installer_ids):
        raise HTTPException(status_code=400, detail="One or more installers not found")

    products = job.get("products_with_area") or job.get("holdprint_data", {}).get("products", [])
    for idx in assignment.item_indices:
        if idx < 0 or idx >= len(products):
            raise HTTPException(status_code=400, detail=f"Invalid item index: {idx}")

    current_assignments = job.get("item_assignments", [])
    now = datetime.now(timezone.utc).isoformat()
    new_assignments = []
    total_m2_assigned = 0

    for item_idx in assignment.item_indices:
        product = products[item_idx] if item_idx < len(products) else None
        item_area = (product.get("total_area_m2") or 0) if product else 0
        for installer_id in assignment.installer_ids:
            installer = installer_map.get(installer_id)
            current_assignments = [a for a in current_assignments if not (a.get("item_index") == item_idx and a.get("installer_id") == installer_id)]
            m2_per_installer = round(item_area / len(assignment.installer_ids), 2) if item_area else 0
            new_assignments.append({"item_index": item_idx, "item_name": product.get("name", f"Item {item_idx}") if product else f"Item {item_idx}", "installer_id": installer_id, "installer_name": installer.get("full_name", ""), "assigned_at": now, "item_area_m2": item_area, "assigned_m2": m2_per_installer, "status": "pending", "manager_difficulty_level": assignment.difficulty_level, "manager_scenario_category": assignment.scenario_category, "assigned_by": current_user.id})
            total_m2_assigned += m2_per_installer

    all_assignments = current_assignments + new_assignments
    all_installer_ids = list(set([a["installer_id"] for a in all_assignments]))
    await sb_update('jobs', job_id, {"item_assignments": all_assignments, "assigned_installers": all_installer_ids})
    return {"message": f"{len(new_assignments)} atribuições criadas", "total_m2_assigned": total_m2_assigned, "assignments": new_assignments}


@router.get("/jobs/{job_id}/assignments")
async def get_job_assignments(job_id: str, current_user: User = Depends(get_current_user)):
    job = await sb_find_one('jobs', {"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    assignments = job.get("item_assignments", [])
    products = job.get("products_with_area") or job.get("holdprint_data", {}).get("products", [])

    by_installer = {}
    for a in assignments:
        iid = a.get("installer_id")
        if iid not in by_installer:
            by_installer[iid] = {"installer_id": iid, "installer_name": a.get("installer_name"), "items": [], "total_m2": 0}
        by_installer[iid]["items"].append(a)
        by_installer[iid]["total_m2"] += a.get("assigned_m2", 0)

    by_item = {}
    for a in assignments:
        idx = a.get("item_index")
        if idx not in by_item:
            product = products[idx] if idx < len(products) else {}
            by_item[idx] = {"item_index": idx, "item_name": product.get("name", f"Item {idx}"), "item_area_m2": product.get("total_area_m2", 0) or 0, "installers": []}
        by_item[idx]["installers"].append({"installer_id": a.get("installer_id"), "installer_name": a.get("installer_name"), "assigned_m2": a.get("assigned_m2"), "status": a.get("status")})

    return {"job_id": job_id, "job_title": job.get("title"), "total_area_m2": job.get("area_m2", 0), "by_installer": list(by_installer.values()), "by_item": list(by_item.values()), "all_assignments": assignments}


@router.put("/jobs/{job_id}/assignments/{item_index}/status")
async def update_assignment_status(job_id: str, item_index: int, status_update: dict, current_user: User = Depends(get_current_user)):
    job = await sb_find_one('jobs', {"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    new_status = status_update.get("status")
    installed_m2 = status_update.get("installed_m2")
    if new_status not in ["pending", "in_progress", "completed"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    assignments = job.get("item_assignments", [])
    updated = False
    for a in assignments:
        if a.get("item_index") == item_index:
            if current_user.role == UserRole.INSTALLER:
                installer = await sb_find_one('installers', {"user_id": current_user.id})
                if not installer or installer.get("id") != a.get("installer_id"):
                    continue
            a["status"] = new_status
            if installed_m2 is not None:
                a["installed_m2"] = installed_m2
            if new_status == "completed":
                a["completed_at"] = datetime.now(timezone.utc).isoformat()
            updated = True

    if not updated:
        raise HTTPException(status_code=404, detail="Assignment not found or unauthorized")

    await sb_update('jobs', job_id, {"item_assignments": assignments})
    return {"message": "Assignment status updated", "assignments": assignments}


# ============ IMPORT ROUTES ============

@router.post("/jobs/import-all")
async def import_all_jobs(request: BatchImportRequest, current_user: User = Depends(get_current_user)):
    await require_role(current_user, [UserRole.ADMIN, UserRole.MANAGER])
    holdprint_jobs = await fetch_holdprint_jobs(request.branch)
    imported, skipped, errors = await _import_job_list(holdprint_jobs, request.branch)
    return {"success": True, "imported": imported, "skipped": skipped, "total": len(holdprint_jobs), "errors": errors[:5]}


@router.post("/jobs/import-current-month")
async def import_current_month_jobs(current_user: User = Depends(get_current_user)):
    await require_role(current_user, [UserRole.ADMIN, UserRole.MANAGER])
    now = datetime.now(timezone.utc)
    total_imported = 0
    total_skipped = 0
    total_errors = []
    branch_results = []

    for branch in ["SP", "POA"]:
        try:
            holdprint_jobs = await fetch_holdprint_jobs(branch, now.month, now.year)
            imported, skipped, errors = await _import_job_list(holdprint_jobs, branch)
            branch_results.append({"branch": branch, "imported": imported, "skipped": skipped, "total": len(holdprint_jobs)})
            total_imported += imported
            total_skipped += skipped
            total_errors.extend(errors)
        except HTTPException as he:
            branch_results.append({"branch": branch, "imported": 0, "skipped": 0, "total": 0, "error": str(he.detail)})
            total_errors.append(f"{branch}: {str(he.detail)}")
        except Exception as e:
            branch_results.append({"branch": branch, "imported": 0, "skipped": 0, "total": 0, "error": str(e)})
            total_errors.append(f"{branch}: {str(e)}")

    return {"success": total_imported > 0 or total_skipped > 0, "month": now.month, "year": now.year, "total_imported": total_imported, "total_skipped": total_skipped, "branches": branch_results, "errors": total_errors[:5]}


@router.post("/jobs/import-month")
async def import_month_jobs(request: ImportMonthRequest, current_user: User = Depends(get_current_user)):
    await require_role(current_user, [UserRole.ADMIN, UserRole.MANAGER])
    total_imported = 0
    total_skipped = 0
    total_errors = []
    branch_results = []

    for branch in ["SP", "POA"]:
        try:
            holdprint_jobs = await fetch_holdprint_jobs(branch, request.month, request.year)
            imported, skipped, errors = await _import_job_list(holdprint_jobs, branch)
            branch_results.append({"branch": branch, "imported": imported, "skipped": skipped, "total": imported + skipped})
            total_imported += imported
            total_skipped += skipped
        except HTTPException as he:
            branch_results.append({"branch": branch, "imported": 0, "skipped": 0, "total": 0, "error": str(he.detail)})
            total_errors.append(f"{branch}: {str(he.detail)}")
        except Exception as e:
            branch_results.append({"branch": branch, "imported": 0, "skipped": 0, "total": 0, "error": str(e)})
            total_errors.append(f"{branch}: {str(e)}")

    return {"success": total_imported > 0 or total_skipped > 0, "month": request.month, "year": request.year, "total_imported": total_imported, "total_skipped": total_skipped, "branches": branch_results, "errors": total_errors[:5]}


@router.post("/jobs/sync-holdprint")
async def sync_holdprint_jobs(
    months_back: int = Query(2, ge=1, le=12),
    current_user: User = Depends(get_current_user)
):
    await require_role(current_user, [UserRole.ADMIN, UserRole.MANAGER])
    results = []
    total_imported = 0
    total_skipped = 0
    total_errors = []
    now = datetime.now(timezone.utc)
    months_to_sync = []

    for i in range(months_back + 1):
        target_date = now - timedelta(days=i * 30)
        month_year = (target_date.month, target_date.year)
        if month_year not in months_to_sync:
            months_to_sync.append(month_year)

    for branch in ["POA", "SP"]:
        for month, year in months_to_sync:
            try:
                holdprint_jobs = await fetch_holdprint_jobs(branch, month, year)
                imported, skipped, errors = await _import_job_list(holdprint_jobs, branch)
                results.append({"branch": branch, "month": month, "year": year, "imported": imported, "skipped": skipped, "total": len(holdprint_jobs), "errors": errors[:3]})
                total_imported += imported
                total_skipped += skipped
                total_errors.extend(errors)
                logger.info(f"Sync {branch} {month}/{year}: {imported} imported, {skipped} skipped")
            except Exception as e:
                logger.error(f"Error syncing {branch} {month}/{year}: {str(e)}")
                results.append({"branch": branch, "month": month, "year": year, "imported": 0, "skipped": 0, "total": 0, "errors": [str(e)]})

    await sb_upsert('system_config', {"key": "last_holdprint_sync", "value": datetime.now(timezone.utc).isoformat(), "total_imported": total_imported, "total_skipped": total_skipped}, on_conflict='key')

    return {"success": True, "sync_date": datetime.now(timezone.utc).isoformat(), "summary": {"total_imported": total_imported, "total_skipped": total_skipped, "total_errors": len(total_errors)}, "details": results}


# ============ JOB JUSTIFICATION ROUTES ============

@router.post("/jobs/{job_id}/justify")
async def submit_job_justification(job_id: str, justification: JobJustificationRequest, current_user: User = Depends(get_current_user)):
    await require_role(current_user, [UserRole.ADMIN, UserRole.MANAGER])
    job = await sb_find_one('jobs', {"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    type_labels = {"no_checkin": "Check-in não realizado", "no_checkout": "Check-out não realizado", "cancelled": "Job cancelado pelo cliente", "rescheduled": "Job reagendado", "other": "Outro motivo"}
    type_label = type_labels.get(justification.type, justification.type)

    justification_record = {"id": str(uuid.uuid4()), "job_id": job_id, "job_title": justification.job_title, "job_code": justification.job_code, "type": justification.type, "type_label": type_label, "reason": justification.reason, "submitted_by": current_user.id, "submitted_by_name": current_user.name, "submitted_by_email": current_user.email, "created_at": datetime.now(timezone.utc).isoformat()}

    await sb_insert('job_justifications', justification_record)
    await sb_update('jobs', job_id, {"status": "justificado", "justification": justification_record, "justified_at": datetime.now(timezone.utc).isoformat(), "exclude_from_metrics": True})

    try:
        scheduled_date = job.get("scheduled_date", "")
        if scheduled_date:
            try:
                dt = datetime.fromisoformat(str(scheduled_date).replace('Z', '+00:00'))
                scheduled_date = dt.strftime("%d/%m/%Y às %H:%M")
            except (ValueError, TypeError):
                pass
        params = {"from": SENDER_EMAIL, "to": NOTIFICATION_EMAILS, "subject": f"Job Justificado: #{justification.job_code} - {justification.job_title}", "html": f"<p><strong>Motivo:</strong> {justification.reason}</p><p><strong>Por:</strong> {current_user.name}</p>"}
        await asyncio.to_thread(resend.Emails.send, params)
    except Exception as e:
        logger.error(f"Failed to send justification email: {str(e)}")

    return {"message": "Justificativa registrada com sucesso", "justification_id": justification_record["id"], "emails_sent_to": NOTIFICATION_EMAILS}


@router.get("/job-justifications")
async def get_job_justifications(current_user: User = Depends(get_current_user)):
    await require_role(current_user, [UserRole.ADMIN, UserRole.MANAGER])

    def _query():
        result = supabase.table('job_justifications').select('*').order('created_at', desc=True).limit(100).execute()
        return result.data or []

    return await asyncio.to_thread(_query)
