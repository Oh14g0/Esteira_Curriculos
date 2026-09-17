# Sistema de Esteira de Processos - Versão com Fallback Completo

## Visão Geral

Esta é uma versão avançada do sistema de esteira de processos que utiliza uma arquitetura híbrida inteligente com fallback completo:
- **MongoDB** como banco primário para gerenciar login e cadastro de empresas e candidatos
- **SQLite** como banco secundário para todas as funcionalidades (vagas, candidaturas, notificações) e como **fallback completo** quando o MongoDB não estiver disponível

## Arquitetura Híbrida com Fallback Completo

### Cenário 1: MongoDB Disponível (Operação Normal)
- **MongoDB**: Empresas e candidatos (login/cadastro)
- **SQLite**: Vagas, candidaturas e notificações

### Cenário 2: MongoDB Indisponível (Fallback Completo)
- **SQLite**: Todas as operações (empresas, candidatos, vagas, candidaturas e notificações)

## Principais Características

### 🔄 Detecção Automática de Conectividade
- Verificação automática da disponibilidade do MongoDB na inicialização
- Monitoramento contínuo da conexão durante as operações
- Redirecionamento automático para SQLite quando necessário

### 🛡️ Fallback Inteligente
- Sistema funciona completamente mesmo sem MongoDB
- Transição transparente entre bancos de dados
- Mensagens informativas sobre o status da conectividade

### 🔧 Compatibilidade de IDs
- Normalização automática de IDs (ObjectId do MongoDB ↔ Integer do SQLite)
- Funções auxiliares para gerenciar diferentes tipos de identificadores
- Integridade referencial mantida em ambos os cenários

## Estrutura de Arquivos

```
esteiraquasela/
├── app_fallback_completo.py   # Aplicação principal com fallback completo
├── app_hibrido.py             # Versão híbrida anterior (sem fallback completo)
├── app.py                     # Aplicação original (apenas MongoDB)
├── migrate_to_mongo.py        # Script de migração (referência)
├── requirements.txt           # Dependências do projeto
├── .env                       # Variáveis de ambiente
├── recrutamento.db            # Banco SQLite (criado automaticamente)
├── templates/                 # Templates HTML
├── static/                    # Arquivos estáticos (CSS, JS)
├── uploads/                   # Diretório para upload de currículos
├── README_FALLBACK_COMPLETO.md # Esta documentação
└── INSTRUCOES_FALLBACK.md     # Instruções de execução
```

## Estrutura do Banco de Dados

### SQLite (Fallback Completo)

#### Tabela `empresas`
```sql
CREATE TABLE empresas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cnpj TEXT NOT NULL UNIQUE,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    senha_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Tabela `candidatos`
```sql
CREATE TABLE candidatos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    senha_hash TEXT NOT NULL,
    telefone TEXT,
    linkedin TEXT,
    endereco_completo TEXT,
    pretensao_salarial REAL,
    texto_curriculo TEXT,
    caminho_curriculo TEXT,
    experiencia TEXT,
    competencias TEXT,
    resumo_profissional TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Tabelas Existentes
- `vagas`: Informações sobre vagas
- `candidaturas`: Registros de candidaturas
- `notificacoes`: Sistema de notificações

### MongoDB (Primário)
- **Coleção `empresas`**: Espelha a estrutura da tabela SQLite
- **Coleção `candidatos`**: Espelha a estrutura da tabela SQLite

## Configuração e Instalação

### 1. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 2. Configurar Variáveis de Ambiente

Edite o arquivo `.env`:

```env
# MongoDB (opcional - sistema funciona sem ele)
MONGO_URI=mongodb://localhost:27017/

# Configurações da aplicação
SECRET_KEY=chave-secreta-mvp-recrutamento-2024
MODO_IA=local
TOP_JOBS=3
```

### 3. Executar a Aplicação

```bash
python3 app_fallback_completo.py
```

A aplicação estará disponível em: `http://localhost:5001`

## Funcionalidades por Cenário

### Cenário 1: MongoDB Disponível

#### Para Empresas
- **Cadastro e Login**: MongoDB (primário)
- **Criação de Vagas**: SQLite
- **Gerenciamento de Candidatos**: Dados híbridos (candidatos do MongoDB, candidaturas do SQLite)
- **Relatórios**: Análise completa com dados de ambos os bancos

#### Para Candidatos
- **Cadastro e Login**: MongoDB (primário)
- **Candidatura a Vagas**: SQLite
- **Visualização de Vagas**: Dados híbridos (vagas do SQLite, empresas do MongoDB)
- **Notificações**: SQLite

### Cenário 2: MongoDB Indisponível (Fallback)

#### Para Empresas
- **Cadastro e Login**: SQLite (fallback)
- **Criação de Vagas**: SQLite
- **Gerenciamento de Candidatos**: SQLite completo
- **Relatórios**: Análise com dados do SQLite

#### Para Candidatos
- **Cadastro e Login**: SQLite (fallback)
- **Candidatura a Vagas**: SQLite
- **Visualização de Vagas**: SQLite completo
- **Notificações**: SQLite

## Funções Principais do Sistema

### Detecção de Conectividade
```python
def check_mongo_connection():
    """Verifica se o MongoDB está disponível"""
    # Implementação com ping e tratamento de exceções
```

