import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
load_dotenv()

if not os.getenv("TAVILY_API_KEY"):
    raise NotImplementedError("Não foi possível encontrar a API Key da Tavily nas variáveis de ambiente")

if not os.getenv("GOOGLE_API_KEY"):
    raise NotImplementedError("Não foi possível encontrar a API Key do Gemini nas variáveis de ambiente")

model = os.getenv("MODEL", "gemini-2.5-flash")
llm = ChatGoogleGenerativeAI(model=model, temperature=0)
