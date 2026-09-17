import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import pymongo
from bson import ObjectId
from datetime import datetime
import io
import json
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'chave-secreta-mvp-recrutamento-2024')
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'

# Configuração MongoDB (primário para empresas e candidatos)
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
mongo_available = False
db_mongo = None

try:
    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.server_info()  # Testa a conexão
    db_mongo = client.recrutamento
    mongo_available = True
    print("✅ MongoDB conectado como banco primário!")
except Exception as e:
    print(f"⚠️ MongoDB não disponível: {e}")
    print("🔄 Usando SQLite como fallback completo para todas as operações")

# Configuração SQLite (fallback completo)
SQLITE_DB = 'recrutamento.db'

def get_sqlite_connection():
    """Retorna uma conexão com o banco SQLite"""
    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row  # Para acessar colunas por nome
    return conn

def check_mongo_connection():
    """Verifica se o MongoDB está disponível"""
    global mongo_available, db_mongo
    if not mongo_available:
        return False
    
    try:
        if db_mongo:
            db_mongo.admin.command('ping')
            return True
    except Exception:
        mongo_available = False
        print("⚠️ MongoDB perdeu conexão, usando SQLite como fallback")
        return False
    return False

def init_sqlite_db():
    """Inicializa todas as tabelas do SQLite (incluindo empresas e candidatos)"""
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    
    # Tabela de empresas (fallback)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS empresas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cnpj TEXT NOT NULL UNIQUE,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela de candidatos (fallback)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidatos (
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
        )
    ''')
    
    # Tabela de vagas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vagas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id TEXT NOT NULL,
            titulo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            requisitos TEXT NOT NULL,
            diferenciais TEXT,
            salario_oferecido REAL NOT NULL,
            tipo_vaga TEXT DEFAULT 'Presencial',
            endereco_vaga TEXT,
            status TEXT DEFAULT 'Ativa',
            candidato_selecionado_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela de candidaturas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidaturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidato_id TEXT NOT NULL,
            vaga_id INTEGER NOT NULL,
            score REAL DEFAULT 75.0,
            posicao INTEGER DEFAULT 1,
            data_candidatura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vaga_id) REFERENCES vagas (id)
        )
    ''')
    
    # Tabela de notificações
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notificacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidato_id TEXT NOT NULL,
            empresa_id TEXT NOT NULL,
            vaga_id INTEGER NOT NULL,
            mensagem TEXT NOT NULL,
            data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            lida BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (vaga_id) REFERENCES vagas (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Banco SQLite inicializado com fallback completo!")

# Inicializar banco SQLite
init_sqlite_db()

# Configurações do ambiente
MODO_IA = os.getenv('MODO_IA', 'local')
TOP_JOBS = int(os.getenv('TOP_JOBS', '3'))

# Funções auxiliares para gerenciar IDs
def normalize_id(id_value):
    """Normaliza IDs para string (compatível com MongoDB ObjectId e SQLite integer)"""
    if isinstance(id_value, ObjectId):
        return str(id_value)
    return str(id_value)

def get_empresa_by_cnpj(cnpj):
    """Busca empresa por CNPJ (MongoDB primeiro, SQLite como fallback)"""
    if check_mongo_connection():
        try:
            return db_mongo.empresas.find_one({'cnpj': cnpj})
        except Exception:
            pass
    
    # Fallback para SQLite
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM empresas WHERE cnpj = ?', (cnpj,))
    empresa = cursor.fetchone()
    conn.close()
    
    if empresa:
        return dict(empresa)
    return None

def get_empresa_by_email(email):
    """Busca empresa por email (MongoDB primeiro, SQLite como fallback)"""
    if check_mongo_connection():
        try:
            return db_mongo.empresas.find_one({'email': email})
        except Exception:
            pass
    
    # Fallback para SQLite
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM empresas WHERE email = ?', (email,))
    empresa = cursor.fetchone()
    conn.close()
    
    if empresa:
        return dict(empresa)
    return None

def insert_empresa(empresa_doc):
    """Insere empresa (MongoDB primeiro, SQLite como fallback)"""
    if check_mongo_connection():
        try:
            result = db_mongo.empresas.insert_one(empresa_doc)
            return str(result.inserted_id)
        except Exception:
            pass
    
    # Fallback para SQLite
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO empresas (cnpj, nome, email, senha_hash, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (empresa_doc['cnpj'], empresa_doc['nome'], empresa_doc['email'], 
          empresa_doc['senha_hash'], empresa_doc['created_at']))
    
    empresa_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return str(empresa_id)

def get_candidato_by_email(email):
    """Busca candidato por email (MongoDB primeiro, SQLite como fallback)"""
    if check_mongo_connection():
        try:
            return db_mongo.candidatos.find_one({'email': email})
        except Exception:
            pass
    
    # Fallback para SQLite
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM candidatos WHERE email = ?', (email,))
    candidato = cursor.fetchone()
    conn.close()
    
    if candidato:
        return dict(candidato)
    return None

def get_candidato_by_id(candidato_id):
    """Busca candidato por ID (MongoDB primeiro, SQLite como fallback)"""
    if check_mongo_connection():
        try:
            if isinstance(candidato_id, str) and len(candidato_id) == 24:
                return db_mongo.candidatos.find_one({'_id': ObjectId(candidato_id)})
        except Exception:
            pass
    
    # Fallback para SQLite
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM candidatos WHERE id = ?', (candidato_id,))
    candidato = cursor.fetchone()
    conn.close()
    
    if candidato:
        return dict(candidato)
    return None

def insert_candidato(candidato_doc):
    """Insere candidato (MongoDB primeiro, SQLite como fallback)"""
    if check_mongo_connection():
        try:
            result = db_mongo.candidatos.insert_one(candidato_doc)
            return str(result.inserted_id)
        except Exception:
            pass
    
    # Fallback para SQLite
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO candidatos (nome, email, senha_hash, telefone, linkedin, 
                              endereco_completo, pretensao_salarial, texto_curriculo,
                              caminho_curriculo, experiencia, competencias, 
                              resumo_profissional, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (candidato_doc['nome'], candidato_doc['email'], candidato_doc['senha_hash'],
          candidato_doc['telefone'], candidato_doc['linkedin'], candidato_doc['endereco_completo'],
          candidato_doc['pretensao_salarial'], candidato_doc['texto_curriculo'],
          candidato_doc['caminho_curriculo'], candidato_doc['experiencia'],
          candidato_doc['competencias'], candidato_doc['resumo_profissional'],
          candidato_doc['created_at']))
    
    candidato_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return str(candidato_id)

def update_candidato(candidato_id, update_data):
    """Atualiza candidato (MongoDB primeiro, SQLite como fallback)"""
    if check_mongo_connection():
        try:
            if isinstance(candidato_id, str) and len(candidato_id) == 24:
                db_mongo.candidatos.update_one(
                    {'_id': ObjectId(candidato_id)},
                    {'$set': update_data}
                )
                return True
        except Exception:
            pass
    
    # Fallback para SQLite
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    
    # Construir query de update dinamicamente
    set_clause = ', '.join([f"{key} = ?" for key in update_data.keys()])
    values = list(update_data.values()) + [candidato_id]
    
    cursor.execute(f'UPDATE candidatos SET {set_clause} WHERE id = ?', values)
    conn.commit()
    conn.close()
    return True

def get_empresa_by_id(empresa_id):
    """Busca empresa por ID (MongoDB primeiro, SQLite como fallback)"""
    if check_mongo_connection():
        try:
            if isinstance(empresa_id, str) and len(empresa_id) == 24:
                return db_mongo.empresas.find_one({'_id': ObjectId(empresa_id)})
        except Exception:
            pass
    
    # Fallback para SQLite
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM empresas WHERE id = ?', (empresa_id,))
    empresa = cursor.fetchone()
    conn.close()
    
    if empresa:
        return dict(empresa)
    return None


def gerar_feedback_ia_vaga(total, alta_compatibilidade, media_compatibilidade,
                           baixa_compatibilidade):
    """Gera feedback inteligente sobre os candidatos da vaga"""
    if total == 0:
        return {
            'texto': 'Nenhum candidato ainda',
            'cor': 'text-gray-500',
            'icone': '📋'
        }

    if alta_compatibilidade > 0:
        percentual_alto = (alta_compatibilidade / total) * 100
        if percentual_alto >= 50:
            return {
                'texto':
                f'{alta_compatibilidade} candidato(s) com perfil excelente (80%+)',
                'cor': 'text-green-600',
                'icone': '🎯'
            }
        else:
            return {
                'texto':
                f'{alta_compatibilidade} candidato(s) muito compatível(eis)',
                'cor': 'text-green-500',
                'icone': '✅'
            }

    if media_compatibilidade > 0:
        return {
            'texto':
            f'{media_compatibilidade} candidato(s) com bom potencial (60-79%)',
            'cor': 'text-yellow-600',
            'icone': '⚡'
        }

    return {
        'texto': f'{total} candidato(s) - revisar requisitos da vaga',
        'cor': 'text-orange-500',
        'icone': '⚠️'
    }


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login_empresa', methods=['GET', 'POST'])
def login_empresa():
    if request.method == 'POST':
        cnpj = request.form.get('cnpj', '').strip()
        senha = request.form.get('senha', '')

        if not cnpj or not senha:
            flash('Por favor, preencha todos os campos', 'error')
            return render_template('login_empresa.html')

        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))

        if len(cnpj_limpo) != 14:
            flash('CNPJ deve ter exatamente 14 dígitos', 'error')
            return render_template('login_empresa.html')

        try:
            empresa = get_empresa_by_cnpj(cnpj_limpo)

            if empresa and check_password_hash(empresa['senha_hash'], senha):
                session.clear()
                session['empresa_id'] = normalize_id(empresa.get('_id', empresa.get('id')))
                session['tipo_usuario'] = 'empresa'
                session.permanent = True
                return redirect(url_for('dashboard_empresa'))
            else:
                flash('CNPJ ou senha incorretos', 'error')
        except Exception as e:
            print(f"Erro no login: {e}")
            flash('Erro interno do sistema. Tente novamente.', 'error')

    return render_template('login_empresa.html')


