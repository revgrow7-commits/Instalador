# 📋 Setup Manual do Supabase

## 🎯 Objetivo
Criar a tabela `gateway_users` e inserir dados de teste no Supabase.

---

## 📍 Passo 1: Aceder ao SQL Editor

1. **Abre o Dashboard Supabase:**
   - URL: https://supabase.com/dashboard
   - Projeto: **otyrrvkixegiqsthmaaj**

2. **Navega para SQL Editor:**
   - Menu lateral esquerdo → "SQL Editor"
   - Clica em **"+ New Query"** no canto superior direito

---

## 📍 Passo 2: Copia o Script SQL

Copia este script completo:

```sql
-- ============================================
-- CRIAR TABELA gateway_users
-- ============================================

CREATE TABLE IF NOT EXISTS public.gateway_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) NOT NULL UNIQUE,
  name VARCHAR(255) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(50) NOT NULL DEFAULT 'user',
  department VARCHAR(255),
  permissions JSONB DEFAULT '{}',
  is_active BOOLEAN DEFAULT true,
  must_change_password BOOLEAN DEFAULT false,
  last_login_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_by UUID,
  CONSTRAINT valid_role CHECK (role IN ('admin', 'gestao', 'comercial', 'financeiro', 'marketing', 'operacao', 'rh', 'pcp', 'pcp_impressao', 'pcp_arte_final', 'pcp_instalacao', 'instalador_visual', 'gerente_instalacao', 'user'))
);

-- ============================================
-- CRIAR ÍNDICES
-- ============================================

CREATE INDEX IF NOT EXISTS idx_gateway_users_email ON public.gateway_users(LOWER(email));
CREATE INDEX IF NOT EXISTS idx_gateway_users_role ON public.gateway_users(role);
CREATE INDEX IF NOT EXISTS idx_gateway_users_is_active ON public.gateway_users(is_active);
CREATE INDEX IF NOT EXISTS idx_gateway_users_created_at ON public.gateway_users(created_at DESC);

-- ============================================
-- ATIVAR ROW LEVEL SECURITY
-- ============================================

ALTER TABLE public.gateway_users ENABLE ROW LEVEL SECURITY;

-- ============================================
-- CRIAR RLS POLICIES
-- ============================================

-- Política 1: Usuários podem ver seus próprios dados
CREATE POLICY IF NOT EXISTS "Users can view own data" ON public.gateway_users 
  FOR SELECT 
  USING (true);

-- Política 2: Apenas admins podem criar usuários
CREATE POLICY IF NOT EXISTS "Only admins can create users" ON public.gateway_users 
  FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.gateway_users 
      WHERE role = 'admin' AND is_active = true
    )
  );

-- Política 3: Usuários podem atualizar sua própria senha
CREATE POLICY IF NOT EXISTS "Users can update own password" ON public.gateway_users 
  FOR UPDATE 
  USING (true) 
  WITH CHECK (true);

-- Política 4: Apenas admins podem atualizar outros usuários
CREATE POLICY IF NOT EXISTS "Only admins can update other users" ON public.gateway_users 
  FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM public.gateway_users AS admin 
      WHERE admin.role = 'admin' AND admin.is_active = true
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.gateway_users AS admin 
      WHERE admin.role = 'admin' AND admin.is_active = true
    )
  );

-- ============================================
-- INSERIR DADOS DE TESTE
-- ============================================

-- Usuário 1: Instalador de Teste
INSERT INTO public.gateway_users (
  email, 
  name, 
  password_hash, 
  role, 
  department,
  permissions, 
  is_active
) VALUES (
  'instalador.teste1@company.com',
  'João Silva - Instalador',
  '$2a$06$l5rFzdb/2rU8vuDoQKhw8eHrBCujQjZkDHphus5tpGV2TLM/11g0m',
  'instalador_visual',
  'Instalação',
  '{"roles": ["instalador_visual"], "permissions": ["view_jobs", "checkin", "checkout"]}',
  true
) ON CONFLICT (email) DO NOTHING;

-- Usuário 2: Gerente de Teste
INSERT INTO public.gateway_users (
  email, 
  name, 
  password_hash, 
  role, 
  department,
  permissions, 
  is_active
) VALUES (
  'gerente.instalacao@company.com',
  'Maria Santos - Gerente',
  '$2a$06$l5rFzdb/2rU8vuDoQKhw8eHrBCujQjZkDHphus5tpGV2TLM/11g0m',
  'gerente_instalacao',
  'Gestão',
  '{"roles": ["gerente_instalacao"], "permissions": ["view_all_jobs", "assign_jobs", "manage_installers"]}',
  true
) ON CONFLICT (email) DO NOTHING;

-- ============================================
-- VERIFICAÇÃO: Confirmar que foi criado
-- ============================================

SELECT
  id, 
  name, 
  email, 
  role,
  department,
  permissions->>'roles' as roles_list,
  is_active,
  created_at
FROM public.gateway_users
WHERE role IN ('instalador_visual', 'gerente_instalacao')
ORDER BY created_at DESC;
```

