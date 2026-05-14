import streamlit as st
import uuid
from langchain_core.messages import HumanMessage, AIMessage
from agents.agents import call_agents
from agents.models import EstadoAgil

@st.cache_resource
def get_workflow():
    return call_agents()

def main():
    st.set_page_config(page_title="Banco Ágil - Atendimento", page_icon="🤖")
    st.title("🤖 Banco Ágil - Atendimento")
    
    agents = get_workflow()

    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
        
    config = {"configurable": {"thread_id": st.session_state.thread_id}}

    if "state" not in st.session_state:
        st.session_state.state = EstadoAgil(
            mensagens=[],
            cpf=None,
            data_nascimento=None,
            nome=None,
            autenticado=False,
            tentativas=0,
            score=0,
            limite_atual=0.0,
            entrevista_etapa=0,
            score_atualizado=False
        )
        
        resultado = agents.invoke(st.session_state.state, config=config)

        for k, v in resultado.items():
            st.session_state.state[k] = v

    for msg in st.session_state.state.get("mensagens", []):
        if isinstance(msg, HumanMessage):
            with st.chat_message("user"):
                st.write(msg.content)
        elif isinstance(msg, AIMessage):
            with st.chat_message("assistant"):
                st.write(msg.content)

    user_input = st.chat_input("Digite sua mensagem...")

    if user_input:
        with st.chat_message("user"):
            st.write(user_input)
            
        nova_mensagem = HumanMessage(content=user_input)
        st.session_state.state["mensagens"].append(nova_mensagem)
        with st.spinner("Processando..."):
            novo_estado = agents.invoke(st.session_state.state, config=config)
            st.session_state.state = novo_estado
            lista_mensagens = st.session_state.state.get("mensagens", [])
            if lista_mensagens:
                ultima_msg = lista_mensagens[-1]
                if isinstance(ultima_msg, AIMessage):
                    with st.chat_message("assistant"):
                        st.write(ultima_msg.content)
                    
        st.rerun()

if __name__ == "__main__":
    # 207.082.580-93
    # 20708258093
    # 954.528.240-14
    # 680.184.570-50
    main()