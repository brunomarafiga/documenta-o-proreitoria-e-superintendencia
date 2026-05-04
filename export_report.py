import os
import pandas as pd

def export_folder_matrix_to_excel(output_name="matriz_documentos_pastas.xlsx"):
    """
    Varre a estrutura de diretórios reais do repositório, identificando
    Pró-reitorias/Superintendências e suas subpastas (exigências).
    Gera uma matriz mostrando quais pastas já possuem arquivos (ENCONTRADO) 
    e quais estão vazias (FALTA).
    """
    
    # Ignorar apenas lixos de sistema e pastas de ambiente Python
    ignore_dirs = {'.git', '.pytest_cache', '__pycache__', '.vscode'}
    
    sectors = [d for d in os.listdir('.') if os.path.isdir(d) and d not in ignore_dirs]
    
    data = []
    
    for sector in sectors:
        sector_path = os.path.join('.', sector)
        subdirs = [d for d in os.listdir(sector_path) if os.path.isdir(os.path.join(sector_path, d))]
        
        for subdir in subdirs:
            subdir_path = os.path.join(sector_path, subdir)
            # Ignorar arquivos de instrução (.png) e contar apenas PDFs
            files = [f for f in os.listdir(subdir_path) if os.path.isfile(os.path.join(subdir_path, f)) and f.lower().endswith('.pdf')]
            
            status = "✅ OK (Possui Arquivo)" if len(files) > 0 else "❌ FALTA"
            
            data.append({
                "Setor": sector,
                "Documento Exigido (Subpasta)": subdir,
                "Status": status
            })

    if not data:
        print("[!] Nenhuma subpasta encontrada para análise.")
        return

    df = pd.DataFrame(data)
    
    # Cria uma tabela dinâmica (Pivot Table)
    # Linhas: Setores | Colunas: Documentos Exigidos | Valores: Status
    pivot_df = df.pivot_table(
        index='Setor', 
        columns='Documento Exigido (Subpasta)', 
        values='Status', 
        aggfunc='first',
        fill_value='-'
    )

    try:
        with pd.ExcelWriter(output_name, engine='openpyxl') as writer:
            pivot_df.to_excel(writer, sheet_name='Matriz de Pastas Físicas')
            df.to_excel(writer, sheet_name='Lista Detalhada', index=False)
            
        print(f"[*] Matriz de pastas gerada com sucesso: {output_name}")
    except Exception as e:
        print(f"[!] Erro ao gerar matriz: {e}")

if __name__ == "__main__":
    export_folder_matrix_to_excel()
