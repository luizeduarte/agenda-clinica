# Proposta Arquitetural - Agendamento de Consultas

## 1. Visão geral

O sistema adota uma arquitetura cliente-servidor, com backend desenvolvido como um monólito modular, organizado em camadas e utilizando princípios da arquitetura hexagonal.

Essa organização combina três decisões:

- **Monólito modular:** os módulos funcionam em uma única aplicação, com responsabilidades e dependências bem definidas.
- **Organização em camadas:** separa apresentação, aplicação, domínio e infraestrutura.
- **Portas e adaptadores:** isolam as regras de negócio das tecnologias externas, como banco de dados, notificações e autenticação.

A escolha busca equilibrar simplicidade de desenvolvimento, facilidade de manutenção, testabilidade e modificabilidade, sem introduzir a complexidade operacional de microsserviços.

## 2. Organização em módulos

O sistema será dividido em módulos conforme suas responsabilidades de negócio.

| Módulo | Responsabilidades |
|---|---|
| `Agenda` | Gerenciar períodos de atendimento, bloqueios e disponibilidade dos profissionais. |
| `Consultas` | Realizar agendamentos, cancelamentos, reagendamentos e confirmações, controlando conflitos de horário. |
| `Cadastros` | Manter as informações essenciais de pacientes, profissionais e especialidades. |
| `Notificacoes` | Registrar notificações pendentes, processar envios e controlar tentativas de reenvio. |
| `Autenticacao` | Integrar a identificação de profissionais e estagiários ao serviço de autenticação da universidade. |

Os módulos pertencem à mesma aplicação e se comunicam por chamadas internas, sem a necessidade de requisições HTTP entre eles.

`Consultas` depende de `Agenda` (usa `Slot`) e de `Cadastros`. `Agenda` não depende de `Consultas`: `AgendaProfissional` recebe os `Slot`s ocupados, e não objetos `Consulta`, evitando um ciclo entre os módulos. O caso de uso `AgendarConsulta` extrai os slots das consultas ativas e os entrega à agenda.

Cada módulo concentra responsabilidades relacionadas. As dependências entre módulos são estabelecidas por contratos e componentes de aplicação, evitando acesso direto aos detalhes internos de outros módulos.

## 3. Organização em camadas

### 3.1. Apresentação

Responsável pela comunicação entre os clientes e o sistema.

A aplicação disponibilizará uma API REST, utilizando HTTP e JSON. Os controllers recebem as requisições, validam sua estrutura e encaminham as operações aos casos de uso.

Também convertem os resultados e erros em respostas HTTP adequadas.

As regras de negócio não são implementadas nos controllers.

### 3.2. Aplicação

Contém os casos de uso responsáveis por coordenar as operações do sistema:

- `ConfigurarHorarioAtendimento`
- `ConsultarDisponibilidade`
- `AgendarConsulta`
- `CancelarConsulta`
- `ReagendarConsulta`
- `ConfirmarConsulta`
- `RegistrarBloqueio`
- `ListarConsultas`

Os casos de uso coordenam as entidades e objetos do domínio e utilizam interfaces para acessar recursos externos.

Por exemplo, `AgendarConsulta` coordena a obtenção dos dados via repositórios, delega a validação temporal e de disponibilidade a `Slot`, `AgendaProfissional` e `AgendaPaciente`, instancia a `Consulta` e persiste as alterações atomicamente pela `UnidadeDeTrabalho`.

Os casos de uso não executam diretamente comandos SQL nem realizam chamadas específicas a serviços externos.

### 3.3. Domínio

Contém as entidades, objetos de valor e regras essenciais do sistema, detalhados em [`responsabilidades.md`](responsabilidades.md).

Entre os principais conceitos estão `Paciente`, `Profissional`, `Especialidade`, `Slot`, `AgendaProfissional`, `AgendaPaciente`, `Consulta`, `HorarioAtendimento`, `Bloqueio` e `PoliticaDeCancelamento`.

A `AgendaProfissional` concentra a avaliação da disponibilidade do profissional, enquanto `AgendaPaciente` concentra as regras de conflito e limite de reservas do paciente. `Slot` encapsula a validação de grade e sobreposição temporal, `PoliticaDeCancelamento` isola prazos por ator e especialidade e `Consulta` controla as transições válidas de seu estado.

As regras de domínio são independentes de HTTP, banco de dados e serviços de notificação.

### 3.4. Infraestrutura

Contém as implementações concretas necessárias para persistência e integração com serviços externos.

Inclui:

