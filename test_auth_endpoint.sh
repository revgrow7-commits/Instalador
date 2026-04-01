#!/bin/bash

# Script para testar o endpoint de autenticação do instalador
# Requer que o backend esteja rodando em http://localhost:8000

echo "=========================================="
echo "Teste de Autenticação - Endpoint Instalador"
echo "=========================================="
echo ""

API_URL="http://localhost:8000/api"
INSTALLER_EMAIL="instalador.teste1@company.com"
INSTALLER_PASSWORD="teste123"

# Teste 1: Verificar se o backend está online
echo "[1/4] Verificando se backend está online..."
response=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/../health")

if [ "$response" = "200" ]; then
    echo "✓ Backend está online"
else
    echo "✗ Backend não respondeu. Status: $response"
    echo "  Inicia o backend com: python -m uvicorn server:app --reload"
    exit 1
fi

echo ""
echo "[2/4] Testando login com credenciais válidas..."

# Teste 2: Login com credenciais corretas
login_response=$(curl -s -X POST "$API_URL/auth/installer/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$INSTALLER_EMAIL\",
    \"password\": \"$INSTALLER_PASSWORD\"
  }")

echo "Resposta:"
echo "$login_response" | python -m json.tool 2>/dev/null || echo "$login_response"

# Extrai o token
access_token=$(echo "$login_response" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$access_token" ]; then
    echo ""
    echo "✗ Login falhou - sem token na resposta"
else
    echo ""
    echo "✓ Login bem-sucedido!"
    echo "  Token: ${access_token:0:50}..."
fi

echo ""
echo "[3/4] Testando com credenciais inválidas..."

# Teste 3: Login com credenciais incorretas
invalid_response=$(curl -s -X POST "$API_URL/auth/installer/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"instalador.teste1@company.com\",
    \"password\": \"senha_errada\"
  }")

echo "Resposta esperada (erro 401):"
echo "$invalid_response" | python -m json.tool 2>/dev/null || echo "$invalid_response"

echo ""
echo "[4/4] Testando com gerente..."

# Teste 4: Login como gerente
manager_response=$(curl -s -X POST "$API_URL/auth/installer/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"gerente.instalacao@company.com\",
    \"password\": \"teste123\"
  }")

manager_token=$(echo "$manager_response" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$manager_token" ]; then
    echo "✗ Login de gerente falhou"
else
    echo "✓ Login de gerente bem-sucedido!"
    echo "  Token: ${manager_token:0:50}..."
fi

echo ""
echo "=========================================="
echo "✓ Testes completados!"
echo "=========================================="
echo ""
echo "Próximos passos:"
echo "1. Inicia o frontend: cd frontend && npm start"
echo "2. Acede a http://localhost:3000/installer/login"
echo "3. Usa credenciais: instalador.teste1@company.com / teste123"
echo ""
