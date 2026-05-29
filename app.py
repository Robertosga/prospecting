import requests
import psycopg2
from datetime import datetime

# Configurações de conexão com o seu banco PostgreSQL
DB_CONFIG = {
    "dbname": "seu_banco",
    "user": "seu_usuario",
    "password": "sua_senha",
    "host": "172.17.0.1",
    "port": "5432"
}

def conectar_banco():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"Erro ao conectar no PostgreSQL: {e}")
        return None

def buscar_e_salvar_leads():
    conn = conectar_banco()
    if not conn:
        return
    
    cursor = conn.cursor()
    print("Iniciando busca real de novos MEIs em Anápolis/GO...")
    
    # Utilizando a API do CNPJ.biz para busca avançada por Município
    # Filtros: Anápolis (GO), Ativas, Natureza Jurídica de MEI (213-5)
    URL_API = "https://api.cnpj.biz/v1/busca-avancada"
    
    # Headers necessários (Algumas APIs exigem Token, ajuste se necessário)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json"
    }
    
    # Payload para trazer empresas abertas recentemente em Anápolis
    payload = {
        "municipio": "Anapolis",
        "uf": "GO",
        "situacao": "ATIVA",
        "natureza_juridica": "2135", # Código para Empresário Individual / MEI
        "ordenar_por": "data_abertura",
        "ordem": "desc",
        "limite": 50 # Traz os últimos 50 abertos
    }
    
    try:
        # Fazendo a chamada HTTP real
        response = requests.post(URL_API, json=payload, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"Erro na API externa: Status {response.status_code}")
            return
            
        dados_api = response.json()
        # Ajuste a chave conforme o retorno da API escolhida (geralmente 'results' ou 'empresas')
        novos_registros = dados_api.get("resultados", [])
        
    except Exception as e:
        print(f"Erro ao conectar na API de busca: {e}")
        return

    contador_inseridos = 0
    
    query_insercao = """
        INSERT INTO novos_meis_anapolis (cnpj, razao_social, data_abertura, bairro, atividade_principal)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (cnpj) DO NOTHING;
    """
    
    print(f"Processando {len(novos_registros)} registros encontrados...")
    
    for empresa in novos_registros:
        try:
            # Mapeamento dos campos baseado nas APIs de mercado
            cnpj_limpo = empresa.get("cnpj").replace(".", "").replace("/", "").replace("-", "")
            
            cursor.execute(query_insercao, (
                cnpj_limpo,
                empresa.get("razao_social"),
                empresa.get("data_abertura"), # Formato esperado: YYYY-MM-DD
                empresa.get("bairro"),
                empresa.get("cnae_principal_descricao") or empresa.get("atividade")
            ))
            
            if cursor.rowcount > 0:
                contador_inseridos += 1
                print(f"Novo lead salvo: {empresa.get('razao_social')} ({empresa.get('bairro')})")
                
        except Exception as err:
            print(f"Erro ao processar registro: {err}")
            conn.rollback()
            
    conn.commit()
    cursor.close()
    conn.close()
    
    print("\n--- Processo Concluído ---")
    print(f"Total de novos MEIs adicionados ao banco hoje: {contador_inseridos}")

if __name__ == "__main__":
    buscar_e_salvar_leads()