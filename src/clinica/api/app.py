from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from clinica.api.controllers.agendamento_controller import AgendamentoController
from clinica.api.erros import registrar_tratadores
from clinica.modulos.autenticacao.portas.servico_autenticacao import ServicoAutenticacao
from clinica.modulos.consultas.aplicacao.agendar_consulta import AgendarConsulta
from clinica.modulos.consultas.aplicacao.consultar_disponibilidade import ConsultarDisponibilidade

DEMONSTRACAO = Path(__file__).with_name("demonstracao")


def criar_app(
    agendar_consulta: AgendarConsulta,
    consultar_disponibilidade: ConsultarDisponibilidade,
    autenticacao: ServicoAutenticacao,
) -> FastAPI:
    """Monta a aplicação web a partir dos casos de uso já criados.
    """
    app = FastAPI(
        title="Agenda de clínica universitária",
        description=(
            "Protótipo do agendamento de consultas. Envie `Authorization: Bearer <token>`; "
            "no protótipo, a autenticação é simulada (tokens de exemplo em `main.py`)."
        ),
        version="0.1.0",
    )
    app.include_router(
        AgendamentoController(agendar_consulta, consultar_disponibilidade, autenticacao).criar_rotas()
    )
    app.mount("/estaticos", StaticFiles(directory=DEMONSTRACAO / "estaticos"))

    @app.get("/", include_in_schema=False)
    def demonstracao() -> FileResponse:
        return FileResponse(DEMONSTRACAO / "index.html", media_type="text/html")

    registrar_tratadores(app)
    _documentar_sem_422(app)
    return app


def _documentar_sem_422(app: FastAPI) -> None:
    """O FastAPI anuncia 422 para entrada inválida, mas aqui ela vira 400 (ver ``api/erros.py``)."""
    gerar = app.openapi

    def openapi() -> dict:
        if app.openapi_schema is None:
            for operacoes in gerar()["paths"].values():
                for operacao in operacoes.values():
                    operacao["responses"].pop("422", None)
        return app.openapi_schema

    app.openapi = openapi
