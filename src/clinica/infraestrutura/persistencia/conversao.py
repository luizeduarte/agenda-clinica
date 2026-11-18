"""Formato em que datas e horas são gravadas no SQLite.

O formato precisa ser sempre o mesmo:
o índice único de consultas compara o ``inicio`` como texto, e as consultas
de intervalo (``inicio < ?``) dependem de a ordem alfabética coincidir com
a cronológica.

Para ler, basta ``datetime.fromisoformat`` e ``time.fromisoformat``.
"""
from datetime import datetime


def para_texto(momento: datetime) -> str:
    """Data e hora, sem frações de segundo: ``2026-12-01T10:00:00``."""
    return momento.isoformat(timespec="seconds")
