# Modelo de Domínio, Responsabilidades e Princípios de Design

## 1. Visão geral

O sistema de agendamento de consultas será organizado de modo a separar as regras de negócio da coordenação dos casos de uso e das tecnologias de infraestrutura. Este documento consolida o modelo de domínio (conceitos, atributos, estados e relacionamentos) e a distribuição de responsabilidades entre camadas e componentes.

A distribuição de responsabilidades busca garantir:

- **Alta coesão:** cada classe ou módulo concentra responsabilidades relacionadas.
- **Baixo acoplamento:** os componentes dependem o mínimo possível de detalhes de outros componentes.
- **Modificabilidade:** alterações em tecnologias externas ou em regras isoladas (como políticas de cancelamento ou formato de slots) não devem se espalhar pelo sistema.
- **Testabilidade:** regras e casos de uso podem ser testados independentemente do banco de dados ou de serviços externos.

Para isso, a arquitetura adotada consiste em um monólito modular, com separação entre domínio, aplicação, apresentação e infraestrutura, utilizando portas e adaptadores nas integrações.

## 2. Distribuição de responsabilidades

### 2.1. Camada de domínio

Contém os conceitos, estados, relacionamentos e regras essenciais do sistema, independentemente das tecnologias utilizadas.

| Classe / Conceito | Atributos principais | Responsabilidade |
|---|---|---|
| `Paciente` | `id`, `nome`, `email` | Representar o paciente atendido na clínica e suas informações essenciais para identificação e notificação. |
| `Profissional` | `id`, `nome`, `especialidade` | Representar o profissional de saúde ou estagiário responsável pelos atendimentos e sua área de atuação. |
| `Especialidade` | `id`, `nome` | Representar a área de atendimento da clínica (ex.: Clínica Médica, Pediatria, Odontologia), permitindo consultar profissionais por área e aplicar políticas específicas. |
| `Slot` (`PeriodoConsulta`) | `inicio`, `fim` | Objeto de valor que representa o período `[inicio, fim)` de uma consulta, encapsulando o alinhamento à grade de 30 minutos (início em `:00` ou `:30`) e o cálculo de sobreposição de horários (isolando a lógica temporal caso o modelo evolua para slots dinâmicos). |
| `AgendaProfissional` | `profissional_id`, `horarios_atendimento`, `bloqueios`, `slots_ocupados` | Avaliar a disponibilidade de horários **do profissional**, considerando seus períodos de atendimento, bloqueios datados e os `Slot`s já ocupados por consultas ativas. Recebe os slots, e não objetos `Consulta`, para que o módulo `agenda` não dependa do módulo `consultas`. |
| `AgendaPaciente` | `paciente_id`, `consultas` | Avaliar a disponibilidade **do paciente** no domínio, impedindo sobreposição de consultas ativas em quaisquer profissionais (RN03) e validando o limite máximo de consultas ativas permitidas (RN08). |
| `Consulta` | `id`, `paciente_id`, `profissional_id`, `especialidade_id`, `slot` (`inicio`, `fim`), `status` | Representar o agendamento entre paciente e profissional, mantendo seus participantes, a especialidade (copiada do profissional no agendamento, para o limite por especialidade da RN08), período e estado, além de controlar as transições válidas. |
| `HorarioAtendimento` | `dia_semana`, `hora_inicio`, `hora_fim` | Representar os períodos **semanais recorrentes** de atendimento configurados individualmente para cada profissional (ex.: terças-feiras, das 08:00 às 12:00). |
| `Bloqueio` | `id`, `inicio`, `fim`, `motivo` | Representar **exceções datadas** no calendário em que a agenda fica indisponível (ex.: férias, feriados, reuniões), diferenciando-se de `HorarioAtendimento` por tratar ocorrências pontuais em datas específicas em vez da grade semanal recorrente. |
| `PoliticaDeCancelamento` | — (estratégia) | Encapsular a regra de antecedência mínima para cancelamento de consultas (24 horas padrão; 72 horas para Odontologia/Dentista; isenção de trava quando o cancelamento parte do profissional). |

#### Estados possíveis de `Consulta`

- `AGENDADA`: agendamento registrado e ativo (ocupa o slot), aguardando confirmação do paciente.
- `CONFIRMADA`: agendamento ativo e confirmado pelo paciente (ocupa o slot).
- `CANCELADA`: agendamento cancelado; libera o slot para novos agendamentos.
- `REALIZADA`: atendimento concluído.
- `FALTOU`: paciente não compareceu ao atendimento.

