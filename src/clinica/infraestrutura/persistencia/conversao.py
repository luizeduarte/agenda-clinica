"""Conversão entre tipos do domínio e o texto armazenado no SQLite."""
from datetime import datetime, time


def para_texto(momento: datetime) -> str:
    return momento.isoformat(timespec="seconds")


def de_texto(texto: str) -> datetime:
    return datetime.fromisoformat(texto)


def hora_para_texto(hora: time) -> str:
    return hora.strftime("%H:%M")


def hora_de_texto(texto: str) -> time:
    return time.fromisoformat(texto)