@app.route('/cadastro_empresa', methods=['GET', 'POST'])
def cadastro_empresa():
    if request.method == 'POST':
        cnpj = request.form.get('cnpj', '').strip()
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '')

        if not all([cnpj, nome, email, senha]):
            flash('Por favor, preencha todos os campos', 'error')
            return render_template('cadastro_empresa.html')

        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))

        if len(cnpj_limpo) != 14:
            flash('CNPJ deve ter exatamente 14 dígitos', 'error')
            return render_template('cadastro_empresa.html')

        if len(senha) < 6:
            flash('A senha deve ter pelo menos 6 caracteres', 'error')
            return render_template('cadastro_empresa.html')

        try:
            if get_empresa_by_cnpj(cnpj_limpo):
                flash('CNPJ já está cadastrado no sistema', 'error')
                return render_template('cadastro_empresa.html')

            if get_empresa_by_email(email):
                flash('Email já está cadastrado no sistema', 'error')
                return render_template('cadastro_empresa.html')

            empresa_doc = {
                'cnpj': cnpj_limpo,
                'nome': nome,
                'email': email,
                'senha_hash': generate_password_hash(senha),
                'created_at': datetime.now()
            }

            insert_empresa(empresa_doc)
            flash('Empresa cadastrada com sucesso!', 'success')
            return redirect(url_for('login_empresa'))
        except Exception as e:
            flash('Erro ao cadastrar empresa. Verifique os dados.', 'error')

    return render_template('cadastro_empresa.html')


