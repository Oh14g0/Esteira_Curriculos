# Instruções de Execução - Sistema com Fallback Completo

## Visão Geral

Este guia fornece instruções detalhadas para configurar e executar o sistema de esteira de processos com fallback completo. O sistema pode operar em dois modos:

1. **Modo Híbrido**: MongoDB (primário) + SQLite (secundário)
2. **Modo Fallback**: SQLite (completo) quando MongoDB não está disponível

## Pré-requisitos

### Sistema Operacional
- Ubuntu 20.04+ ou similar
- Python 3.8+
- pip3

### Bancos de Dados
- **SQLite**: Incluído com Python (obrigatório)
- **MongoDB**: Opcional, mas recomendado para produção

## Cenários de Instalação

### Cenário 1: Instalação Completa (MongoDB + SQLite)

#### 1.1. Preparar o Ambiente
```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Python e dependências
sudo apt install python3 python3-pip python3-venv sqlite3 -y
```

#### 1.2. Instalar MongoDB
```bash
# Importar chave pública do MongoDB
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -

# Adicionar repositório
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list

# Instalar MongoDB
sudo apt update
sudo apt install -y mongodb-org

# Iniciar e habilitar MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod

# Verificar status
sudo systemctl status mongod
```

#### 1.3. Configurar o Projeto
```bash
# Navegar para o diretório do projeto
cd /caminho/para/esteiraquasela

# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

#### 1.4. Configurar Variáveis de Ambiente
```bash
# Editar arquivo .env
nano .env
```

Conteúdo do `.env`:
```env
# MongoDB (primário)
MONGO_URI=mongodb://localhost:27017/

# Configurações da aplicação
SECRET_KEY=chave-secreta-mvp-recrutamento-2024
MODO_IA=local
TOP_JOBS=3
```

#### 1.5. Executar a Aplicação
```bash
python3 app_fallback_completo.py
```

**Saída esperada:**
```
✅ MongoDB conectado como banco primário!
✅ Banco SQLite inicializado com fallback completo!
 * Serving Flask app 'app_fallback_completo'
 * Debug mode: on
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5001
```

### Cenário 2: Instalação Apenas SQLite (Fallback Completo)

#### 2.1. Preparar o Ambiente
```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar apenas Python e SQLite
sudo apt install python3 python3-pip python3-venv sqlite3 -y
```

#### 2.2. Configurar o Projeto
```bash
# Navegar para o diretório do projeto
cd /caminho/para/esteiraquasela

# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

#### 2.3. Configurar Variáveis de Ambiente
```bash
# Editar arquivo .env
nano .env
```

Conteúdo do `.env` (MongoDB opcional):
```env
# MongoDB (opcional - pode ser comentado ou removido)
# MONGO_URI=mongodb://localhost:27017/

# Configurações da aplicação
SECRET_KEY=chave-secreta-mvp-recrutamento-2024
MODO_IA=local
TOP_JOBS=3
```

#### 2.4. Executar a Aplicação
```bash
python3 app_fallback_completo.py
```

**Saída esperada:**
```
⚠️ MongoDB não disponível: [Errno 111] Connection refused
🔄 Usando SQLite como fallback completo para todas as operações
✅ Banco SQLite inicializado com fallback completo!
 * Serving Flask app 'app_fallback_completo'
 * Debug mode: on
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5001
```

### Cenário 3: MongoDB Atlas (Cloud)

#### 3.1. Configurar MongoDB Atlas
1. Criar conta em https://cloud.mongodb.com
2. Criar cluster gratuito
3. Configurar usuário e senha
4. Obter string de conexão
5. Adicionar IP à whitelist

#### 3.2. Configurar Variáveis de Ambiente
```env
# MongoDB Atlas
MONGO_URI=mongodb+srv://usuario:senha@cluster.mongodb.net/recrutamento

# Configurações da aplicação
SECRET_KEY=chave-secreta-mvp-recrutamento-2024
MODO_IA=local
TOP_JOBS=3
```

## Verificação da Instalação

### 1. Verificar Logs de Inicialização

Ao executar a aplicação, observe as mensagens:

#### MongoDB Disponível:
```
✅ MongoDB conectado como banco primário!
✅ Banco SQLite inicializado com fallback completo!
```

