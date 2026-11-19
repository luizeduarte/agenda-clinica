-- Esquema do protótipo (SQLite). Ver docs/arquitetura.md seção 6 e ADR-003.
-- Datas e horas ficam como texto ISO sem fuso ("2026-12-01T10:00:00" e "08:00"):
-- a ordem alfabética coincide com a cronológica, então comparações de intervalo
-- funcionam direto no SQL.

CREATE TABLE IF NOT EXISTS especialidade (
    id   INTEGER PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS profissional (
    id              INTEGER PRIMARY KEY,
    nome            TEXT NOT NULL,
    especialidade_id INTEGER NOT NULL REFERENCES especialidade (id)
);

-- Dados mínimos do paciente (LGPD).
CREATE TABLE IF NOT EXISTS paciente (
    id    INTEGER PRIMARY KEY,
    nome  TEXT NOT NULL,
    email TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS horario_atendimento (
    id              INTEGER PRIMARY KEY,
    profissional_id INTEGER NOT NULL REFERENCES profissional (id),
    dia_semana      INTEGER NOT NULL CHECK (dia_semana BETWEEN 0 AND 6),
    hora_inicio     TEXT NOT NULL,
    hora_fim        TEXT NOT NULL
);

-- profissional_id NULL = bloqueio coletivo (feriado).
CREATE TABLE IF NOT EXISTS bloqueio (
    id              INTEGER PRIMARY KEY,
    profissional_id INTEGER REFERENCES profissional (id),
    inicio          TEXT NOT NULL,
    fim             TEXT NOT NULL,
    motivo          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS consulta (
    id               INTEGER PRIMARY KEY,
    paciente_id      INTEGER NOT NULL REFERENCES paciente (id),
    profissional_id  INTEGER NOT NULL REFERENCES profissional (id),
    especialidade_id INTEGER NOT NULL REFERENCES especialidade (id),
    inicio           TEXT NOT NULL,
    fim              TEXT NOT NULL,
    status           TEXT NOT NULL
        CHECK (status IN ('AGENDADA', 'CONFIRMADA', 'CANCELADA', 'REALIZADA', 'FALTOU'))
);

-- ASR-01: no máximo uma consulta ativa por participante e horário.
-- Como os slots seguem uma grade global, basta comparar o início (RN02).
CREATE UNIQUE INDEX IF NOT EXISTS uq_consulta_profissional_ativa
    ON consulta (profissional_id, inicio)
    WHERE status IN ('AGENDADA', 'CONFIRMADA');

CREATE UNIQUE INDEX IF NOT EXISTS uq_consulta_paciente_ativa
    ON consulta (paciente_id, inicio)
    WHERE status IN ('AGENDADA', 'CONFIRMADA');

CREATE INDEX IF NOT EXISTS ix_consulta_profissional ON consulta (profissional_id, inicio);
CREATE INDEX IF NOT EXISTS ix_consulta_paciente ON consulta (paciente_id, inicio);

-- Transactional Outbox (ADR-002): gravada na mesma transação da consulta.
CREATE TABLE IF NOT EXISTS notificacao_pendente (
    id           INTEGER PRIMARY KEY,
    destinatario TEXT NOT NULL,
    tipo         TEXT NOT NULL,
    texto        TEXT NOT NULL,
    estado       TEXT NOT NULL DEFAULT 'PENDENTE'
        CHECK (estado IN ('PENDENTE', 'ENVIADA', 'FALHA')),
    tentativas   INTEGER NOT NULL DEFAULT 0,
    ultimo_erro  TEXT
);