@app.route('/login_candidato', methods=['GET', 'POST'])
@app.route('/index.html', methods=['GET', 'POST'])
def login_candidato():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        candidato = get_candidato_by_email(email)

        if candidato and check_password_hash(candidato['senha_hash'], senha):
            session['candidato_id'] = normalize_id(candidato.get('_id', candidato.get('id')))
            session['tipo_usuario'] = 'candidato'
            return redirect(url_for('dashboard_candidato'))
        else:
            flash('Email ou senha incorretos', 'error')

    return render_template('login_candidato.html')


@app.route('/cadastro_candidato', methods=['GET', 'POST'])
def cadastro_candidato():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        telefone = request.form['telefone']
        linkedin = request.form['linkedin']
        endereco_completo = request.form['endereco_completo']
        pretensao_salarial = float(request.form['pretensao_salarial'])

        try:
            if get_candidato_by_email(email):
                flash('Email já cadastrado', 'error')
                return render_template('cadastro_candidato.html')

            candidato_doc = {
                'nome': nome,
                'email': email,
                'senha_hash': generate_password_hash(senha),
                'telefone': telefone,
                'linkedin': linkedin,
                'endereco_completo': endereco_completo,
                'pretensao_salarial': pretensao_salarial,
                'texto_curriculo': '',
                'caminho_curriculo': '',
                'experiencia': '',
                'competencias': '',
                'resumo_profissional': '',
                'created_at': datetime.now()
            }

            insert_candidato(candidato_doc)
            flash('Candidato cadastrado com sucesso!', 'success')
            return redirect(url_for('login_candidato'))
        except Exception as e:
            flash(f'Erro ao cadastrar: {str(e)}', 'error')

    return render_template('cadastro_candidato.html')


@app.route('/dashboard_empresa')
def dashboard_empresa():
    if 'empresa_id' not in session or session.get('tipo_usuario') != 'empresa':
        flash('Faça login para acessar esta página', 'error')
        return redirect(url_for('login_empresa'))

    try:
        empresa_id = session['empresa_id']
        
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        
        # Buscar vagas da empresa com estatísticas de candidaturas
        cursor.execute('''
            SELECT v.*, 
                   COUNT(c.id) as total_candidatos,
                   COUNT(CASE WHEN c.score >= 80 THEN 1 END) as candidatos_80_plus,
                   COUNT(CASE WHEN c.score >= 60 AND c.score < 80 THEN 1 END) as candidatos_60_79,
                   COUNT(CASE WHEN c.score < 60 THEN 1 END) as candidatos_abaixo_60
            FROM vagas v
            LEFT JOIN candidaturas c ON v.id = c.vaga_id
            WHERE v.empresa_id = ?
            GROUP BY v.id
            ORDER BY v.created_at DESC
        ''', (empresa_id,))
        
        vagas = cursor.fetchall()
        conn.close()

        # Processar vagas para exibição
        vagas_processadas = []
        for vaga in vagas:
            vaga_dict = {
                'id': vaga['id'],
                'titulo': vaga['titulo'],
                'descricao': vaga['descricao'],
                'requisitos': vaga['requisitos'],
                'salario_oferecido': vaga['salario_oferecido'],
                'diferenciais': vaga['diferenciais'] or '',
                'tipo_vaga': vaga['tipo_vaga'] or 'Presencial',
                'endereco_vaga': vaga['endereco_vaga'] or '',
                'status': vaga['status'] or 'Ativa',
                'data_criacao': vaga['created_at'],
                'total_candidatos': vaga['total_candidatos'] or 0,
                'candidatos_80_plus': vaga['candidatos_80_plus'] or 0,
                'candidatos_60_79': vaga['candidatos_60_79'] or 0,
                'candidatos_abaixo_60': vaga['candidatos_abaixo_60'] or 0
            }
            vagas_processadas.append(vaga_dict)

        return render_template('dashboard_empresa.html', vagas=vagas_processadas)

    except Exception as e:
        flash(f'Erro ao carregar dashboard: {str(e)}', 'error')
        return redirect(url_for('login_empresa'))


