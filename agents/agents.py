from agents.models import EstadoAgil
from tools.csv import validar_cliente, aumentar_limite, atualizar_score
from tools.utils import calcular_score, buscar_tavily
from tools.logger import save_log_to_json
from agents.mensagens import mensagens_triagem, mensagens_credito, mensagens_entrevistador, mensagens_cambio
from langgraph.types import Command
from typing import Literal
from langchain_core.messages import AIMessage, SystemMessage
from config.variables import (
    llm,
    llm_acao_credito,
    llm_dados_entrevista,
    llm_extrator_triagem,
    llm_rota,
    llm_verificador,
    llm_cambio
)
from langgraph.graph import StateGraph, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from agents.mensagens import system_prompt_encerramento

def verifica_encerrar(state):
    intencao = llm_verificador.invoke([SystemMessage(content=system_prompt_encerramento), state.messages[-1]])
            
    if intencao.encerrar:
        return Command(
            goto="__end__", 
            update={
                "messages": [AIMessage(content=mensagens_entrevistador['msg_despedida'])], 
                "entrevista_etapa": 0
            }
        )
    return None

def agent_triagem(state: EstadoAgil) -> Command[Literal["analista_credito", "agent_cambio", "entrevistador", "__end__"]]:
    """
    Agente de Triagem
    Responsável por coletar CPF e Data de Nascimento, validar em clientes.csv
    e redirecionar para o agente correto.
    """
    try:
        tentativas = state.tentativas
        if not state.messages:
            return Command(update={"messages": [AIMessage(content=mensagens_triagem['saudacao'])]})
        else:
            status = verifica_encerrar(state)
            if status: return status
        if state.autenticado:
            # Trava para manter na entrevista
            if 0 < state.entrevista_etapa <= 5:
                return Command(goto="entrevistador")
            decisao = llm_rota.invoke([SystemMessage(content=mensagens_triagem["system_prompt_rota"]), *state.messages[-5:]])
            return Command(
                goto=decisao.agente
            )
        
        cpf = state.cpf
        dt_nascimento = state.data_nascimento
        extracao = llm_extrator_triagem.invoke(state.messages)
        if extracao.cpf:
            cpf = extracao.cpf
        if extracao.data_nascimento:
            dt_nascimento = extracao.data_nascimento

        if cpf and dt_nascimento:
            dados_cliente = validar_cliente(cpf=cpf, data_nascimento=dt_nascimento)
            
            if dados_cliente:
                return Command(
                    update={
                        "messages": [AIMessage(content=mensagens_triagem["autenticado"].format(nome=dados_cliente['nome']))],
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
                        update={"messages": [AIMessage(content=mensagens_triagem["falha_autenticacao"])], "tentativas": tentativas}
                    )
                else:
                    return Command(
                        update={
                            "messages": [AIMessage(content=mensagens_triagem['tentativa_auth'].format(tentativas=tentativas))], 
                            "tentativas": tentativas,
                            "cpf": cpf,
                            "data_nascimento": dt_nascimento
                        }
                    )
        else:
            response = llm.invoke([SystemMessage(content=mensagens_triagem["system_prompt"])] + state.messages)
            return Command(
                update={
                    "messages": [response],
                    "cpf": cpf,
                    "data_nascimento": dt_nascimento
                }
            )
    except Exception as error:
        save_log_to_json(error, state)
        return Command(goto="__end__", update={"messages": [AIMessage(content=mensagens_triagem['exception'])]})
    
def analista_credito(state: EstadoAgil) -> Command[Literal["entrevistador", "__end__"]]:
    """
    Agente de Crédito
    Responsável por informar limite atual e processar pedidos de aumento.
    """
    try:
        action = llm_acao_credito.invoke([SystemMessage(content=mensagens_credito['system_prompt'].format(nome=state.nome, limite_atual=state.limite_atual, score=state.score))] + state.messages)
        if action.acao == "encerrar":
            return Command(goto="__end__", update={"messages": [AIMessage(content=action.mensagem_resposta)]})
            
        if action.acao == "redirecionar_entrevista":
            if state.score_atualizado:
                return Command(goto="__end__", update={"messages": [AIMessage(content=mensagens_credito['atualizado_rejeitado'])]})
            return Command(
                goto="entrevistador",
                update={
                    "entrevista_etapa": 0
                }
            )
        
        if action.acao == "oferecer_entrevista" and state.score_atualizado:
            return Command(goto="__end__", update={"messages": [AIMessage(content=mensagens_credito['atualizado_rejeitado'])]})

        if action.acao == "processar_aumento" and action.valor_solicitado:
            if aumentar_limite(
                cpf=state.cpf,
                limite_atual=state.limite_atual,
                score=state.score,
                valor_solicitado=action.valor_solicitado
            ):
                return Command(
                    update={
                        "messages": [AIMessage(content=mensagens_credito['aprovado'].format(valor_solicitado=action.valor_solicitado))],
                        "limite_atual": action.valor_solicitado
                    }
                )
            else:
                # Se já fez a entrevista de crédito e mesmo assim foi rejeitado
                if state.score_atualizado:
                    return Command(goto="__end__", update={"messages": [AIMessage(content=mensagens_credito['atualizado_rejeitado'])]})
                return Command(update={"messages": [AIMessage(content=mensagens_credito['rejeitado'].format(valor_solicitado=action.valor_solicitado))]})

        # Resposta padrão
        return Command(update={"messages": [AIMessage(content=action.mensagem_resposta)]})
    except Exception as error:
        save_log_to_json(error, state)
        return Command(goto="__end__", update={"messages": [AIMessage(content=mensagens_credito['exception'])]})

def entrevistador(state: EstadoAgil) -> Command[Literal["analista_credito"]]:
    """
    Agente de Entrevista
    Faz 5 perguntas estruturadas para recalcular o score.
    """
    try:
        if state.messages:
            status = verifica_encerrar(state)
            if status: return status
        
        if state.entrevista_etapa < 5:
            return Command(goto="__end__", update={"messages": [AIMessage(content=mensagens_entrevistador['perguntas'][state.entrevista_etapa])], "entrevista_etapa": state.entrevista_etapa + 1})
            
        dados = llm_dados_entrevista.invoke([SystemMessage(content="Extraia as respostas financeiras do usuário no histórico para recalcular o score.")] + state.messages)
        novo_score = calcular_score(dados)

        atualizar_score(cpf=state.cpf, novo_score=novo_score)
        return Command(
            goto="analista_credito",
            update={
                "messages": [AIMessage(content=mensagens_entrevistador['msg_fim'].format(novo_score=novo_score))],
                "score": novo_score,
                "entrevista_etapa": 0,
                "score_atualizado": True
            }
        )
    except Exception as error:
        save_log_to_json(error, state)
        return Command(goto="__end__", update={"messages": [AIMessage(content=mensagens_entrevistador['exception'])], "entrevista_etapa": 0})

def agent_cambio(state: EstadoAgil):
    """
    Agente de Câmbio
    Deixa o LangGraph (via tools_condition) gerenciar o roteamento para o ToolNode.
    """
    try:
        response = llm_cambio.invoke(
            [SystemMessage(content=mensagens_cambio['system_prompt'])] + state.messages
        )
        return {"messages": [response]}
    except Exception as error:
        save_log_to_json(error, state)
        return Command(goto="__end__", update={"messages": [AIMessage(content=mensagens_cambio['exception'])]})

def call_agents():
    workflow = StateGraph(EstadoAgil)

    # Nodes
    workflow.add_node("agent_triagem", agent_triagem)
    workflow.add_node("analista_credito", analista_credito)
    workflow.add_node("entrevistador", entrevistador)
    workflow.add_node("agent_cambio", agent_cambio)
    workflow.add_node("tools_cambio", ToolNode([buscar_tavily]))

    # Start
    workflow.add_edge(START, "agent_triagem")
    
    # Conditional tools
    workflow.add_conditional_edges(
        "agent_cambio",
        tools_condition,
        {
            "tools": "tools_cambio", 
            "__end__": "__end__"
        }
    )
    workflow.add_edge("tools_cambio", "agent_cambio")
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)