#### MongoDB Indisponível:
```
⚠️ MongoDB não disponível: [detalhes do erro]
🔄 Usando SQLite como fallback completo para todas as operações
✅ Banco SQLite inicializado com fallback completo!
```

### 2. Verificar Banco SQLite

```bash
# Verificar se o banco foi criado
ls -la recrutamento.db

# Verificar tabelas (deve incluir empresas e candidatos)
sqlite3 recrutamento.db ".tables"
# Saída esperada: candidatos  candidaturas  empresas  notificacoes  vagas

# Verificar estrutura da tabela empresas
sqlite3 recrutamento.db ".schema empresas"

# Verificar estrutura da tabela candidatos
sqlite3 recrutamento.db ".schema candidatos"
```

### 3. Testar Conectividade MongoDB (se aplicável)

```bash
# Teste direto
mongo --eval "db.runCommand('ping')"

# Teste via Python
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

### Teste 1: Funcionalidade Básica (Qualquer Cenário)

1. **Acessar a aplicação**: `http://localhost:5001`
2. **Cadastrar empresa**: Ir para cadastro de empresa e criar uma conta
3. **Login empresa**: Fazer login com a empresa criada
4. **Criar vaga**: No dashboard, criar uma vaga de teste
5. **Cadastrar candidato**: Criar uma conta de candidato
6. **Login candidato**: Fazer login como candidato
7. **Candidatar-se**: Candidatar-se à vaga criada

### Teste 2: Verificar Fallback (MongoDB → SQLite)

1. **Iniciar com MongoDB**: Executar aplicação com MongoDB funcionando
2. **Criar dados**: Cadastrar empresa e candidato
3. **Parar MongoDB**: `sudo systemctl stop mongod`
4. **Reiniciar aplicação**: Deve mostrar mensagem de fallback
5. **Testar funcionalidades**: Login deve funcionar com dados do SQLite

### Teste 3: Verificar Dados nos Bancos

#### SQLite:
```bash
# Verificar empresas
sqlite3 recrutamento.db "SELECT * FROM empresas;"

# Verificar candidatos
sqlite3 recrutamento.db "SELECT * FROM candidatos;"

# Verificar vagas
sqlite3 recrutamento.db "SELECT * FROM vagas;"

# Verificar candidaturas
sqlite3 recrutamento.db "SELECT * FROM candidaturas;"
```

#### MongoDB (se disponível):
```bash
# Conectar ao MongoDB
mongo recrutamento

# Verificar empresas
db.empresas.find().pretty()

# Verificar candidatos
db.candidatos.find().pretty()
```

## Solução de Problemas

### Problema: "ModuleNotFoundError"
```bash
# Verificar ambiente virtual
source venv/bin/activate

# Reinstalar dependências
pip install -r requirements.txt

# Instalar módulos específicos se necessário
pip install pymongo flask python-dotenv werkzeug
```

### Problema: "MongoDB connection refused"
```bash
# Verificar status do MongoDB
sudo systemctl status mongod

# Iniciar MongoDB se parado
sudo systemctl start mongod

# Verificar logs do MongoDB
sudo journalctl -u mongod

# Alternativa: usar apenas SQLite
# Comentar MONGO_URI no .env
```

### Problema: "Permission denied" no SQLite
```bash
# Verificar permissões do diretório
ls -la recrutamento.db

# Ajustar permissões
chmod 664 recrutamento.db
chown $USER:$USER recrutamento.db

# Verificar permissões do diretório
chmod 755 .
```

### Problema: "Port already in use"
```bash
# Verificar processos na porta 5001
sudo lsof -i :5001

# Matar processo se necessário
sudo kill -9 <PID>

# Ou alterar porta no arquivo Python
# Última linha: app.run(host='0.0.0.0', port=5002, debug=True)
```

### Problema: Dados não aparecem após fallback
```bash
# Verificar se dados estão no banco correto
sqlite3 recrutamento.db "SELECT COUNT(*) FROM empresas;"
sqlite3 recrutamento.db "SELECT COUNT(*) FROM candidatos;"

# Se vazio, dados estão apenas no MongoDB
# Criar novos dados ou implementar migração
```

