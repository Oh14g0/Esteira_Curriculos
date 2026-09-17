# Sistema de Esteira de Processos - Versão Híbrida

## Visão Geral

Esta é uma versão híbrida do sistema de esteira de processos que utiliza:
- **MongoDB** para gerenciar login e cadastro de empresas e candidatos
- **SQLite** para gerenciar vagas, candidaturas e notificações

## Arquitetura Híbrida

### MongoDB (Autenticação)
- **Coleção `empresas`**: Dados de login e cadastro das empresas
- **Coleção `candidatos`**: Dados de login e cadastro dos candidatos

### SQLite (Funcionalidades Principais)
- **Tabela `vagas`**: Informações sobre as vagas criadas pelas empresas
- **Tabela `candidaturas`**: Registros de candidaturas dos candidatos às vagas
- **Tabela `notificacoes`**: Notificações enviadas aos candidatos

## Estrutura de Arquivos

```
esteiraquasela/
├── app_hibrido.py          # Aplicação principal com arquitetura híbrida
├── app.py                  # Aplicação original (apenas MongoDB)
├── migrate_to_mongo.py     # Script de migração (referência)
├── requirements.txt        # Dependências do projeto
├── .env                    # Variáveis de ambiente
├── recrutamento.db         # Banco SQLite (criado automaticamente)
├── templates/              # Templates HTML
├── static/                 # Arquivos estáticos (CSS, JS)
├── uploads/                # Diretório para upload de currículos
└── README_HIBRIDO.md       # Esta documentação
```

## Configuração e Instalação

### 1. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 2. Configurar Variáveis de Ambiente

Edite o arquivo `.env`:

```env
MONGO_URI=mongodb://localhost:27017/
SECRET_KEY=chave-secreta-mvp-recrutamento-2024
MODO_IA=local
TOP_JOBS=3
```

### 3. Executar a Aplicação

```bash
python3 app_hibrido.py
```

A aplicação estará disponível em: `http://localhost:5001`

## Funcionalidades

### Para Empresas
- **Cadastro e Login**: Dados armazenados no MongoDB
- **Criação de Vagas**: Dados armazenados no SQLite
- **Gerenciamento de Candidatos**: Visualização de candidaturas (SQLite) com dados dos candidatos (MongoDB)
- **Relatórios**: Análise de candidaturas e vagas

### Para Candidatos
- **Cadastro e Login**: Dados armazenados no MongoDB
- **Candidatura a Vagas**: Registros armazenados no SQLite
- **Visualização de Vagas**: Dados das vagas (SQLite) com informações das empresas (MongoDB)
- **Notificações**: Sistema de notificações armazenado no SQLite

## Vantagens da Arquitetura Híbrida

1. **Escalabilidade**: MongoDB para autenticação permite melhor escalabilidade horizontal
2. **Performance**: SQLite para operações locais rápidas de vagas e candidaturas
3. **Flexibilidade**: Cada banco otimizado para seu caso de uso específico
4. **Manutenção**: Separação clara de responsabilidades

## Diferenças da Versão Original

### Mudanças Principais

1. **Conexões de Banco**:
   - MongoDB: Apenas para `empresas` e `candidatos`
   - SQLite: Para `vagas`, `candidaturas` e `notificacoes`

2. **Funções Modificadas**:
   - `get_sqlite_connection()`: Nova função para conexão SQLite
   - `init_sqlite_db()`: Inicialização automática das tabelas SQLite
   - Todas as rotas relacionadas a vagas/candidaturas adaptadas para SQLite

3. **Tratamento de Erros**:
   - Sistema funciona mesmo se MongoDB estiver indisponível (com limitações)
   - Mensagens de erro específicas para cada tipo de banco

### Rotas que Usam MongoDB
- `/login_empresa`
- `/cadastro_empresa`
- `/login_candidato`
- `/cadastro_candidato`
- `/editar_perfil_candidato`

### Rotas que Usam SQLite
- `/dashboard_empresa`
- `/criar_vaga`
- `/candidatos_vaga/<vaga_id>`
- `/dashboard_candidato`
- `/candidatar/<vaga_id>`
- `/encerrar_vaga`
- `/editar_vaga/<vaga_id>`
- `/vaga/<vaga_id>`
- `/minhas_candidaturas`
- `/api/notificacoes`
- E outras relacionadas a vagas/candidaturas/notificações

## Considerações Técnicas

### Integridade Referencial
- Os IDs do MongoDB (empresas e candidatos) são armazenados como strings no SQLite
- Verificações de integridade são feitas na aplicação, não no banco

### Backup e Migração
- **MongoDB**: Use ferramentas nativas do MongoDB (mongodump/mongorestore)
- **SQLite**: Copie o arquivo `recrutamento.db`

### Monitoramento
- Logs separados para cada tipo de banco
- Verificação de conectividade do MongoDB na inicialização

## Troubleshooting

### MongoDB Indisponível
- A aplicação ainda funciona para operações que não envolvem autenticação
- Mensagens de erro específicas são exibidas

### SQLite Corrompido
- Delete o arquivo `recrutamento.db` - será recriado automaticamente
- Dados de vagas/candidaturas serão perdidos

### Problemas de Performance
- Considere indexação no SQLite para consultas frequentes
- Monitor conexões do MongoDB

## Próximos Passos

1. **Implementar Cache**: Redis para sessões e dados frequentes
2. **Indexação**: Criar índices apropriados no SQLite
3. **Monitoramento**: Implementar logs estruturados
4. **Testes**: Criar suite de testes automatizados
5. **Deploy**: Configurar para produção com bancos externos

## Suporte

Para dúvidas ou problemas, consulte:
- Logs da aplicação
- Documentação do Flask
- Documentação do MongoDB
- Documentação do SQLite

