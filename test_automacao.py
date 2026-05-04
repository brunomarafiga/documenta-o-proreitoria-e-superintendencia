import pytest
from automacao import normalize_filename, build_search_query, map_document_to_sector

# ==========================================
# 1. Testes de Normalização de Arquivos
# ==========================================
def test_normalize_filename_removes_system_suffixes():
    """Testa se sufixos como _v2, final, _compressed são removidos."""
    original = "pdi_final_v2_compressed.pdf"
    expected = "PROPLAD - Plano de Desenvolvimento Institucional (PDI) - 2022-2026.pdf"
    
    # Assumindo que a função receba: (nome original, Setor, Nome Padrão, Ano/Vigência)
    result = normalize_filename(
        original, 
        sector="PROPLAD", 
        doc_type="Plano de Desenvolvimento Institucional (PDI)", 
        year="2022-2026"
    )
    assert result == expected

def test_normalize_filename_handles_accents_and_special_chars():
    """Testa se caracteres estranhos e acentos indesejados são tratados, 
    embora o nome padrão já deva resolver a maioria."""
    original = "relatório_CPA_à_avaliação_final_@2023!.pdf"
    expected = "CPA - Relatorio de Autoavaliacao Institucional - 2023.pdf"
    
    result = normalize_filename(
        original, 
        sector="CPA", 
        doc_type="Relatorio de Autoavaliacao Institucional", 
        year="2023"
    )
    assert result == expected

def test_normalize_filename_without_year():
    """Testa comportamento quando um documento não possui um ano específico atrelado."""
    original = "estatuto_ufpr_scan.pdf"
    expected = "SOC - Estatuto da UFPR.pdf"
    
    result = normalize_filename(
        original, 
        sector="SOC", 
        doc_type="Estatuto da UFPR", 
        year=None
    )
    assert result == expected


# ==========================================
# 2. Testes do Sistema de Sanitização
# ==========================================
from automacao import sanitize_string, is_safe_url

def test_sanitize_string_removes_invalid_path_chars():
    """Garante que caracteres inválidos para o Windows sejam removidos."""
    dirty_string = 'Relatório: CPA <Final> | "2023"?.pdf'
    expected = 'Relatorio CPA Final 2023.pdf'
    
    assert sanitize_string(dirty_string) == expected

def test_sanitize_string_removes_accents():
    """Garante que acentuação complexa seja normalizada para evitar erros de encoding."""
    dirty_string = 'Açãô dë Âvâliáçãõ'
    expected = 'Acao de Avaliacao'
    
    assert sanitize_string(dirty_string) == expected

def test_is_safe_url_validates_domain():
    """O sistema de sanitização de rede deve bloquear URLs fora do escopo da UFPR."""
    assert is_safe_url("https://proplad.ufpr.br/documentos/pdi.pdf") is True
    assert is_safe_url("https://www.google.com/url?q=ufpr.br/pdi") is False
    assert is_safe_url("http://malicious-site.com/fake_ufpr_pdi.pdf") is False

def test_is_safe_url_validates_extension():
    """Garante que só aceitamos links que terminem em .pdf (ou que o Content-Type confirme)."""
    assert is_safe_url("https://ufpr.br/documento.pdf") is True
    assert is_safe_url("https://ufpr.br/pagina_html") is False


# ==========================================
# 3. Testes de Construção de Query (Dorking)
# ==========================================
def test_build_search_query_basic():
    """Testa se a string de busca para o Google/DuckDuckGo está correta e restrita à UFPR."""
    doc_type = "Plano de Desenvolvimento Institucional"
    expected_query = 'site:ufpr.br filetype:pdf "Plano de Desenvolvimento Institucional"'
    
    result = build_search_query(doc_type)
    assert result == expected_query

def test_build_search_query_with_year():
    """Testa se o ano/vigência é embutido na query de pesquisa."""
    doc_type = "Relatório de Gestão"
    year = "2023"
    expected_query = 'site:ufpr.br filetype:pdf "Relatório de Gestão" 2023'
    
    result = build_search_query(doc_type, year=year)
    assert result == expected_query


# ==========================================
# 3. Testes de Mapeamento Lógico (Setores)
# ==========================================
def test_map_document_to_sector_proplad():
    """Testa se documentos de planejamento e orçamento vão para a PROPLAD."""
    assert map_document_to_sector("Plano de Desenvolvimento Institucional (PDI)") == "PROPLAD"
    assert map_document_to_sector("Relatório de Gestão") == "PROPLAD"

def test_map_document_to_sector_progepe():
    """Testa se documentos de pessoal vão para a PROGEPE."""
    assert map_document_to_sector("Plano de Carreira Docente") == "PROGEPE"
    assert map_document_to_sector("Políticas de Capacitação") == "PROGEPE"

def test_map_document_to_sector_cpa():
    """Testa se documentos de avaliação vão para a CPA."""
    assert map_document_to_sector("Relatório de Autoavaliação Institucional") == "CPA"
    assert map_document_to_sector("Relato Institucional") == "CPA"

def test_map_document_to_sector_unknown():
    """Testa fallback para um documento não mapeado."""
    assert map_document_to_sector("Documento Alienígena Inexistente") == "Geral"