@app.route('/criar_vaga', methods=['GET', 'POST'])
def criar_vaga():
    if 'empresa_id' not in session:
        return redirect(url_for('login_empresa'))

    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        requisitos = request.form['requisitos']
        diferenciais = request.form.get('diferenciais', '')
        salario_oferecido = float(request.form['salario_oferecido'])
        tipo_vaga = request.form['tipo_vaga']
        endereco_vaga = request.form.get('endereco_vaga', '')

        if tipo_vaga in ['Presencial', 'Híbrida'] and not endereco_vaga:
            flash('Endereço é obrigatório para vagas presenciais ou híbridas',
                  'error')
            return render_template('criar_vaga.html')

        try:
            empresa_id = session['empresa_id']
            
            conn = get_sqlite_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO vagas (empresa_id, titulo, descricao, requisitos, diferenciais, 
                                 salario_oferecido, tipo_vaga, endereco_vaga, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (empresa_id, titulo, descricao, requisitos, diferenciais, 
                  salario_oferecido, tipo_vaga, endereco_vaga, 'Ativa'))
            
            conn.commit()
            conn.close()
            
            flash('Vaga criada com sucesso!', 'success')
            return redirect(url_for('dashboard_empresa'))

        except Exception as e:
            flash(f'Erro ao criar vaga: {str(e)}', 'error')
            return render_template('criar_vaga.html')

    return render_template('criar_vaga.html')


@app.route('/candidatos_vaga/<int:vaga_id>')
def candidatos_vaga(vaga_id):
    if 'empresa_id' not in session:
        return redirect(url_for('login_empresa'))

    try:
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        
        # Buscar candidatos da vaga
        cursor.execute('''
            SELECT c.candidato_id, c.score, c.posicao
            FROM candidaturas c
            WHERE c.vaga_id = ?
            ORDER BY c.score DESC
        ''', (vaga_id,))
        
        candidaturas = cursor.fetchall()
        
        # Buscar título da vaga
        cursor.execute('SELECT titulo FROM vagas WHERE id = ?', (vaga_id,))
        vaga = cursor.fetchone()
        vaga_titulo = vaga['titulo'] if vaga else ''
        
        conn.close()
        
        # Buscar dados dos candidatos (MongoDB ou SQLite)
        candidatos = []
        for candidatura in candidaturas:
            candidato = get_candidato_by_id(candidatura['candidato_id'])
            if candidato:
                candidatos.append({
                    '_id': candidatura['candidato_id'],
                    'nome': candidato['nome'],
                    'email': candidato['email'],
                    'telefone': candidato['telefone'],
                    'linkedin': candidato['linkedin'],
                    'score': candidatura['score'],
                    'posicao': candidatura['posicao'],
                    'endereco_completo': candidato['endereco_completo']
                })

        return render_template('candidatos_vaga.html',
                               candidatos=candidatos,
                               vaga_titulo=vaga_titulo,
                               vaga_id=vaga_id)
    except Exception as e:
        flash(f'Erro ao carregar candidatos: {str(e)}', 'error')
        return redirect(url_for('dashboard_empresa'))


