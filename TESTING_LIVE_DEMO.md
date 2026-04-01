# 🧪 Teste Live Demo - Agendamento de Jobs

## 📋 Problema Identificado

O frontend tem uma incompatibilidade de versão (Node.js v24 vs react-scripts).

**Solução:** Use Node.js v18 ou v20 em vez de v24.

---

## ✅ Como Testar (Passo-a-Passo)

### **Passo 0: Verificar/Mudar Versão do Node**

```bash
node --version
# Se for v24, instala nvm ou nvm-windows

# Com nvm
nvm install 20
nvm use 20
node --version  # Deve ser v20.x.x
```

### **Passo 1: Instalar Frontend**

```bash
cd frontend
npm install --legacy-peer-deps
```

### **Passo 2: Iniciar Serviços (3 Terminals)**

**Terminal 1 - Backend:**
```bash
cd backend
python -m uvicorn server:app --reload --port 8000
# Esperado: "Application startup complete"
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm start
# Esperado: "webpack compiled successfully"
# Abre automaticamente http://localhost:3000
```

**Terminal 3 - Opcional (Verificar Logs):**
```bash
curl http://localhost:8000/health
# {"status": "healthy", "service": "industria-visual-api"}
```

---

## 🎯 Teste de Autenticação

### **1. Aceder à Página de Login**

URL: `http://localhost:3000/installer/login`

Deverás ver:
- Logo "INDÚSTRIA VISUAL"
- Campo Email
- Campo Senha
- Botão "Entrar como Instalador"

### **2. Login com Credenciais de Teste**

**Dados:**
```
Email: instalador.teste1@company.com
Senha: teste123
```

**Esperado:**
- ✓ Toast com mensagem "Login realizado com sucesso!"
- ✓ Redirecionamento para `/installer/dashboard`
- ✓ Token armazenado em localStorage (DevTools → Application → Local Storage)

### **3. Verificar Dados do Utilizador**

Abre DevTools (F12) → Application → Local Storage → http://localhost:3000

Deverás ver:
```javascript
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": "test-installer-1",
    "email": "instalador.teste1@company.com",
    "name": "João Silva - Instalador",
    "role": "instalador_visual"
  }
}
```

---

## 📅 Teste de Agendamento de Jobs

### **1. Navegar para Jobs**

Após login, deverás ver uma sidebar com menu.

Clica em: **"Jobs"** ou acede a `http://localhost:3000/jobs`

### **2. Ver Lista de Jobs**

Deverás ver:
- Cards com jobs do Holdprint
- Informações: título, cliente, status, data
- Botões de ação

### **3. Agendador um Job**

**Opção A: Botão de Agendamento**
1. Clica em um job card
2. Procura botão "Agendar" ou "Schedule"
3. Seleciona data e hora
4. Clica "Confirmar"

**Opção B: Jobs → Agendar**
1. Clica botão "Agendar Job" na página Jobs
2. Seleciona job da lista
3. Escolhe data/hora
4. Seleciona instaladores
5. Confirma

**Esperado:**
- ✓ Modal de agendamento aparece
- ✓ Data-picker funciona
- ✓ Instaladores aparecem na lista
- ✓ Toast com confirmação "Job agendado com sucesso!"

---

## 🔧 Testes via cURL (Sem Frontend)

Se o frontend tiver problemas, podes testar via API diretamente:

### **1. Login**

```bash
curl -X POST http://localhost:8000/api/auth/installer/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "instalador.teste1@company.com",
    "password": "teste123"
  }' | jq
```

**Resposta:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {...}
}
```

### **2. Obter Dados do Utilizador**

```bash
TOKEN="<access_token_from_above>"

curl -X GET http://localhost:8000/api/auth/installer/me \
  -H "Authorization: Bearer $TOKEN" | jq
```

### **3. Listar Jobs**

```bash
curl -X GET http://localhost:8000/api/jobs \
  -H "Authorization: Bearer $TOKEN" | jq '.[:2]'
```

### **4. Agendar Job**

```bash
JOB_ID="<job_id_from_list>"