#### Relacionamentos principais do domínio

- Um `Paciente` possui uma `AgendaPaciente` e pode possuir zero ou várias `Consultas`.
- Um `Profissional` está associado a uma `Especialidade`, possui uma `AgendaProfissional` e pode realizar zero ou várias `Consultas`.
- Cada `Consulta` vincula exatamente um `Paciente`, um `Profissional` e um `Slot` (`PeriodoConsulta`).
- Uma `AgendaProfissional` agrega os registros recorrentes de `HorarioAtendimento` do profissional, os `Slot`s ocupados por suas consultas ativas e os `Bloqueio`s datados aplicáveis (individuais ou coletivos, como feriados).

Tanto `AgendaProfissional` quanto `AgendaPaciente` avaliam regras inteiramente em memória a partir dos dados fornecidos a elas, sem consultar diretamente o banco de dados. Retirar a checagem de disponibilidade e de limites do paciente de dentro do caso de uso `AgendarConsulta` e colocá-la em `AgendaPaciente` evita acoplamento da camada de aplicação às regras de conflito.

### 2.2. Camada de aplicação

Coordena os casos de uso e a interação entre as entidades/serviços do domínio e as portas de infraestrutura necessárias.

| Caso de uso | Requisito(s) | Responsabilidade |
|---|---|---|
| `ConfigurarHorarioAtendimento` | RF01 | Coordenar o cadastro ou atualização dos períodos semanais de atendimento de um profissional. |
| `ConsultarDisponibilidade` | RF02 | Obter os dados necessários e listar os slots disponíveis de um profissional específico ou filtrados por uma especialidade. |
| `AgendarConsulta` | RF03, RF06, RF08 | Coordenar a validação do `Slot`, a verificação de disponibilidade em `AgendaProfissional` e `AgendaPaciente`, a criação da `Consulta`, sua persistência atômica e o registro da notificação pendente. |
| `CancelarConsulta` | RF04, RF08 | Obter a consulta, validar a `PoliticaDeCancelamento` adequada ao ator e à especialidade, alterar o estado da consulta para `CANCELADA` e registrar a notificação pendente. |
| `ReagendarConsulta` | RF05, RF06, RF08 | Coordenar a alteração de horário, liberando o slot original e reservando o novo na mesma transação, preservando a consulta original em caso de conflito ou falha. |
| `ConfirmarConsulta` | RF07 | Registrar a confirmação do paciente em uma consulta `AGENDADA`, alterando seu estado para `CONFIRMADA`. |
| `RegistrarBloqueio` | RF09 | Registrar períodos datados de indisponibilidade (férias, feriados, reuniões) na agenda do profissional ou de forma coletiva. |
| `ListarConsultas` | RF10 | Consultar e retornar o histórico de consultas de um paciente ou a lista de agendamentos de um profissional. |

O protótipo priorizará `AgendarConsulta` e `ConsultarDisponibilidade`. Os demais casos de uso permanecem especificados para evolução incremental.

Os casos de uso não devem conter SQL, detalhes de HTTP ou lógica específica de envio de notificações.

### 2.3. Apresentação e infraestrutura

**Apresentação**

O `AgendamentoController` recebe requisições da API REST, valida o formato dos dados de entrada, obtém o usuário autenticado (quando aplicável via `ServicoAutenticacao`) e encaminha as operações aos casos de uso correspondentes.

Também é responsável por transformar os resultados e erros da aplicação em respostas HTTP adequadas.

Não deve implementar regras de disponibilidade ou cancelamento, nem acessar diretamente o banco de dados.

**Portas e adaptadores**

