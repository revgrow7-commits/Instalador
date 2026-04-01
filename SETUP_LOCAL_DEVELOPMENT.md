# 🚀 Setup Local Development - Autenticação

## 📋 Resumo

Criei uma infraestrutura de autenticação que funciona de duas formas:
1. **Desenvolvimento Local** - sem depender de Supabase
2. **Produção** - com Supabase integrado

---

## 💻 Setup Local (Recomendado para Testar)

### **Passo 1: Instalar Dependências do Backend**

```bash
cd backend
pip install -r requirements.txt
```

**Dependências necessárias:**
- fastapi
- motor (async MongoDB)
- pydantic
- python-jose
- passlib
- httpx (para Supabase)

### **Passo 2: Configurar MongoDB Localmente**

**Opção A: MongoDB via Docker** (Recomendado)
```bash
docker run -d \
  --name mongodb \
  -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=admin \
  mongo:latest
```

**Opção B: MongoDB instalado localmente**
```bash
# No Windows
mongod.exe

# No macOS
brew services start mongodb-community

# No Linux
sudo service mongod start
```

### **Passo 3: Iniciar Backend**

```bash
cd backend
python -m uvicorn server:app --reload --port 8000
```

**Verifica que está pronto:**
```bash
curl http://localhost:8000/health
# Resposta esperada: {"status": "healthy", "service": "industria-visual-api"}
```

### **Passo 4: Iniciar Frontend**

```bash
cd frontend
npm install
npm start
```

Abrirá automaticamente em `http://localhost:3000`

---

## 🧪 Testar Autenticação Localmente

### **Teste 1: Login de Instalador via cURL**

Cria primeiro um utilizador de teste em MongoDB:

```bash
# 1. Criar um utilizador de teste
curl -X POST http://localhost:8000/api/auth/installer/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test.installer@company.com",
    "password": "Test@1234"
  }'
```

**Nota:** Este endpoint tentará validar contra Supabase. Para desenvolvimento local, precisamos de um mock.

### **Teste 2: Usando o Frontend**

1. **Acede a http://localhost:3000/installer/login**
2. **Usa credenciais de teste:**
   - Email: `instalador.teste1@company.com`
   - Password: (qualquer coisa)
3. **Esperado:** Vês erro ou sucesso dependendo do backend

---

## 🔧 Modo Development - Bypass Supabase

Para testar localmente **sem precisar de Supabase**, vou criar um mock:

<br/>

### **Criar arquivo: `backend/services/supabase_auth_mock.py`**

```python
"""
Mock de autenticação Supabase para desenvolvimento local.
Usa dados em memória para testes.
"""
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Dados de teste em memória
TEST_USERS = {
    "instalador.teste1@company.com": {
        "id": "test-installer-1",
        "email": "instalador.teste1@company.com",
        "name": "João Silva - Instalador",
        "password": "teste123",  # Em produção, usar hash bcrypt
        "role": "instalador_visual",
        "is_active": True
    },
    "gerente.instalacao@company.com": {
        "id": "test-manager-1",
        "email": "gerente.instalacao@company.com",
        "name": "Maria Santos - Gerente",
        "password": "teste123",
        "role": "gerente_instalacao",
        "is_active": True
    }
}


async def login_installer(email: str, password: str) -> dict:
    """
    LOGIN MOCK PARA DESENVOLVIMENTO LOCAL.
    Em produção, usa Supabase real.
    """
    user = TEST_USERS.get(email)
    
    if not user:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    
    # Verificação simples (em produção usar bcrypt)
    if user["password"] != password and password != "teste123":
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    
    if not user["is_active"]:
        raise HTTPException(status_code=401, detail="Conta desativada")
    
    logger.info(f"Mock login successful: {email}")
    
    return {
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "permissions": {"roles": [user["role"]]}
        }
    }
```

### **Modificar: `backend/server.py`**

Adiciona este import no topo do arquivo:

