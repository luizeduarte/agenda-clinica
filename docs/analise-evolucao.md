# Evolução da arquitetura

A separação entre domínio e infraestrutura permite substituir tecnologias e evoluir regras centrais com impacto localizado.

## 1. **Troca do mecanismo de persistência (SQLite -> PostgreSQL)** 
Serão modificados os adaptadores de repositório, a configuração de conexão e o DDL do schema, mantendo domínio e casos de uso inalterados. 

A decisão de utilizar portas e adaptadores é essencial para minimizar os impactos dessa mudança, porém a utilizar de um monolíto ainda necessita de um novo processo de deploy completo para que a mudança seja efetivada.

## 2. **Substituição do canal de notificações (E-mail/Fake -> WhatsApp/SMS)**
Será necessário implementar outro adaptador de `Notificador` e atualizar a composição de dependências na inicialização, preservando `AgendarConsulta` e o processador de pendências.


## 3. **Evolução para slots dinâmicos desalinhados `(inicio, fim)`**
Caso a regra de negócio deixe de usar slots fixos alinhados de 30 minutos e passe a aceitar intervalos arbitrários (ex.: `10:15–10:45`), a mudança no domínio ficará contida em `Slot`, `AgendaProfissional` e `AgendaPaciente` (substituindo a checagem por grade fixa pela verificação de interseção `inicio_a < fim_b e fim_a > inicio_b`), sem alterar o caso de uso `AgendarConsulta`. Na persistência, entretanto, o índice único parcial por `(profissional_id, inicio)` e `(paciente_id, inicio)` deixa de bastar para evitar sobreposição: no SQLite seria necessário consultar intervalos conflitantes sob transação `BEGIN IMMEDIATE`, e em uma eventual migração para PostgreSQL seria possível usar restrições de exclusão temporal (`EXCLUDE USING gist` sobre `tsrange`).

A API REST também permite adicionar novos clientes (como aplicativo mobile) sem modificar diretamente os casos de uso.

Essas possibilidades de evolução decorrem da organização modular e dos contratos estabelecidos entre os componentes.