| Componente | Tipo | Responsabilidade |
|---|---|---|
| `ConsultaRepositorio` | Porta (Interface) | Definir operações de persistência e recuperação de consultas (por ID, por profissional ou por paciente), sem executar regras de negócio. |
| `AgendaRepositorio` | Porta (Interface) | Definir operações de persistência e leitura de horários de atendimento e bloqueios. |
| `PacienteRepositorio` | Porta (Interface) | Definir operações de leitura dos dados essenciais do paciente para correlação com agendas e consultas. |
| `ProfissionalRepositorio` | Porta (Interface) | Definir operações de leitura de profissionais e suas especialidades (incluindo consulta por especialidade). |
| `NotificacaoPendenteRepositorio` | Porta (Interface) | Definir operações para registrar, consultar e atualizar o estado de notificações pendentes. |
| `UnidadeDeTrabalho` | Porta (Interface) | Coordenar uma transação única compartilhada pelos repositórios cujas gravações precisam ocorrer atomicamente. |
| `Notificador` | Porta (Interface) | Definir o contrato para envio de notificações, independentemente do canal utilizado. |
| `ServicoAutenticacao` | Porta (Interface) | Definir o contrato de identificação do usuário e seu papel (incluindo autenticação universitária de profissionais e estagiários). |
| `SQLiteConsultaRepositorio` | Adaptador (Infraestrutura) | Implementar `ConsultaRepositorio` utilizando SQLite. |
| `SQLiteAgendaRepositorio` | Adaptador (Infraestrutura) | Implementar `AgendaRepositorio` utilizando SQLite. |
| `SQLitePacienteRepositorio` | Adaptador (Infraestrutura) | Implementar `PacienteRepositorio` utilizando SQLite. |
| `SQLiteProfissionalRepositorio` | Adaptador (Infraestrutura) | Implementar `ProfissionalRepositorio` utilizando SQLite. |
| `SQLiteNotificacaoPendenteRepositorio` | Adaptador (Infraestrutura) | Implementar `NotificacaoPendenteRepositorio` utilizando SQLite sobre a conexão da unidade de trabalho. |
| `SQLiteUnidadeDeTrabalho` | Adaptador (Infraestrutura) | Implementar `UnidadeDeTrabalho` gerenciando a conexão e a transação (`BEGIN IMMEDIATE`, commit e rollback) no SQLite. |
| `NotificadorFake` | Adaptador (Infraestrutura) | Simular o envio de notificações durante o desenvolvimento e os testes. |
| `ServicoAutenticacaoFake` | Adaptador (Infraestrutura) | Simular o serviço de autenticação da universidade durante o protótipo. |

As interfaces representam contratos utilizados pela aplicação. As implementações concretas pertencem à infraestrutura.

Um componente de processamento de notificações consulta as pendências via `NotificacaoPendenteRepositorio` e utiliza a interface `Notificador` para realizar os envios e registrar eventuais falhas para reenvio.

## 3. Aplicação dos princípios GRASP

### 3.1. Information Expert

**Aplicação: `AgendaProfissional`, `AgendaPaciente`, `Slot` e `Consulta`**

- A responsabilidade de avaliar a disponibilidade **do profissional** é atribuída à `AgendaProfissional`, pois ela conhece seus horários de atendimento, bloqueios e slots ocupados.
- A responsabilidade de avaliar conflitos e limites **do paciente** é atribuída à `AgendaPaciente`, pois ela reúne as consultas ativas do paciente e as regras de sobreposição e limite diário/por especialidade.
- O objeto de valor `Slot` concentra o conhecimento sobre alinhamento à grade e interseção temporal.
- A entidade `Consulta` concentra a validação de suas transições de estado.

Isso evita que regras de disponibilidade e restrições de agenda sejam espalhadas entre controllers, repositórios e casos de uso. Entretanto, a verificação em memória não substitui o controle transacional necessário para impedir reservas concorrentes.

### 3.2. Controller

**Aplicação: `AgendamentoController`**

O controller recebe as solicitações externas HTTP e delega sua execução aos casos de uso apropriados.

Por exemplo:

`AgendamentoController -> AgendarConsulta`

Assim, a camada de apresentação não concentra regras de negócio, facilitando a inclusão futura de outras interfaces (como aplicativo mobile ou interface web).

### 3.3. Creator

**Aplicação: criação de `Consulta` no fluxo de agendamento**

O caso de uso `AgendarConsulta` reúne os dados necessários e coordena a criação da consulta após a aprovação de `Slot`, `AgendaProfissional` e `AgendaPaciente`.

A instanciação ocorre por meio do construtor ou método de fábrica da própria entidade `Consulta` (ou delegada pela agenda), iniciando no estado `AGENDADA`, sem necessidade de uma classe fábrica separada para essa operação.

### 3.4. Low Coupling e High Cohesion

As responsabilidades são separadas conforme seus motivos de mudança:

- `AgendaProfissional` concentra disponibilidade do profissional.
- `AgendaPaciente` concentra conflitos e limites do paciente.
- `Slot` isola o modelo temporal dos horários.
- `PoliticaDeCancelamento` isola prazos de cancelamento por perfil/especialidade.
- `Consulta` concentra o estado e o comportamento do agendamento.
- Os casos de uso apenas orquestram fluxos entre domínio e portas.
- Os repositórios implementam o acesso aos dados de forma segregada por recurso.
- Os adaptadores externos encapsulam comunicação e autenticação.

Essa divisão reduz dependências desnecessárias e mantém alterações localizadas.

### 3.5. Protected Variations e Indirection

**Aplicação: `Notificador`, `ServicoAutenticacao`, `PoliticaDeCancelamento`, `Slot` e interfaces de repositório**

O sistema não depende diretamente de um provedor de e-mail, do serviço real da universidade ou do SQLite. Além disso, variações previstas de regras de negócio — como prazos distintos de cancelamento (`PoliticaDeCancelamento`) ou evolução de grade fixa para horários dinâmicos (`Slot`) — ficam protegidas atrás de contratos e objetos de domínio bem definidos.

Substituir `NotificadorFake` por `EmailNotificador` ou `WhatsAppNotificador` exige apenas um novo adaptador e ajuste na composição das dependências.

### 3.6. Pure Fabrication

**Aplicação: repositórios, `UnidadeDeTrabalho` e casos de uso**

Componentes como repositórios e `UnidadeDeTrabalho` não representam entidades naturais do domínio da clínica, mas são introduzidos para coordenar persistência e transações sem contaminar entidades de domínio com detalhes técnicos de SQL.

## 4. Aplicação dos princípios SOLID

| Princípio | Aplicação proposta |
|---|---|
| **SRP** | Separar regras de disponibilidade (`AgendaProfissional`, `AgendaPaciente`), regra temporal (`Slot`), política de cancelamento (`PoliticaDeCancelamento`), coordenação de fluxo (casos de uso) e persistência (repositórios distintos para consultas, agendas, pacientes, profissionais e notificações pendentes). |
| **OCP** | Permitir adicionar novos canais de notificação implementando `Notificador` e novas regras de antecedência implementando `PoliticaDeCancelamento` (como 24h padrão e 72h para Odontologia/Dentista), sem modificar `AgendarConsulta` ou `CancelarConsulta`. |
| **LSP** | Garantir que diferentes implementações de `Notificador`, `PoliticaDeCancelamento` ou dos repositórios possam substituir umas às outras sem violar o comportamento esperado pelos contratos. |
| **ISP** | Manter interfaces enxutas e específicas para seus clientes (`ConsultaRepositorio` separado de `NotificacaoPendenteRepositorio`; `Notificador` focado em envio; `ServicoAutenticacao` focado em identificação). |
| **DIP** | Fazer com que os casos de uso dependam de abstrações (portas), e não diretamente de implementações de SQLite ou serviços externos. |

A aplicação desses princípios é mantida proporcional às necessidades do sistema, evitando abstrações sem variação ou responsabilidade clara.

## 5. Coesão e acoplamento

A organização proposta mantém responsabilidades relacionadas dentro de um mesmo componente e reduz dependências entre partes do sistema que possuem motivos diferentes para mudar.

### 5.1. Coesão

- **Domínio:** `AgendaProfissional`, `AgendaPaciente`, `Slot`, `Consulta`, `HorarioAtendimento`, `Bloqueio` e `PoliticaDeCancelamento` concentram regras de negócio puras, sem SQL ou HTTP.
- **Aplicação:** os casos de uso coordenam operações específicas, delegando validações de negócio às classes de domínio.
- **Apresentação:** controllers concentram tradução HTTP/JSON e validação estrutural de entrada.
- **Infraestrutura:** repositórios, unidade de trabalho e adaptadores concentram detalhes de SQLite e integrações externas.

### 5.2. Acoplamento

O acoplamento é reduzido pela inversão de dependências e pelo isolamento das regras de negócio:

- `AgendarConsulta` depende das portas de repositório e de `UnidadeDeTrabalho`, e não do SQLite.
- `AgendarConsulta` delega conflitos e limites do paciente para `AgendaPaciente`, evitando que o caso de uso precise ser alterado caso a regra de conflito mude (ex.: slots dinâmicos).
- O processamento de notificações depende apenas de `NotificacaoPendenteRepositorio` e `Notificador`.
- `ConsultaRepositorio` e `NotificacaoPendenteRepositorio` permanecem desacoplados em suas interfaces, compartilhando a mesma transação física apenas na infraestrutura via `SQLiteUnidadeDeTrabalho`.

