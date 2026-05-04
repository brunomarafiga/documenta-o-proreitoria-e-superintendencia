import asyncio
import aiohttp
from duckduckgo_search import AsyncDDGS
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import os

from state_db import get_pending_documents, update_document_status
from automacao import build_search_query, is_safe_url, normalize_filename

# Headers robustos para evitar bloqueio (User-Agent Institucional/Transparente)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


class ScrapingError(Exception):
    pass

@retry(
    stop=stop_after_attempt(4), 
    wait=wait_exponential(multiplier=2, min=2, max=10),
    retry=retry_if_exception_type((aiohttp.ClientError, ScrapingError, Exception))
)
async def search_document_url(session: aiohttp.ClientSession, doc_type: str, year: str) -> str:
    """
    Usa a API do duckduckgo_search para contornar o bloqueio anti-bot.
    """
    query = build_search_query(doc_type, year)
    
    try:
        # DDGS Async permite rodar sem bloquear o loop
        async with AsyncDDGS() as ddgs:
            results = await ddgs.atext(query, max_results=3)
            
            for result in results:
                url = result.get('href', '')
                if is_safe_url(url):
                    return url
                    
    except Exception as e:
        print(f"[!] Erro no motor de busca DDGS: {e}")
        raise ScrapingError(f"Erro na busca: {e}")
        
    return None

@retry(
    stop=stop_after_attempt(3), 
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type(aiohttp.ClientError)
)
async def download_pdf(session: aiohttp.ClientSession, url: str, local_path: str):
    """Baixa o PDF e salva no disco de forma assíncrona."""
    async with session.get(url, headers=HEADERS) as response:
        response.raise_for_status()
        
        # Garante que a pasta do setor existe
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        with open(local_path, 'wb') as f:
            while True:
                chunk = await response.content.read(1024 * 64)
                if not chunk:
                    break
                f.write(chunk)

async def process_document(session: aiohttp.ClientSession, doc: dict):
    """Processa um documento de ponta a ponta: Busca -> Baixa -> Salva -> Atualiza DB."""
    doc_id = doc['id']
    doc_type = doc['doc_type']
    sector = doc['sector']
    year = doc['year']
    
    print(f"[*] Worker Iniciado: Buscando '{doc_type}' para {sector}...")
    
    try:
        # 1. Busca a URL
        url = await search_document_url(session, doc_type, year)
        
        if not url:
            print(f" [!] Falha: Nenhuma URL segura encontrada para '{doc_type}'.")
            update_document_status(doc_id, "FALHA")
            return
            
        print(f" [+] URL encontrada: {url}")
        
        # 2. Normaliza o nome do arquivo e monta o caminho local
        final_filename = normalize_filename("pdf_web.pdf", sector, doc_type, year)
        # Salva dentro de uma subpasta do setor atual
        local_path = os.path.join(os.getcwd(), sector, final_filename)
        
        # 3. Baixa o arquivo
        await download_pdf(session, url, local_path)
        
        # 4. Atualiza o banco (Transaction Commit)
        update_document_status(doc_id, "BAIXADO", url=url, local_path=local_path)
        print(f" [OK] Salvo com sucesso: {local_path}")
        
    except Exception as e:
        print(f" [X] Erro crítico ao processar '{doc_type}': {str(e)}")
        update_document_status(doc_id, "FALHA")

async def main_pipeline():
    """Ponto de entrada assíncrono para processar todos os pendentes."""
    pendentes = get_pending_documents()
    
    if not pendentes:
        print("Nenhum documento pendente no banco de dados!")
        return
        
    print(f"Encontrados {len(pendentes)} documentos pendentes. Iniciando Workers Async...")
    
    # Limita conexões simultâneas para não estressar a rede/servidores
    connector = aiohttp.TCPConnector(limit=5)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Cria uma task para cada documento pendente (Paralelismo)
        tasks = [process_document(session, doc) for doc in pendentes]
        await asyncio.gather(*tasks)
        
    print("\nPipeline Finalizado! Verifique o banco de dados e as pastas.")

if __name__ == "__main__":
    asyncio.run(main_pipeline())