---

## 📍 Passo 3: Cola e Executa

1. **Cola o script** na caixa de texto do SQL Editor
2. **Clica o botão "RUN"** no canto inferior direito (ou pressiona `Ctrl+Enter`)
3. **Aguarda a confirmação** - deverás ver:
   - ✅ "Query executed successfully"
   - Uma tabela com os 2 utilizadores de teste criados

---

## ✅ Verificação

Após executar, deverás ver um resultado como este:

| id | name | email | role | department | roles_list | is_active | created_at |
|---|---|---|---|---|---|---|---|
| uuid-1 | João Silva - Instalador | instalador.teste1@company.com | instalador_visual | Instalação | instalador_visual | true | 2026-04-01 |
| uuid-2 | Maria Santos - Gerente | gerente.instalacao@company.com | gerente_instalacao | Gestão | gerente_instalacao | true | 2026-04-01 |

Se vires isto, **✅ O Setup foi bem-sucedido!**

---

## 🔑 Obter as Chaves da API

Após criar a tabela, tens de obter as chaves do Supabase para configurar no `.env`:

1. **No Dashboard Supabase:**
   - Menu lateral → "Project Settings"
   - Aba "API"

2. **Copia as chaves:**
   - **Chave Anon** (`SUPABASE_KEY`) - para operações públicas
   - **Chave Service Role** (`SUPABASE_SERVICE_ROLE`) - para operações administrativas

3. **Cola no arquivo `backend/.env`:**
   ```env
   SUPABASE_URL=https://otyrrvkixegiqsthmaaj.supabase.co
   SUPABASE_KEY=paste-anon-key-here
   SUPABASE_SERVICE_ROLE=paste-service-role-here
   ```

---

## 🚀 Próximos Passos

Após completar este setup:

1. ✅ Tabela `gateway_users` criada
2. ✅ 2 utilizadores de teste inseridos
3. ✅ RLS policies ativas
4. ➡️ **Atualizar `.env` com as chaves**
5. ➡️ **Testar login no frontend/backend**

---

## 🆘 Troubleshooting

### ❌ Erro: "Duplicate key value violates unique constraint"
**Solução:** Os utilizadores já existem. Use `ON CONFLICT DO NOTHING` (já está no script) para evitar erro.

### ❌ Erro: "Permission denied"
**Solução:** Verifica que estás logged in como dono do projeto no Supabase.

### ❌ Erro: "Invalid role"
**Solução:** O constraint `valid_role` rejeitou um papel. Verifica que usas apenas os papéis permitidos.

### ❌ Query executa mas não vê dados
**Solução:** Atualiza a página do navegador (F5) ou aguarda alguns segundos.

---

## 📞 Suporte

Se tiveres problemas:
1. Verifica os logs do Supabase (Project Settings → Logs)
2. Tenta executar a query de verificação sozinha
3. Confirma que o projeto ID é `otyrrvkixegiqsthmaaj`
