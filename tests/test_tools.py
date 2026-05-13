import pytest
from unittest.mock import patch
import pandas as pd

from tools.csv import validar_cliente, registrar_solicitacao, aumentar_limite, atualizar_score
from tools.utils import calcular_score, buscar_tavily
from agents.models import DadosEntrevista

@pytest.fixture
def mock_clientes_csv():
    return pd.DataFrame([
        {
            "cpf": "12345678900",
            "data_nascimento": "01/01/1990",
            "nome": "João Silva",
            "score": 500,
            "limite_atual": 1000.0
        },
        {
            "cpf": "09876543211",
            "data_nascimento": "02/02/1980",
            "nome": "Maria Souza",
            "score": 800,
            "limite_atual": 5000.0
        }
    ])

@pytest.fixture
def mock_score_limite_csv():
    return pd.DataFrame([
        {"score_min": 0, "score_max": 300, "limite_permitido": 0.0},
        {"score_min": 301, "score_max": 600, "limite_permitido": 1500.0},
        {"score_min": 601, "score_max": 1000, "limite_permitido": 10000.0}
    ])

@patch("pandas.read_csv")
def test_validar_cliente_sucesso(mock_read_csv, mock_clientes_csv):
    mock_read_csv.return_value = mock_clientes_csv
    
    resultado = validar_cliente("123.456.789-00", "01/01/1990")
    
    assert resultado != False
    assert resultado["nome"] == "João Silva"
    assert resultado["score"] == 500
    assert resultado["limite_atual"] == 1000.0
    mock_read_csv.assert_called_once_with("./resources/clientes.csv", dtype={"cpf": str}, sep=";")

@patch("pandas.read_csv")
def test_validar_cliente_nao_encontrado(mock_read_csv, mock_clientes_csv):
    mock_read_csv.return_value = mock_clientes_csv
    
    resultado = validar_cliente("11122233344", "01/01/1990")
    assert resultado == False

@patch("pandas.read_csv")
def test_validar_cliente_dados_faltantes(mock_read_csv):
    mock_df = pd.DataFrame([
        {
            "cpf": "12345678900",
            "data_nascimento": "01/01/1990",
            "nome": None,
            "score": 500,
            "limite_atual": 1000.0
        }
    ])
    mock_read_csv.return_value = mock_df
    
    with pytest.raises(Exception, match="Falha ao resgatar dados do cliente"):
        validar_cliente("12345678900", "01/01/1990")

@patch("pandas.read_csv")
def test_validar_cliente_erro_geral(mock_read_csv):
    mock_read_csv.side_effect = Exception("Erro de leitura")
    
    with pytest.raises(Exception, match="Erro em validar_cliente: Erro de leitura"):
        validar_cliente("12345678900", "01/01/1990")

@patch("pandas.DataFrame.to_csv")
@patch("os.path.exists")
def test_registrar_solicitacao_sucesso(mock_exists, mock_to_csv):
    mock_exists.return_value = True
    registrar_solicitacao("12345678900", 1000.0, 2000.0, "aprovado")
    mock_to_csv.assert_called_once()
    args, kwargs = mock_to_csv.call_args
    assert kwargs["mode"] == "a"
    assert kwargs["header"] == False
    assert kwargs["index"] == False
    assert kwargs["sep"] == ";"

@patch("pandas.DataFrame.to_csv")
@patch("os.path.exists")
def test_registrar_solicitacao_novo_arquivo(mock_exists, mock_to_csv):
    mock_exists.return_value = False
    registrar_solicitacao("12345678900", 1000.0, 2000.0, "aprovado")
    mock_to_csv.assert_called_once()
    _, kwargs = mock_to_csv.call_args
    assert kwargs["header"] == True

@patch("pandas.DataFrame.to_csv")
def test_registrar_solicitacao_erro(mock_to_csv):
    mock_to_csv.side_effect = Exception("Erro de gravação")
    with pytest.raises(Exception, match="Erro em registrar_solicitacao: Erro de gravação"):
        registrar_solicitacao("12345678900", 1000.0, 2000.0, "aprovado")

