# Modelo de Domínio - Agendamento de Consultas

## 1. Visão Geral

O sistema tem como objetivo gerenciar o agendamento de consultas em uma clínica universitária, permitindo que pacientes consultem horários disponíveis, realizem agendamentos, cancelamentos e reagendamentos.

O domínio contempla o gerenciamento das agendas dos profissionais de saúde, o controle de conflitos de horários e o acompanhamento do estado das consultas.

## 2. Principais Conceitos do Domínio

### Paciente
Representa o indivíduo que recebe atendimento na clínica.

**Atributos principais:**
- `id`: identificador único.
- `nome`: nome do paciente.
- `email`: contato para notificações.

**Relacionamentos:** um paciente pode possuir várias consultas.

### Profissional
Representa o profissional de saúde responsável pelos atendimentos.

**Atributos principais:**
- `id`: identificador único.
- `nome`: nome do profissional.
- `especialidade`: especialidade de atendimento.

**Relacionamentos:** um profissional possui uma agenda e pode realizar várias consultas.

### Agenda
Representa a organização dos horários de atendimento de um profissional.

**Responsabilidades:**
- Determinar a disponibilidade dos horários.
- Considerar consultas existentes e períodos bloqueados.
- Aplicar as regras de disponibilidade do domínio.

**Relacionamentos:** pertence a um profissional e está associada a horários de atendimento, bloqueios e consultas.

### HorarioAtendimento
Representa um período em que o profissional está disponível para realizar consultas.

**Atributos principais:**
- `dia_semana`: dia do atendimento.
- `hora_inicio`: início do período.
- `hora_fim`: término do período.

### Bloqueio
Representa um período em que a agenda do profissional está indisponível.

**Atributos principais:**
- `id`: identificador único.
- `inicio`: início do bloqueio.
- `fim`: término do bloqueio.
- `motivo`: justificativa da indisponibilidade.

### Consulta
Representa um agendamento entre um paciente e um profissional.

**Atributos principais:**
- `id`: identificador único.
- `paciente_id`: referência ao paciente.
- `profissional_id`: referência ao profissional.
- `inicio`: data e horário da consulta.
- `fim`: horário de término.
- `status`: estado atual da consulta.

**Estados possíveis:**
- `AGENDADA`: agendamento registrado, aguardando confirmação do paciente.
- `CONFIRMADA`: consulta confirmada pelo paciente.
- `CANCELADA`: consulta cancelada.
- `REALIZADA`: atendimento concluído.
- `FALTOU`: paciente não compareceu.

### Especialidade
Representa uma área de atendimento da clínica, como clínica médica, pediatria ou dermatologia.

Permite identificar e consultar profissionais por especialidade.

## 3. Relacionamentos Principais

- Um **Paciente** pode possuir zero ou várias **Consultas**.
- Um **Profissional** pode realizar zero ou várias **Consultas**.
- Cada **Consulta** pertence a exatamente um **Paciente** e um **Profissional**.
- Um **Profissional** possui uma **Agenda**.
- Uma **Agenda** possui horários de atendimento e pode possuir bloqueios.
- Um **Profissional** está associado a uma **Especialidade**, podendo essa relação ser ampliada futuramente.

## 4. Regras de Domínio

**RN01 - Disponibilidade:** uma consulta só pode ser agendada dentro de um horário de atendimento do profissional.

**RN02 - Conflitos:** não podem existir consultas ativas com horários sobrepostos para o mesmo profissional ou paciente.

**RN03 - Bloqueios:** horários bloqueados não podem receber novos agendamentos.

**RN04 - Duração:** inicialmente, as consultas terão duração fixa de 30 minutos, utilizando horários padronizados e alinhados à grade da agenda.

**RN05 - Cancelamento:** o cancelamento deve respeitar uma antecedência mínima de 24 horas, conforme política inicialmente proposta.

**RN06 - Reagendamento:** a alteração de horário deve preservar a consulta original caso o novo agendamento não possa ser concluído.

**RN07 - Confirmação:** o registro de um agendamento e a confirmação do paciente são operações distintas.

## 5. Consistência dos Agendamentos

A disponibilidade poderá ser avaliada pelas regras da Agenda, considerando consultas existentes, horários de atendimento e bloqueios.

Entretanto, a verificação de disponibilidade, isoladamente, não garante a ausência de conflitos em solicitações concorrentes.

Portanto, a implementação deverá garantir que a ocupação de um horário ocorra de maneira atômica, utilizando transações e restrições adequadas na persistência.

Essa decisão atende ao ASR de consistência dos agendamentos, impedindo que solicitações simultâneas produzam reservas conflitantes.

## 6. Considerações de Modelagem

O modelo de domínio deve permanecer independente das tecnologias utilizadas para persistência, comunicação HTTP e notificações.

As entidades e regras descritas representam os conceitos centrais do problema. A definição dos casos de uso, interfaces e adaptadores será detalhada na documentação de responsabilidades e arquitetura.
