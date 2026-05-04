import fitz  # PyMuPDF
import re
from state_db import register_document
from automacao import map_document_to_sector

def extract_documents_from_pdf(pdf_path: str):
    """
    Lê o PDF do MEC, extrai a lista de documentos obrigatórios e
    alimenta o nosso banco de estado (SQLite) de forma idempotente.
    """
    print(f"[*] Extraindo exigências do arquivo: {pdf_path}")
    
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"[!] Erro ao abrir PDF: {e}")
        return

    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"
        
    doc.close()

    # Dicionário de documentos oficiais básicos exigidos em qualquer recredenciamento
    # Isso atua como nossa "Regex Semântica" para identificar se o termo está no edital
    expected_docs = [
        "Plano de Desenvolvimento Institucional",
        "Projeto Pedagógico Institucional",
        "Relatório de Autoavaliação Institucional",
        "Estatuto",
        "Regimento Geral",
        "Plano de Carreira Docente",
        "Relatório de Gestão"
    ]
    
    found_count = 0
    
    for expected_doc in expected_docs:
        # Busca case-insensitive no texto do PDF
        if re.search(expected_doc, full_text, re.IGNORECASE):
            sector = map_document_to_sector(expected_doc)
            # Insere no banco de dados. O state_db garante que não haverá duplicatas (idempotência)
            register_document(doc_type=expected_doc, sector=sector)
            found_count += 1
            print(f" [+] Encontrado: {expected_doc} -> Roteado para {sector}")
            
    print(f"[*] Total de documentos obrigatórios identificados e registrados no DB: {found_count}")

if __name__ == "__main__":
    # Teste rápido de extração
    pdf_alvo = "Art. 20 do Decreto nº 9.235, de 15 de dezembro de 2017.pdf"
    extract_documents_from_pdf(pdf_alvo)
