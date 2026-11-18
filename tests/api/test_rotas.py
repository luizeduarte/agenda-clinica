"""A API de ponta a ponta: HTTP, casos de uso e SQLite de verdade.

Os testes usam ``criar_aplicacao`` (a mesma composição do protótipo), com um banco
temporário e relógio fixo.
"""
import threading
from contextlib import closing
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from clinica.infraestrutura.persistencia.conexao import abrir_conexao
from clinica.main import criar_aplicacao

ANA = {"Authorization": "Bearer token-ana"}
BIA = {"Authorization": "Bearer token-bia"}
DR_JOAO = {"Authorization": "Bearer token-dr-joao"}


AGORA = datetime(2026, 11, 20, 9)
SEGUNDA = date(2026, 11, 23)


def horario(hora: int, minuto: int = 0, dia: date = SEGUNDA) -> str:
    return datetime(dia.year, dia.month, dia.day, hora, minuto).isoformat()


@pytest.fixture
def caminho(tmp_path):
    return tmp_path / "api.db"


@pytest.fixture
def app(caminho):
    return criar_aplicacao(caminho, relogio=lambda: AGORA)


@pytest.fixture
def cliente(app):
    return TestClient(app)


def agendar(cliente, cabecalhos=ANA, profissional_id=10, inicio=None):
    return cliente.post(
        "/consultas",
        json={"profissional_id": profissional_id, "inicio": inicio or horario(10)},
        headers=cabecalhos,
    )


class TestConsultarDisponibilidade:
    def test_lista_os_slots_livres_de_um_profissional(self, cliente):
        resposta = cliente.get(
            "/disponibilidade", params={"dia": SEGUNDA.isoformat(), "profissional_id": 10}, headers=ANA
        )

        assert resposta.status_code == 200
        (item,) = resposta.json()
        assert item["profissional"] == {"id": 10, "nome": "Dr. João", "especialidade": "Clínica Geral"}
        assert len(item["slots"]) == 16  # 08–12 e 14–18, em slots de 30 minutos
        assert item["slots"][0] == {"inicio": horario(8), "fim": horario(8, 30)}

    def test_lista_por_especialidade(self, cliente):
        resposta = cliente.get(
            "/disponibilidade", params={"dia": SEGUNDA.isoformat(), "especialidade": "Odontologia"}, headers=ANA
        )

        assert [i["profissional"]["id"] for i in resposta.json()] == [11]

    def test_horario_agendado_some_da_lista(self, cliente):
        agendar(cliente, inicio=horario(10))

        resposta = cliente.get(
            "/disponibilidade", params={"dia": SEGUNDA.isoformat(), "profissional_id": 10}, headers=ANA
        )

        inicios = [s["inicio"] for s in resposta.json()[0]["slots"]]
        assert horario(10) not in inicios
        assert horario(9, 30) in inicios and horario(10, 30) in inicios

    @pytest.mark.parametrize("dia", [AGORA.date() - timedelta(days=1), SEGUNDA + timedelta(days=5)])
    def test_data_passada_ou_sem_atendimento_retorna_agenda_vazia(self, cliente, dia):
        resposta = cliente.get("/disponibilidade", params={"dia": dia.isoformat(), "profissional_id": 10}, headers=ANA)
        assert resposta.status_code == 200
        assert resposta.json()[0]["slots"] == []

    def test_distingue_especialidade_vazia_de_busca_sem_resultados(self, cliente, caminho):
        with closing(abrir_conexao(caminho)) as con:
            con.execute("INSERT INTO especialidade VALUES (3, 'Pediatria')")

        for nome in ("Cardiologia", "Pediatria"):
            resposta = cliente.get(
                "/disponibilidade", params={"dia": SEGUNDA.isoformat(), "especialidade": nome}, headers=ANA
            )
            assert resposta.status_code == 200 and resposta.json() == []

        resposta = cliente.get(
            "/disponibilidade", params={"dia": SEGUNDA.isoformat(), "especialidade": " "}, headers=ANA
        )
        assert resposta.status_code == 400
        assert resposta.json() == {"erro": "Informe o nome da especialidade."}

    def test_aceita_ultima_data_do_calendario(self, cliente):
        resposta = cliente.get(
            "/disponibilidade", params={"dia": date.max.isoformat(), "profissional_id": 10}, headers=ANA
        )
        assert resposta.status_code == 200

    def test_profissional_tambem_consulta(self, cliente):
        resposta = cliente.get(
            "/disponibilidade", params={"dia": SEGUNDA.isoformat(), "profissional_id": 10}, headers=DR_JOAO
        )

        assert resposta.status_code == 200

    def test_exige_exatamente_um_filtro(self, cliente):
        sem_filtro = cliente.get("/disponibilidade", params={"dia": SEGUNDA.isoformat()}, headers=ANA)
        dois = cliente.get(
            "/disponibilidade",
            params={"dia": SEGUNDA.isoformat(), "profissional_id": 10, "especialidade": "Odontologia"},
            headers=ANA,
        )

        assert sem_filtro.status_code == 400 and dois.status_code == 400
        assert set(sem_filtro.json()) == set(dois.json()) == {"erro"}

    def test_data_invalida(self, cliente):
        resposta = cliente.get("/disponibilidade", params={"dia": "ontem", "profissional_id": 10}, headers=ANA)

        assert resposta.status_code == 400
        assert resposta.json()["erro"].startswith("Entrada inválida")

    def test_profissional_inexistente(self, cliente):
        resposta = cliente.get(
            "/disponibilidade", params={"dia": SEGUNDA.isoformat(), "profissional_id": 999}, headers=ANA
        )

        assert resposta.status_code == 404

    def test_exige_autenticacao(self, cliente):
        resposta = cliente.get("/disponibilidade", params={"dia": SEGUNDA.isoformat(), "profissional_id": 10})

        assert resposta.status_code == 401


