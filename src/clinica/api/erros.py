"""Tradução dos erros da aplicação para respostas HTTP."""
from collections.abc import Mapping

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from clinica.api.esquemas import ErroResposta
from clinica.compartilhado.erros import (
    ConflitoDoPacienteError,
    EntidadeNaoEncontradaError,
    ErroDeDominio,
    HorarioIndisponivelError,
    LimiteDoPacienteExcedidoError,
    NaoAutenticadoError,
    NaoAutorizadoError,
    SlotInvalidoError,
)

STATUS_POR_ERRO: dict[type[Exception], int] = {
    NaoAutenticadoError: 401,
    NaoAutorizadoError: 403,
    EntidadeNaoEncontradaError: 404,
    SlotInvalidoError: 400,
    HorarioIndisponivelError: 409,
    ConflitoDoPacienteError: 409,
    LimiteDoPacienteExcedidoError: 409,
    # Qualquer outra regra de negócio violada é um pedido inválido.
    ErroDeDominio: 400,
}


# Descrição dos erros de cada rota, para a documentação (OpenAPI).
RESPOSTA_400 = {"model": ErroResposta, "description": "Entrada inválida ou horário fora da grade ou já iniciado."}
RESPOSTA_401 = {"model": ErroResposta, "description": "Credencial ausente ou inválida."}
RESPOSTA_403 = {"model": ErroResposta, "description": "O perfil do usuário não permite a operação."}
RESPOSTA_404 = {"model": ErroResposta, "description": "Paciente ou profissional inexistente."}
RESPOSTA_409 = {
    "model": ErroResposta,
    "description": "Horário indisponível, conflito do paciente ou limite de reservas excedido.",
}
RESPOSTA_500 = {"model": ErroResposta, "description": "Erro interno inesperado."}

_MENSAGEM_INTERNA = "Erro interno inesperado."
_MENSAGENS_HTTP = {
    404: "Recurso não encontrado.",
    405: "Método não permitido para este recurso.",
}
_CAMPOS = {
    "dia": "a data",
    "especialidade": "a especialidade",
    "profissional_id": "o identificador do profissional",
    "inicio": "o início da consulta (data e hora locais, sem fuso horário)",
}


def _resposta(
    status: int, mensagem: str, cabecalhos: Mapping[str, str] | None = None
) -> JSONResponse:
    resposta = JSONResponse(status_code=status, content={"erro": mensagem}, headers=cabecalhos)
    if status == 401:
        resposta.headers.setdefault("WWW-Authenticate", "Bearer")
    return resposta


def registrar_tratadores(app: FastAPI) -> None:
    for tipo_de_erro, status in STATUS_POR_ERRO.items():

        async def tratar(_: Request, erro: Exception, status: int = status) -> JSONResponse:
            return _resposta(status, str(erro))

        app.add_exception_handler(tipo_de_erro, tratar)

    async def tratar_entrada_invalida(_: Request, erro: RequestValidationError) -> JSONResponse:
        campos = []
        for detalhe in erro.errors():
            local = detalhe["loc"]
            if len(local) > 1 and local[1] in _CAMPOS:
                campos.append(_CAMPOS[local[1]])
        if campos:
            return _resposta(400, f"Entrada inválida. Verifique {', '.join(campos)}.")
        return _resposta(400, "Entrada inválida. Verifique o conteúdo da solicitação.")

    async def tratar_http(_: Request, erro: StarletteHTTPException) -> JSONResponse:
        if erro.status_code >= 500:
            mensagem = _MENSAGEM_INTERNA
        else:
            mensagem = _MENSAGENS_HTTP.get(erro.status_code, "Não foi possível concluir a solicitação.")
        return _resposta(erro.status_code, mensagem, erro.headers)

    async def tratar_erro_interno(_: Request, _erro: Exception) -> JSONResponse:
        return _resposta(500, _MENSAGEM_INTERNA)

    app.add_exception_handler(RequestValidationError, tratar_entrada_invalida)
    app.add_exception_handler(StarletteHTTPException, tratar_http)
    app.add_exception_handler(Exception, tratar_erro_interno)
