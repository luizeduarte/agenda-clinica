"""``PoliticaDeCancelamento``: antecedência mínima para cancelamento (RN05)."""
from datetime import datetime, timedelta

from clinica.compartilhado.erros import CancelamentoForaDoPrazoError
from clinica.modulos.autenticacao.portas.servico_autenticacao import Papel
from clinica.modulos.consultas.dominio.consulta import Consulta


class PoliticaDeCancelamento:
    """Encapsula a regra de antecedência mínima para cancelamento (RN05).

    - Paciente: 24h de antecedência para especialidades gerais e 72h para Odontologia (Dentista).
    - Profissional: isento da trava de antecedência.
    """

    ANTECEDENCIA_PADRAO = timedelta(hours=24)
    ANTECEDENCIA_ODONTOLOGIA = timedelta(hours=72)
    _TERMOS_ODONTOLOGIA = ("odontologia", "dentista")

    def antecedencia_minima(self, nome_especialidade: str) -> timedelta:
        nome = nome_especialidade.strip().lower()
        if any(termo in nome for termo in self._TERMOS_ODONTOLOGIA):
            return self.ANTECEDENCIA_ODONTOLOGIA
        return self.ANTECEDENCIA_PADRAO

    def permite_cancelar(
        self,
        consulta: Consulta,
        papel: Papel,
        agora: datetime,
        nome_especialidade: str = "",
    ) -> bool:
        if papel == Papel.PROFISSIONAL:
            return True
        return (consulta.slot.inicio - agora) >= self.antecedencia_minima(nome_especialidade)

    def verificar_pode_cancelar(
        self,
        consulta: Consulta,
        papel: Papel,
        agora: datetime,
        nome_especialidade: str = "",
    ) -> None:
        if not self.permite_cancelar(consulta, papel, agora, nome_especialidade):
            horas = int(self.antecedencia_minima(nome_especialidade).total_seconds() // 3600)
            raise CancelamentoForaDoPrazoError(
                f"Cancelamento pelo paciente exige pelo menos {horas}h de antecedência."
            )