class TestAgendarConsulta:
    def test_agenda_e_devolve_201_com_a_consulta(self, cliente):
        resposta = agendar(cliente)

        assert resposta.status_code == 201
        corpo = resposta.json()
        assert corpo["status"] == "AGENDADA"
        assert corpo["paciente_id"] == 7 and corpo["profissional_id"] == 10
        assert corpo["inicio"] == horario(10) and corpo["fim"] == horario(10, 30)
        assert corpo["id"] > 0

    def test_horario_ocupado_devolve_409(self, cliente):
        agendar(cliente, ANA)

        resposta = agendar(cliente, BIA)

        assert resposta.status_code == 409
        assert "ocupado" in resposta.json()["erro"]

    def test_horario_fora_do_atendimento_devolve_409(self, cliente):
        resposta = agendar(cliente, inicio=horario(13))  # intervalo do almoço

        assert resposta.status_code == 409
        assert "fora" in resposta.json()["erro"]

    def test_horario_fora_da_grade_devolve_400(self, cliente):
        resposta = agendar(cliente, inicio=horario(10, 15))

        assert resposta.status_code == 400
        assert "30" in resposta.json()["erro"] or ":00" in resposta.json()["erro"]

    def test_horario_ja_iniciado_devolve_400(self, cliente):
        resposta = agendar(cliente, inicio=AGORA.isoformat())

        assert resposta.status_code == 400
        assert resposta.json() == {"erro": "O horário da consulta deve estar no futuro."}

    def test_paciente_com_dois_agendamentos_no_mesmo_horario_devolve_409(self, cliente):
        agendar(cliente, ANA, profissional_id=10, inicio=horario(10))

        resposta = agendar(cliente, ANA, profissional_id=11, inicio=horario(10))

        assert resposta.status_code == 409

    def test_segunda_consulta_futura_na_mesma_especialidade_devolve_409(self, cliente):
        agendar(cliente, ANA, inicio=horario(10))

        resposta = agendar(cliente, ANA, inicio=horario(11))

        assert resposta.status_code == 409
        assert "especialidade" in resposta.json()["erro"]

    def test_profissional_e_recusado_com_403(self, cliente):
        resposta = agendar(cliente, DR_JOAO)

        assert resposta.status_code == 403
        # nada foi reservado: o mesmo horário segue livre para um paciente
        assert agendar(cliente, ANA).status_code == 201

    def test_profissional_inexistente_devolve_404(self, cliente):
        resposta = agendar(cliente, profissional_id=999)

        assert resposta.status_code == 404

    @pytest.mark.parametrize(
        "corpo",
        [
            {},
            {"profissional_id": "x", "inicio": "2026-12-01T10:00:00"},
            {"profissional_id": 10, "inicio": "nao-e-data"},
            {"profissional_id": 10, "inicio": "2026-12-01T10:00:00+00:00"},  # com fuso
        ],
    )
    def test_corpo_invalido_devolve_400(self, cliente, corpo):
        resposta = cliente.post("/consultas", json=corpo, headers=ANA)

        assert resposta.status_code == 400
        assert resposta.json()["erro"].startswith("Entrada inválida")


