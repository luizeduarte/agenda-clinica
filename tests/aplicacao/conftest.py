from datetime import date, datetime, time

import pytest

from clinica.modulos.agenda.contratos import Agenda
from clinica.modulos.agenda.dominio.horarios import HorarioAtendimento
from clinica.modulos.cadastros.contratos import Cadastros, Especialidade, Paciente, Profissional
from clinica.modulos.consultas.contratos import Consultas
from clinica.modulos.notificacoes.contratos import Notificacoes
from tests.aplicacao.fakes import (
    AgendaRepositorioEmMemoria,
    BancoEmMemoria,
    ConsultaRepositorioEmMemoria,
    NotificacaoPendenteRepositorioEmMemoria,
    PacienteRepositorioEmMemoria,
    ProfissionalRepositorioEmMemoria,
)

TERCA = date(2026, 12, 1)
AGORA = datetime(2026, 11, 20, 9, 0)

CLINICA_GERAL = Especialidade(1, "Clínica Geral")
ODONTOLOGIA = Especialidade(2, "Odontologia")


def dt(hora, minuto=0, dia=TERCA):
    return datetime(dia.year, dia.month, dia.day, hora, minuto)


@pytest.fixture
def banco():
    """Ana (7) e Bia (8); Dr. João (10, Clínica Geral) e Dra. Marta (11, Odontologia),
    ambos atendendo às terças das 08:00 às 12:00."""
    b = BancoEmMemoria()
    b.pacientes = {
        7: Paciente(7, "Ana", "ana@exemplo.com"),
        8: Paciente(8, "Bia", "bia@exemplo.com"),
    }
    b.profissionais = {
        10: Profissional(10, "Dr. João", CLINICA_GERAL),
        11: Profissional(11, "Dra. Marta", ODONTOLOGIA),
    }
    b.horarios = {
        10: [HorarioAtendimento(1, time(8, 0), time(12, 0))],
        11: [HorarioAtendimento(1, time(8, 0), time(12, 0))],
    }
    Agenda.configurar(AgendaRepositorioEmMemoria(b))
    Cadastros.configurar(
        PacienteRepositorioEmMemoria(b),
        ProfissionalRepositorioEmMemoria(b),
    )
    Consultas.configurar(ConsultaRepositorioEmMemoria(b))
    Notificacoes.configurar(NotificacaoPendenteRepositorioEmMemoria(b))
    return b
