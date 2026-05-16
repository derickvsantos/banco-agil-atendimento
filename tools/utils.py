from langchain_tavily import TavilySearch
from tenacity import retry, stop_after_attempt, wait_fixed
from agents.models import DadosEntrevista
from langchain_core.tools import tool

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

@tool
@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def buscar_tavily(query: str) -> str:
    """
    Executa uma busca na web utilizando a API da Tavily para obter informações em tempo real (ex: cotação de moedas).

    Esta função possui um mecanismo interno de tolerância a falhas (retry). Caso a API 
    externa apresente instabilidade, ela tentará executar a requisição até 3 vezes, 
    com pausas de 1 segundo entre as tentativas, antes de falhar definitivamente.

    Args:
        query (str): A string de busca com o termo ou pergunta a ser pesquisada.

    Returns:
        str: Uma string contendo os resultados estruturados da busca (limitado aos 2 
             principais resultados), pronta para ser enviada como contexto ao LLM.

    Raises:
        RetryError: Caso todas as 3 tentativas de conexão com a API da Tavily falhem.
        ValidationError: Caso a chave de API (TAVILY_API_KEY) não esteja configurada no ambiente.
    """
    search = TavilySearch(max_results=2)
    resultados = search.invoke(query)
    return str(resultados)