- Repositórios e `SQLiteUnidadeDeTrabalho` que utilizam SQLite.
- Adaptadores de notificação (`NotificadorFake`).
- Adaptador de autenticação universitária (`ServicoAutenticacaoFake`).
- Processamento das notificações pendentes.

Esses componentes implementam os contratos utilizados pela aplicação, mantendo os detalhes tecnológicos fora das regras de negócio.

## 4. Dependências e interfaces

### 4.1. Direção das dependências

As dependências do código devem preservar a independência do domínio.

A apresentação utiliza os casos de uso. Os casos de uso utilizam as entidades de domínio e dependem de interfaces para acessar recursos externos.

Os adaptadores da infraestrutura implementam essas interfaces.

Assim, a dependência do caso de uso em relação à persistência não é estabelecida com a implementação concreta do SQLite, mas com o contrato de repositório.

A configuração da aplicação é responsável por criar os componentes e associar cada interface à implementação correspondente.

### 4.2. Interfaces principais

| Interface | Responsabilidade |
|---|---|
| `ConsultaRepositorio` | Persistir e recuperar consultas por ID, por profissional ou por paciente (incluindo listagens de histórico e consultas ativas), sem realizar validações de regra de negócio. |
| `AgendaRepositorio` | Persistir e recuperar períodos de atendimento e bloqueios das agendas. |
| `PacienteRepositorio` | Recuperar os dados essenciais de pacientes. |
| `ProfissionalRepositorio` | Recuperar os dados essenciais de profissionais e suas especialidades (incluindo filtro por especialidade). |
| `NotificacaoPendenteRepositorio` | Registrar, consultar e atualizar notificações pendentes de envio. |
| `UnidadeDeTrabalho` | Coordenar as operações de persistência de múltiplos repositórios que devem ocorrer na mesma transação. |
| `Notificador` | Estabelecer o contrato para envio de mensagens, independentemente do canal. |
| `ServicoAutenticacao` | Estabelecer o contrato de identificação de usuários e seus papéis pelo serviço de autenticação universitário. |

Essas interfaces permitem substituir implementações concretas sem alterar os casos de uso e as regras centrais do sistema.

## 5. Comunicação

### 5.1. Comunicação com os clientes

O sistema utilizará uma API REST sobre HTTP/JSON, permitindo a comunicação com interfaces web e outros clientes.

Entre os endpoints previstos estão:

| Método | Endpoint | Operação |
|---|---|---|
| `GET` | `/disponibilidade` | Consultar horários disponíveis (filtrando por profissional ou especialidade e data). |
| `PUT` | `/profissionais/{id}/horarios-atendimento` | Configurar ou atualizar períodos de atendimento do profissional. |
| `POST` | `/profissionais/{id}/bloqueios` | Registrar bloqueio datado na agenda. |
| `POST` | `/consultas` | Agendar consulta. |
| `GET` | `/consultas` | Listar consultas de um paciente ou da agenda de um profissional. |
| `GET` | `/consultas/{id}` | Consultar detalhes de uma consulta. |
| `PATCH` | `/consultas/{id}` | Reagendar uma consulta. |
| `DELETE` | `/consultas/{id}` | Cancelar uma consulta (alterando seu estado para `CANCELADA` e liberando o slot). |
| `POST` | `/consultas/{id}/confirmacao` | Confirmar uma consulta. |

A consulta de disponibilidade receberá a data desejada e o filtro (`profissional_id` ou `especialidade`) como parâmetros de consulta.

As respostas utilizarão códigos HTTP adequados, incluindo `201 Created` para agendamentos realizados, `200 OK` / `204 No Content` para cancelamentos e consultas, `400 Bad Request` para entradas inválidas, `403 Forbidden` para operações não autorizadas, `404 Not Found` para recursos inexistentes e `409 Conflict` para conflitos de agendamento.

A documentação detalhada das operações e de seus formatos de entrada e saída será mantida junto à implementação da API.

### 5.2. Comunicação interna

Os módulos se comunicam por chamadas de métodos e interfaces dentro da aplicação.

Não será utilizada comunicação HTTP entre os módulos, já que todos pertencem ao mesmo monólito.

Essa escolha evita latência de rede e infraestrutura adicional para operações internas.

### 5.3. Comunicação assíncrona

O envio de notificações será separado do processamento dos agendamentos.

O caso de uso registra a consulta e uma notificação pendente na mesma transação. O envio é executado posteriormente por um componente de processamento de notificações.

