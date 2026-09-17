# Instruções de Execução - Sistema Híbrido

## Pré-requisitos

### Sistema Operacional
- Ubuntu 20.04+ ou similar
- Python 3.8+
- pip3

### Bancos de Dados
- **MongoDB** (opcional, mas recomendado para funcionalidade completa)
- **SQLite** (incluído com Python)

## Instalação Passo a Passo

### 1. Preparar o Ambiente

```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Python e pip (se não estiverem instalados)
sudo apt install python3 python3-pip python3-venv -y

# Instalar SQLite (para debug/administração)
sudo apt install sqlite3 -y
```

### 2. Configurar MongoDB (Opcional)

#### Opção A: MongoDB Local
```bash
# Instalar MongoDB
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt update
sudo apt install -y mongodb-org

# Iniciar MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod

# Verificar status
sudo systemctl status mongod
```

#### Opção B: MongoDB Atlas (Cloud)
1. Criar conta em https://cloud.mongodb.com
2. Criar cluster gratuito
3. Obter string de conexão
4. Atualizar `MONGO_URI` no arquivo `.env`

#### Opção C: Sem MongoDB
- O sistema funcionará com limitações (sem login/cadastro)
- Apenas funcionalidades SQLite estarão disponíveis

### 3. Configurar o Projeto

```bash
# Navegar para o diretório do projeto
cd /caminho/para/esteiraquasela

# Criar ambiente virtual (recomendado)
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### 4. Configurar Variáveis de Ambiente

Editar o arquivo `.env`:

```env
# MongoDB (ajustar conforme sua configuração)
MONGO_URI=mongodb://localhost:27017/

# Ou para MongoDB Atlas:
# MONGO_URI=mongodb+srv://usuario:senha@cluster.mongodb.net/recrutamento

# Configurações da aplicação
SECRET_KEY=chave-secreta-mvp-recrutamento-2024
MODO_IA=local
TOP_JOBS=3
```

### 5. Executar a Aplicação

```bash
# Executar versão híbrida
python3 app_hibrido.py
```

A aplicação estará disponível em: `http://localhost:5001`

## Verificação da Instalação

### 1. Verificar Logs de Inicialização

Ao executar `python3 app_hibrido.py`, você deve ver:

```
✅ MongoDB conectado para autenticação!
✅ Banco SQLite inicializado!
 * Serving Flask app 'app_hibrido'
 * Debug mode: on
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5001
```

**Ou, se MongoDB não estiver disponível:**

```
⚠️ MongoDB não disponível: [detalhes do erro]
✅ Banco SQLite inicializado!
 * Serving Flask app 'app_hibrido'
 * Debug mode: on
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5001
```

### 2. Verificar Banco SQLite

```bash
# Verificar se o banco foi criado
ls -la recrutamento.db

# Verificar tabelas
sqlite3 recrutamento.db ".tables"
# Deve mostrar: candidaturas  notificacoes  vagas

# Verificar estrutura de uma tabela
sqlite3 recrutamento.db ".schema vagas"
```

### 3. Testar Conectividade MongoDB

```bash
# Se MongoDB local estiver rodando
mongo --eval "db.runCommand('ping')"

# Ou usando Python
python3 -c "
import pymongo
try:
    client = pymongo.MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
    client.server_info()
    print('✅ MongoDB conectado!')
except Exception as e:
    print(f'❌ MongoDB erro: {e}')
"
```

## Testando as Funcionalidades

### 1. Teste Básico (Sem MongoDB)

1. Acesse `http://localhost:5001`
2. Tente acessar páginas que não requerem login
3. Verifique se mensagens de erro são apropriadas para login/cadastro

### 2. Teste Completo (Com MongoDB)

1. **Cadastro de Empresa**:
   - Acesse `http://localhost:5001/cadastro_empresa`
   - Cadastre uma empresa teste
   - Verifique se foi salva no MongoDB

2. **Login de Empresa**:
   - Faça login com a empresa cadastrada
   - Acesse o dashboard

3. **Criar Vaga**:
   - No dashboard da empresa, crie uma vaga
   - Verifique se foi salva no SQLite

4. **Cadastro de Candidato**:
   - Cadastre um candidato teste
   - Verifique se foi salvo no MongoDB

5. **Candidatura**:
   - Faça login como candidato
   - Candidate-se à vaga criada
   - Verifique se foi salva no SQLite

### 3. Verificar Dados nos Bancos

```bash
# Verificar dados no SQLite
sqlite3 recrutamento.db "SELECT * FROM vagas;"
sqlite3 recrutamento.db "SELECT * FROM candidaturas;"

# Verificar dados no MongoDB (se disponível)
mongo recrutamento --eval "db.empresas.find().pretty()"
mongo recrutamento --eval "db.candidatos.find().pretty()"
```

## Solução de Problemas

### Erro: "ModuleNotFoundError"
```bash
# Reinstalar dependências
pip install -r requirements.txt

# Ou instalar módulo específico
pip install pymongo flask python-dotenv
```

### Erro: "MongoDB connection refused"
```bash
# Verificar se MongoDB está rodando
sudo systemctl status mongod

# Iniciar MongoDB se necessário
sudo systemctl start mongod

# Ou ajustar MONGO_URI no .env para usar serviço externo
```

### Erro: "Permission denied" no SQLite
```bash
# Verificar permissões do diretório
ls -la recrutamento.db

# Ajustar permissões se necessário
chmod 664 recrutamento.db
```

### Erro: "Port already in use"
```bash
# Verificar processos na porta 5001
sudo lsof -i :5001

# Matar processo se necessário
sudo kill -9 <PID>

# Ou alterar porta no app_hibrido.py (última linha)
```

### Aplicação não carrega páginas
1. Verificar se templates/ existe e contém arquivos HTML
2. Verificar se static/ existe para CSS/JS
3. Verificar logs de erro no terminal

## Configuração para Produção

### 1. Usar WSGI Server

```bash
# Instalar gunicorn
pip install gunicorn

# Executar com gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 app_hibrido:app
```

### 2. Configurar Nginx (Opcional)

```nginx
server {
    listen 80;
    server_name seu-dominio.com;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. Configurar Variáveis de Ambiente de Produção

```env
SECRET_KEY=chave-super-secreta-producao
MONGO_URI=mongodb://usuario:senha@servidor-mongo:27017/recrutamento
MODO_IA=producao
```

## Backup e Manutenção

### Backup SQLite
```bash
# Backup simples
cp recrutamento.db backup_$(date +%Y%m%d_%H%M%S).db

# Backup com dump
sqlite3 recrutamento.db ".dump" > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Backup MongoDB
```bash
# Backup completo
mongodump --db recrutamento --out backup_mongo_$(date +%Y%m%d_%H%M%S)

# Restore
mongorestore backup_mongo_YYYYMMDD_HHMMSS/
```

### Logs
```bash
# Executar com logs em arquivo
python3 app_hibrido.py > app.log 2>&1 &

# Monitorar logs
tail -f app.log
```

## Contato e Suporte

Para problemas específicos:
1. Verificar logs de erro
2. Consultar documentação do Flask/MongoDB/SQLite
3. Verificar issues conhecidos no repositório

