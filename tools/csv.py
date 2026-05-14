import pandas as pd
from datetime import datetime
import os
from typing import Union, Dict, Any

def validar_cliente(cpf: str, data_nascimento: str) -> Union[Dict[str, Any], bool]:
    """
    Retorna um dicionário com os dados do cliente se validado, ou False caso não encontre.
    """
    try:
        df = pd.read_csv("./resources/clientes.csv", dtype={"cpf": str}, sep=";")
        df['cpf'] = df['cpf'].astype(str).str.replace(r'\D', '', regex=True)
        clean_cpf = ''.join(filter(str.isdigit, str(cpf)))
        match = df[(df['cpf'] == clean_cpf) & (df['data_nascimento'] == data_nascimento)]
        
        if not match.empty:
            cliente = match.iloc[0]
            if pd.isna(cliente.get("nome")) or pd.isna(cliente.get("score")) or pd.isna(cliente.get("limite_atual")):
                raise Exception("Falha ao resgatar dados do cliente")
                
            return {
                "nome": str(cliente['nome']),
                "score": int(cliente["score"]),
                "limite_atual": float(cliente["limite_atual"])
            }
        else:
            return False
            
    except Exception as e:
        raise Exception(f"Erro em validar_cliente: {e}")
    
def registrar_solicitacao(cpf: str, limite_atual: float, valor_solicitado: float, status: str) -> None:
    """
    Registra a solicitação no CSV. Não possui retorno (None).
    """
    try:
        novo_registro = pd.DataFrame([{
                'cpf_cliente': cpf,
                'data_hora_solicitacao': datetime.now().isoformat(),
                'limite_atual': limite_atual,
                'novo_limite_solicitado': valor_solicitado,
                'status_pedido': status
            }])
        novo_registro.to_csv("./resources/solicitacoes_aumento_limite.csv", mode='a', header=not os.path.exists("./resources/solicitacoes_aumento_limite.csv"), index=False, sep=";")
    except Exception as e:
        raise Exception(f"Erro em registrar_solicitacao: {e}")
    
def aumentar_limite(cpf: str, limite_atual: float, score: int, valor_solicitado: float) -> bool:
    """
    Tenta aumentar o limite e retorna True se aprovado, ou False se rejeitado.
    """
    try:
        df_regras = pd.read_csv("./resources/score_limite.csv", sep=";")
        limite_maximo_permitido = 0
        for _, row in df_regras.iterrows():
            if row['score_min'] <= score <= row['score_max']:
                limite_maximo_permitido = row['limite_permitido']
                break
        
        status = 'aprovado' if valor_solicitado <= limite_maximo_permitido else 'rejeitado'
        registrar_solicitacao(cpf, limite_atual, valor_solicitado, status)
        if status == 'aprovado':
            df_clientes = pd.read_csv("./resources/clientes.csv", dtype={"cpf": str}, sep=";")
            df_clientes.loc[df_clientes['cpf'] == cpf, 'limite_atual'] = valor_solicitado
            df_clientes.to_csv("./resources/clientes.csv", index=False, sep=";")
            return True
        else:
            return False
    except Exception as e:
        raise Exception(f"Erro em aumentar_limite: {e}")
    
def atualizar_score(cpf: str, novo_score: int) -> None:
    """
    Atualiza o score do cliente no CSV. Não possui retorno (None).
    """
    try:
        df_clientes = pd.read_csv("./resources/clientes.csv", dtype={"cpf": str}, sep=";")
        df_clientes.loc[df_clientes['cpf'] == cpf, 'score'] = novo_score
        df_clientes.to_csv("./resources/clientes.csv", index=False, sep=";")
    except Exception as e:
        raise Exception(f"Erro em atualizar_score: {e}")