# Claude Certification:

## Domains: Total of five domains.

- Agentic Architecture & Orchestration 27%
- Tool Design & MCP Integration 18%
- Claude Code Configuration & Workflows 20%
- Prompt Engineering & Structured Output 20%
- Context Management & Reliability 15%

> Conhecimentos técnicos do Claude - Claude API, Agent SDK, Claude Code e Model Context Protocol - MCP.

### As questões são baseadas em cenários (No total de 6 contextos reais de Arquitetura).

1. **Agente de Suporte ao Cliente:** Agente via Agent SDK com ferramentas MCP personalizadas e lógica de escalonamento (meta de 80%+ de resolução no primeiro contato).
2. **Geração de Código com Claude Code:** Automação de refatoração, debug e fluxos dev com comandos slash, `CLAUDE.md` e modo de planejamento (*plan mode*).
3. **Sistema de Pesquisa Multi-Agente:** Arquitetura coordenador-subagente para busca web, análise de documentos e geração de relatórios com citações.
4. **Produtividade do Desenvolvedor:** Exploração de bases de código legadas usando ferramentas nativas (`Read`, `Write`, `Bash`, `Grep`, `Glob`) e MCP.
5. **Claude Code em CI/CD:** Integração em pipelines de CI/CD para revisões automáticas de PRs e geração de casos de teste sem bloquear builds.
6. **Extração de Dados Estruturados:** Extração de documentos não estruturados, validação estrita com JSON Schema e tratamento de exceções.

# Mindmap:
![Claude Domains](/Claude.Domain.png)

# Detalhamento dos domínios (Step-by-Step):

## Agentic Architecture & Orchestration 27%
* **Agentic Loop:** Ciclo de vida dos agentes via `stop_reason` (`tool_use` vs `end_turn`), encadeamento do histórico de conversas e eliminação de anti-padrões (como tentar identificar fim de ciclo via parsing de texto natural).

* **Invocação e Passagem de Contexto:** Uso da ferramenta `Task` (`allowedTools`), passagem explícita de descobertas no prompt do subagente e execução em paralelo de múltiplos subagentes em um único turno.
* **Workflows e Hand-off:** Bloqueio programático pré-requisito (ex: proibir `process_refund` antes de verificar o ID do cliente) versus instruções probabilísticas no prompt; protocolos de transferência para humanos.
* **Hooks do Agent SDK:** Uso de `PostToolUse` para normalização de dados (fusos horários, formatos) e interceptação de chamadas para garantir cumprimento rígido de regras de negócio.
* **Estratégias de Decomposição:** Encadeamento de prompts (*prompt chaining*) para etapas sequenciais previsíveis versus decomposição dinâmica para investigações abertas.
* **Sessões e Ramificação:** Uso de `--resume`, `fork_session` para testar abordagens divergentes e decisão entre retomar sessão ou iniciar do zero injetando resumos estruturados.

## Tool Design & MCP Integration 18%
* **Interface de Ferramentas:** Escrita de descrições detalhadas com exemplos de entradas/saídas e fronteiras claras para evitar ambiguidades na escolha do modelo.
* **Tratamento de Erros Estruturados no MCP:** Uso do padrão `isError`, respostas de erro categorizadas (`transient`, `validation`, `business`, `permission`) e inclusão da flag `isRetryable`.
* **Escopo de Ferramentas:** Limitação do número de ferramentas por agente (4-5 por papel) para evitar degradação de desempenho e configuração de `tool_choice` (`auto`, `any`, ou escolha forçada de ferramenta específica).
* **Servidores MCP:** Configuração no nível do projeto (`.mcp.json`) vs. usuário (`~/.claude.json`), uso de variáveis de ambiente para credenciais (`${GITHUB_TOKEN}`) e exposição de catálogos via MCP *resources*.
* **Ferramentas Nativas:** Aplicação tática de `Grep` (busca de conteúdo de código), `Glob` (padrões de caminho de arquivo), `Read`/`Write` e uso de `Edit` (com fallback para Read + Write em correspondências ambíguas).

