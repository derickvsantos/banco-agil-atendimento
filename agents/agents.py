from agents.models import EstadoAgil, DecisaoRota, ExtracaoCPF_DT_Nascimento, AcaoCredito, DadosEntrevista, VerificadorEncerramento
from tools.csv import validar_cliente, aumentar_limite, atualizar_score
from tools.utils import calcular_score, buscar_tavily
from tools.logger import save_log_to_json
from agents.mensagens import mensagens_triagem, mensagens_credito, mensagens_entrevistador, mensagens_cambio
from langgraph.types import Command
from typing import Literal
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from config.variables import llm
from langgraph.graph import StateGraph, START
from langgraph.checkpoint.memory import MemorySaver

def agent_triagem(state: EstadoAgil) -> Command[Literal["analista_credito", "agent_cambio", "entrevistador", "__end__"]]:
    """
    Agente de Triagem
    Responsável por coletar CPF e Data de Nascimento, validar em clientes.csv
    e redirecionar para o agente correto.
    """
    try:
        mensagens = state.get("mensagens", [])
        tentativas = state.get("tentativas", 0)
        auth = state.get("autenticado", False)
        etapa_entrevista = state.get("entrevista_etapa", 0)
        if not mensagens:
            return Command(update={"mensagens": [AIMessage(content=mensagens_triagem['saudacao'])]})
        if auth:
            # Trava para manter na entrevista
            if 0 < etapa_entrevista <= 5:
                return Command(goto="entrevistador")
            rota = llm.with_structured_output(DecisaoRota)
            decisao = rota.invoke(mensagens)
            return Command(
                goto=decisao.agente
            )
        
        cpf = state.get("cpf", "")
        dt_nascimento = state.get("data_nascimento", "")
        if not cpf or not dt_nascimento:
            extractor_llm = llm.with_structured_output(ExtracaoCPF_DT_Nascimento)
            extracao = extractor_llm.invoke(mensagens[-2:])
            if not extracao.cpf and not extracao.data_nascimento:
                response = llm.invoke([SystemMessage(mensagens_triagem["system_prompt"])] + mensagens)
                return Command(
                    update={
                        "mensagens": [response],
                        "cpf": cpf,
                        "data_nascimento": dt_nascimento
                    }
                )
            else:
                cpf = extracao.cpf
                dt_nascimento = extracao.data_nascimento
        
        dados_cliente = validar_cliente(cpf=cpf, data_nascimento=dt_nascimento)
        if dados_cliente:
            return Command(
                update={
                    "mensagens": [AIMessage(mensagens_triagem["autenticado"].format(nome=dados_cliente['nome']))],
                    "autenticado": True,
                    "cpf": cpf,
                    "data_nascimento": dt_nascimento,
                    "nome": dados_cliente.get("nome"),
                    "score": dados_cliente.get("score"),
                    "limite_atual": dados_cliente.get("limite_atual")
                }
            )
        else:
            tentativas += 1
            if tentativas >= 3:
                return Command(
                    goto="__end__",
                    update={"mensagens": [AIMessage(mensagens_triagem["falha_autenticacao"])], "tentativas": tentativas}
                )
            else:
                return Command(
                    update={
                        "mensagens": [AIMessage(content=mensagens_triagem['tentativa_auth'].format(tentativas=tentativas))], 
                        "tentativas": tentativas,
                        "cpf": None,
                        "data_nascimento": None
                    }
                )
    except Exception as error:
        save_log_to_json(error, state)
        return Command(goto="__end__", update={"mensagens": [AIMessage(content=mensagens_triagem['exception'])]})
    