### Operações Híbridas
```python
def get_empresa_by_cnpj(cnpj):
    """Busca empresa por CNPJ (MongoDB primeiro, SQLite como fallback)"""
    # Tenta MongoDB primeiro, depois SQLite
```

### Normalização de IDs
```python
def normalize_id(id_value):
    """Normaliza IDs para string (compatível com MongoDB ObjectId e SQLite integer)"""
    # Converte ObjectId e integers para string
```

## Vantagens da Arquitetura

### 1. **Alta Disponibilidade**
- Sistema nunca fica completamente indisponível
- Operação contínua mesmo com falhas de infraestrutura

### 2. **Flexibilidade de Deploy**
- Pode ser implantado com ou sem MongoDB
- Ideal para ambientes de desenvolvimento e produção

### 3. **Performance Otimizada**
- MongoDB para operações de autenticação (escalável)
- SQLite para operações locais rápidas

### 4. **Manutenção Simplificada**
- Fallback automático reduz intervenções manuais
- Logs claros sobre o status dos bancos

### 5. **Desenvolvimento Ágil**
- Desenvolvedores podem trabalhar apenas com SQLite
- Produção pode usar MongoDB para melhor performance

## Diferenças das Versões Anteriores

### Novas Funcionalidades

1. **Tabelas SQLite para Autenticação**:
   - Tabelas `empresas` e `candidatos` no SQLite
   - Estrutura idêntica às coleções do MongoDB

2. **Funções de Fallback**:
   - `get_empresa_by_cnpj()`, `get_candidato_by_email()`
   - `insert_empresa()`, `insert_candidato()`
   - `update_candidato()`, `get_empresa_by_id()`

3. **Detecção Dinâmica**:
   - `check_mongo_connection()` com verificação contínua
   - Logs informativos sobre mudanças de status

4. **Normalização de IDs**:
   - `normalize_id()` para compatibilidade entre bancos
   - Tratamento transparente de ObjectId e integers

### Rotas Adaptadas

Todas as rotas de autenticação agora suportam fallback:
- `/login_empresa` e `/cadastro_empresa`
- `/login_candidato` e `/cadastro_candidato`
- `/editar_perfil_candidato`
- Todas as rotas que buscam dados de empresas/candidatos

## Monitoramento e Logs

### Mensagens de Status
```
✅ MongoDB conectado como banco primário!
⚠️ MongoDB não disponível: [erro]
🔄 Usando SQLite como fallback completo para todas as operações
⚠️ MongoDB perdeu conexão, usando SQLite como fallback
✅ Banco SQLite inicializado com fallback completo!
```

### Verificação de Status
O sistema exibe claramente qual banco está sendo usado para cada operação.

## Considerações Técnicas

### Sincronização de Dados
- **Não há sincronização automática** entre MongoDB e SQLite
- Dados inseridos no SQLite durante fallback não são transferidos automaticamente
- Para sincronização, seria necessário um script de migração personalizado

### Performance
- **MongoDB**: Melhor para operações de autenticação em escala
- **SQLite**: Excelente para operações locais e desenvolvimento
- **Fallback**: Pequena latência adicional na verificação de conectividade

### Backup e Recuperação
- **MongoDB**: Use ferramentas nativas (mongodump/mongorestore)
- **SQLite**: Copie o arquivo `recrutamento.db`
- **Estratégia Híbrida**: Backup de ambos os bancos recomendado

## Troubleshooting

### MongoDB Temporariamente Indisponível
- Sistema continua funcionando com SQLite
- Usuários podem continuar usando todas as funcionalidades
- Dados ficam no SQLite até MongoDB voltar

### SQLite Corrompido
- Delete `recrutamento.db` - será recriado automaticamente
- Dados de vagas/candidaturas serão perdidos
- Dados de autenticação do MongoDB permanecem intactos

### Problemas de ID
- Sistema normaliza automaticamente IDs entre bancos
- Em caso de erro, verifique logs para identificar incompatibilidades

## Cenários de Uso Recomendados

### Desenvolvimento
```bash
# Sem MongoDB - apenas SQLite
python3 app_fallback_completo.py
```

### Produção com Alta Disponibilidade
```bash
# Com MongoDB primário e SQLite como backup
MONGO_URI=mongodb://servidor-producao:27017/recrutamento python3 app_fallback_completo.py
```

### Ambiente Híbrido
```bash
# MongoDB para autenticação, SQLite para dados operacionais
MONGO_URI=mongodb://auth-server:27017/recrutamento python3 app_fallback_completo.py
```

## Próximos Passos

1. **Sincronização Automática**: Implementar sincronização bidirecional entre bancos
2. **Cache Inteligente**: Redis para otimizar consultas frequentes
3. **Monitoramento Avançado**: Métricas de performance e disponibilidade
4. **Balanceamento**: Distribuição inteligente de carga entre bancos
5. **Migração Assistida**: Ferramentas para migrar dados entre bancos

## Suporte

Para dúvidas ou problemas:
- Consulte os logs da aplicação para status dos bancos
- Verifique conectividade de rede para MongoDB
- Confirme permissões de escrita para SQLite
- Documentação do Flask, MongoDB e SQLite