curl -X PUT http://localhost:8000/api/jobs/$JOB_ID/schedule \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scheduled_date": "2026-04-05T14:00:00Z",
    "installer_ids": ["test-installer-1"]
  }' | jq
```

---

## 📊 Fluxo Esperado (Diagramado)

```
┌──────────────────────────────────────┐
│  1. Login Page                       │
│  http://localhost:3000/installer/login
│  Email + Senha                       │
└────────────────┬──────────────────────┘
                 │ POST /auth/installer/login
                 ↓
         ┌───────────────────┐
         │ Backend Mock Auth │
         │ Valida credenciais│
         └─────────┬─────────┘
                   │ JWT Token gerado
                   ↓
         ┌─────────────────────────┐
         │ localStorage.setItem()  │
         │ - token                 │
         │ - user                  │
         └────────────┬────────────┘
                      │ Redirecionamento
                      ↓
         ┌──────────────────────────┐
         │ 2. Installer Dashboard   │
         │ /installer/dashboard     │
         └────────────┬─────────────┘
                      │ Clica em "Jobs"
                      ↓
         ┌──────────────────────────┐
         │ 3. Jobs List Page        │
         │ /jobs                    │
         │ GET /api/jobs            │
         │ Authorization: Bearer... │
         └────────────┬─────────────┘
                      │ Lista de jobs
                      │ (do Holdprint)
                      ↓
         ┌──────────────────────────┐
         │ 4. Schedule Job          │
         │ Modal de agendamento     │
         │ Data Picker +            │
         │ Instaladores Dropdown    │
         └────────────┬─────────────┘
                      │ PUT /jobs/{id}/schedule
                      │ + scheduled_date
                      │ + installer_ids
                      ↓
         ┌──────────────────────────┐
         │ 5. Success!              │
         │ Toast: "Agendado!"       │
         │ Job status: "scheduled"  │
         └──────────────────────────┘
```

---

## 🆘 Troubleshooting

### ❌ "EACCES: permission denied" no npm install
**Solução:**
```bash
sudo npm install --legacy-peer-deps  # macOS/Linux
# Ou reinstala Node.js no Windows
```

### ❌ "Cannot find module 'react-scripts'"
**Solução:**
```bash
rm -rf node_modules package-lock.json
npm install --legacy-peer-deps
```

### ❌ "webpack compiled with problems"
**Solução:**
- Verifica que backend está rodando
- Limpa browser cache (Ctrl+Shift+Delete)
- Reinicia frontend (Ctrl+C, depois npm start)

### ❌ "Network Error" no login
**Solução:**
- Verifica que backend está em http://localhost:8000
- Verifica CORS_ORIGINS em `.env`
- Check console do browser para mais detalhes

### ❌ "Cannot GET /installer/login"
**Solução:**
- Frontend não compilou. Verifica logs
- Aguarda "webpack compiled successfully"
- Hard refresh: Ctrl+Shift+R

---

## ✅ Checklist de Sucesso

- [ ] Node.js v18+ instalado
- [ ] Backend a rodar em http://localhost:8000/health
- [ ] Frontend a rodar em http://localhost:3000
- [ ] Acesso a /installer/login funciona
- [ ] Login com credenciais de teste bem-sucedido
- [ ] Token em localStorage após login
- [ ] Redirecionamento para /installer/dashboard funciona
- [ ] Página /jobs carrega
- [ ] Lista de jobs exibe items
- [ ] Modal de agendamento abre
- [ ] Agendamento de job conclui com sucesso

---

## 📚 Comando Rápido (Copiar-Colar)

Para testar tudo de uma vez:

```bash
# Terminal 1
cd ~/Instalador/backend
python -m uvicorn server:app --reload --port 8000

# Terminal 2
cd ~/Instalador/frontend
npm install --legacy-peer-deps
npm start

# Acede a:
# - Login: http://localhost:3000/installer/login
# - Dashboard: http://localhost:3000/installer/dashboard
# - Jobs: http://localhost:3000/jobs
```

---

**Status:** ✅ Pronto para testar após resolver versão Node.js
