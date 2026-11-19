"""Para rodar o protótipo::

    uvicorn --factory clinica.main:criar_aplicacao

A documentação interativa da API fica em http://127.0.0.1:8000/docs.
Tokens de exemplo: ``token-ana`` e ``token-bia`` (pacientes), ``token-dr-joao`` e ``token-dra-marta`` (profissionais).
"""
import os
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI

from clinica.api.app import criar_app
from clinica.infraestrutura.autenticacao.servico_autenticacao_fake import ServicoAutenticacaoFake
from clinica.infraestrutura.persistencia import ConexaoSQLite, inicializar_banco
from clinica.infraestrutura.persistencia.agenda_repositorio import SQLiteAgendaRepositorio
from clinica.infraestrutura.persistencia.cadastros_repositorios import (
    SQLitePacienteRepositorio,
    SQLiteProfissionalRepositorio,
)
from clinica.infraestrutura.persistencia.consulta_repositorio import SQLiteConsultaRepositorio
from clinica.infraestrutura.persistencia.dados_exemplo import popular_dados_de_exemplo
from clinica.infraestrutura.persistencia.notificacao_pendente_repositorio import (
    SQLiteNotificacaoPendenteRepositorio,
)
from clinica.modulos.agenda.aplicacao import ConsultarDisponibilidade
from clinica.modulos.agenda.contratos import Agenda
from clinica.modulos.autenticacao.contratos import Autenticacao
from clinica.modulos.cadastros.contratos import Cadastros
from clinica.modulos.consultas.aplicacao import AgendarConsulta
from clinica.modulos.consultas.contratos import Consultas
from clinica.modulos.notificacoes.contratos import Notificacoes


def criar_aplicacao(
    caminho_do_banco: str | Path | None = None,
    relogio: Callable[[], datetime] = datetime.now,
) -> FastAPI:
    caminho = caminho_do_banco or os.environ.get("CLINICA_DB", "clinica.db")
    inicializar_banco(caminho)
    popular_dados_de_exemplo(caminho)  # só para o protótipo: cadastros e horários de demonstração

    banco = ConexaoSQLite(caminho)
    consultas_repo = SQLiteConsultaRepositorio(banco)
    agendas_repo = SQLiteAgendaRepositorio(banco)
    pacientes_repo = SQLitePacienteRepositorio(banco)
    profissionais_repo = SQLiteProfissionalRepositorio(banco)
    pendentes_repo = SQLiteNotificacaoPendenteRepositorio(banco)
    autenticacao = ServicoAutenticacaoFake()

    Agenda.configurar(agendas_repo)
    Cadastros.configurar(pacientes_repo, profissionais_repo)
    Consultas.configurar(consultas_repo)
    Notificacoes.configurar(pendentes_repo)
    Autenticacao.configurar(autenticacao)

    return criar_app(
        agendar_consulta=AgendarConsulta(consultas_repo, relogio=relogio),
        consultar_disponibilidade=ConsultarDisponibilidade(relogio=relogio),
    )
