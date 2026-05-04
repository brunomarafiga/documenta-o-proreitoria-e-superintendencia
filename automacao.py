import re
import urllib.parse
from urllib.parse import urlparse

# ==========================================
# 1. Funções de Sanitização
# ==========================================

def sanitize_string(dirty_string: str) -> str:
    """
    Remove caracteres inválidos para sistema de arquivos do Windows
    e normaliza acentuações simples para ASCII.
    """
    # 1. Substituições manuais para acentuação comum (para não precisar de unidecode externo)
    replacements = {
        'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a',
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
        'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c', 'ñ': 'n',
        'Á': 'A', 'À': 'A', 'Â': 'A', 'Ã': 'A', 'Ä': 'A',
        'É': 'E', 'È': 'E', 'Ê': 'E', 'Ë': 'E',
        'Í': 'I', 'Ì': 'I', 'Î': 'I', 'Ï': 'I',
        'Ó': 'O', 'Ò': 'O', 'Ô': 'O', 'Õ': 'O', 'Ö': 'O',
        'Ú': 'U', 'Ù': 'U', 'Û': 'U', 'Ü': 'U',
        'Ç': 'C', 'Ñ': 'N'
    }
    for char, replacement in replacements.items():
        dirty_string = dirty_string.replace(char, replacement)

    # 2. Remover caracteres inválidos do Windows e alguns pontuadores feios (< > : " / \ | ? * e |)
    dirty_string = re.sub(r'[<>:"/\\|?*]', '', dirty_string)
    
    # 3. Remover underscores excessivos e múltiplos espaços
    dirty_string = re.sub(r'_+', ' ', dirty_string)
    dirty_string = re.sub(r'\s+', ' ', dirty_string)
    
    return dirty_string.strip()

def is_safe_url(url: str) -> bool:
    """
    Valida se a URL pertence ao domínio ufpr.br e (idealmente) termina em .pdf.
    """
    try:
        parsed = urlparse(url)
        # Trava de domínio
        if "ufpr.br" not in parsed.netloc:
            return False
        
        # Trava de extensão (básica, sem checar headers ainda)
        path = parsed.path.lower()
        if not path.endswith('.pdf'):
            # Algumas URLs podem ser rotas que geram pdf, mas vamos manter estrito no teste
            return False
            
        return True
    except Exception:
        return False


# ==========================================
# 2. Funções de Normalização
# ==========================================

def normalize_filename(original_name: str, sector: str, doc_type: str, year: str = None) -> str:
    """
    Constrói o nome final padronizado do arquivo.
    Ignora o original_name quase completamente, usando-o apenas como log se necessário.
    """
    clean_doc_type = sanitize_string(doc_type)
    
    if year:
        clean_year = sanitize_string(str(year))
        return f"{sector} - {clean_doc_type} - {clean_year}.pdf"
    else:
        return f"{sector} - {clean_doc_type}.pdf"


# ==========================================
# 3. Mapeamento e Query (Dorking)
# ==========================================

def map_document_to_sector(doc_type: str) -> str:
    """
    Mapeia os documentos exigidos para as Pró-Reitorias/Superintendências da UFPR.
    """
    doc_lower = doc_type.lower()
    
    if "desenvolvimento institucional" in doc_lower or "gestão" in doc_lower or "pdi" in doc_lower:
        return "PROPLAD"
    elif "pessoal" in doc_lower or "carreira" in doc_lower or "capacitação" in doc_lower:
        return "PROGEPE"
    elif "autoavaliação" in doc_lower or "cpa" in doc_lower or "relato institucional" in doc_lower:
        return "CPA"
    elif "estatuto" in doc_lower or "regimento geral" in doc_lower:
        return "SOC"
    elif "graduação" in doc_lower or "pedagógico" in doc_lower:
        return "PROGRAD"
    
    return "Geral"

def build_search_query(doc_type: str, year: str = None) -> str:
    """
    Cria a string de dorking para a busca do Google.
    """
    query = f'site:ufpr.br filetype:pdf "{doc_type}"'
    if year:
        query += f' {year}'
    return query

