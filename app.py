import os
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

# Configuração MongoDB
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
client = pymongo.MongoClient(MONGO_URI)
db = client.recrutamento

# Configurações do ambiente
MODO_IA = os.getenv('MODO_IA', 'local')
TOP_JOBS = int(os.getenv('TOP_JOBS', '3'))


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
            empresa = db.empresas.find_one({'cnpj': cnpj_limpo})

            if empresa and check_password_hash(empresa['senha_hash'], senha):
                session.clear()
                session['empresa_id'] = str(empresa['_id'])
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
            if db.empresas.find_one({'cnpj': cnpj_limpo}):
                flash('CNPJ já está cadastrado no sistema', 'error')
                return render_template('cadastro_empresa.html')

            if db.empresas.find_one({'email': email}):
                flash('Email já está cadastrado no sistema', 'error')
                return render_template('cadastro_empresa.html')

            empresa_doc = {
                'cnpj': cnpj_limpo,
                'nome': nome,
                'email': email,
                'senha_hash': generate_password_hash(senha),
                'created_at': datetime.now()
            }

            db.empresas.insert_one(empresa_doc)
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

        candidato = db.candidatos.find_one({'email': email})

        if candidato and check_password_hash(candidato['senha_hash'], senha):
            session['candidato_id'] = str(candidato['_id'])
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
            if db.candidatos.find_one({'email': email}):
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

            db.candidatos.insert_one(candidato_doc)
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
        empresa_id = ObjectId(session['empresa_id'])

        # Buscar vagas da empresa com estatísticas de candidaturas
        pipeline = [
            {'$match': {'empresa_id': empresa_id}},
            {'$lookup': {
                'from': 'candidaturas',
                'localField': '_id',
                'foreignField': 'vaga_id',
                'as': 'candidaturas'
            }},
            {'$addFields': {
                'total_candidatos': {'$size': '$candidaturas'},
                'candidatos_80_plus': {
                    '$size': {
                        '$filter': {
                            'input': '$candidaturas',
                            'cond': {'$gte': ['$$this.score', 80]}
                        }
                    }
                },
                'candidatos_60_79': {
                    '$size': {
                        '$filter': {
                            'input': '$candidaturas',
                            'cond': {
                                '$and': [
                                    {'$gte': ['$$this.score', 60]},
                                    {'$lt': ['$$this.score', 80]}
                                ]
                            }
                        }
                    }
                },
                'candidatos_abaixo_60': {
                    '$size': {
                        '$filter': {
                            'input': '$candidaturas',
                            'cond': {'$lt': ['$$this.score', 60]}
                        }
                    }
                }
            }},
            {'$sort': {'created_at': -1}}
        ]

        vagas = list(db.vagas.aggregate(pipeline))

        # Processar vagas para exibição
        vagas_processadas = []
        for vaga in vagas:
            vaga_dict = {
                'id': str(vaga['_id']),
                'titulo': vaga['titulo'],
                'descricao': vaga['descricao'],
                'requisitos': vaga['requisitos'],
                'salario_oferecido': vaga['salario_oferecido'],
                'diferenciais': vaga.get('diferenciais', ''),
                'tipo_vaga': vaga.get('tipo_vaga', 'Presencial'),
                'endereco_vaga': vaga.get('endereco_vaga', ''),
                'status': vaga.get('status', 'Ativa'),
                'data_criacao': vaga['created_at'].strftime('%d/%m/%Y'),
                'total_candidatos': vaga['total_candidatos'],
                'candidatos_80_plus': vaga['candidatos_80_plus'],
                'candidatos_60_79': vaga['candidatos_60_79'],
                'candidatos_abaixo_60': vaga['candidatos_abaixo_60']
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
            empresa_id = ObjectId(session['empresa_id'])
            vaga_doc = {
                'empresa_id': empresa_id,
                'titulo': titulo,
                'descricao': descricao,
                'requisitos': requisitos,
                'diferenciais': diferenciais,
                'salario_oferecido': salario_oferecido,
                'tipo_vaga': tipo_vaga,
                'endereco_vaga': endereco_vaga,
                'status': 'Ativa',
                'created_at': datetime.now()
            }

            db.vagas.insert_one(vaga_doc)
            flash('Vaga criada com sucesso!', 'success')
            return redirect(url_for('dashboard_empresa'))

        except Exception as e:
            flash(f'Erro ao criar vaga: {str(e)}', 'error')
            return render_template('criar_vaga.html')

    return render_template('criar_vaga.html')


@app.route('/candidatos_vaga/<string:vaga_id>')
def candidatos_vaga(vaga_id):
    if 'empresa_id' not in session:
        return redirect(url_for('login_empresa'))

    try:
        vaga_object_id = ObjectId(vaga_id)
        # Fetch candidates for the given vaga_id
        candidates = list(db.candidaturas.aggregate([
            {
                '$match': {
                    'vaga_id': vaga_object_id
                }
            },
            {
                '$lookup': {
                    'from': 'candidatos',
                    'localField': 'candidato_id',
                    'foreignField': '_id',
                    'as': 'candidato_info'
                }
            },
            {
                '$unwind': '$candidato_info'
            },
            {
                '$project': {
                    '_id': '$candidato_info._id',
                    'nome': '$candidato_info.nome',
                    'email': '$candidato_info.email',
                    'telefone': '$candidato_info.telefone',
                    'linkedin': '$candidato_info.linkedin',
                    'score': '$score',
                    'posicao': '$posicao',
                    'endereco_completo': '$candidato_info.endereco_completo'
                }
            },
            {
                '$sort': {
                    'score': -1
                }
            }
        ]))

        # Fetch the title of the job posting
        vaga = db.vagas.find_one({'_id': vaga_object_id})
        vaga_titulo = vaga['titulo'] if vaga else ''

        return render_template('candidatos_vaga.html',
                               candidatos=candidates,
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
        candidato_id = ObjectId(session['candidato_id'])
        candidato = db.candidatos.find_one({'_id': candidato_id})

        if not candidato or not candidato.get('texto_curriculo'):
            return redirect(url_for('upload_curriculo'))

        # Buscar candidaturas do candidato
        candidaturas = list(db.candidaturas.find({'candidato_id': candidato_id}))

        # Buscar vagas disponíveis (não candidatadas)
        candidaturas_vaga_ids = [c['vaga_id'] for c in candidaturas]
        vagas_disponiveis = list(db.vagas.find({
            '_id': {'$nin': candidaturas_vaga_ids},
            'status': {'$in': ['Ativa', None]}
        }))

        # Calcular scores para vagas disponíveis (simulado por agora)
        top_vagas = []
        for vaga in vagas_disponiveis[:TOP_JOBS]:
            empresa = db.empresas.find_one({'_id': vaga['empresa_id']})
            vaga_processada = {
                'id': str(vaga['_id']),
                'titulo': vaga['titulo'],
                'descricao': vaga['descricao'],
                'requisitos': vaga['requisitos'],
                'salario_oferecido': vaga['salario_oferecido'],
                'empresa_nome': empresa['nome'] if empresa else 'N/A',
                'diferenciais': vaga.get('diferenciais', ''),
                'tipo_vaga': vaga.get('tipo_vaga', 'Presencial'),
                'endereco_vaga': vaga.get('endereco_vaga', ''),
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

    # resultado = finalizar_processamento_curriculo(request,
    #                                               session['candidato_id'])
    #
    # for mensagem in resultado['mensagens']:
    #     flash(mensagem['texto'], mensagem['tipo'])
    #
    # if resultado['sucesso']:
    #     return redirect(url_for('dashboard_candidato'))
    # else:
    #     return redirect(url_for('upload_curriculo'))
    flash('Funcionalidade em construção', 'info')
    return redirect(url_for('dashboard_candidato'))

@app.route('/candidatar/<string:vaga_id>')
def candidatar(vaga_id):
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))

    try:
        candidato_id = ObjectId(session['candidato_id'])
        vaga_id_object = ObjectId(vaga_id)

        # Check if the candidate has already applied for this job
        if db.candidaturas.find_one({'candidato_id': candidato_id, 'vaga_id': vaga_id_object}):
            flash('Você já se candidatou para esta vaga.', 'warning')
            return redirect(url_for('dashboard_candidato'))

        # Create a new application document
        candidatura = {
            'candidato_id': candidato_id,
            'vaga_id': vaga_id_object,
            'data_candidatura': datetime.now(),
            'score': 75.0,  # Default score, you can calculate it later
            'posicao': 1  # Default position, you can update it later
        }

        db.candidaturas.insert_one(candidatura)

        flash('Candidatura realizada com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao candidatar-se: {str(e)}', 'error')

    return redirect(url_for('dashboard_candidato'))

@app.route('/api/candidatos_vaga/<string:vaga_id>')
def api_candidatos_vaga(vaga_id):
    if 'empresa_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    try:
        vaga_object_id = ObjectId(vaga_id)
        # Fetch candidates for the given vaga_id
        candidates = list(db.candidaturas.aggregate([
            {
                '$match': {
                    'vaga_id': vaga_object_id
                }
            },
            {
                '$lookup': {
                    'from': 'candidatos',
                    'localField': 'candidato_id',
                    'foreignField': '_id',
                    'as': 'candidato_info'
                }
            },
            {
                '$unwind': '$candidato_info'
            },
            {
                '$project': {
                    '_id': '$candidato_info._id',
                    'nome': '$candidato_info.nome',
                    'score': '$score'
                }
            },
            {
                '$sort': {
                    'score': -1
                }
            }
        ]))

        # Structure the data for JSON response
        candidate_list = []
        for candidate in candidates:
            candidate_list.append({
                'id': str(candidate['_id']),
                'nome': candidate['nome'],
                'score': round(candidate['score'], 1)
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
        vaga_object_id = ObjectId(vaga_id)
        empresa_id = ObjectId(session['empresa_id'])

        # Verificar se a vaga pertence à empresa
        vaga = db.vagas.find_one({'_id': vaga_object_id, 'empresa_id': empresa_id})
        if not vaga:
            return jsonify({'error': 'Vaga não encontrada'}), 404

        if acao == 'contratar':
            if not candidato_id:
                return jsonify({'error': 'Candidato não selecionado'}), 400

            candidato_object_id = ObjectId(candidato_id)
            # Verificar se o candidato se candidatou à vaga
            candidatura = db.candidaturas.find_one({'candidato_id': candidato_object_id, 'vaga_id': vaga_object_id})
            if not candidatura:
                return jsonify({'error': 'Candidato não se candidatou a esta vaga'}), 400

            # Marcar vaga como Concluída e definir candidato selecionado
            db.vagas.update_one(
                {'_id': vaga_object_id},
                {'$set': {'status': 'Concluída', 'candidato_selecionado_id': candidato_object_id}}
            )

            # Criar notificação para o candidato
            if not mensagem_personalizada:
                mensagem_personalizada = "Parabéns! Você foi selecionado para esta vaga."

            notificacao = {
                'candidato_id': candidato_object_id,
                'empresa_id': empresa_id,
                'vaga_id': vaga_object_id,
                'mensagem': mensagem_personalizada,
                'data_envio': datetime.now(),
                'lida': False
            }

            db.notificacoes.insert_one(notificacao)

            # Buscar informações para log
            candidato_info = db.candidatos.find_one({'_id': candidato_object_id})
            vaga_info = db.vagas.find_one({'_id': vaga_object_id})

            if candidato_info and vaga_info:
                print(
                    f"Candidato contratado: {candidato_info['nome']} para a vaga {vaga_info['titulo']}. Notificação enviada."
                )

            response = {
                'success': True,
                'message': 'Candidato contratado com sucesso!'
            }

        elif acao == 'congelar':
            db.vagas.update_one(
                {'_id': vaga_object_id},
                {'$set': {'status': 'Congelada'}}
            )
            response = {
                'success': True,
                'message': 'Vaga congelada com sucesso!'
            }

        elif acao == 'excluir':
            # Excluir candidaturas primeiro
            db.candidaturas.delete_many({'vaga_id': vaga_object_id})
            db.vagas.delete_one({'_id': vaga_object_id})

            response = {
                'success': True,
                'message': 'Vaga excluída com sucesso!'
            }

        elif acao == 'reativar':
            db.vagas.update_one(
                {'_id': vaga_object_id},
                {'$set': {'status': 'Ativa'}}
            )
            response = {
                'success': True,
                'message': 'Vaga reativada com sucesso!'
            }

        else:
            return jsonify({'error': 'Ação inválida'}), 400

        return jsonify(response)

    except Exception as e:
        return jsonify({'error': f'Erro ao processar ação: {str(e)}'}), 500

@app.route('/editar_perfil_candidato', methods=['GET', 'POST'])
def editar_perfil_candidato():
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))

    candidato_id = ObjectId(session['candidato_id'])
    candidato = db.candidatos.find_one({'_id': candidato_id})

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
            db.candidatos.update_one(
                {'_id': candidato_id},
                {'$set': {
                    'nome': nome,
                    'telefone': telefone,
                    'linkedin': linkedin,
                    'pretensao_salarial': pretensao_salarial,
                    'experiencia': experiencia,
                    'competencias': competencias,
                    'resumo_profissional': resumo_profissional
                }}
            )
            flash('Perfil atualizado com sucesso!', 'success')
            return redirect(url_for('dashboard_candidato'))
        except Exception as e:
            flash(f'Erro ao atualizar perfil: {str(e)}', 'error')

    return render_template('editar_perfil_candidato.html', candidato=candidato)

@app.route('/editar_vaga/<string:vaga_id>', methods=['GET', 'POST'])
def editar_vaga(vaga_id):
    if 'empresa_id' not in session:
        return redirect(url_for('login_empresa'))

    try:
        vaga_object_id = ObjectId(vaga_id)
        empresa_id = ObjectId(session['empresa_id'])

        # Verificar se a vaga pertence à empresa
        vaga = db.vagas.find_one({'_id': vaga_object_id, 'empresa_id': empresa_id})
        if not vaga:
            flash('Vaga não encontrada', 'error')
            return redirect(url_for('dashboard_empresa'))

        if request.method == 'POST':
            titulo = request.form['titulo']
            descricao = request.form['descricao']
            requisitos = request.form['requisitos']
            salario_oferecido = float(request.form['salario_oferecido'])
            tipo_vaga = request.form['tipo_vaga']
            endereco_vaga = request.form['endereco_vaga']

            db.vagas.update_one(
                {'_id': vaga_object_id},
                {'$set': {
                    'titulo': titulo,
                    'descricao': descricao,
                    'requisitos': requisitos,
                    'salario_oferecido': salario_oferecido,
                    'tipo_vaga': tipo_vaga,
                    'endereco_vaga': endereco_vaga
                }}
            )

            flash('Vaga atualizada com sucesso!', 'success')
            return redirect(url_for('dashboard_empresa'))

        return render_template('editar_vaga.html', vaga=vaga)
    except Exception as e:
        flash(f'Erro ao editar vaga: {str(e)}', 'error')
        return redirect(url_for('dashboard_empresa'))

@app.route('/vaga/<string:vaga_id>')
def detalhes_vaga(vaga_id):
    if 'candidato_id' not in session:
        return redirect(url_for('login_candidato'))

    try:
        vaga_object_id = ObjectId(vaga_id)
        candidato_id = ObjectId(session['candidato_id'])

        # Buscar dados da vaga e empresa
        vaga_data = db.vagas.find_one({'_id': vaga_object_id, 'status': 'Ativa'})

        if not vaga_data:
            flash('Vaga não encontrada ou não está mais ativa', 'error')
            return redirect(url_for('dashboard_candidato'))

        empresa = db.empresas.find_one({'_id': vaga_data['empresa_id']})

        # Verificar se já se candidatou
        candidatura = db.candidaturas.find_one({'candidato_id': candidato_id, 'vaga_id': vaga_object_id})

        # Buscar dados do candidato para calcular feedback
        candidato_data = db.candidatos.find_one({'_id': candidato_id})

        # Estruturar dados da vaga
        vaga = {
            'id': str(vaga_data['_id']),
            'titulo': vaga_data['titulo'],
            'descricao': vaga_data['descricao'],
            'requisitos': vaga_data['requisitos'],
            'salario_oferecido': vaga_data['salario_oferecido'],
            'tipo_vaga': vaga_data.get('tipo_vaga', 'Presencial'),
            'endereco_vaga': vaga_data.get('endereco_vaga', ''),
            'diferenciais': vaga_data.get('diferenciais', ''),
            'data_criacao': vaga_data['created_at']
        }

        empresa_info = {'nome': empresa['nome'] if empresa else 'N/A'}

        # Calcular score e feedback se não candidatado ainda
        score = None
        feedback_performance = None

        if candidato_data:
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
        candidato_id = ObjectId(session['candidato_id'])
        # Fetch all applications for the current candidate
        candidaturas = list(db.candidaturas.aggregate([
            {
                '$match': {
                    'candidato_id': candidato_id
                }
            },
            {
                '$lookup': {
                    'from': 'vagas',
                    'localField': 'vaga_id',
                    'foreignField': '_id',
                    'as': 'vaga_info'
                }
            },
            {
                '$unwind': '$vaga_info'
            },
            {
                '$lookup': {
                    'from': 'empresas',
                    'localField': 'vaga_info.empresa_id',
                    'foreignField': '_id',
                    'as': 'empresa_info'
                }
            },
            {
                '$unwind': '$empresa_info'
            },
            {
                '$project': {
                    '_id': '$vaga_info._id',
                    'titulo': '$vaga_info.titulo',
                    'empresa_nome': '$empresa_info.nome',
                    'salario_oferecido': '$vaga_info.salario_oferecido',
                    'score': '$score',
                    'posicao': '$posicao',
                    'data_candidatura': '$data_candidatura'
                }
            },
            {
                '$sort': {
                    'data_candidatura': -1
                }
            }
        ]))

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
        candidato_object_id = ObjectId(candidato_id)
        empresa_id = ObjectId(session['empresa_id'])

        # Verificar se a empresa tem acesso ao candidato (através de candidatura)
        candidatura = db.candidaturas.find_one({
            'candidato_id': candidato_object_id
        })

        if not candidatura:
            flash('Acesso negado ao currículo', 'error')
            return redirect(url_for('dashboard_empresa'))

        # Buscar dados do candidato
        candidato = db.candidatos.find_one({'_id': candidato_object_id})

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

    # Buscar vagas da empresa para o filtro
    vagas_disponiveis = db.vagas.find({'empresa_id': ObjectId(empresa_id)})

    # from utils.relatorio_generator import gerar_dados_graficos
    # dados_graficos = gerar_dados_graficos(empresa_id)

    return render_template('relatorio_empresa.html',
                           vagas_disponiveis=vagas_disponiveis,
                           dados_graficos=json.dumps({}))

@app.route('/empresa/relatorio/completo')
def relatorio_completo():
    if 'empresa_id' not in session:
        return redirect(url_for('login_empresa'))

    empresa_id = session['empresa_id']
    filtro_vagas = request.args.getlist('vagas')

    # Se foi especificado filtro, converter para inteiros
    if filtro_vagas:
        try:
            filtro_vagas = [ObjectId(v) for v in filtro_vagas]
        except ValueError:
            filtro_vagas = None
    else:
        filtro_vagas = None

    # from utils.relatorio_generator import gerar_relatorio_completo, gerar_html_relatorio

    try:
        # dados = gerar_relatorio_completo(empresa_id, filtro_vagas)
        # html_relatorio = gerar_html_relatorio(dados)
        html_relatorio = "<h1>Relatório Completo (Em Desenvolvimento)</h1>"
        return html_relatorio

    except Exception as e:
        flash(f'Erro ao gerar relatório: {str(e)}', 'error')
        return redirect(url_for('relatorio_empresa'))

@app.route('/api/relatorio/graficos')
def api_relatorio_graficos():
    if 'empresa_id' not in session:
        return {'error': 'Não autorizado'}, 401

    empresa_id = session['empresa_id']
    filtro_vagas = request.args.getlist('vagas')

    if filtro_vagas:
        try:
            filtro_vagas = [ObjectId(v) for v in filtro_vagas]
        except ValueError:
            filtro_vagas = None
    else:
        filtro_vagas = None

    # from utils.relatorio_generator import gerar_dados_graficos

    try:
        # dados = gerar_dados_graficos(empresa_id, filtro_vagas)
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
        candidato_id = ObjectId(session['candidato_id'])
        vaga_object_id = ObjectId(vaga_id)

        # Verificar se a candidatura existe
        candidatura = db.candidaturas.find_one({'candidato_id': candidato_id, 'vaga_id': vaga_object_id})

        if not candidatura:
            return {'error': 'Candidatura não encontrada'}, 404

        # Remover candidatura
        db.candidaturas.delete_one({'candidato_id': candidato_id, 'vaga_id': vaga_object_id})

        # # Recalcular posições dos candidatos restantes (Implementar se necessário)
        # db.candidaturas.update_many({'vaga_id': vaga_object_id}, {'$inc': {'posicao': -1}})

        return {'success': True}

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/reativar_vaga/<string:vaga_id>", methods=["POST"])
def reativar_vaga_route(vaga_id):
    if 'empresa_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    try:
        vaga_object_id = ObjectId(vaga_id)

        db.vagas.update_one(
            {'_id': vaga_object_id},
            {'$set': {'status': 'Ativa'}}
        )

        return redirect(url_for('dashboard_empresa'))

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/notificacoes')
def api_notificacoes():
    if 'candidato_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    try:
        candidato_id = ObjectId(session['candidato_id'])

        notificacoes = list(db.notificacoes.aggregate([
            {
                '$match': {
                    'candidato_id': candidato_id
                }
            },
            {
                '$lookup': {
                    'from': 'vagas',
                    'localField': 'vaga_id',
                    'foreignField': '_id',
                    'as': 'vaga_info'
                }
            },
            {
                '$unwind': '$vaga_info'
            },
            {
                '$lookup': {
                    'from': 'empresas',
                    'localField': 'empresa_id',
                    'foreignField': '_id',
                    'as': 'empresa_info'
                }
            },
            {
                '$unwind': '$empresa_info'
            },
            {
                '$project': {
                    '_id': '$_id',
                    'mensagem': '$mensagem',
                    'data_envio': '$data_envio',
                    'lida': '$lida',
                    'vaga_titulo': '$vaga_info.titulo',
                    'empresa_nome': '$empresa_info.nome'
                }
            },
            {
                '$sort': {
                    'data_envio': -1
                }
            }
        ]))

        # Convert ObjectId to string for JSON serialization
        for notificacao in notificacoes:
            notificacao['_id'] = str(notificacao['_id'])
            notificacao['data_envio'] = notificacao['data_envio'].isoformat()

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
        notificacao_object_id = ObjectId(notificacao_id)
        candidato_id = ObjectId(session['candidato_id'])

        db.notificacoes.update_one(
            {'_id': notificacao_object_id, 'candidato_id': candidato_id},
            {'$set': {'lida': True}}
        )

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/notificacoes/marcar-todas-lidas', methods=['POST'])
def marcar_todas_notificacoes_lidas():
    if 'candidato_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401

    try:
        candidato_id = ObjectId(session['candidato_id'])

        db.notificacoes.update_many(
            {'candidato_id': candidato_id},
            {'$set': {'lida': True}}
        )

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # inicializar_banco() # Removed: Not needed with MongoDB
    app.run(host='0.0.0.0', port=5001, debug=True)

