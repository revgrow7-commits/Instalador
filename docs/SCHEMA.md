# Installation Schema Documentation

## Overview

This document describes the Supabase database schema for the Installation Management System. The schema consists of 8 tables, 1 enum type, 11 indexes, 1 view, and Row Level Security (RLS) policies.

**Created:** 2026-03-31
**Migration File:** `supabase/migrations/20260331120000_installation_schema.sql`

## Enum Types

### installation_status

Status values for installation jobs:

- `agendado` - Job scheduled but not yet started
- `em_progresso` - Job currently in progress
- `concluido` - Job completed successfully
- `cancelado` - Job cancelled

## Tables

### 1. installation_job_assignments (Master Record)

Represents a complete installation job assignment, linked to Holdprint ERP jobs.

**Columns:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique identifier |
| job_id | TEXT | NOT NULL | Reference to Holdprint job |
| holdprint_job_data | JSONB | NOT NULL | Complete Holdprint job payload |
| scheduled_date | TIMESTAMP | NOT NULL | Scheduled start date/time |
| scheduled_end_time | TIMESTAMP | | Expected completion time |
| status | installation_status | DEFAULT 'agendado' | Current job status |
| created_by | UUID | FK auth.users | User who created the assignment |
| updated_at | TIMESTAMP | DEFAULT now() | Last update timestamp |
| created_at | TIMESTAMP | DEFAULT now() | Creation timestamp |
| cancelled_at | TIMESTAMP | | When job was cancelled |
| cancellation_reason | TEXT | | Reason for cancellation |
| branch_id | TEXT | | Branch code (SP, POA, etc.) |
| kanban_history | JSONB | | Historical status changes for audit |

**Indexes:**
- `idx_assignments_status` - For filtering by status
- `idx_assignments_branch` - For branch-based queries
- `idx_assignments_date` - For date range queries

**Unique Constraints:**
- `(job_id, scheduled_date)` - One assignment per job per date

---

### 2. installation_assignment_items (Detail Records)

Detail records for individual items/services assigned to one or more installers.

**Columns:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique identifier |
| assignment_id | UUID | FK assignment | Parent assignment (CASCADE delete) |
| job_item_id | TEXT | NOT NULL | Item ID from Holdprint |
| item_data | JSONB | | Item details (size, type, specs) |
| assigned_installer_ids | UUID[] | NOT NULL | Array of installer UUIDs |
| assigned_installers | JSONB | | Detailed installer info |
| status | TEXT | DEFAULT 'aguardando' | Item status |
| created_at | TIMESTAMP | DEFAULT now() | Creation timestamp |
| updated_at | TIMESTAMP | DEFAULT now() | Last update timestamp |

**Indexes:**
- `idx_assignment_items_assignment` - For finding items by assignment

---

### 3. installation_checklists (Check-in/Check-out)

GPS-tagged check-in and check-out records with photo evidence.

**Columns:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique identifier |
| assignment_id | UUID | FK assignment | Parent assignment (CASCADE delete) |
| assignment_item_id | UUID | FK items | Related item (CASCADE delete) |
| installer_id | UUID | FK auth.users | Installer performing check |
| type | TEXT | CHECK IN ('checkin', 'checkout') | Type of check |
| latitude | DECIMAL(10,8) | NOT NULL | GPS latitude |
| longitude | DECIMAL(11,8) | NOT NULL | GPS longitude |
| address | TEXT | | Reverse geocoded address |
| photo_url | TEXT | NOT NULL | URL to check photo |
| photo_metadata | JSONB | | Photo metadata (device, timestamp) |
| notes | TEXT | | Additional notes |
| rating | INTEGER | CHECK 1-5 OR NULL | Quality rating (1-5 stars) |
| created_at | TIMESTAMP | DEFAULT now() | Check timestamp |

**Indexes:**
- `idx_checklists_assignment` - For finding checks by assignment
- `idx_checklists_installer` - For finding checks by installer
- `idx_checklists_type` - For filtering by check type

**Unique Constraints:**
- `(assignment_item_id, installer_id, type)` - One check-in and one check-out per installer per item

---

### 4. installation_photos (Photo Index/Gallery)

Photo gallery index for all installation documentation photos.

