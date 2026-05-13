from typing import Annotated, Literal, TypedDict, List
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class EstadoAgil(TypedDict):
    mensagens: Annotated[List[BaseMessage], add_messages]
    cpf: str
    data_nascimento: str
    nome: str
    autenticado: bool
    tentativas: int
    score: int
    limite_atual: float
    entrevista_etapa: int
    score_atualizado: bool

class DecisaoRota(BaseModel):
    agente: Literal["analista_credito", "agent_cambio"] = Field(
        description="Escolha 'analista_credito' para crédito, 'agent_cambio' para câmbio, ou '__end__' se o usuário quiser encerrar"
    )

class ExtracaoCPF_DT_Nascimento(BaseModel):
    cpf: str | None = Field(description="CPF informado pelo usuário. Apenas números.")
    data_nascimento: str | None = Field(description="Data de nascimento informada. Formato DD/MM/AAAA.")

class AcaoCredito(BaseModel):
    acao: Literal["informar_limite", "solicitar_novo_valor", "processar_aumento", "oferecer_entrevista", "redirecionar_entrevista", "encerrar", "responder_geral"] = Field(description="O que o agente deve fazer baseado na conversa.")
    valor_solicitado: float | None = Field(description="Se o cliente informou o valor que deseja, coloque aqui.")
    mensagem_resposta: str = Field(description="A resposta que será exibida para o cliente. Não há necessidade de saudar novamente. Caso seja um redirecionamento apenas redirecione.")

class DadosEntrevista(BaseModel):
    renda_mensal: float
    tipo_emprego: Literal["formal", "autônomo", "desempregado"]
    despesas_mensais: float
    num_dependentes: Literal["0", "1", "2", "3+"]
    tem_dividas: Literal["sim", "não"]

class VerificadorEncerramento(BaseModel):
    encerrar: bool = Field(description="Retorne True APENAS se o usuário pedir para parar, cancelar, sair ou encerrar a conversa. False caso contrário.")