from langchain_tavily import TavilySearch
from tenacity import retry, stop_after_attempt, wait_fixed
from agents.models import DadosEntrevista

def calcular_score(dados: DadosEntrevista) -> int:
    """
    Calcula o score de crédito com base nas respostas financeiras do usuário.
    Garante que o score fique no intervalo de 0 a 1000.
    """
    try:
        peso_renda = 30
        peso_emprego = {"formal": 300, "autônomo": 200, "desempregado": 0}
        peso_dependentes = {"0": 100, "1": 80, "2": 60, "3+": 30}
        peso_dividas = {"sim": -100, "não": 100}
        
        score_bruto = (
            (dados.renda_mensal / (dados.despesas_mensais + 1)) * peso_renda +
            peso_emprego[dados.tipo_emprego] +
            peso_dependentes[str(dados.num_dependentes)] +
            peso_dividas[dados.tem_dividas]
        )
        novo_score = int(max(0, min(1000, score_bruto)))
        return novo_score
    except Exception as e:
        raise Exception(f"Erro em calcular_score: {e}")

@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def buscar_tavily(query: str) -> str:
    """
    Busca informações na web usando a API da Tavily.
    """
    search = TavilySearch(max_results=2)
    resultados = search.invoke(query)
    return str(resultados)