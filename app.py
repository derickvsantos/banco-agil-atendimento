import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from agents.agents import call_agents
from agents.models import EstadoAgil
from agents.mensagens import mensagens_encerramento
import uuid

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
        resultado = agents.invoke(EstadoAgil(), config=config)
        st.session_state.state = EstadoAgil.model_validate(resultado)

    for msg in st.session_state.state.messages:
        if isinstance(msg, HumanMessage):
            with st.chat_message("user"):
                st.write(msg.content)
        elif isinstance(msg, AIMessage):
            texto_ai = extrair_texto_limpo(msg)
            if texto_ai.strip():
                with st.chat_message("assistant"):
                    st.write(texto_ai)

    user_input = st.chat_input("Digite sua mensagem...")

    if user_input:
        if st.session_state.get('atendimento_encerrado', False):
            resetar_atendimento(agents)
            st.rerun()
        with st.chat_message("user"):
            st.write(user_input)
        st.session_state.state.messages.append(HumanMessage(content=user_input))
        with st.spinner("Processando..."):
            resultado = agents.invoke(
                {"messages": [HumanMessage(content=user_input)]}, 
                config=config
            )
            st.session_state.state = EstadoAgil.model_validate(resultado)
            ultima_mensagem = extrair_texto_limpo(st.session_state.state.messages[-1])
            if ultima_mensagem == mensagens_encerramento['msg_despedida']:
                st.session_state.atendimento_encerrado = True
                        
        st.rerun()

def extrair_texto_limpo(mensagem):
       """Extrai apenas a string de texto, lidando com retornos do Gemini."""
       conteudo = mensagem.content
       if isinstance(conteudo, list):
           partes_texto = [item.get("text", "") for item in conteudo if isinstance(item, dict) and "text" in item]
           texto = " ".join(partes_texto) if partes_texto else str(conteudo)
       else:
           texto = str(conteudo)

       texto = texto.replace("R$", r"R\$")
       return texto

def resetar_atendimento(agents):
    """Reseta o atendimento gerando uma nova thread_id."""
    st.session_state.thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    resultado_inicial = agents.invoke(EstadoAgil(), config=config)
    st.session_state.state = EstadoAgil.model_validate(resultado_inicial)
    st.session_state.atendimento_encerrado = False

if __name__ == "__main__":
    # 207.082.580-93
    # 20708258093
    # 954.528.240-14
    # 680.184.570-50
    main()