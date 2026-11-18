"""Tradução dos erros do núcleo para respostas HTTP.
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

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
RESPOSTA_400 = {"model": ErroResposta, "description": "Entrada inválida ou horário fora da grade de 30 minutos."}
RESPOSTA_401 = {"model": ErroResposta, "description": "Credencial ausente ou inválida."}
RESPOSTA_403 = {"model": ErroResposta, "description": "O perfil do usuário não permite a operação."}
RESPOSTA_404 = {"model": ErroResposta, "description": "Paciente ou profissional inexistente."}
RESPOSTA_409 = {
    "model": ErroResposta,
    "description": "Horário indisponível, conflito do paciente ou limite de reservas excedido.",
}


def _resposta(status: int, mensagem: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"erro": mensagem})


def registrar_tratadores(app: FastAPI) -> None:
    for tipo_de_erro, status in STATUS_POR_ERRO.items():

        async def tratar(_: Request, erro: Exception, status: int = status) -> JSONResponse:
            return _resposta(status, str(erro))

        app.add_exception_handler(tipo_de_erro, tratar)

    async def tratar_entrada_invalida(_: Request, erro: RequestValidationError) -> JSONResponse:
        detalhes = "; ".join(
            f"{'.'.join(str(parte) for parte in e['loc'][1:])}: {e['msg']}" for e in erro.errors()
        )
        return _resposta(400, f"Entrada inválida ({detalhes}).")

    app.add_exception_handler(RequestValidationError, tratar_entrada_invalida)