**Columns:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique identifier |
| assignment_id | UUID | FK assignment | Parent assignment (CASCADE delete) |
| assignment_item_id | UUID | FK items | Related item (CASCADE delete) |
| installer_id | UUID | FK auth.users | Photographer |
| checklist_id | UUID | FK checklists | Related check-in/out (CASCADE delete) |
| photo_url | TEXT | NOT NULL | Full photo URL |
| photo_key | TEXT | NOT NULL | S3/Storage key |
| thumbnail_url | TEXT | | Thumbnail URL |
| latitude | DECIMAL(10,8) | | GPS latitude (if available) |
| longitude | DECIMAL(11,8) | | GPS longitude (if available) |
| type | TEXT | NOT NULL | Photo category (before/after/detail) |
| file_size | INTEGER | | File size in bytes |
| mime_type | TEXT | | MIME type (image/jpeg, etc.) |
| created_at | TIMESTAMP | DEFAULT now() | Upload timestamp |

**Indexes:**
- `idx_photos_assignment` - For finding photos by assignment
- `idx_photos_installer` - For finding photos by installer

---

### 5. installation_pause_logs (Break Tracking)

Tracks work breaks and pauses during installation jobs.

**Columns:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique identifier |
| assignment_id | UUID | FK assignment | Parent assignment (CASCADE delete) |
| installer_id | UUID | FK auth.users | Installer taking break |
| pause_type | TEXT | CHECK IN ('almoco', 'banheiro', 'tecnico', 'material') | Type of pause |
| started_at | TIMESTAMP | NOT NULL | When pause started |
| ended_at | TIMESTAMP | | When pause ended |
| duration_minutes | INTEGER | | Calculated pause duration |
| notes | TEXT | | Reason or notes |
| created_at | TIMESTAMP | DEFAULT now() | Record creation timestamp |

**Pause Types:**
- `almoco` - Lunch break
- `banheiro` - Bathroom break
- `tecnico` - Technical issue/troubleshooting
- `material` - Waiting for materials

**Indexes:**
- `idx_pauses_assignment` - For finding pauses by assignment
- `idx_pauses_installer` - For finding pauses by installer

---

### 6. installation_notifications (Communication)

Tracks email and WhatsApp notifications sent to installers.

**Columns:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique identifier |
| assignment_id | UUID | FK assignment | Related assignment (CASCADE delete) |
| installer_id | UUID | FK auth.users | Recipient installer |
| email_type | TEXT | NOT NULL | Type of notification |
| channel | TEXT | DEFAULT 'email' | Channel (email/whatsapp) |
| email_data | JSONB | | Email content and metadata |
| whatsapp_message_id | TEXT | | WhatsApp message ID for tracking |
| phone_number_sent_to | TEXT | | Phone number for WhatsApp |
| status | TEXT | DEFAULT 'pending' | Send status (pending/sent/failed) |
| email_sent_at | TIMESTAMP | | When email was sent |
| created_at | TIMESTAMP | DEFAULT now() | Record creation timestamp |

**Indexes:**
- `idx_notifications_installer` - For finding notifications by installer

---

### 7. installer_coins_balance (Gamification)

Tracks installer coin balances for rewards and marketplace system.

**Columns:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique identifier |
| installer_id | UUID | UNIQUE FK auth.users | Installer (CASCADE delete) |
| total_coins | INTEGER | DEFAULT 0 | Current coin balance |
| updated_at | TIMESTAMP | DEFAULT now() | Last update timestamp |

**Unique Constraints:**
- `installer_id` - One balance record per installer

**Indexes:**
- `idx_coins_installer` - For finding balance by installer

---

### 8. coins_transactions (Audit Log)

Complete audit log of all coin transactions and adjustments.

**Columns:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique identifier |
| installer_id | UUID | FK auth.users | Installer involved |
| amount | INTEGER | NOT NULL | Coin amount (positive/negative) |
| reason | TEXT | NOT NULL | Reason for transaction |
| related_checklist_id | UUID | FK checklists | Related check (SET NULL on delete) |
| created_at | TIMESTAMP | DEFAULT now() | Transaction timestamp |

**Indexes:**
- `idx_coins_transactions_installer` - For finding transactions by installer

---

## Views

### installation_jobs_public

Secure view of installation jobs without pricing information for non-admin users.

**Features:**
- Shows customer name, address, city
- Shows full `holdprint_job_data` only to admins or the job creator
- Non-admins see NULL for pricing fields
- Used for public-facing API endpoints

