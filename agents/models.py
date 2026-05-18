from typing import Annotated, Literal, List
from pydantic import BaseModel, Field, field_validator
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class EstadoAgil(BaseModel):
    messages: Annotated[List[BaseMessage], add_messages] = Field(default_factory=list)
    cpf: str | None = None
    data_nascimento: str | None = None
    nome: str | None = None
    autenticado: bool = False
    tentativas: int = 0
    score: int = 0
    limite_atual: float = 0.0
    entrevista_etapa: int = 0
    score_atualizado: bool = False

    @field_validator("limite_atual", mode="before")
    @classmethod
    def formatar_limite(cls, v):
        if v is None:
            return 0.0
        if isinstance(v, str):
            v = v.replace("R$", "").replace(".", "").replace(",", ".").strip()
            try:
                return float(v)
            except ValueError:
                return 0.0
        return float(v)

class DecisaoRota(BaseModel):
    agente: Literal["analista_credito", "agent_cambio", "__end__"] = Field(
        description="Escolha 'analista_credito' para crédito, 'agent_cambio' para câmbio, ou '__end__' se o usuário quiser encerrar"
    )

class ExtracaoCPF_DT_Nascimento(BaseModel):
    cpf: str = Field(description="CPF informado pelo usuário. Apenas números.")
    data_nascimento: str = Field(description="Data de nascimento informada. Formato DD/MM/AAAA.")

class AcaoCredito(BaseModel):
    acao: Literal["informar_limite", "solicitar_novo_valor", "processar_aumento", "oferecer_entrevista", "redirecionar_entrevista", "encerrar"] = Field(
        description="O que o agente deve fazer baseado na conversa."
    )
    valor_solicitado: float = Field(
        description="O valor numérico desejado pelo cliente para o novo limite. Se ele não informou um valor, retorne 0.0."
    )
    mensagem_resposta: str = Field(
        description="A resposta clara e direta que será exibida para o cliente. Não inclua saudações."
    )
    
class DadosEntrevista(BaseModel):
    renda_mensal: float
    tipo_emprego: Literal["formal", "autônomo", "desempregado"]
    despesas_mensais: float
    num_dependentes: Literal["0", "1", "2", "3+"]
    tem_dividas: Literal["sim", "não"]

class VerificadorEncerramento(BaseModel):
    encerrar: bool = Field(
        default=False,
        description="Retorne true APENAS se o usuário pedir explicitamente para parar, cancelar, sair ou encerrar. Se ele informar dados ou fizer uma pergunta, retorne false."
    )