def analista_credito(state: EstadoAgil) -> Command[Literal["entrevistador", "__end__"]]:
    """
    Agente de Crédito
    Responsável por informar limite atual e processar pedidos de aumento.
    """
    try:
        mensagens = state.get("mensagens", [])
        action_llm = llm.with_structured_output(AcaoCredito)
        ja_atualizou = state.get("score_atualizado")
        action = action_llm.invoke([SystemMessage(content=mensagens_credito['system_prompt'].format(nome=state.get("nome"), limite_atual=float(state.get("limite_atual")), score=state.get("score")))] + mensagens)

        if action.acao == "encerrar":
            return Command(goto="__end__", update={"mensagens": [AIMessage(content=action.mensagem_resposta)]})
            
        if action.acao == "redirecionar_entrevista":
            return Command(
                goto="entrevistador",
                update={
                    "entrevista_etapa": 0
                }
            )

        if action.acao == "processar_aumento" and action.valor_solicitado:
            if aumentar_limite(
                cpf=state.get("cpf"),
                limite_atual=state.get("limite_atual"),
                score=state.get("score"),
                valor_solicitado=action.valor_solicitado
            ):
                return Command(
                    update={
                        "mensagens": [AIMessage(content=mensagens_credito['aprovado'].format(valor_solicitado=action.valor_solicitado))],
                        "limite_atual": action.valor_solicitado
                    }
                )
            else:
                # Se já fez a entrevista de crédito e mesmo assim foi rejeitado
                if ja_atualizou:
                    return Command(goto="__end__", update={"mensagens": [AIMessage(content=mensagens_credito['atualizado_rejeitado'])]})
                return Command(update={"mensagens": [AIMessage(content=mensagens_credito['rejeitado'].format(valor_solicitado=action.valor_solicitado))]})

        # Resposta padrão
        return Command(update={"mensagens": [AIMessage(content=action.mensagem_resposta)]})
    except Exception as error:
        save_log_to_json(error, state)
        return Command(goto="__end__", update={"mensagens": [AIMessage(content=mensagens_credito['exception'])]})

def entrevistador(state: EstadoAgil) -> Command[Literal["analista_credito"]]:
    """
    Agente de Entrevista
    Faz 5 perguntas estruturadas para recalcular o score.
    """
    try:
        mensagens = state.get("mensagens", [])
        etapa = state.get("entrevista_etapa", 0)

        if mensagens:
            verificador = llm.with_structured_output(VerificadorEncerramento)
            intencao = verificador.invoke([mensagens[-1]])
            
            if intencao.encerrar:
                return Command(
                    goto="__end__", 
                    update={
                        "mensagens": [AIMessage(content=mensagens_entrevistador['msg_despedida'])], 
                        "entrevista_etapa": 0
                    }
                )
        
        if etapa < 5:
            return Command(goto="__end__", update={"mensagens": [AIMessage(content=mensagens_entrevistador['perguntas'][etapa])], "entrevista_etapa": etapa + 1})
            
        extrator_entrevista = llm.with_structured_output(DadosEntrevista)
        dados = extrator_entrevista.invoke([SystemMessage(content="Extraia as respostas financeiras do usuário no histórico para recalcular o score.")] + mensagens)
        novo_score = calcular_score(dados)

        atualizar_score(cpf=state.get("cpf"), novo_score=novo_score)
        return Command(
            goto="analista_credito",
            update={
                "mensagens": [AIMessage(content=mensagens_entrevistador['msg_fim'].format(novo_score=novo_score))],
                "score": novo_score,
                "entrevista_etapa": 0,
                "score_atualizado": True
            }
        )
    except Exception as error:
        return Command(goto="__end__", update={"mensagens": [AIMessage(content=mensagens_entrevistador['exception'])], "entrevista_etapa": 0})

def agent_cambio(state: EstadoAgil) -> Command[Literal["__end__"]]:
    """
    Agente de Câmbio
    Busca cotação de moedas em tempo real usando Tavily.
    Após responder, encerra o atendimento.
    """
    try:
        mensagens = state.get("mensagens", [])
        ultima_msg = mensagens[-1].content
        query = f"Cotação atual do {ultima_msg}"
        search_result = buscar_tavily(query)
        response = llm.invoke([
            SystemMessage(content=mensagens_cambio['system_prompt'].format(search_result=search_result)),
            HumanMessage(content=f"Extraia e informe o valor atual para: {ultima_msg}")
        ])
        return Command(goto="__end__", update={"mensagens": [response]})
    except Exception as error:
        save_log_to_json(error, state)
        return Command(goto="__end__", update={"mensagens": [AIMessage(content=mensagens_cambio['exception'])]})

def call_agents():
    workflow = StateGraph(EstadoAgil)
    workflow.add_node("agent_triagem", agent_triagem)
    workflow.add_node("analista_credito", analista_credito)
    workflow.add_node("entrevistador", entrevistador)
    workflow.add_node("agent_cambio", agent_cambio)

    #Start
    workflow.add_edge(START, "agent_triagem")
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)