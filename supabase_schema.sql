-- ============================================================
-- SCHEMA SUPABASE - Sistema Indústria Visual / Instaladores
-- Executar no Supabase Dashboard → SQL Editor
-- ============================================================

-- Extensão para UUID (já ativada por padrão no Supabase)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- TABELAS PRINCIPAIS
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  role TEXT DEFAULT 'installer' CHECK (role IN ('admin', 'manager', 'installer')),
  is_active BOOLEAN DEFAULT true,
  password_hash TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS installers (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
  full_name TEXT,
  phone TEXT,
  branch TEXT DEFAULT 'POA' CHECK (branch IN ('SP', 'POA')),
  is_active BOOLEAN DEFAULT true,
  avatar_url TEXT,
  coins INTEGER DEFAULT 0,
  level INTEGER DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  holdprint_job_id TEXT UNIQUE,
  title TEXT,
  client_name TEXT,
  client_address TEXT,
  status TEXT DEFAULT 'aguardando',
  branch TEXT,
  area_m2 FLOAT,
  assigned_installers JSONB DEFAULT '[]',
  scheduled_date TIMESTAMPTZ,
  items JSONB DEFAULT '[]',
  holdprint_data JSONB DEFAULT '{}',
  products_with_area JSONB DEFAULT '[]',
  total_products INTEGER DEFAULT 0,
  total_quantity FLOAT DEFAULT 0,
  item_assignments JSONB DEFAULT '[]',
  archived_items JSONB DEFAULT '[]',
  archived BOOLEAN DEFAULT false,
  archived_at TIMESTAMPTZ,
  archived_by TEXT,
  archived_by_name TEXT,
  exclude_from_metrics BOOLEAN DEFAULT false,
  no_installation BOOLEAN DEFAULT false,
  notes TEXT,
  cancelled_at TIMESTAMPTZ,
  justification JSONB,
  justified_at TIMESTAMPTZ,
  installation_config JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS item_checkins (
  id TEXT PRIMARY KEY,
  job_id TEXT REFERENCES jobs(id) ON DELETE CASCADE,
  installer_id TEXT REFERENCES installers(id) ON DELETE SET NULL,
  item_index INTEGER,
  status TEXT DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'paused', 'completed')),
  checkin_at TIMESTAMPTZ DEFAULT NOW(),
  checkout_at TIMESTAMPTZ,
  duration_minutes FLOAT,
  net_duration_minutes FLOAT,
  total_pause_minutes FLOAT,
  checkin_photo TEXT,
  checkout_photo TEXT,
  gps_lat FLOAT,
  gps_long FLOAT,
  gps_accuracy FLOAT,
  checkout_gps_lat FLOAT,
  checkout_gps_long FLOAT,
  checkout_gps_accuracy FLOAT,
  product_name TEXT,
  family_name TEXT,
  installed_m2 FLOAT,
  complexity_level INTEGER,
  height_category TEXT,
  scenario_category TEXT,
  notes TEXT,
  productivity_m2_h FLOAT,
  is_archived BOOLEAN DEFAULT false,
  products_installed JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS item_pause_logs (
  id TEXT PRIMARY KEY,
  checkin_id TEXT REFERENCES item_checkins(id) ON DELETE CASCADE,
  reason TEXT,
  paused_at TIMESTAMPTZ DEFAULT NOW(),
  resumed_at TIMESTAMPTZ,
  duration_minutes FLOAT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS checkins (
  id TEXT PRIMARY KEY,
  job_id TEXT REFERENCES jobs(id) ON DELETE CASCADE,
  installer_id TEXT REFERENCES installers(id) ON DELETE SET NULL,
  status TEXT DEFAULT 'in_progress',
  checkin_at TIMESTAMPTZ DEFAULT NOW(),
  checkout_at TIMESTAMPTZ,
  duration_minutes FLOAT,
  checkin_photo TEXT,
  checkout_photo TEXT,
  gps_lat FLOAT,
  gps_long FLOAT,
  checkout_gps_lat FLOAT,
  checkout_gps_long FLOAT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- GAMIFICAÇÃO
-- ============================================================

CREATE TABLE IF NOT EXISTS coin_balances (
  id TEXT PRIMARY KEY,
  user_id TEXT UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  total_coins INTEGER DEFAULT 0,
  lifetime_coins INTEGER DEFAULT 0,
  daily_engagement_date TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS coin_transactions (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
  amount INTEGER,
  transaction_type TEXT,
  description TEXT,
  reference_id TEXT,
  breakdown JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rewards (
  id TEXT PRIMARY KEY,
  name TEXT,
  description TEXT,
  cost_coins INTEGER,
  category TEXT,
  image_url TEXT,
  stock INTEGER,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reward_requests (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
  reward_id TEXT REFERENCES rewards(id) ON DELETE SET NULL,
  reward_name TEXT,
  cost_coins INTEGER,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'delivered')),
  notes TEXT,
  processed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- AUTENTICAÇÃO / SEGURANÇA
-- ============================================================

CREATE TABLE IF NOT EXISTS password_resets (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
  token TEXT UNIQUE,
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- NOTIFICAÇÕES
-- ============================================================

CREATE TABLE IF NOT EXISTS push_subscriptions (
  id TEXT PRIMARY KEY,
  user_id TEXT UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  subscription JSONB,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- PRODUTOS E RELATÓRIOS
-- ============================================================

CREATE TABLE IF NOT EXISTS product_families (
  id TEXT PRIMARY KEY,
  name TEXT,
  keywords JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS installed_products (
  id TEXT PRIMARY KEY,
  checkin_id TEXT REFERENCES item_checkins(id) ON DELETE CASCADE,
  job_id TEXT REFERENCES jobs(id) ON DELETE CASCADE,
  installer_id TEXT REFERENCES installers(id) ON DELETE SET NULL,
  family_id TEXT REFERENCES product_families(id) ON DELETE SET NULL,
  family_name TEXT,
  product_name TEXT,
  quantity FLOAT,
  width_m FLOAT,
  height_m FLOAT,
  area_m2 FLOAT,
  complexity_level INTEGER,
  height_category TEXT,
  scenario_category TEXT,
  duration_minutes FLOAT,
  productivity_m2_h FLOAT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS productivity_history (
  id TEXT PRIMARY KEY,
  family_id TEXT REFERENCES product_families(id) ON DELETE SET NULL,
  family_name TEXT,
  installer_id TEXT REFERENCES installers(id) ON DELETE SET NULL,
  date TEXT,
  total_m2 FLOAT,
  total_minutes FLOAT,
  items_count INTEGER,
  productivity_m2_h FLOAT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INTEGRAÇÕES
-- ============================================================

CREATE TABLE IF NOT EXISTS google_tokens (
  id TEXT PRIMARY KEY,
  user_id TEXT UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  token JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS job_justifications (
  id TEXT PRIMARY KEY,
  job_id TEXT REFERENCES jobs(id) ON DELETE CASCADE,
  job_title TEXT,
  job_code TEXT,
  type TEXT,
  type_label TEXT,
  reason TEXT,
  submitted_by TEXT REFERENCES users(id) ON DELETE SET NULL,
  submitted_by_name TEXT,
  submitted_by_email TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS system_config (
  id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
  key TEXT UNIQUE,
  value TEXT,
  total_imported INTEGER,
  total_skipped INTEGER,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- ÍNDICES PARA PERFORMANCE
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_jobs_holdprint_job_id ON jobs(holdprint_job_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_branch ON jobs(branch);
CREATE INDEX IF NOT EXISTS idx_item_checkins_job_id ON item_checkins(job_id);
CREATE INDEX IF NOT EXISTS idx_item_checkins_installer_id ON item_checkins(installer_id);
CREATE INDEX IF NOT EXISTS idx_item_checkins_status ON item_checkins(status);
CREATE INDEX IF NOT EXISTS idx_checkins_job_id ON checkins(job_id);
CREATE INDEX IF NOT EXISTS idx_installers_user_id ON installers(user_id);
CREATE INDEX IF NOT EXISTS idx_coin_transactions_user_id ON coin_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_coin_transactions_created_at ON coin_transactions(created_at);

-- ============================================================
-- ROW LEVEL SECURITY (RLS) - Opcional mas recomendado
-- Descomente e adapte conforme necessário
-- ============================================================

-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE item_checkins ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- FIM DO SCHEMA
-- ============================================================