## Claude Code Configuration & Workflows 20%
* **Hierarquia do** **CLAUDE.md** **:** Organização por nível de usuário, projeto e subdiretórios; modularização com sintaxe `@import` e diretório `.claude/rules/`.
* **Comandos Slash e Skills:** Criação de comandos do projeto (`.claude/commands/`) e skills (`.claude/skills/` com `SKILL.md`), utilizando opções de frontmatter como `context: fork` para isolar execuções verbosas.
* **Regras por Caminho (** **Path-Specific Rules** **):** Regras ativadas por padrões glob em YAML (`paths: ["terraform/**/*"]`) para carregar contexto dinamicamente apenas ao editar arquivos correspondentes.
* **Modo de Planejamento (** **Plan Mode** **) vs. Execução Direta:** Uso do *plan mode* para decisões arquiteturais e mudanças multi-arquivos, utilizando o subagente *Explore* para evitar exaustão da janela de contexto.
* **Refinamento Iterativo:** Utilização de exemplos concretos de entrada/saída, desenvolvimento guiado por testes (fornecer logs de falha ao Claude) e padrão de entrevista para detalhar requisitos.
* **Claude Code em CI/CD:** Execução não interativa com `-p`, saída estruturada em JSON com `--output-format json` e `--json-schema`, e isolamento de instância para revisão de código sem viés da geração.

## Prompt Engineering & Structured Output 20%
* **Redução de Falsos Positivos:** Definição de critérios explícitos de severidade e exemplos práticos, evitando termos vagos como "seja conservador" ou "apenas alta confiança".
* **Few-Shot Prompting:** Criação de 2 a 4 exemplos focados demonstrando o raciocínio correto para casos ambíguos e formatos esperados.
* **Saída Estruturada Rígida:** Uso de `tool_use` combinado com JSON Schema, configuração de campos opcionais/nulos para evitar alucinações de dados e enums extensíveis (`other` \+ campo de detalhes).
* **Loops de Validação e Autocorreção:** Reenvio da mensagem com o erro específico de validação para correção do modelo, reconhecendo os limites quando o dado não existe no documento original.
* **Processamento em Lote (** **Message Batches API** **):** Economia de 50% de custo para cargas assíncronas (janela de 24h), rastreamento com `custom_id` e adaptação para a ausência de chamadas interativas de ferramentas multi-turnos.
* **Arquiteturas de Revisão Multi-Instância:** Uso de uma segunda instância independente do Claude (sem o contexto do raciocínio de geração) para realizar revisões de código de alta precisão.

## Context Management & Reliability 15%
* **Preservação de Informações Críticas:** Manutenção de um bloco fixo de fatos ("case facts") fora do histórico resumido, mitigação do efeito *lost in the middle* e poda de retornos extensos de ferramentas.
* **Padrões de Escalonamento:** Gatilhos objetivos de transferência humana (solicitação explícita do cliente, lacunas/ambiguidades de política ou incapacidade de progredir).
* **Propagação de Erros:** Reporte estruturado do erro ao agente coordenador (tipo de falha, o que foi tentado e alternativas), diferenciando falhas de conexão de resultados vazios legítimos.
* **Bases de Código Extensas:** Uso de arquivos *scratchpad* para salvar descobertas, subagentes dedicados para buscas específicas, comando `/compact` e salvamento de estado (*manifests*) para crash recovery.
* **Calibração de Confiança e Revisão Humana:** Validação por amostragem aleatória estratificada e calibração de limiares de confiança por conjuntos de validação rotulados.
* **Proveniência de Dados e Incerteza:** Mapeamento estruturado de afirmação-fonte, preservação de datas de publicação/coleta para evitar contradições temporais falsas e destaque de divergências entre fontes.





