"""A API de ponta a ponta: HTTP, casos de uso e SQLite de verdade.

Os testes usam ``criar_aplicacao`` (a mesma composição do protótipo), com um banco
temporário. As datas são calculadas a partir de hoje para não envelhecerem.
"""
import threading
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from clinica.main import criar_aplicacao

ANA = {"Authorization": "Bearer token-ana"}
BIA = {"Authorization": "Bearer token-bia"}
DR_JOAO = {"Authorization": "Bearer token-dr-joao"}


def proxima_segunda(minimo_de_dias: int = 7) -> date:
    """Primeira segunda-feira a pelo menos ``minimo_de_dias`` de hoje (os profissionais atendem seg–sex)."""
    dia = date.today() + timedelta(days=minimo_de_dias)
    while dia.weekday() != 0:
        dia += timedelta(days=1)
    return dia


SEGUNDA = proxima_segunda()


def horario(hora: int, minuto: int = 0, dia: date = SEGUNDA) -> str:
    return datetime(dia.year, dia.month, dia.day, hora, minuto).isoformat()


@pytest.fixture
def app(tmp_path):
    return criar_aplicacao(tmp_path / "api.db")


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
        assert "erro" in sem_filtro.json() or "detail" in sem_filtro.json()

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
        assert "erro" in resposta.json()

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
        assert set(caminhos["/consultas"]["post"]["responses"]) == {"201", "400", "401", "403", "404", "409"}
        assert "422" not in caminhos["/disponibilidade"]["get"]["responses"]


class TestConcorrenciaPelaApi:
    """ASR-01 vista de fora: dois pacientes disputam o mesmo horário pela API."""

    def test_so_um_dos_dois_consegue_cada_horario(self, tmp_path):
        # Um banco novo por rodada: quem ganha um horário não pode, pela RN08, ganhar
        # outro com a mesma especialidade, o que misturaria as rodadas.
        for rodada, hora in enumerate([8, 9, 10, 11, 14, 15, 16, 17]):
            app = criar_aplicacao(tmp_path / f"rodada{rodada}.db")
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