### 5.3. Trade-offs

Essa separação introduz interfaces, objetos de domínio adicionais (`AgendaPaciente`, `Slot`, `PoliticaDeCancelamento`) e indireção entre camadas, aumentando moderadamente o número de arquivos.

Esse custo é justificado pela necessidade de testar regras de negócio isoladamente, trocar tecnologias externas sem impacto no domínio e absorver evoluções previstas (como canais de notificação, regras de cancelamento e formato dos slots).

## 6. Fluxo de responsabilidades - Agendar consulta

O principal caso de uso seguirá conceitualmente as seguintes etapas:

1. O `AgendamentoController` recebe a solicitação HTTP, valida os parâmetros de entrada e obtém o contexto autenticado (quando aplicável via `ServicoAutenticacao`).
2. O caso de uso `AgendarConsulta` cria o `Slot` do horário solicitado, que valida a duração e o alinhamento à grade. Essa validação depende apenas do horário pedido, por isso ocorre antes de abrir a transação. Assim, um horário fora da grade é recusado sem ocupar o bloqueio de escrita do banco.
3. `AgendarConsulta` inicia a `UnidadeDeTrabalho` (abrindo a transação de escrita no banco), recupera os dados necessários por meio de `AgendaRepositorio`, `ConsultaRepositorio`, `PacienteRepositorio` e `ProfissionalRepositorio`, e o domínio valida a operação:
   - `AgendaProfissional` avalia a disponibilidade do profissional (período de atendimento em `HorarioAtendimento`, ausência de `Bloqueio` e ausência de conflito com consultas ativas).
   - `AgendaPaciente` verifica se o paciente não possui outra consulta ativa sobreposta no período e se respeita o limite de agendamentos ativos.
4. `AgendarConsulta` instancia a entidade `Consulta` no estado inicial `AGENDADA`.
5. Dentro da mesma transação coordenada por `UnidadeDeTrabalho`, `ConsultaRepositorio` persiste a consulta e `NotificacaoPendenteRepositorio` registra a notificação pendente.
6. A unidade de trabalho confirma a transação (`commit`) e a aplicação retorna os dados do agendamento.
7. Um processamento separado consulta as pendências e utiliza o `Notificador` para enviar a confirmação e tratar eventuais falhas.

A validação realizada em memória pelo domínio não é suficiente, isoladamente, para garantir a consistência em situações de concorrência.

A infraestrutura de persistência aplica transações com bloqueio de escrita antecipado (`BEGIN IMMEDIATE` no SQLite) e restrições únicas parciais condicionadas às consultas ativas (`AGENDADA` e `CONFIRMADA`) por `(profissional_id, inicio)` e `(paciente_id, inicio)`. Em caso de conflito ou falha, a transação é revertida integralmente, sem gerar consulta nem notificação pendente indevida.

## 7. Justificativas das decisões

A distribuição proposta atende diretamente aos três requisitos arquiteturalmente significativos selecionados:

- **ASR-01 - Consistência:** `Slot`, `AgendaProfissional` e `AgendaPaciente` centralizam as regras de disponibilidade e conflito no domínio, enquanto `UnidadeDeTrabalho` e os repositórios garantem atomicidade e restrições únicas transacionais no banco tanto para o profissional quanto para o paciente.
- **ASR-02 - Modificabilidade:** portas como `Notificador`, `ServicoAutenticacao` e os repositórios, somadas a `PoliticaDeCancelamento` e `Slot` no domínio, permitem evoluir integrações e regras sem reescrever os casos de uso.
- **ASR-03 - Resiliência:** o registro conjunto da consulta e da notificação pendente via `UnidadeDeTrabalho` — mantendo `ConsultaRepositorio` e `NotificacaoPendenteRepositorio` segregados pelo SRP — permite que falhas no envio posterior não invalidem o agendamento.

## 8. Considerações finais

A distribuição de responsabilidades equilibra separação de interesses, clareza de modelagem e simplicidade de implementação para o protótipo. Este documento orientará diretamente os diagramas UML e a implementação da fatia vertical.