class TestAutenticacao:
    @pytest.mark.parametrize(
        "cabecalhos",
        [{}, {"Authorization": "token-ana"}, {"Authorization": "Bearer "}, {"Authorization": "Bearer invalido"}],
    )
    def test_sem_credencial_valida_devolve_401(self, cliente, cabecalhos):
        resposta = cliente.post(
            "/consultas", json={"profissional_id": 10, "inicio": horario(10)}, headers=cabecalhos
        )

        assert resposta.status_code == 401
        assert set(resposta.json()) == {"erro"}
        assert resposta.headers["WWW-Authenticate"] == "Bearer"

    def test_a_credencial_invalida_nao_grava_nada(self, cliente):
        cliente.post(
            "/consultas",
            json={"profissional_id": 10, "inicio": horario(10)},
            headers={"Authorization": "Bearer invalido"},
        )

        assert agendar(cliente).status_code == 201


class TestDocumentacao:
    def test_openapi_descreve_as_duas_rotas_e_os_erros_reais(self, cliente):
        caminhos = cliente.get("/openapi.json").json()["paths"]

        assert set(caminhos) == {"/disponibilidade", "/consultas"}
        assert set(caminhos["/consultas"]["post"]["responses"]) == {"201", "400", "401", "403", "404", "409", "500"}
        assert "422" not in caminhos["/disponibilidade"]["get"]["responses"]


class TestErrosHTTP:
    def test_rota_inexistente_e_metodo_invalido_usam_o_mesmo_formato(self, cliente):
        inexistente = cliente.get("/ausente")
        metodo_invalido = cliente.get("/consultas")

        assert inexistente.status_code == 404
        assert inexistente.json() == {"erro": "Recurso não encontrado."}
        assert metodo_invalido.status_code == 405
        assert metodo_invalido.json() == {"erro": "Método não permitido para este recurso."}
        assert metodo_invalido.headers["Allow"] == "POST"

    @pytest.mark.parametrize(
        ("tabela", "acao", "detalhe"),
        [
            ("consulta", "ABORT", "UNIQUE constraint failed: consulta.profissional_id, consulta.inicio"),
            ("notificacao_pendente", "ROLLBACK", "detalhe interno da persistência"),
        ],
    )
    def test_falha_interna_reverte_o_agendamento_sem_vazar_detalhes(self, app, caminho, tabela, acao, detalhe):
        with closing(abrir_conexao(caminho)) as con, TestClient(app, raise_server_exceptions=False) as cliente:
            con.execute(
                f"CREATE TRIGGER falha BEFORE INSERT ON {tabela}"
                f" BEGIN SELECT RAISE({acao}, '{detalhe}'); END"
            )

            resposta = agendar(cliente)

            assert resposta.status_code == 500
            assert resposta.json() == {"erro": "Erro interno inesperado."}
            assert con.execute("SELECT COUNT(*) FROM consulta").fetchone()[0] == 0
            assert con.execute("SELECT COUNT(*) FROM notificacao_pendente").fetchone()[0] == 0
            con.execute("DROP TRIGGER falha")
            assert agendar(cliente).status_code == 201


class TestInterface:
    def test_pagina_estaticos_e_swagger_estao_disponiveis(self, cliente):
        pagina = cliente.get("/")
        estilo = cliente.get("/estaticos/agenda.css")
        script = cliente.get("/estaticos/agenda.js")

        assert pagina.status_code == estilo.status_code == script.status_code == 200
        assert pagina.headers["content-type"].startswith("text/html")
        assert estilo.headers["content-type"].startswith("text/css")
        assert "javascript" in script.headers["content-type"]
        assert 'lang="pt-BR"' in pagina.text
        assert '/estaticos/agenda.css' in pagina.text and '/estaticos/agenda.js' in pagina.text
        assert cliente.get("/docs").status_code == 200


class TestConcorrenciaPelaApi:
    """ASR-01 vista de fora: dois pacientes disputam o mesmo horário pela API."""

    def test_so_um_dos_dois_consegue_cada_horario(self, tmp_path):
        # Um banco novo por rodada: quem ganha um horário não pode, pela RN08, ganhar
        # outro com a mesma especialidade, o que misturaria as rodadas.
        for rodada, hora in enumerate([8, 9, 10, 11, 14, 15, 16, 17]):
            app = criar_aplicacao(tmp_path / f"rodada{rodada}.db", relogio=lambda: AGORA)
            codigos = []
            trava = threading.Lock()
            largada = threading.Barrier(2)

            def disputar(cabecalhos):
                cliente = TestClient(app)
                largada.wait()
                codigo = agendar(cliente, cabecalhos, inicio=horario(hora)).status_code
                with trava:
                    codigos.append(codigo)

            threads = [threading.Thread(target=disputar, args=(c,)) for c in (ANA, BIA)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert sorted(codigos) == [201, 409], f"às {hora}h: {sorted(codigos)}"
