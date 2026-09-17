
import sqlite3
import pymongo
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

# Configuração MongoDB
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
client = pymongo.MongoClient(MONGO_URI)
db = client.recrutamento

def migrate_data():
    """Migra dados do SQLite para MongoDB"""
    
    # Conectar ao SQLite
    conn = sqlite3.connect('recrutamento.db')
    cursor = conn.cursor()
    
    try:
        # Migrar empresas
        cursor.execute('SELECT * FROM empresas')
        empresas = cursor.fetchall()
        
        for empresa in empresas:
            empresa_doc = {
                'sqlite_id': empresa[0],
                'cnpj': empresa[1],
                'nome': empresa[2],
                'email': empresa[3],
                'senha_hash': empresa[4],
                'created_at': datetime.now()
            }
            db.empresas.insert_one(empresa_doc)
            print(f"Migrada empresa: {empresa[2]}")
        
        # Migrar candidatos
        cursor.execute('SELECT * FROM candidatos')
        candidatos = cursor.fetchall()
        
        for candidato in candidatos:
            candidato_doc = {
                'sqlite_id': candidato[0],
                'nome': candidato[1],
                'email': candidato[2],
                'senha_hash': candidato[3],
                'telefone': candidato[4] if len(candidato) > 4 else '',
                'linkedin': candidato[5] if len(candidato) > 5 else '',
                'endereco_completo': candidato[6] if len(candidato) > 6 else '',
                'pretensao_salarial': candidato[7] if len(candidato) > 7 else 0.0,
                'texto_curriculo': candidato[8] if len(candidato) > 8 else '',
                'caminho_curriculo': candidato[9] if len(candidato) > 9 else '',
                'experiencia': candidato[10] if len(candidato) > 10 else '',
                'competencias': candidato[11] if len(candidato) > 11 else '',
                'resumo_profissional': candidato[12] if len(candidato) > 12 else '',
                'created_at': datetime.now()
            }
            db.candidatos.insert_one(candidato_doc)
            print(f"Migrado candidato: {candidato[1]}")
        
        # Migrar vagas
        cursor.execute('SELECT * FROM vagas')
        vagas = cursor.fetchall()
        
        for vaga in vagas:
            # Buscar empresa MongoDB ID
            empresa_mongo = db.empresas.find_one({'sqlite_id': vaga[1]})
            
            vaga_doc = {
                'sqlite_id': vaga[0],
                'empresa_id': empresa_mongo['_id'] if empresa_mongo else None,
                'titulo': vaga[2],
                'descricao': vaga[3],
                'requisitos': vaga[4],
                'salario_oferecido': vaga[5],
                'data_criacao': vaga[6],
                'tipo_vaga': vaga[7] if len(vaga) > 7 else 'Presencial',
                'endereco_vaga': vaga[8] if len(vaga) > 8 else '',
                'status': vaga[9] if len(vaga) > 9 else 'Ativa',
                'candidato_selecionado_id': vaga[10] if len(vaga) > 10 else None,
                'diferenciais': vaga[11] if len(vaga) > 11 else '',
                'created_at': datetime.now()
            }
            db.vagas.insert_one(vaga_doc)
            print(f"Migrada vaga: {vaga[2]}")
        
        # Migrar candidaturas
        cursor.execute('SELECT * FROM candidaturas')
        candidaturas = cursor.fetchall()
        
        for candidatura in candidaturas:
            # Buscar IDs MongoDB correspondentes
            candidato_mongo = db.candidatos.find_one({'sqlite_id': candidatura[1]})
            vaga_mongo = db.vagas.find_one({'sqlite_id': candidatura[2]})
            
            candidatura_doc = {
                'sqlite_id': candidatura[0],
                'candidato_id': candidato_mongo['_id'] if candidato_mongo else None,
                'vaga_id': vaga_mongo['_id'] if vaga_mongo else None,
                'score': candidatura[3],
                'posicao': candidatura[4],
                'data_candidatura': candidatura[5],
                'created_at': datetime.now()
            }
            db.candidaturas.insert_one(candidatura_doc)
            print(f"Migrada candidatura ID: {candidatura[0]}")
        
        print("Migração concluída com sucesso!")
        
    except Exception as e:
        print(f"Erro na migração: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_data()