**Query:**
```sql
SELECT
  a.id,
  a.job_id,
  a.scheduled_date,
  a.scheduled_end_time,
  a.status,
  a.branch_id,
  a.created_at,
  a.updated_at,
  (a.holdprint_job_data ->> 'customer_name') AS customer_name,
  (a.holdprint_job_data ->> 'address') AS address,
  (a.holdprint_job_data ->> 'city') AS city,
  -- Conditional pricing visibility
  a.holdprint_job_data AS holdprint_job_data,
  a.created_by
FROM installation_job_assignments a;
```

---

## Row Level Security (RLS) Policies

All 8 tables have RLS enabled.

### installation_job_assignments
- **SELECT:** Users can view assignments for their branch or admins
- Policy: `Users can view assignments for their branch`

### installation_checklists
- **SELECT:** Installers can view their own checklists or admins can view all
- **INSERT:** Installers can only insert their own checklists

### installer_coins_balance
- **SELECT:** Installers can view their own balance or admins can view all
- **UPDATE:** Only system can update (policy prevents direct updates)

### coins_transactions
- **SELECT:** Installers can view their own transactions or admins can view all

---

## Indexes Summary

Total: 11 indexes created for optimal query performance

| Index | Table | Purpose |
|-------|-------|---------|
| idx_assignments_status | installation_job_assignments | Filter by status (agendado, em_progresso, etc.) |
| idx_assignments_branch | installation_job_assignments | Filter by branch (SP, POA) |
| idx_assignments_date | installation_job_assignments | Date range queries |
| idx_assignment_items_assignment | installation_assignment_items | Find items by assignment |
| idx_checklists_assignment | installation_checklists | Find checks by assignment |
| idx_checklists_installer | installation_checklists | Find checks by installer |
| idx_checklists_type | installation_checklists | Filter by check type |
| idx_photos_assignment | installation_photos | Find photos by assignment |
| idx_photos_installer | installation_photos | Find photos by installer |
| idx_pauses_assignment | installation_pause_logs | Find pauses by assignment |
| idx_pauses_installer | installation_pause_logs | Find pauses by installer |

---

## Foreign Key Cascade Behavior

All foreign key relationships use `ON DELETE CASCADE` except where noted:

- Deleting an assignment cascades to:
  - All assignment items
  - All checklists
  - All photos
  - All pause logs
  - All related notifications

- Deleting a checklist cascades to:
  - All photos linked to that checklist

- Deleting a checklist (SET NULL on delete):
  - coins_transactions.related_checklist_id

---

## Auth.users Extended Fields

The following fields should be added to Supabase's built-in `auth.users` table via dashboard:

```sql
ALTER TABLE auth.users ADD COLUMN branch_id TEXT;
ALTER TABLE auth.users ADD COLUMN timezone TEXT;
ALTER TABLE auth.users ADD COLUMN phone_number TEXT;
```

These fields store:
- **branch_id**: Branch code (SP, POA, etc.) for multi-region deployments
- **timezone**: User's timezone for scheduling
- **phone_number**: For WhatsApp notifications

---

## Data Flow Example

1. **Job Creation**
   - User creates `installation_job_assignments` with Holdprint job data
   - Multiple `installation_assignment_items` created for job items
   - Installers assigned via `assigned_installer_ids` array

2. **Job Execution**
   - Installer checks in: Create `installation_checklists` (checkin)
   - Installer takes photos: Create `installation_photos` records
   - Installer logs pauses: Create `installation_pause_logs`
   - Installer checks out: Create `installation_checklists` (checkout)

3. **Gamification**
   - System creates `coins_transactions` for each checkin/checkout
   - Updates `installer_coins_balance.total_coins` from transaction ledger

4. **Notifications**
   - System creates `installation_notifications` for pre-job reminders
   - Tracks send status and delivery confirmations

---

## Performance Considerations

- All key join columns have indexes
- Date ranges optimized for monthly/weekly reporting
- JSONB fields allow flexible data storage without schema changes
- Timestamp fields use `TIMESTAMP WITH TIME ZONE` for global compatibility
- Array fields (`assigned_installer_ids`) for efficient team assignments

---

## Testing

See `tests/schema.test.sql` for comprehensive validation queries:

1. Verify enum exists with correct values
2. Verify all 8 tables exist
3. Verify all 11 indexes exist
4. Verify foreign key constraints
5. Verify view exists
6. Verify RLS is enabled
7. Verify column types
8. Verify unique constraints
