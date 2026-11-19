"""``AgendamentoController`` (GRASP Controller): recebe o pedido HTTP e delega.

Não tem regra de negócio. Faz quatro coisas: identifica quem pede, converte o
JSON em comando, chama o caso de uso e devolve a resposta. Os erros do núcleo
são traduzidos para HTTP em ``api/erros.py``.

As rotas são funções comuns (``def``), que o FastAPI executa em um pool de
threads. A ``UnidadeDeTrabalho`` guarda a conexão por thread, então cada
requisição tem a sua transação.
"""
from datetime import date

from fastapi import APIRouter, Header

from clinica.api.erros import (
    RESPOSTA_400,
    RESPOSTA_401,
    RESPOSTA_403,
    RESPOSTA_404,
    RESPOSTA_409,
    RESPOSTA_500,
)
from clinica.api.esquemas import (
    AgendarConsultaPedido,
    ConsultaResposta,
    DisponibilidadeResposta,
)
from clinica.compartilhado.erros import NaoAutenticadoError
from clinica.modulos.autenticacao.portas.servico_autenticacao import ServicoAutenticacao, Usuario
from clinica.modulos.consultas.aplicacao.agendar_consulta import (
    AgendarConsulta,
    AgendarConsultaComando,
)
from clinica.modulos.consultas.aplicacao.consultar_disponibilidade import ConsultarDisponibilidade


class AgendamentoController:
    def __init__(
        self,
        agendar_consulta: AgendarConsulta,
        consultar_disponibilidade: ConsultarDisponibilidade,
        autenticacao: ServicoAutenticacao,
    ) -> None:
        self._agendar_consulta = agendar_consulta
        self._consultar_disponibilidade = consultar_disponibilidade
        self._autenticacao = autenticacao

    def _identificar(self, authorization: str | None) -> Usuario:
        """Lê ``Authorization: Bearer <token>`` e pergunta ao serviço de autenticação."""
        esquema, _, token = (authorization or "").partition(" ")
        if esquema.lower() != "bearer" or not token.strip():
            raise NaoAutenticadoError("Informe o cabeçalho 'Authorization: Bearer <token>'.")
        return self._autenticacao.identificar(token.strip())

    def consultar_disponibilidade(
        self,
        dia: date,
        profissional_id: int | None = None,
        especialidade: str | None = None,
        authorization: str | None = Header(default=None),
    ):
        self._identificar(authorization)
        resultado = self._consultar_disponibilidade.executar(dia, profissional_id, especialidade)
        return [DisponibilidadeResposta.de(item) for item in resultado]

    def agendar_consulta(
        self,
        pedido: AgendarConsultaPedido,
        authorization: str | None = Header(default=None),
    ):
        usuario = self._identificar(authorization)
        consulta = self._agendar_consulta.executar(
            AgendarConsultaComando(usuario, pedido.profissional_id, pedido.inicio)
        )
        return ConsultaResposta.de(consulta)

    def criar_rotas(self) -> APIRouter:
        rotas = APIRouter()
        rotas.add_api_route(
            "/disponibilidade",
            self.consultar_disponibilidade,
            methods=["GET"],
            response_model=list[DisponibilidadeResposta],
            responses={400: RESPOSTA_400, 401: RESPOSTA_401, 404: RESPOSTA_404, 500: RESPOSTA_500},
            summary="Consultar horários disponíveis (RF02)",
            description="Informe `profissional_id` **ou** `especialidade`, mais a data.",
        )
        rotas.add_api_route(
            "/consultas",
            self.agendar_consulta,
            methods=["POST"],
            status_code=201,
            response_model=ConsultaResposta,
            responses={
                400: RESPOSTA_400,
                401: RESPOSTA_401,
                403: RESPOSTA_403,
                404: RESPOSTA_404,
                409: RESPOSTA_409,
                500: RESPOSTA_500,
            },
            summary="Agendar consulta (RF03)",
            description="Somente pacientes agendam. A consulta nasce `AGENDADA`.",
        )
        return rotas
