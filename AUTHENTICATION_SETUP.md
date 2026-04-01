# 🔐 Guia de Configuração - Autenticação Instaladores

## 📋 Resumo da Implementação

Implementei um **fluxo completo de autenticação** para instaladores usando:
- **Frontend**: React com componente `InstallerLogin.jsx`
- **Backend**: FastAPI com serviço Supabase (`services/supabase_auth.py`)
- **Database**: Supabase PostgreSQL com tabela `gateway_users`

---

## 🚀 Configuração Passo a Passo

### **Passo 1: Executar SQL no Supabase** (OBRIGATÓRIO)

1. Acede a: https://supabase.com/dashboard/project/otyrrvkixegiqsthmaaj/sql
2. Clica "+ New Query"
3. Cola o script de `SETUP_INSTALACAO_DATABASE.sql`
4. Executa o script
5. Verifica que a tabela `gateway_users` foi criada e contém 2 utilizadores de teste

**Utilizadores de Teste Criados:**
```
1. instalador.teste1@company.com (papel: instalador_visual)
2. gerente.instalacao@company.com (papel: gerente_instalacao)
```

### **Passo 2: Configurar Variáveis de Ambiente**

No arquivo `backend/.env`, atualiza com as chaves do Supabase:

```env
# Supabase Configuration
SUPABASE_URL=https://otyrrvkixegiqsthmaaj.supabase.co
SUPABASE_KEY=your-supabase-anon-key          # ← Substitui com chave real
SUPABASE_SERVICE_ROLE=your-service-role-key  # ← Substitui com chave real

# MongoDB Configuration
MONGO_URL=mongodb://localhost:27017/instalador
DB_NAME=instalador
```

**Como obter as chaves Supabase:**
1. Dashboard Supabase → Projecto otyrrvkixegiqsthmaaj
2. Settings → API
3. Copia a chave "anon public" e "service_role"

### **Passo 3: Instalar Dependências Supabase (Backend)**

```bash
cd backend
pip install httpx  # Já está em requirements.txt se não tiveres
```

### **Passo 4: Iniciar Ambiente Local**

**Terminal 1 - Backend:**
```bash
cd backend
python -m uvicorn server:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm install
npm start
```

---

## 🔗 Rotas e Endpoints

### **Frontend Routes**
- `/login` — Login padrão (usuários administrativos)
- `/installer/login` — Login de instaladores ✨ NOVO
- `/installer/dashboard` — Dashboard do instalador (protegido)

### **Backend Endpoints**

**Login de Instalador:**
```
POST /api/auth/installer/login
Body: { "email": "...", "password": "..." }
Response: { "access_token": "...", "user": { ... } }
```

**Obter Dados do Utilizador:**
```
GET /api/auth/installer/me
Headers: Authorization: Bearer {token}
Response: { "id": "...", "email": "...", "name": "...", "role": "..." }
```

---

## 🧪 Testar Localmente

### **1. Testar Backend com cURL:**

```bash
curl -X POST http://localhost:8000/api/auth/installer/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "instalador.teste1@company.com",
    "password": "senha-test"
  }'
```

**Resposta esperada:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "instalador.teste1@company.com",
    "name": "João Silva - Instalador",
    "role": "instalador_visual"
  }
}
```

### **2. Testar Frontend:**

1. Acede a http://localhost:3000/installer/login
2. Submete credenciais de teste
3. Deverás ver sucesso e redirecionamento para `/installer/dashboard`

---

## 📁 Arquivos Criados/Modificados

### **Novos Arquivos:**
- `backend/services/supabase_auth.py` — Integração Supabase
- `frontend/src/pages/InstallerLogin.jsx` — Componente de login
- `SETUP_INSTALACAO_DATABASE.sql` — Script de criação de tabela
- `TESTING_GUIDE.md` — Guia detalhado de testes

### **Modificados:**
- `backend/.env` — Adicionadas variáveis Supabase
- `backend/server.py` — Endpoints `/auth/installer/`
- `frontend/src/App.js` — Rota `/installer/login`

---

## 🔍 Verificação de Sucesso

✅ **Backend:**
- [ ] Servidor inicia sem erros
- [ ] Endpoint `/health` devolve status "healthy"
- [ ] Endpoint `/api/auth/installer/login` responde com token

✅ **Frontend:**
- [ ] Página `/installer/login` carrega corretamente
- [ ] Login com credenciais válidas funciona
- [ ] Token é armazenado em localStorage
- [ ] Redirecionamento automático para `/installer/dashboard`

✅ **Database:**
- [ ] Tabela `gateway_users` existe em Supabase
- [ ] 2 utilizadores de teste estão criados
- [ ] RLS policies estão ativas

---

## 🚨 Troubleshooting

### **Erro: "Credenciais inválidas"**
- Verifica que o SQL foi executado no Supabase
- Confirma que `is_active = true` para o utilizador
- Testa a query de verificação do SQL script

### **Erro: "SUPABASE_KEY not configured"**
- Verifica `.env` tem a variável `SUPABASE_KEY`
- Recarrega o processo do backend

### **Erro 401 no Frontend**
- Abre DevTools → Network
- Verifica se o pedido POST para `/auth/installer/login` volta com erro
- Lê a resposta para mais detalhes

### **Token não persiste**
- Verifica se localStorage está funcionando
- Abre DevTools → Application → Local Storage → http://localhost:3000
- Verifica se `token` e `user` estão lá

---

## 📞 Próximos Passos

1. **Integrar com Dashboard do Instalador:**
   - Usar o token para buscar jobs atribuídos
   - Exibir informações personalizadas

2. **Adicionar Redefinição de Senha:**
   - Implementar flow de "Esqueci Senha" para instaladores

3. **Dois Fatores (2FA) Opcional:**
   - Adicionar autenticação por SMS ou email

4. **Deploy em Produção:**
   - Configurar Vercel + Supabase para produção
   - Testar fluxo completo

---

## 📚 Documentação Relevante

- [Supabase Docs](https://supabase.com/docs)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [React Authentication Patterns](https://reactrouter.com/en/main/guides/data-fetching)

---

**Última atualização:** 2026-04-01  
**Status:** ✅ Implementação Completa  
**Próximo:** Executar SQL e testar
