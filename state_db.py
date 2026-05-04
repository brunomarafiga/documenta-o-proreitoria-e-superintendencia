import sqlite3
import os
from datetime import datetime

DB_NAME = "recredenciamento_estado.db"

def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados SQLite local."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    """
    Cria a tabela de estado se não existir.
    Status possíveis: 'PENDENTE', 'BAIXADO', 'FALHA'
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_type TEXT NOT NULL,
            sector TEXT NOT NULL,
            year TEXT,
            status TEXT DEFAULT 'PENDENTE',
            url_found TEXT,
            local_path TEXT,
            last_updated TIMESTAMP
        )
    ''')
    
    # Adicionando um índice único para evitar duplicar a mesma exigência
    cursor.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_doc_unique 
        ON documentos(doc_type, sector, year)
    ''')
    
    conn.commit()
    conn.close()

def register_document(doc_type: str, sector: str, year: str = None):
    """
    Registra um documento extraído do edital no banco.
    Se já existir, não faz nada (Idempotência).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO documentos (doc_type, sector, year, last_updated)
            VALUES (?, ?, ?, ?)
        ''', (doc_type, sector, year, datetime.now()))
        conn.commit()
    except sqlite3.IntegrityError:
        # Documento já registrado na base, segue a vida
        pass
    finally:
        conn.close()

def get_pending_documents():
    """Retorna todos os documentos que ainda precisam ser baixados."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM documentos WHERE status = 'PENDENTE'")
    rows = cursor.fetchall()
    
    conn.close()
    return [dict(row) for row in rows]

def update_document_status(doc_id: int, status: str, url: str = None, local_path: str = None):
    """Atualiza o estado de um documento após a tentativa de download."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE documentos 
        SET status = ?, url_found = ?, local_path = ?, last_updated = ?
        WHERE id = ?
    ''', (status, url, local_path, datetime.now(), doc_id))
    
    conn.commit()
    conn.close()

# Inicializa o DB ao importar este módulo
initialize_database()