```python
import os
USE_MOCK_AUTH = os.environ.get("USE_MOCK_AUTH", "true").lower() == "true"
```

Depois substitui o endpoint de auth do instalador:

```python
@api_router.post("/auth/installer/login")
async def installer_login(credentials: dict):
    """Login para instaladores"""
    from services.supabase_auth_mock import login_installer as mock_login
    from services.supabase_auth import login_installer as real_login
    
    email = credentials.get('email')
    password = credentials.get('password')
    
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email e senha são obrigatórios")
    
    # Usar mock em desenvolvimento, real em produção
    if USE_MOCK_AUTH:
        result = await mock_login(email, password)
    else:
        result = await real_login(email, password)
    
    # Gerar JWT token
    access_token = create_access_token(
        data={"sub": result['user']['id'], "email": result['user']['email'], "role": result['user']['role']}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": result['user']
    }
```

---

## 🎯 Testar com Mock Localmente

### **Passo 1: Configurar variável de ambiente**

No `backend/.env`, adiciona:
```env
USE_MOCK_AUTH=true
```

### **Passo 2: Testar via cURL**

```bash
curl -X POST http://localhost:8000/api/auth/installer/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "instalador.teste1@company.com",
    "password": "teste123"
  }'
```

**Resposta esperada:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": "test-installer-1",
    "email": "instalador.teste1@company.com",
    "name": "João Silva - Instalador",
    "role": "instalador_visual"
  }
}
```

### **Passo 3: Testar no Frontend**

1. Acede a http://localhost:3000/installer/login
2. Usa:
   - Email: `instalador.teste1@company.com`
   - Password: `teste123`
3. Deverás ver sucesso e redirecionamento para `/installer/dashboard`

---

## 🔄 Fluxo de Desenvolvimento

```
[Frontend] → POST /api/auth/installer/login
    ↓
[Backend Mock] (desenvolvimento) ou [Supabase] (produção)
    ↓
Retorna: { access_token, user }
    ↓
[Frontend] armazena em localStorage
    ↓
Redireciona para /installer/dashboard
```

---

## ✅ Checklist de Testes Locais

- [ ] Backend inicia sem erros
- [ ] Endpoint `/health` responde
- [ ] Mock auth retorna token válido
- [ ] Frontend acessa `/installer/login`
- [ ] Login com credenciais de teste funciona
- [ ] Token é armazenado em localStorage
- [ ] Redirecionamento automático funciona

---

## 📦 Próximas Etapas

### **Para Desenvolvimento:**
✅ Usar mock local (já pronto)

### **Para Produção:**
1. Executar SQL no Supabase (via SUPABASE_SETUP_MANUAL.md)
2. Obter chaves de API do Supabase
3. Definir `USE_MOCK_AUTH=false` em `.env`
4. Deploy em Vercel + Supabase

---

## 🆘 Troubleshooting

### Erro: "Cannot connect to MongoDB"
**Solução:** Inicia MongoDB (Docker ou local)

### Erro: "Module not found: requests"
**Solução:** `pip install requests`

### Login falha com "Credenciais inválidas"
**Solução:** Verifica email/senha corretos:
- Email: `instalador.teste1@company.com`
- Senha: `teste123`

### Token não persiste no frontend
**Solução:** Abre DevTools → Application → Local Storage → verifica se `token` está lá

---

## 📚 Estrutura de Ficheiros

```
Instalador/
├── backend/
│   ├── services/
│   │   ├── supabase_auth.py (real Supabase)
│   │   └── supabase_auth_mock.py (mock para dev)
│   ├── server.py (endpoints)
│   └── .env (configuração)
├── frontend/
│   └── src/
│       └── pages/
│           └── InstallerLogin.jsx
└── SETUP_LOCAL_DEVELOPMENT.md (este arquivo)
```

---

**Última atualização:** 2026-04-01  
**Status:** Pronto para desenvolvimento local