## Configuração para Produção

### 1. Usar WSGI Server
```bash
# Instalar gunicorn
pip install gunicorn

# Executar com gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 app_fallback_completo:app
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
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 3. Variáveis de Ambiente de Produção
```env
SECRET_KEY=chave-super-secreta-producao-muito-longa
MONGO_URI=mongodb://usuario:senha@servidor-mongo:27017/recrutamento
MODO_IA=producao
TOP_JOBS=5
```

### 4. Monitoramento
```bash
# Executar com logs
python3 app_fallback_completo.py > app.log 2>&1 &

# Monitorar logs
tail -f app.log

# Verificar status dos bancos
grep -E "(MongoDB|SQLite)" app.log
```

## Backup e Manutenção

### Backup SQLite
```bash
# Backup simples
cp recrutamento.db backup_$(date +%Y%m%d_%H%M%S).db

# Backup com dump SQL
sqlite3 recrutamento.db ".dump" > backup_$(date +%Y%m%d_%H%M%S).sql

# Restaurar backup
sqlite3 recrutamento_novo.db < backup_YYYYMMDD_HHMMSS.sql
```

### Backup MongoDB
```bash
# Backup completo
mongodump --db recrutamento --out backup_mongo_$(date +%Y%m%d_%H%M%S)

# Backup específico
mongodump --db recrutamento --collection empresas --out backup_empresas

# Restaurar
mongorestore backup_mongo_YYYYMMDD_HHMMSS/
```

### Migração entre Bancos
```bash
# Exportar dados do MongoDB para SQLite (script personalizado necessário)
python3 -c "
import pymongo
import sqlite3
from bson import ObjectId

# Conectar aos bancos
mongo_client = pymongo.MongoClient('mongodb://localhost:27017/')
mongo_db = mongo_client.recrutamento
sqlite_conn = sqlite3.connect('recrutamento.db')

# Migrar empresas
for empresa in mongo_db.empresas.find():
    sqlite_conn.execute('''
        INSERT OR REPLACE INTO empresas (cnpj, nome, email, senha_hash, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (empresa['cnpj'], empresa['nome'], empresa['email'], 
          empresa['senha_hash'], empresa['created_at']))

sqlite_conn.commit()
print('Migração concluída!')
"
```

## Monitoramento e Alertas

### Scripts de Monitoramento
```bash
#!/bin/bash
# monitor_sistema.sh

# Verificar se aplicação está rodando
if ! pgrep -f "app_fallback_completo.py" > /dev/null; then
    echo "ALERTA: Aplicação não está rodando!"
    # Reiniciar aplicação
    cd /caminho/para/projeto
    python3 app_fallback_completo.py &
fi

# Verificar MongoDB
if ! mongo --eval "db.runCommand('ping')" > /dev/null 2>&1; then
    echo "AVISO: MongoDB não disponível - usando fallback SQLite"
fi

# Verificar SQLite
if [ ! -f "recrutamento.db" ]; then
    echo "ERRO: Banco SQLite não encontrado!"
fi
```

### Logs Estruturados
```bash
# Configurar logrotate para logs da aplicação
sudo nano /etc/logrotate.d/esteira-processos

# Conteúdo:
/caminho/para/projeto/app.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
```

## Contato e Suporte

Para problemas específicos:
1. **Verificar logs**: `tail -f app.log`
2. **Testar conectividade**: Scripts de teste fornecidos
3. **Consultar documentação**: Flask, MongoDB, SQLite
4. **Verificar issues**: Problemas conhecidos no repositório

### Comandos Úteis de Debug
```bash
# Status completo do sistema
python3 -c "
import pymongo
import sqlite3
import os

print('=== STATUS DO SISTEMA ===')
print(f'Arquivo SQLite existe: {os.path.exists(\"recrutamento.db\")}')

try:
    client = pymongo.MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
    client.server_info()
    print('MongoDB: ✅ Conectado')
except:
    print('MongoDB: ❌ Indisponível')

conn = sqlite3.connect('recrutamento.db')
cursor = conn.cursor()
cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")
tables = cursor.fetchall()
print(f'Tabelas SQLite: {[t[0] for t in tables]}')
conn.close()
"
```

