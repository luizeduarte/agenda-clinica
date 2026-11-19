"""Mensagens de erro do sistema."""


class ErroDeDominio(Exception):
    """Base de todos os erros de regra de negócio."""

class SlotInvalidoError(ErroDeDominio):
    """Slot que não dura 30 minutos ou não começa em :00/:30 (RN02)."""

class HorarioDeAtendimentoInvalidoError(ErroDeDominio):
    """Período ou bloqueio fora da grade, invertido ou sobreposto (RN01, RN02)."""

class HorarioIndisponivelError(ErroDeDominio):
    """Fora do atendimento, bloqueado ou já ocupado pelo profissional (RN01, RN03, RN04)."""

class ConflitoDoPacienteError(ErroDeDominio):
    """O paciente já tem consulta ativa sobreposta ao horário (RN03)."""

class LimiteDoPacienteExcedidoError(ErroDeDominio):
    """Excede 2 consultas ativas no dia ou 1 futura por especialidade (RN08)."""

class FiltroInvalidoError(ErroDeDominio):
    """Consulta de disponibilidade sem exatamente um filtro (profissional ou especialidade)."""


class EntidadeNaoEncontradaError(ErroDeDominio):
    """Paciente, profissional ou consulta inexistente."""

class NaoAutenticadoError(ErroDeDominio):
    """Credencial não identificada pelo serviço de autenticação."""

class NaoAutorizadoError(ErroDeDominio):
    """O papel do usuário não permite a operação (RNF03)."""

class ConflitoDePersistenciaError(Exception):
    """Restrição única do banco violada na gravação (ASR-01).

    Levantada pelos repositórios quando duas reservas concorrentes disputam o
    mesmo ``(participante, inicio)``. ``participante`` é ``"profissional"`` ou
    ``"paciente"``. O caso de uso a converte em ``HorarioIndisponivelError`` ou
    ``ConflitoDoPacienteError``.
    """

    def __init__(self, participante: str) -> None:
        super().__init__(f"Conflito de horário do {participante}.")
        self.participante = participante

class FalhaNoEnvioError(Exception):
    """Falha do canal ao enviar uma notificação (ASR-03).

    Levantada por qualquer implementação de ``Notificador``; o processador de
    pendências registra a falha e mantém a notificação para reenvio.
    """
