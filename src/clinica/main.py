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
from clinica.infraestrutura.persistencia import SQLiteUnidadeDeTrabalho, inicializar_banco
from clinica.infraestrutura.persistencia.dados_exemplo import popular_dados_de_exemplo
from clinica.modulos.consultas.aplicacao.agendar_consulta import AgendarConsulta
from clinica.modulos.consultas.aplicacao.consultar_disponibilidade import ConsultarDisponibilidade


def criar_aplicacao(
    caminho_do_banco: str | Path | None = None,
    relogio: Callable[[], datetime] = datetime.now,
) -> FastAPI:
    caminho = caminho_do_banco or os.environ.get("CLINICA_DB", "clinica.db")
    inicializar_banco(caminho)
    popular_dados_de_exemplo(caminho)  # só para o protótipo: cadastros e horários de demonstração

    uow = SQLiteUnidadeDeTrabalho(caminho)
    autenticacao = ServicoAutenticacaoFake()

    return criar_app(
        agendar_consulta=AgendarConsulta(uow, relogio=relogio),
        consultar_disponibilidade=ConsultarDisponibilidade(uow),
        autenticacao=autenticacao,
    )