@app.route('/dashboard_candidato')
def dashboard_candidato():
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))

    try:
        candidato_id = session['candidato_id']
        candidato = get_candidato_by_id(candidato_id)

        if not candidato or not candidato.get('texto_curriculo'):
            return redirect(url_for('upload_curriculo'))
        
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        
        # Buscar candidaturas do candidato
        cursor.execute('SELECT vaga_id FROM candidaturas WHERE candidato_id = ?', (candidato_id,))
        candidaturas_vaga_ids = [row['vaga_id'] for row in cursor.fetchall()]
        
        # Buscar vagas disponíveis (não candidatadas)
        if candidaturas_vaga_ids:
            placeholders = ','.join('?' * len(candidaturas_vaga_ids))
            cursor.execute(f'''
                SELECT * FROM vagas 
                WHERE id NOT IN ({placeholders}) AND status IN ('Ativa', '')
                ORDER BY created_at DESC
                LIMIT ?
            ''', candidaturas_vaga_ids + [TOP_JOBS])
        else:
            cursor.execute('''
                SELECT * FROM vagas 
                WHERE status IN ('Ativa', '')
                ORDER BY created_at DESC
                LIMIT ?
            ''', (TOP_JOBS,))
        
        vagas_disponiveis = cursor.fetchall()
        conn.close()

        # Calcular scores para vagas disponíveis (simulado por agora)
        top_vagas = []
        for vaga in vagas_disponiveis:
            empresa = get_empresa_by_id(vaga['empresa_id'])
            
            vaga_processada = {
                'id': vaga['id'],
                'titulo': vaga['titulo'],
                'descricao': vaga['descricao'],
                'requisitos': vaga['requisitos'],
                'salario_oferecido': vaga['salario_oferecido'],
                'empresa_nome': empresa['nome'] if empresa else 'N/A',
                'diferenciais': vaga['diferenciais'] or '',
                'tipo_vaga': vaga['tipo_vaga'] or 'Presencial',
                'endereco_vaga': vaga['endereco_vaga'] or '',
                'score': 85.0  # Score simulado - implementar avaliador depois
            }
            top_vagas.append(vaga_processada)

        return render_template('dashboard_candidato.html',
                             vagas_recomendadas=top_vagas,
                             vagas_candidatadas=[])

    except Exception as e:
        flash(f'Erro ao carregar dashboard: {str(e)}', 'error')
        return redirect(url_for('login_candidato'))


@app.route('/upload_curriculo', methods=['GET', 'POST'])
def upload_curriculo():
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))

    if request.method == 'POST':
        # Implementar upload de currículo
        flash('Funcionalidade de upload em desenvolvimento', 'info')
        return redirect(url_for('dashboard_candidato'))

    return render_template('upload_curriculo.html')


@app.route('/finalizar_curriculo', methods=['POST'])
def finalizar_curriculo():
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))

    flash('Funcionalidade em construção', 'info')
    return redirect(url_for('dashboard_candidato'))


@app.route('/candidatar/<int:vaga_id>')
def candidatar(vaga_id):
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))

    try:
        candidato_id = session['candidato_id']
        
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        
        # Verificar se já se candidatou
        cursor.execute('SELECT id FROM candidaturas WHERE candidato_id = ? AND vaga_id = ?', 
                      (candidato_id, vaga_id))
        if cursor.fetchone():
            flash('Você já se candidatou para esta vaga.', 'warning')
            conn.close()
            return redirect(url_for('dashboard_candidato'))

        # Criar nova candidatura
        cursor.execute('''
            INSERT INTO candidaturas (candidato_id, vaga_id, score, posicao)
            VALUES (?, ?, ?, ?)
        ''', (candidato_id, vaga_id, 75.0, 1))
        
        conn.commit()
        conn.close()

        flash('Candidatura realizada com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao candidatar-se: {str(e)}', 'error')

    return redirect(url_for('dashboard_candidato'))