@patch("pandas.DataFrame.to_csv")
@patch("pandas.read_csv")
@patch("tools.csv.registrar_solicitacao")
def test_aumentar_limite_aprovado(mock_registrar, mock_read_csv, mock_to_csv, mock_score_limite_csv, mock_clientes_csv):
    def read_csv_side_effect(path, **kwargs):
        if "score_limite" in path:
            return mock_score_limite_csv
        if "clientes" in path:
            return mock_clientes_csv
        return pd.DataFrame()
    
    mock_read_csv.side_effect = read_csv_side_effect
    
    resultado = aumentar_limite("12345678900", 1000.0, 500, 1500.0)
    
    assert resultado == True
    mock_registrar.assert_called_once_with("12345678900", 1000.0, 1500.0, "aprovado")
    mock_to_csv.assert_called_once()

@patch("pandas.DataFrame.to_csv")
@patch("pandas.read_csv")
@patch("tools.csv.registrar_solicitacao")
def test_aumentar_limite_rejeitado(mock_registrar, mock_read_csv, mock_to_csv, mock_score_limite_csv):
    mock_read_csv.return_value = mock_score_limite_csv
    resultado = aumentar_limite("12345678900", 1000.0, 500, 2000.0)
    
    assert resultado == False
    mock_registrar.assert_called_once_with("12345678900", 1000.0, 2000.0, "rejeitado")
    mock_to_csv.assert_not_called()

@patch("pandas.read_csv")
def test_aumentar_limite_erro(mock_read_csv):
    mock_read_csv.side_effect = Exception("Falha lendo arquivo")
    with pytest.raises(Exception, match="Erro em aumentar_limite: Falha lendo arquivo"):
        aumentar_limite("12345678900", 1000.0, 500, 2000.0)

@patch("pandas.DataFrame.to_csv")
@patch("pandas.read_csv")
def test_atualizar_score_sucesso(mock_read_csv, mock_to_csv, mock_clientes_csv):
    mock_read_csv.return_value = mock_clientes_csv
    atualizar_score("12345678900", 600)
    mock_read_csv.assert_called_once_with("./resources/clientes.csv", dtype={"cpf": str}, sep=";")
    mock_to_csv.assert_called_once_with("./resources/clientes.csv", index=False, sep=";")

@patch("pandas.read_csv")
def test_atualizar_score_erro(mock_read_csv):
    mock_read_csv.side_effect = Exception("Erro ao atualizar")
    with pytest.raises(Exception, match="Erro em atualizar_score: Erro ao atualizar"):
        atualizar_score("12345678900", 600)

def test_calcular_score_sucesso():
    dados = DadosEntrevista(
        renda_mensal=5000.0,
        tipo_emprego="formal",
        despesas_mensais=2000.0,
        num_dependentes="0",
        tem_dividas="não"
    )
    score = calcular_score(dados)
    assert 0 <= score <= 1000
    assert score == int((5000 / 2001) * 30 + 300 + 100 + 100)

def test_calcular_score_maximo():
    dados = DadosEntrevista(
        renda_mensal=100000.0,
        tipo_emprego="formal",
        despesas_mensais=0.0,
        num_dependentes="0",
        tem_dividas="não"
    )
    score = calcular_score(dados)
    assert score == 1000

def test_calcular_score_minimo():
    dados = DadosEntrevista(
        renda_mensal=0.0,
        tipo_emprego="desempregado",
        despesas_mensais=5000.0,
        num_dependentes="3+",
        tem_dividas="sim"
    )
    score = calcular_score(dados)
    assert score == 0

def test_calcular_score_erro():
    with pytest.raises(Exception, match="Erro em calcular_score:"):
        calcular_score(None)

@patch("tools.utils.TavilySearch")
def test_buscar_tavily_sucesso(mock_tavily_class):
    mock_instancia = mock_tavily_class.return_value
    mock_instancia.invoke.return_value = [{"url": "http://exemplo.com", "content": "resultado teste"}]
    
    resultado = buscar_tavily("teste")
    
    assert "resultado teste" in resultado
    mock_instancia.invoke.assert_called_once_with("teste")

@patch("tools.utils.TavilySearch")
def test_buscar_tavily_erro(mock_tavily_class):
    mock_instancia = mock_tavily_class.return_value
    mock_instancia.invoke.side_effect = Exception("Erro na API")
    
    with pytest.raises(Exception, match="RetryError"):
        buscar_tavily("teste")
        
    # Como o tenacity tenta 3 vezes, verificamos se o invoke foi chamado 3 vezes
    assert mock_instancia.invoke.call_count == 3