Esse mecanismo funciona como uma **fila de notificações**, implementada como uma tabela de pendências no próprio banco de dados (padrão *Transactional Outbox*), sem necessidade de um broker de mensagens externo. Cada pendência é uma mensagem na fila, com registro de envio, tentativas e possibilidade de reenvio. Por exigir atomicidade local, as implementações de `ConsultaRepositorio` e `NotificacaoPendenteRepositorio` precisam operar sobre o mesmo banco transacional. Em vez de fundir essas duas interfaces em um único repositório — o que violaria o SRP e acoplaria o módulo de consultas ao ciclo de vida das notificações —, as portas permanecem separadas e o compartilhamento da conexão/transação é coordenado na infraestrutura pela `SQLiteUnidadeDeTrabalho`.

## 6. Persistência e consistência

### 6.1. Banco de dados

O protótipo utilizará SQLite para armazenar pacientes, profissionais, agendas, consultas, bloqueios e notificações pendentes.

O acesso aos dados ocorrerá por repositórios, evitando dependências diretas entre os casos de uso e a tecnologia de persistência.

### 6.2. Controle de conflitos

As consultas possuem duração fixa de 30 minutos e utilizam uma grade alinhada a `:00` e `:30`, comum a todos os profissionais e pacientes (RN02). Os períodos de atendimento também devem respeitar essa grade.

Antes de realizar o agendamento, o domínio verifica:

1. A validade e o alinhamento do `Slot` solicitado.
2. Na `AgendaProfissional`: a existência de um `HorarioAtendimento` válido, a ausência de `Bloqueio` datado e a ausência de outra consulta ativa do profissional no horário.
3. Na `AgendaPaciente`: a ausência de outra consulta ativa do paciente no mesmo horário e o respeito ao limite máximo de consultas ativas permitidas.

Consideram-se ativas as consultas com estado `AGENDADA` ou `CONFIRMADA`.

Como os slots são discretizados e alinhados à grade (RN02), não ocorre sobreposição parcial entre horários, bastando impedir duplicidade de horário inicial entre consultas ativas. Para isso, o banco utilizará restrições de unicidade condicionadas às consultas ativas para os pares:

- `(profissional_id, inicio)`
- `(paciente_id, inicio)`

A verificação prévia de disponibilidade não é suficiente para garantir a consistência sob concorrência.

No SQLite, as operações de reserva utilizarão transações de escrita iniciadas antes das verificações de disponibilidade, com bloqueio de escrita antecipado (`BEGIN IMMEDIATE`). A validação dos bloqueios, dos limites do paciente e a gravação da consulta ocorrerão dentro da mesma transação.

As operações que alteram a disponibilidade, como criação de bloqueios e alteração de horários de atendimento, seguirão o mesmo controle transacional.

Caso a reserva não possa ser concluída, a transação será revertida e a operação retornará um erro, sem produzir agendamento parcial.

### 6.3. Reagendamento

O reagendamento será tratado como uma operação transacional.

A disponibilidade do novo horário será verificada antes da confirmação da mudança. A liberação do horário anterior e a ocupação do novo serão realizadas na mesma transação.

Se ocorrer conflito ou falha, a transação será revertida, preservando a consulta original.

### 6.4. Unidade de trabalho

A interface `UnidadeDeTrabalho` coordenará as operações que precisam ser persistidas atomicamente entre diferentes repositórios.

No agendamento, isso inclui o registro da consulta via `ConsultaRepositorio` e o registro da notificação pendente via `NotificacaoPendenteRepositorio`. Manter os contratos separados preserva a coesão de cada módulo, enquanto a implementação concreta (`SQLiteUnidadeDeTrabalho`) garante que ambos compartilhem a mesma conexão e transação no banco de dados.

Todas as operações da unidade de trabalho utilizarão a mesma transação, permitindo confirmar ou reverter as alterações em conjunto.

## 7. Notificações

### 7.1. Registro na fila de notificações

Após validar um agendamento, a aplicação coloca uma notificação pendente na fila de notificações, juntamente com a consulta.

Esse registro ocorrerá na mesma transação, garantindo que um agendamento persistido tenha sua notificação correspondente registrada.

A operação de agendamento não dependerá do sucesso do envio externo.

### 7.2. Processamento

Um componente separado será responsável por:

1. Consultar as notificações pendentes na fila.
2. Realizar o envio por meio da interface `Notificador`.
3. Registrar o resultado da tentativa.
4. Manter notificações com falha disponíveis para reenvio.

As notificações terão estados como `PENDENTE`, `ENVIADA` e `FALHA`, além de informações sobre tentativas de envio.

O processamento poderá ser executado por um processo separado da API, utilizando a mesma base de dados.

### 7.3. Substituição do canal

O contrato `Notificador` será implementado inicialmente por `NotificadorFake`.