@app.route('/api/candidatos_vaga/<int:vaga_id>')
def api_candidatos_vaga(vaga_id):
    if 'empresa_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    try:
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT candidato_id, score
            FROM candidaturas
            WHERE vaga_id = ?
            ORDER BY score DESC
        ''', (vaga_id,))
        
        candidaturas = cursor.fetchall()
        conn.close()
        
        # Buscar nomes dos candidatos
        candidate_list = []
        for candidatura in candidaturas:
            candidato = get_candidato_by_id(candidatura['candidato_id'])
            if candidato:
                candidate_list.append({
                    'id': candidatura['candidato_id'],
                    'nome': candidato['nome'],
                    'score': round(candidatura['score'], 1)
                })

        return jsonify(candidate_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/encerrar_vaga', methods=['POST'])
def encerrar_vaga():
    if 'empresa_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    data = request.get_json()
    vaga_id = data.get('vaga_id')
    acao = data.get('acao')
    candidato_id = data.get('candidato_id')
    mensagem_personalizada = data.get('mensagem_personalizada', '')

    if not vaga_id or not acao:
        return jsonify({'error': 'Dados incompletos'}), 400

    try:
        empresa_id = session['empresa_id']
        
        conn = get_sqlite_connection()
        cursor = conn.cursor()

        # Verificar se a vaga pertence à empresa
        cursor.execute('SELECT id FROM vagas WHERE id = ? AND empresa_id = ?', (vaga_id, empresa_id))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Vaga não encontrada'}), 404

        if acao == 'contratar':
            if not candidato_id:
                conn.close()
                return jsonify({'error': 'Candidato não selecionado'}), 400

            # Verificar se o candidato se candidatou à vaga
            cursor.execute('SELECT id FROM candidaturas WHERE candidato_id = ? AND vaga_id = ?', 
                          (candidato_id, vaga_id))
            if not cursor.fetchone():
                conn.close()
                return jsonify({'error': 'Candidato não se candidatou a esta vaga'}), 400

            # Marcar vaga como Concluída e definir candidato selecionado
            cursor.execute('''
                UPDATE vagas 
                SET status = 'Concluída', candidato_selecionado_id = ?
                WHERE id = ?
            ''', (candidato_id, vaga_id))

            # Criar notificação para o candidato
            if not mensagem_personalizada:
                mensagem_personalizada = "Parabéns! Você foi selecionado para esta vaga."

            cursor.execute('''
                INSERT INTO notificacoes (candidato_id, empresa_id, vaga_id, mensagem)
                VALUES (?, ?, ?, ?)
            ''', (candidato_id, empresa_id, vaga_id, mensagem_personalizada))

            response = {
                'success': True,
                'message': 'Candidato contratado com sucesso!'
            }

        elif acao == 'congelar':
            cursor.execute('UPDATE vagas SET status = ? WHERE id = ?', ('Congelada', vaga_id))
            response = {
                'success': True,
                'message': 'Vaga congelada com sucesso!'
            }

        elif acao == 'excluir':
            # Excluir candidaturas primeiro
            cursor.execute('DELETE FROM candidaturas WHERE vaga_id = ?', (vaga_id,))
            cursor.execute('DELETE FROM vagas WHERE id = ?', (vaga_id,))

            response = {
                'success': True,
                'message': 'Vaga excluída com sucesso!'
            }

        elif acao == 'reativar':
            cursor.execute('UPDATE vagas SET status = ? WHERE id = ?', ('Ativa', vaga_id))
            response = {
                'success': True,
                'message': 'Vaga reativada com sucesso!'
            }

        else:
            conn.close()
            return jsonify({'error': 'Ação inválida'}), 400

        conn.commit()
        conn.close()
        return jsonify(response)

    except Exception as e:
        return jsonify({'error': f'Erro ao processar ação: {str(e)}'}), 500


@app.route('/editar_perfil_candidato', methods=['GET', 'POST'])
def editar_perfil_candidato():
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))

    candidato_id = session['candidato_id']
    candidato = get_candidato_by_id(candidato_id)

    if not candidato:
        flash('Candidato não encontrado', 'error')
        return redirect(url_for('dashboard_candidato'))

    if request.method == 'POST':
        nome = request.form['nome']
        telefone = request.form['telefone']
        linkedin = request.form['linkedin']
        pretensao_salarial = float(request.form['pretensao_salarial'])
        experiencia = request.form['experiencia']
        competencias = request.form['competencias']
        resumo_profissional = request.form['resumo_profissional']

        try:
            update_data = {
                'nome': nome,
                'telefone': telefone,
                'linkedin': linkedin,
                'pretensao_salarial': pretensao_salarial,
                'experiencia': experiencia,
                'competencias': competencias,
                'resumo_profissional': resumo_profissional
            }
            
            update_candidato(candidato_id, update_data)
            flash('Perfil atualizado com sucesso!', 'success')
            return redirect(url_for('dashboard_candidato'))
        except Exception as e:
            flash(f'Erro ao atualizar perfil: {str(e)}', 'error')

    return render_template('editar_perfil_candidato.html', candidato=candidato)


@app.route('/editar_vaga/<int:vaga_id>', methods=['GET', 'POST'])
def editar_vaga(vaga_id):
    if 'empresa_id' not in session:
        return redirect(url_for('login_empresa'))

    try:
        empresa_id = session['empresa_id']
        
        conn = get_sqlite_connection()
        cursor = conn.cursor()

        # Verificar se a vaga pertence à empresa
        cursor.execute('SELECT * FROM vagas WHERE id = ? AND empresa_id = ?', (vaga_id, empresa_id))
        vaga = cursor.fetchone()
        
        if not vaga:
            flash('Vaga não encontrada', 'error')
            conn.close()
            return redirect(url_for('dashboard_empresa'))

        if request.method == 'POST':
            titulo = request.form['titulo']
            descricao = request.form['descricao']
            requisitos = request.form['requisitos']
            salario_oferecido = float(request.form['salario_oferecido'])
            tipo_vaga = request.form['tipo_vaga']
            endereco_vaga = request.form['endereco_vaga']

            cursor.execute('''
                UPDATE vagas 
                SET titulo = ?, descricao = ?, requisitos = ?, salario_oferecido = ?, 
                    tipo_vaga = ?, endereco_vaga = ?
                WHERE id = ?
            ''', (titulo, descricao, requisitos, salario_oferecido, tipo_vaga, endereco_vaga, vaga_id))

            conn.commit()
            conn.close()
            
            flash('Vaga atualizada com sucesso!', 'success')
            return redirect(url_for('dashboard_empresa'))

        conn.close()
        return render_template('editar_vaga.html', vaga=vaga)
    except Exception as e:
        flash(f'Erro ao editar vaga: {str(e)}', 'error')
        return redirect(url_for('dashboard_empresa'))


@app.route('/vaga/<int:vaga_id>')
def detalhes_vaga(vaga_id):
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))

    try:
        candidato_id = session['candidato_id']
        
        conn = get_sqlite_connection()
        cursor = conn.cursor()

        # Buscar dados da vaga
        cursor.execute('SELECT * FROM vagas WHERE id = ? AND status = ?', (vaga_id, 'Ativa'))
        vaga_data = cursor.fetchone()

        if not vaga_data:
            flash('Vaga não encontrada ou não está mais ativa', 'error')
            conn.close()
            return redirect(url_for('dashboard_candidato'))

        # Verificar se já se candidatou
        cursor.execute('SELECT * FROM candidaturas WHERE candidato_id = ? AND vaga_id = ?', 
                      (candidato_id, vaga_id))
        candidatura = cursor.fetchone()
        
        conn.close()

        # Buscar dados da empresa
        empresa = get_empresa_by_id(vaga_data['empresa_id'])

        # Estruturar dados da vaga
        vaga = {
            'id': vaga_data['id'],
            'titulo': vaga_data['titulo'],
            'descricao': vaga_data['descricao'],
            'requisitos': vaga_data['requisitos'],
            'salario_oferecido': vaga_data['salario_oferecido'],
            'tipo_vaga': vaga_data['tipo_vaga'] or 'Presencial',
            'endereco_vaga': vaga_data['endereco_vaga'] or '',
            'diferenciais': vaga_data['diferenciais'] or '',
            'data_criacao': vaga_data['created_at']
        }

        empresa_info = {'nome': empresa['nome'] if empresa else 'N/A'}

        # Calcular score e feedback se não candidatado ainda
        score = candidatura['score'] if candidatura else 80.0  # Simulate the score

        # Gerar feedback de performance (simulado)
        feedback_performance = {
            'requisitos_atendidos': 5,
            'total_requisitos': 10,
            'diferenciais_atendidos': 2,
            'bonus_localizacao': True
        }

        return render_template('detalhes_vaga.html',
                             vaga=vaga,
                             empresa=empresa_info,
                             score=score,
                             feedback_performance=feedback_performance,
                             ja_candidatado=bool(candidatura))

    except Exception as e:
        flash(f'Erro ao visualizar detalhes da vaga: {str(e)}', 'error')
        return redirect(url_for('dashboard_candidato'))


@app.route('/minhas_candidaturas')
def minhas_candidaturas():
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))

    try:
        candidato_id = session['candidato_id']
        
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        
        # Buscar candidaturas do candidato com dados das vagas
        cursor.execute('''
            SELECT c.*, v.titulo, v.salario_oferecido, v.empresa_id
            FROM candidaturas c
            JOIN vagas v ON c.vaga_id = v.id
            WHERE c.candidato_id = ?
            ORDER BY c.data_candidatura DESC
        ''', (candidato_id,))
        
        candidaturas_data = cursor.fetchall()
        conn.close()
        
        # Buscar nomes das empresas
        candidaturas = []
        for candidatura in candidaturas_data:
            empresa = get_empresa_by_id(candidatura['empresa_id'])
            
            candidaturas.append({
                '_id': candidatura['vaga_id'],
                'titulo': candidatura['titulo'],
                'empresa_nome': empresa['nome'] if empresa else 'N/A',
                'salario_oferecido': candidatura['salario_oferecido'],
                'score': candidatura['score'],
                'posicao': candidatura['posicao'],
                'data_candidatura': candidatura['data_candidatura']
            })

        return render_template('minhas_candidaturas.html',
                               candidaturas=candidaturas)
    except Exception as e:
        flash(f'Erro ao carregar candidaturas: {str(e)}', 'error')
        return redirect(url_for('dashboard_candidato'))


@app.route('/baixar_curriculo/<string:candidato_id>')
def baixar_curriculo(candidato_id):
    if 'empresa_id' not in session:
        return redirect(url_for('login_empresa'))

    try:
        empresa_id = session['empresa_id']
        
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        
        # Verificar se a empresa tem acesso ao candidato (através de candidatura)
        cursor.execute('SELECT id FROM candidaturas WHERE candidato_id = ?', (candidato_id,))
        candidatura = cursor.fetchone()
        conn.close()

        if not candidatura:
            flash('Acesso negado ao currículo', 'error')
            return redirect(url_for('dashboard_empresa'))

        # Buscar dados do candidato
        candidato = get_candidato_by_id(candidato_id)

        if not candidato:
            flash('Candidato não encontrado', 'error')
            return redirect(url_for('dashboard_empresa'))

        # Verificar se o arquivo do currículo existe
        caminho_curriculo = candidato.get('caminho_curriculo')
        if not caminho_curriculo:
            flash('Currículo não disponível para download', 'error')
            return redirect(url_for('dashboard_empresa'))

        caminho_completo = os.path.join('uploads', caminho_curriculo)

        if not os.path.exists(caminho_completo):
            flash('Arquivo do currículo não encontrado', 'error')
            return redirect(url_for('dashboard_empresa'))

        nome_download = f"curriculo_{candidato['nome'].replace(' ', '_')}.pdf"

        return send_file(caminho_completo,
                         as_attachment=True,
                         download_name=nome_download,
                         mimetype='application/pdf')

    except Exception as e:
        flash(f'Erro ao baixar currículo: {str(e)}', 'error')
        return redirect(url_for('dashboard_empresa'))


@app.route('/empresa/relatorio')
def relatorio_empresa():
    if 'empresa_id' not in session:
        flash('Faça login para acessar essa página', 'error')
        return redirect(url_for('login_empresa'))

    empresa_id = session['empresa_id']
    
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    
    # Buscar vagas da empresa para o filtro
    cursor.execute('SELECT id, titulo FROM vagas WHERE empresa_id = ?', (empresa_id,))
    vagas_disponiveis = cursor.fetchall()
    conn.close()

    return render_template('relatorio_empresa.html',
                           vagas_disponiveis=vagas_disponiveis,
                           dados_graficos=json.dumps({}))


@app.route('/empresa/relatorio/completo')
def relatorio_completo():
    if 'empresa_id' not in session:
        return redirect(url_for('login_empresa'))

    try:
        html_relatorio = "<h1>Relatório Completo (Em Desenvolvimento)</h1>"
        return html_relatorio

    except Exception as e:
        flash(f'Erro ao gerar relatório: {str(e)}', 'error')
        return redirect(url_for('relatorio_empresa'))


@app.route('/api/relatorio/graficos')
def api_relatorio_graficos():
    if 'empresa_id' not in session:
        return {'error': 'Não autorizado'}, 401

    try:
        dados = {}
        return dados
    except Exception as e:
        return {'error': str(e)}, 500


@app.route('/cancelar_candidatura', methods=['POST'])
def cancelar_candidatura():
    if 'candidato_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    data = request.get_json()
    vaga_id = data.get('vaga_id')

    try:
        candidato_id = session['candidato_id']
        
        conn = get_sqlite_connection()
        cursor = conn.cursor()

        # Verificar se a candidatura existe
        cursor.execute('SELECT id FROM candidaturas WHERE candidato_id = ? AND vaga_id = ?', 
                      (candidato_id, vaga_id))
        candidatura = cursor.fetchone()

        if not candidatura:
            conn.close()
            return {'error': 'Candidatura não encontrada'}, 404

        # Remover candidatura
        cursor.execute('DELETE FROM candidaturas WHERE candidato_id = ? AND vaga_id = ?', 
                      (candidato_id, vaga_id))
        
        conn.commit()
        conn.close()

        return {'success': True}

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/reativar_vaga/<int:vaga_id>", methods=["POST"])
def reativar_vaga_route(vaga_id):
    if 'empresa_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    try:
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        
        cursor.execute('UPDATE vagas SET status = ? WHERE id = ?', ('Ativa', vaga_id))
        
        conn.commit()
        conn.close()

        return redirect(url_for('dashboard_empresa'))

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/notificacoes')
def api_notificacoes():
    if 'candidato_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    try:
        candidato_id = session['candidato_id']
        
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        
        # Buscar notificações com dados das vagas e empresas
        cursor.execute('''
            SELECT n.*, v.titulo as vaga_titulo, v.empresa_id
            FROM notificacoes n
            JOIN vagas v ON n.vaga_id = v.id
            WHERE n.candidato_id = ?
            ORDER BY n.data_envio DESC
        ''', (candidato_id,))
        
        notificacoes_data = cursor.fetchall()
        conn.close()
        
        # Buscar nomes das empresas
        notificacoes = []
        for notificacao in notificacoes_data:
            empresa = get_empresa_by_id(notificacao['empresa_id'])
            
            notificacoes.append({
                '_id': notificacao['id'],
                'mensagem': notificacao['mensagem'],
                'data_envio': notificacao['data_envio'],
                'lida': bool(notificacao['lida']),
                'vaga_titulo': notificacao['vaga_titulo'],
                'empresa_nome': empresa['nome'] if empresa else 'N/A'
            })

        return jsonify(notificacoes)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/notificacoes/marcar-lida', methods=['POST'])
def marcar_notificacao_lida():
    if 'candidato_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    data = request.get_json()
    notificacao_id = data.get('id')

    if not notificacao_id:
        return jsonify({'error': 'ID da notificação é obrigatório'}), 400

    try:
        candidato_id = session['candidato_id']
        
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE notificacoes 
            SET lida = 1 
            WHERE id = ? AND candidato_id = ?
        ''', (notificacao_id, candidato_id))
        
        conn.commit()
        conn.close()

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/notificacoes/marcar-todas-lidas', methods=['POST'])
def marcar_todas_notificacoes_lidas():
    if 'candidato_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    try:
        candidato_id = session['candidato_id']
        
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        
        cursor.execute('UPDATE notificacoes SET lida = 1 WHERE candidato_id = ?', (candidato_id,))
        
        conn.commit()
        conn.close()

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)

