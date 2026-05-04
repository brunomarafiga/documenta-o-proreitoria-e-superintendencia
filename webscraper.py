import os
import time
import random
import requests
from ddgs import DDGS
import urllib.parse
from pypdf import PdfReader

def clean_doc_name(raw_name: str) -> str:
    """Remove a numeração do nome da pasta (ex: '1. Documentos Institucionais' -> 'Documentos Institucionais')"""
    parts = raw_name.split('.', 1)
    if len(parts) > 1:
        return parts[1].strip()
    return raw_name.strip()

def get_sector_info(raw_name: str) -> tuple:
    """Extrai a sigla e o nome completo da pró-reitoria (ex: 'PROPG - Pós-graduação' -> 'PROPG', 'Pós-graduação')"""
    parts = raw_name.split(' - ', 1)
    acronym = parts[0].strip()
    name = parts[1].strip() if len(parts) > 1 else acronym
    return acronym, name

def verify_pdf_content(file_path: str, acronym: str, full_name: str) -> bool:
    """Verifica se o PDF baixado realmente contém a sigla ou o nome completo do setor"""
    try:
        reader = PdfReader(file_path)
        # Analisa as primeiras 5 páginas (otimização de tempo)
        num_pages = min(5, len(reader.pages))
        
        for i in range(num_pages):
            page = reader.pages[i]
            text = page.extract_text()
            if text:
                text_lower = text.lower()
                # Removemos acentos e afins para melhorar a robustez se necessário, 
                # mas uma busca com lower() já atende 90% dos casos.
                if acronym.lower() in text_lower or full_name.lower() in text_lower:
                    return True
                    
        print(f"      [!] Rejeitado: O texto do PDF não cita '{acronym}' nem '{full_name}'.")
        return False
    except Exception as e:
        print(f"      [!] Falha ao ler PDF (pode estar corrompido ou restrito): {e}")
        return False

def download_pdf(url: str, save_path: str) -> bool:
    """Baixa um arquivo PDF da URL e o salva no disco"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, stream=True, timeout=10)
        response.raise_for_status()
        
        # Garante que é um PDF
        content_type = response.headers.get('Content-Type', '').lower()
        if 'pdf' not in content_type and not url.lower().endswith('.pdf'):
            print(f"      [!] URL não parece ser um PDF válido: {url}")
            return False
            
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"      [!] Erro ao baixar {url}: {e}")
        return False

def run_scraper():
    print("="*60)
    print(" INICIANDO ROBÔ DE WEBSCRAPING (Preenchimento de Pastas)")
    print("="*60)
    
    ignore_dirs = {'.git', '.pytest_cache', '__pycache__', '.vscode'}
    sectors = [d for d in os.listdir('.') if os.path.isdir(d) and d not in ignore_dirs]
    
    ddgs = DDGS()
    
    for sector in sectors:
        sector_acronym, sector_name = get_sector_info(sector)
        sector_path = os.path.join('.', sector)
        subdirs = [d for d in os.listdir(sector_path) if os.path.isdir(os.path.join(sector_path, d))]
        
        for subdir in subdirs:
            subdir_path = os.path.join(sector_path, subdir)
            # Verifica se já existe algum PDF baixado
            existing_pdfs = [f for f in os.listdir(subdir_path) if f.lower().endswith('.pdf')]
            
            if existing_pdfs:
                print(f"[PULANDO] {sector_acronym} -> {subdir} (Já possui arquivo)")
                continue
                
            doc_name = clean_doc_name(subdir)
            
            # Formar a dork query com sigla E nome completo, maximizando acertos
            query = f"site:ufpr.br {sector_acronym} \"{sector_name}\" {doc_name} pdf"
            print(f"[*] BUSCANDO: {sector_acronym} -> {doc_name} | Query: '{query}'")
            
            success = False
            try:
                # Buscando no DuckDuckGo
                results = list(ddgs.text(query, max_results=3))
                
                for res in results:
                    url = res.get('href', '')
                    if url and ('pdf' in url.lower()):
                        print(f"    [+] Link promissor encontrado: {url}")
                        
                        safe_filename = f"{sector_acronym} - {doc_name}.pdf"
                        safe_filename = safe_filename.replace('/', '-').replace('\\', '-')
                        save_path = os.path.join(subdir_path, safe_filename)
                        
                        if download_pdf(url, save_path):
                            print(f"    [>] Verificando autenticidade interna do PDF...")
                            if verify_pdf_content(save_path, sector_acronym, sector_name):
                                print(f"    [OK] PDF validado e salvo com sucesso!")
                                success = True
                                break
                            else:
                                os.remove(save_path)
                                print(f"    [X] Arquivo excluído por não pertencer ao setor. Tentando o próximo...")
                
                if not success:
                    print("    [FALHA] Nenhum PDF direto encontrado para esta busca.")
                    
            except Exception as e:
                print(f"    [!] Falha ao consultar o motor de busca: {e}")
            
            # Anti-Rate Limit: Pausa aleatória de 2 a 4 segundos
            delay = random.uniform(2.0, 4.0)
            print(f"    [Zzz] Pausando por {delay:.1f} segundos para evitar bloqueio...")
            time.sleep(delay)

    print("\n" + "="*60)
    print(" VARREDURA FINALIZADA! Rode 'python export_report.py' para ver a matriz.")
    print("="*60)

if __name__ == "__main__":
    run_scraper()