A substituição por um canal real, como e-mail ou WhatsApp, exigirá a implementação de um novo adaptador e sua configuração na aplicação.

As regras de agendamento e o processamento das pendências permanecerão independentes do canal utilizado.

## 8. Autenticação e segurança

O sistema utilizará o serviço de autenticação universitário para identificar profissionais e estagiários.

A integração será isolada pela interface `ServicoAutenticacao`, implementada no protótipo por `ServicoAutenticacaoFake`.

As permissões serão verificadas conforme o papel do usuário (`Paciente` ou `Profissional / Estagiário`), separando autenticação de autorização.

Os dados pessoais utilizados no agendamento serão limitados às informações necessárias para o funcionamento do sistema, considerando as exigências da LGPD.

O adaptador simulado será utilizado apenas no ambiente de desenvolvimento e demonstração, não sendo um mecanismo de autenticação adequado para produção.

## 9. Organização do código

A implementação seguirá uma estrutura modular, com separação entre apresentação, aplicação, domínio e infraestrutura.

Uma organização de referência é:

```text
src/
  clinica/
    main.py
    api/
      controllers/
    modulos/
      agenda/
        dominio/
        portas/
      consultas/
        dominio/
        aplicacao/
        portas/
      cadastros/
        dominio/
        portas/
      notificacoes/
        aplicacao/
        portas/
      autenticacao/
        portas/
    infraestrutura/
      persistencia/
      notificacoes/
      autenticacao/

tests/
  dominio/
  aplicacao/
  integracao/
```

As interfaces ficarão próximas dos componentes que as utilizam. As implementações concretas serão mantidas na infraestrutura.

A composição das dependências será realizada na inicialização da aplicação.

Essa estrutura preserva a separação de responsabilidades e permite evoluir os módulos sem exigir sua implantação independente.

## 10. Relação com os ASRs

| ASR | Decisões arquiteturais relacionadas |
|---|---|
| **ASR-01 - Consistência** | Slots discretizados (`Slot`), validação de disponibilidade no domínio (`AgendaProfissional` e `AgendaPaciente`), restrições de unicidade e transações via `UnidadeDeTrabalho`. |
| **ASR-02 - Modificabilidade** | Interfaces `Notificador`, `ServicoAutenticacao` e repositórios, além de `PoliticaDeCancelamento` e `Slot` desacoplados, separando regras de negócio e infraestrutura. |
| **ASR-03 - Resiliência** | Registro transacional de notificações pendentes pela `UnidadeDeTrabalho` (mantendo repositórios segregados), envio desacoplado e mecanismo de reenvio. |

A arquitetura introduz algumas abstrações adicionais, mas mantém a aplicação em um único processo principal, reduzindo os custos de desenvolvimento e operação.

As alternativas arquiteturais e os custos das decisões serão detalhados nos documentos de trade-offs e ADRs.

## 11. Evolução da arquitetura

A separação entre domínio e infraestrutura permite substituir tecnologias e evoluir regras centrais com impacto localizado.

1. **Troca do mecanismo de persistência (SQLite -> PostgreSQL):** serão modificados os adaptadores de repositório, a implementação de `UnidadeDeTrabalho`, a configuração de conexão e o DDL do schema, mantendo domínio e casos de uso inalterados.
2. **Substituição do canal de notificações (E-mail/Fake -> WhatsApp/SMS):** será necessário implementar outro adaptador de `Notificador` e atualizar a composição de dependências na inicialização, preservando `AgendarConsulta` e o processador de pendências.
3. **Evolução para slots dinâmicos desalinhados `(inicio, fim)`:** caso a regra de negócio deixe de usar slots fixos alinhados de 30 minutos e passe a aceitar intervalos arbitrários (ex.: `10:15–10:45`), a mudança no domínio ficará contida em `Slot`, `AgendaProfissional` e `AgendaPaciente` (substituindo a checagem por grade fixa pela verificação de interseção `inicio_a < fim_b e fim_a > inicio_b`), sem alterar o caso de uso `AgendarConsulta`. Na persistência, entretanto, o índice único parcial por `(profissional_id, inicio)` e `(paciente_id, inicio)` deixa de bastar para evitar sobreposição: no SQLite seria necessário consultar intervalos conflitantes sob transação `BEGIN IMMEDIATE`, e em uma eventual migração para PostgreSQL seria possível usar restrições de exclusão temporal (`EXCLUDE USING gist` sobre `tsrange`).

A API REST também permite adicionar novos clientes (como aplicativo mobile) sem modificar diretamente os casos de uso.

Essas possibilidades de evolução decorrem da organização modular e dos contratos estabelecidos entre os componentes.