# 🧪 Guia de Testes - Fluxo de Autenticação

## 1️⃣ Verificar Dados de Teste no Supabase

Após executar o SQL, verifica que estes utilizadores existem:

```
Email: instalador.teste1@company.com
Senha: (temporária - deve ser redefinida)
Papel: instalador_visual

Email: gerente.instalacao@company.com
Senha: (temporária - deve ser redefinida)
Papel: gerente_instalacao
```

## 2️⃣ Testar Backend Localmente

### Iniciar o Backend:
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn server:app --reload --port 8000
```

### Testar Endpoint de Login (via curl ou Postman):
```bash
curl -X POST http://localhost:8000/api/auth/installer/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "instalador.teste1@company.com",
    "password": "senha-do-teste"
  }'
```

**Resposta esperada:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": "uuid-aqui",
    "email": "instalador.teste1@company.com",
    "name": "João Silva - Instalador",
    "role": "instalador_visual"
  }
}
```

## 3️⃣ Testar Frontend Localmente

### Iniciar o Frontend:
```bash
cd frontend
npm install
npm start
```

### Passos de Teste:

**Passo 1: Acede ao Login de Instalador**
- URL: http://localhost:3000/installer/login
- Deverás ver um formulário com logo Indústria Visual

**Passo 2: Submete Credenciais**
- Email: `instalador.teste1@company.com`
- Senha: (a que está configurada no SQL)
- Clica "Entrar como Instalador"

**Passo 3: Verifica Redirecionamento**
- Deverás ser redirecionado para `/installer/dashboard`
- O token deve estar armazenado em `localStorage['token']`

**Passo 4: Verifica Proteção de Rotas**
- Se tentares aceder sem estar autenticado, és redirecionado para `/installer/login`
- Se estiveres autenticado e tentares aceder a `/login`, és redirecionado para `/installer/dashboard`

## 4️⃣ Checklist de Funcionalidades

- [ ] Endpoint `/auth/installer/login` devolve token JWT
- [ ] Token é armazenado em localStorage
- [ ] Redirecionamento automático funciona
- [ ] Botão "Voltar para login padrão" em `/installer/login`
- [ ] Mensagens de erro são exibidas no toast
- [ ] Loading state funciona (spinner aparece durante login)

## 5️⃣ Testar em Produção (Vercel + Supabase)

### Deploy:
```bash
git add .
git commit -m "feat: implement installer authentication flow"
git push origin main
```

Vercel fará deploy automaticamente.

### Testar em Produção:
- URL: https://instalador-lilac.vercel.app/installer/login
- Submete as mesmas credenciais de teste
- Verifica que o login funciona contra Supabase em produção

## 🐛 Troubleshooting

### Erro: "Credenciais inválidas"
- Verifica que o SQL foi executado completamente
- Confirma que os utilizadores existem em `gateway_users`
- Verifica que `is_active = true`

### Erro: "Chave de API não configurada"
- Verifica `.env` tem `SUPABASE_KEY`
- Certifica-te que é uma chave válida do Supabase
- Usa a chave **anon** para operações públicas (login)

### Erro: "Serviço indisponível"
- Verifica conexão com Supabase
- Testa se o URL do Supabase é acessível
- Verifica logs do backend para mais detalhes

### Token não é armazenado
- Abre DevTools → Application → Local Storage
- Verifica se `token` e `user` estão lá
- Se não estiverem, há erro no frontend após login bem-sucedido

## 📊 Métricas de Sucesso

✅ **Completo quando:**
- Login de instalador funciona com credenciais válidas
- Token JWT é gerado e armazenado
- Rotas protegidas redirecionam corretamente
- Erro handling funciona (credenciais inválidas, conta desativada)
- Integração MongoDB + Supabase funciona juntas
