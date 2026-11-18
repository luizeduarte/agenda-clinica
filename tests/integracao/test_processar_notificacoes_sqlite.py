import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from datetime import datetime

import pytest

from clinica.compartilhado.erros import FalhaNoEnvioError
from clinica.infraestrutura.notificacoes.notificador_fake import NotificadorFake
from clinica.infraestrutura.persistencia import SQLiteUnidadeDeTrabalho, inicializar_banco
from clinica.infraestrutura.persistencia.conexao import abrir_conexao
from clinica.infraestrutura.persistencia.dados_exemplo import popular_dados_de_exemplo
from clinica.modulos.autenticacao.portas.servico_autenticacao import Papel, Usuario
from clinica.modulos.consultas.aplicacao.agendar_consulta import AgendarConsulta, AgendarConsultaComando
from clinica.processar_notificacoes import criar_processador


@pytest.fixture
def caminho(tmp_path):
    banco = tmp_path / "envios.db"
    inicializar_banco(banco)
    popular_dados_de_exemplo(banco)
    return banco


def registrar_consulta(caminho, paciente_id=7, hora=10):
    agendar = AgendarConsulta(SQLiteUnidadeDeTrabalho(caminho), lambda: datetime(2026, 11, 20))
    return agendar.executar(
        AgendarConsultaComando(Usuario(paciente_id, Papel.PACIENTE), 10, datetime(2026, 12, 1, hora))
    )


def estados_no_banco(caminho):
    with closing(abrir_conexao(caminho)) as con:
        linhas = con.execute("SELECT estado, tentativas, ultimo_erro FROM notificacao_pendente ORDER BY id")
        return [tuple(linha) for linha in linhas]


def test_falha_e_reenvio_em_processos_distintos(caminho):
    registrar_consulta(caminho)
    registrar_consulta(caminho, paciente_id=8, hora=11)

    def executar(*argumentos):
        return subprocess.run(
            [sys.executable, "-m", "clinica.processar_notificacoes", *argumentos],
            env={**os.environ, "CLINICA_DB": str(caminho)},
            capture_output=True, text=True, check=True, timeout=10,
        ).stdout

    assert estados_no_banco(caminho) == [("PENDENTE", 0, None)] * 2
    assert "Notificação 1 · FALHA · tentativas 1" in executar("--limite", "1", "--simular-falha")
    assert estados_no_banco(caminho) == [
        ("FALHA", 1, "Falha simulada no canal de notificações."), ("PENDENTE", 0, None)
    ]
    assert "Notificação 2 · ENVIADA · tentativas 1" in executar("--limite", "1")
    assert "Notificação 1 · ENVIADA · tentativas 2" in executar()
    assert "Nenhuma notificação" in executar()
    assert estados_no_banco(caminho) == [("ENVIADA", 2, None), ("ENVIADA", 1, None)]


def test_agendamento_pode_gravar_durante_envio_com_falha(caminho):
    registrar_consulta(caminho)

    class CanalIndisponivel:
        def enviar(self, notificacao):
            registrar_consulta(caminho, paciente_id=8, hora=11)
            raise FalhaNoEnvioError("Canal indisponível")

    (resultado,) = criar_processador(caminho, CanalIndisponivel()).executar()

    assert resultado.ultimo_erro == "Canal indisponível"
    assert estados_no_banco(caminho) == [("FALHA", 1, "Canal indisponível"), ("PENDENTE", 0, None)]
    with closing(abrir_conexao(caminho)) as con:
        assert con.execute("SELECT COUNT(*) FROM consulta WHERE status = 'AGENDADA'").fetchone()[0] == 2


def test_falha_ao_persistir_o_resultado_permite_reenvio(caminho):
    registrar_consulta(caminho)
    canal = NotificadorFake()
    processador = criar_processador(caminho, canal)

    with closing(abrir_conexao(caminho)) as con:
        con.execute(
            "CREATE TRIGGER falha_no_resultado BEFORE UPDATE ON notificacao_pendente"
            " BEGIN SELECT RAISE(ABORT, 'gravação indisponível'); END"
        )
        with pytest.raises(sqlite3.IntegrityError, match="gravação indisponível"):
            processador.executar()
        assert estados_no_banco(caminho) == [("PENDENTE", 0, None)]
        con.execute("DROP TRIGGER falha_no_resultado")

    processador.executar()
    assert len(canal.enviadas) == 2 and canal.enviadas[0] == canal.enviadas[1]
    assert estados_no_banco(caminho) == [("ENVIADA", 1, None)]


def test_tentativa_concorrente_nao_reverte_um_sucesso(caminho):
    registrar_consulta(caminho)
    registrar_consulta(caminho, paciente_id=8, hora=11)
    outro_canal = NotificadorFake()

    class CanalComFalhaTardia:
        def enviar(self, notificacao):
            criar_processador(caminho, outro_canal).executar()
            raise FalhaNoEnvioError("Resposta tardia do canal")

    (resultado,) = criar_processador(caminho, CanalComFalhaTardia()).executar()

    assert resultado.id == 1  # A segunda candidata já foi enviada pelo outro lote.
    assert len(outro_canal.enviadas) == 2
    assert estados_no_banco(caminho) == [("ENVIADA", 2, None), ("ENVIADA", 1, None)]
