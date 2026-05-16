import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from agents.models import DecisaoRota, ExtracaoCPF_DT_Nascimento, AcaoCredito, DadosEntrevista, VerificadorEncerramento
from tools.utils import buscar_tavily
load_dotenv()

if not os.getenv("TAVILY_API_KEY"):
    raise NotImplementedError("Não foi possível encontrar a API Key da Tavily nas variáveis de ambiente")

if not os.getenv("GOOGLE_API_KEY"):
    raise NotImplementedError("Não foi possível encontrar a API Key do Gemini nas variáveis de ambiente")

# LLMs
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
llm_rota = llm.with_structured_output(DecisaoRota)
llm_extrator_triagem = llm.with_structured_output(ExtracaoCPF_DT_Nascimento)
llm_acao_credito = llm.with_structured_output(AcaoCredito)
llm_verificador = llm.with_structured_output(VerificadorEncerramento)
llm_dados_entrevista = llm.with_structured_output(DadosEntrevista)
llm_cambio = llm.bind_tools([buscar_tavily])