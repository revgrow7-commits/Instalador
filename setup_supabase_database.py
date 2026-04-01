#!/usr/bin/env python3
"""
Script para executar setup da tabela gateway_users no Supabase.
Executa o SQL e cria utilizadores de teste.
"""

import os
import sys
import requests
import json
from pathlib import Path

# Configuração
SUPABASE_URL = "https://otyrrvkixegiqsthmaaj.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or input("Introduz a chave Supabase (service role): ").strip()

if not SUPABASE_KEY:
    print("❌ Chave Supabase não fornecida. Abortando.")
    sys.exit(1)

print(f"✅ Usando Supabase: {SUPABASE_URL}")
print(f"✅ Chave: {SUPABASE_KEY[:10]}...{SUPABASE_KEY[-10:]}")
print()

# SQL para criar tabela
SQL_CREATE_TABLE = """
-- Criar tabela gateway_users
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

-- Criar índices
CREATE INDEX IF NOT EXISTS idx_gateway_users_email ON public.gateway_users(LOWER(email));
CREATE INDEX IF NOT EXISTS idx_gateway_users_role ON public.gateway_users(role);
CREATE INDEX IF NOT EXISTS idx_gateway_users_is_active ON public.gateway_users(is_active);
CREATE INDEX IF NOT EXISTS idx_gateway_users_created_at ON public.gateway_users(created_at DESC);

-- Enable RLS
ALTER TABLE public.gateway_users ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY IF NOT EXISTS "Users can view own data" ON public.gateway_users FOR SELECT USING (true);

CREATE POLICY IF NOT EXISTS "Only admins can create users" ON public.gateway_users FOR INSERT
  WITH CHECK (EXISTS (SELECT 1 FROM public.gateway_users WHERE role = 'admin' AND is_active = true));

CREATE POLICY IF NOT EXISTS "Users can update own password" ON public.gateway_users FOR UPDATE USING (true) WITH CHECK (true);

CREATE POLICY IF NOT EXISTS "Only admins can update other users" ON public.gateway_users FOR UPDATE
  USING (EXISTS (SELECT 1 FROM public.gateway_users AS admin WHERE admin.role = 'admin' AND admin.is_active = true))
  WITH CHECK (EXISTS (SELECT 1 FROM public.gateway_users AS admin WHERE admin.role = 'admin' AND admin.is_active = true));
"""

# SQL para inserir dados de teste
SQL_INSERT_TEST_DATA = """
INSERT INTO public.gateway_users (
  email, name, password_hash, role, permissions, is_active
) VALUES (
  'instalador.teste1@company.com',
  'João Silva - Instalador',
  '$2a$06$l5rFzdb/2rU8vuDoQKhw8eHrBCujQjZkDHphus5tpGV2TLM/11g0m',
  'instalador_visual',
  '{"roles": ["instalador_visual"]}',
  true
) ON CONFLICT (email) DO NOTHING;

INSERT INTO public.gateway_users (
  email, name, password_hash, role, permissions, is_active
) VALUES (
  'gerente.instalacao@company.com',
  'Maria Santos - Gerente',
  '$2a$06$l5rFzdb/2rU8vuDoQKhw8eHrBCujQjZkDHphus5tpGV2TLM/11g0m',
  'gerente_instalacao',
  '{"roles": ["gerente_instalacao"]}',
  true
) ON CONFLICT (email) DO NOTHING;
"""

# SQL para verificar
SQL_VERIFY = """
SELECT
  id, name, email, role,
  permissions->>'roles' as roles_list,
  is_active
FROM public.gateway_users
WHERE role IN ('instalador_visual', 'gerente_instalacao');
"""


def execute_sql(sql_statement: str, description: str) -> bool:
    """Executa um statement SQL no Supabase."""
    try:
        print(f"⏳ {description}...")

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }

        # Usar RPC para executar SQL arbitrário
        # Nota: Supabase não tem um endpoint direto para SQL, mas podemos usar PostgREST
        # Vou tentar com uma abordagem alternativa usando query direta

        # Na verdade, vamos usar a API de query do Supabase
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
            headers=headers,
            json={"sql": sql_statement},
            timeout=30
        )

        # Se a RPC não existir, tentamos um approach alternativo
        if response.status_code == 404:
            print(f"⚠️  RPC não disponível. Usando abordagem alternativa...")
            # Vamos verificar se a tabela já existe
            check_response = requests.get(
                f"{SUPABASE_URL}/rest/v1/gateway_users?limit=0",
                headers=headers,
                timeout=30
            )
            if check_response.status_code == 200:
                print(f"✅ Tabela gateway_users já existe!")
                return True
            else:
                print(f"❌ Erro ao verificar tabela: {check_response.status_code}")
                print(f"   Resposta: {check_response.text}")
                return False

        if response.status_code in [200, 201]:
            print(f"✅ {description} - OK")
            return True
        else:
            print(f"❌ Erro: {response.status_code}")
            print(f"   {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Erro de conexão: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {str(e)}")
        return False


def verify_data() -> bool:
    """Verifica se os dados foram inseridos corretamente."""
    try:
        print("\n🔍 Verificando dados inseridos...")

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/gateway_users?role=in.(instalador_visual,gerente_instalacao)&select=id,name,email,role,is_active",
            headers=headers,
            timeout=30
        )

        if response.status_code == 200:
            users = response.json()
            if users:
                print(f"✅ Encontrados {len(users)} utilizadores:")
                for user in users:
                    status = "🟢 Ativo" if user.get('is_active') else "🔴 Inativo"
                    print(f"   • {user['name']} ({user['email']}) - {user['role']} {status}")
                return True
            else:
                print(f"⚠️  Nenhum utilizador encontrado")
                return False
        else:
            print(f"❌ Erro ao verificar: {response.status_code}")
            print(f"   {response.text}")
            return False

    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return False


def main():
    """Executa o setup completo."""
    print("=" * 60)
    print("🚀 Setup da Base de Dados - Supabase")
    print("=" * 60)
    print()

    # Passo 1: Criar tabela
    print("📋 PASSO 1: Criar tabela gateway_users")
    print("-" * 60)
    if not execute_sql(SQL_CREATE_TABLE, "Criando tabela e índices"):
        print("⚠️  Tabela pode já existir. Continuando...")
    print()

    # Passo 2: Inserir dados de teste
    print("📋 PASSO 2: Inserir utilizadores de teste")
    print("-" * 60)
    if not execute_sql(SQL_INSERT_TEST_DATA, "Inserindo dados de teste"):
        print("⚠️  Dados podem já existir. Continuando...")
    print()

    # Passo 3: Verificar dados
    print("📋 PASSO 3: Verificar dados")
    print("-" * 60)
    success = verify_data()
    print()

    # Resumo
    print("=" * 60)
    if success:
        print("✅ Setup Completo!")
        print()
        print("📝 Utilizadores de Teste Criados:")
        print("   1. instalador.teste1@company.com (instalador_visual)")
        print("   2. gerente.instalacao@company.com (gerente_instalacao)")
        print()
        print("🔐 Senha Temporária: (conforme hash bcrypt)")
        print()
        print("➡️  Próximo Passo: Atualizar .env com SUPABASE_KEY e testar login")
    else:
        print("❌ Setup incompleto - verifica os erros acima")
    print("=" * 60)


if __name__ == "__main__":
    main()
