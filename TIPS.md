
# Claude Certified Architect Foundation (CCAF) — Foundations: Study Guide

## Domain 1 — Agentic Architecture (27%)

### Building block 1: the tier ladder

Everything goes through one endpoint, `POST /v1/messages`. The architecture question is always *how much control you hand to the model*:

| Tier | Who drives the loop | Use for |
|---|---|---|
| Single call | Nobody | Classification, summarization, extraction, Q&A |
| Workflow | **Your code** | Multi-step pipelines with known steps |
| Agent | **The model** | Open-ended, can't be fully specified up front |

**Default to the simplest tier that works.** Half the exam's wrong answers are "build an agent" when a workflow suffices.

### Building block 2: the "should I build an agent?" gate

Four criteria — if any is "no," drop a tier:

- **Complexity** — multi-step and hard to specify in advance?
- **Value** — does the outcome justify higher cost and latency?
- **Viability** — is Claude actually good at this task type?
- **Cost of error** — can mistakes be caught and recovered (tests, review, rollback)?

### Building block 3: four ways to build an agent — and the harness/deployment split

This is the single highest-value distinction in the whole exam. Two independent questions: *who supplies the harness* (loop + context management) and *who supplies the deployment*.

| Approach | You write | Harness | Deployment |
|---|---|---|---|
| **Manual loop** | the `while stop_reason == "tool_use"` loop | you | you |
| **Tool Runner** (`client.beta.messages.tool_runner`) | just the tool functions | SDK | **you** |
| **Managed Agents (CMA)** | agent config + tool results | Anthropic | **Anthropic** |
| **Claude Agent SDK** (`claude-agent-sdk`) | a prompt + options | SDK (Claude Code harness) | **you** |

**Only Managed Agents supplies both.** The classic trap: *Tool Runner ≠ Claude Agent SDK.* Tool Runner is a thin helper inside the regular Anthropic SDK that loops over tools **you** define — no built-in tools, no sandbox. Agent SDK is Claude Code packaged as a library, with built-in Read/Write/Edit/Bash/Grep + subagents + hooks.

Reach for **Managed Agents** when you see: persisted/versioned agent configs, a per-session container workspace, scheduled runs ("every night," cron), long-running multi-turn sessions with file mounts. Mandatory flow: **Agent created once → Session per run.** `model`/`system`/`tools` live on the *agent*, never the session. Never call `agents.create()` in the request path.

### Building block 4: the loop mechanics

```
request → stop_reason == "tool_use" → execute tools → append ALL tool_results
          in a SINGLE user message → repeat
```

Two rules that get tested directly:

- **Parallel tool use is on by default.** One assistant message can hold several `tool_use` blocks. Return every `tool_result` in **one** user message — splitting them across messages silently trains Claude to stop calling tools in parallel.
- **A failed tool still gets a `tool_result`**, with `is_error: true`. Never drop it.

`stop_reason` taxonomy: `end_turn`, `max_tokens`, `tool_use`, `pause_turn` (resumable, server tools), `refusal`.

### Building block 5: multi-agent

Fan out when **the task fans out** (research across N sources, per-file work) or when **one loop would fill its context just reading**. Orchestrator + workers, workers on a cheaper model (Haiku 4.5, or Sonnet 5 when the worker needs judgment). The win is context isolation, not speed.

---

## Domain 2 — Claude Code Configuration (20%)

Study this one as *"which mechanism for which job"* — that's the exam framing.

| Need | Mechanism |
|---|---|
| Durable project knowledge, loaded every session | `CLAUDE.md` (enterprise → user `~/.claude/` → project → subdirectory, most specific wins) |
| A repeatable multi-step procedure invoked on demand | **Skill** — `.claude/skills/<name>/SKILL.md`, frontmatter `name` + `description` |
| **Deterministic** enforcement that must not depend on the model complying | **Hook** in `settings.json` |
| An isolated context window with its own tools/model | **Subagent** — `.claude/agents/*.md` |
| External system access (Jira, GitLab, DB) | **MCP server** |
| Permissions, env vars | `settings.json` / `settings.local.json` |

The sharpest exam-relevant line: **if the requirement says "always," "before every," or "must never," it's a hook, not a CLAUDE.md instruction.** A hook is code the harness executes; CLAUDE.md is a request the model can deviate from. `PreToolUse` exiting non-zero blocks the call — that's the enforcement primitive.

Also know: skills trigger off their **`description`** field (so description quality = trigger accuracy), subagents exist primarily for **context isolation**, and CI/headless runs use `claude -p` with `--output-format json`/`stream-json` and `--allowedTools`.

---

## Domain 3 — Prompt Engineering & Structured Output (20%)

### The lever order

1. Be clear and direct; state the task, context, and output format explicitly.
2. **Examples (multishot)** — the strongest lever after clarity.
3. **XML tags** to delimit sections (`<document>`, `<instructions>`) — Claude is specifically tuned for them.
4. Let it think (see below).
5. Chain prompts rather than writing one mega-prompt.

### Structured output — three distinct mechanisms

- **`output_config: {format: {...}}`** on `messages.create()` — constrains the response. (The old top-level `output_format` is deprecated. `messages.parse()` validates for you.)
- **`strict: true`** on a *tool definition* — guarantees `tool_use.input` validates exactly. Note it goes **top-level on the tool**, alongside `name`/`description`/`input_schema` — *not* on `tool_choice`. Requires `additionalProperties: false` + `required`.
- **Citations** (`citations: {enabled: true}` per document block) for grounded extraction. Incompatible with `output_config.format` — that pairing is a 400.

> 🚩 **High-probability exam trap: assistant prefill is removed.** On every current model (Opus 5, Sonnet 5, Fable 5/5.1, the 4.6/4.7/4.8 family), prefilling the last assistant turn returns a **400**. Any answer option that says "prefill the assistant message with `{`" is wrong. Use structured outputs or a system instruction instead.

### Thinking & effort

- Current models: `thinking: {type: "adaptive"}`. **`budget_tokens` is dead** — deprecated on 4.6, hard 400 on Opus 5 / 4.7 / 4.8 / Sonnet 5 / Fable. If a question mentions "thinking budget," the right answer is adaptive thinking + effort.
- **`output_config: {effort: "low"|"medium"|"high"|"xhigh"|"max"}`** — nested in `output_config`, not top-level. Default `high`. `xhigh` is the sweet spot for coding/agentic work; `low` for subagents and simple tasks.
- `display: "summarized"` vs `"omitted"` (the default on current models) — controls *visibility only*; thinking happens and is billed identically either way.

---

## Domain 4 — Tool Design & MCP (18%)

### A tool definition is a prompt

`name` + `description` + `input_schema`. The **description is the highest-leverage field** — it's how the model decides whether and how to call. Design tools around *what the agent needs to accomplish*, not around your existing API surface.

### The tool taxonomy

| Kind | Who executes | Examples |
|---|---|---|
| **Custom (client-side)** | your code | anything you define |
| **Anthropic-defined, schema-less** | your code | `bash_20250124`, `text_editor_20250728`, `memory_20250818` — declare `type` + `name`, **no `input_schema`** |
| **Server-side** | Anthropic | `web_search`, `web_fetch`, `code_execution`, `tool_search` |
| **MCP** | an MCP server | shared/reusable integrations |

### MCP

Client–server protocol for exposing tools, resources, and prompts to any MCP-capable client. Choose MCP when the integration should be **reusable across apps and teams**; choose a native tool for app-specific logic.

> 🚩 The MCP connector needs **both halves** — `mcp_servers=[{type:"url", url, name}]` alone is a validation error. You also need `tools=[{type: "mcp_toolset", mcp_server_name: <same name>}]`.

### Scaling the tool surface

`tool_search` + `defer_loading: true` on individual tools lets Claude search for tools instead of loading all definitions into context. Constraint: the search tool itself must **not** be deferred, and at least one tool must stay non-deferred — otherwise 400.

Also know `tool_choice`: `auto` / `any` / `tool` / `none` — and that forced `any`/`tool` now 400s on the Fable tier, where the answer is `auto` + an explicit instruction + `strict: true`.

---

## Domain 5 — Context Management & Reliability (15%)

### Prompt caching — the mechanics that get tested

- **Prefix match.** Render order is `tools` → `system` → `messages`. Any byte change anywhere in the prefix invalidates **everything after it**.
- Stable content first (frozen system prompt, deterministic tool order), volatile content (timestamps, per-request IDs, the actual question) **after** the last breakpoint.
- Max **4 breakpoints**; minimum cacheable prefix is 512–4096 tokens depending on model — shorter prefixes silently don't cache.
- **Verify with `usage.cache_read_input_tokens`.** Zero across repeated requests ⇒ a silent invalidator: `Date.now()` in the system prompt, unsorted JSON keys, a varying tool list.
- Caches are **model-scoped** — a model cascade forfeits cache reuse across its models.
- **Mid-conversation system messages**: append `{role: "system", ...}` to `messages[]` instead of editing top-level `system`. Preserves the cached prefix *and* is the prompt-injection-safe operator channel.

### Three context strategies — the most confusable trio on the exam

| Strategy | What it does | Mechanism |
|---|---|---|
| **Context editing** | **Deletes** old tool results / thinking blocks | `context_management.edits: [{type: "clear_tool_uses_20250919"}]` |
| **Compaction** | **Summarizes** earlier history server-side | `{type: "compact_20260112"}`, beta `compact-2026-01-12` |
| **Memory tool** | **Persists** outside the context window entirely | `{type: "memory_20250818", name: "memory"}` |

Compaction gotcha: you must append the **full `response.content`** back on each turn, not just the extracted text — the compaction blocks carry the state. Extract-the-string and you silently lose it.

### Reliability

- Catch a **chain**, not one broad class: `NotFoundError` → `RateLimitError` → `APIStatusError` → `APIConnectionError`. One broad catch loses the retryable (429, 5xx, network) vs non-retryable (400/404) distinction.
- SDK defaults: 10-min timeout, `max_retries` 2 (retries 408/409/429/5xx). Wall clock can reach `timeout × (max_retries+1)`.
- **Batches API**: 50% cost, asynchronous. Results come back in **any order** — key by `custom_id`, never by position.
- **`task_budget` vs `max_tokens`**: a task budget is an *advisory* token ceiling the model **can see** and paces itself against; `max_tokens` is a hard per-response cap the model is **unaware** of and gets cut off by.
- **Cost lever order**: free wins first (caching, input/output hygiene, batch), *then* tradeoffs (effort, model choice). Judge **cost per completed task**, not per request — a cheaper call that needs three retries isn't cheaper.

## Summary

1.⁠ ⁠Agente (Agent)

O Agente é o sistema de IA configurado para agir de forma autônoma para atingir um objetivo específico. Ao contrário de um modelo de linguagem comum (LLM) que apenas responde perguntas, o agente combina o LLM com memória, planejamento e acesso a ferramentas. Ele avalia a situação, decide qual ação tomar e executa essa ação.

2.⁠ ⁠Loop (O Ciclo de Execução)

O Loop é o motor que mantém o agente funcionando de forma independente. Em vez de parar após dar uma resposta, o agente entra em um ciclo de Pensar → Agir → Observar → Ajustar. Ele repete esse ciclo continuamente até que o objetivo final seja alcançado ou um critério de parada seja atingido.

3.⁠ ⁠Janela de Contexto (Context Window)

A Janela de Contexto é a "memória de curto prazo" do modelo de IA durante o loop. Ela define o limite máximo de dados (textos, códigos, imagens) que o modelo consegue processar e "lembrar" de uma só vez em uma única iteração.
•⁠  ⁠O desafio no Loop: À medida que o loop roda e o agente executa muitas ações, o histórico de mensagens cresce. Se o histórico ultrapassar a janela de contexto, a IA começa a "esquecer" o objetivo inicial ou as instruções de segurança.

4.⁠ ⁠Tools (Ferramentas)

As Tools são as capacidades técnicas ou funções externas que damos ao agente para que ele possa interagir com o mundo real. Uma IA sozinha só processa texto; com tools, ela ganha "mãos". Exemplos de ferramentas incluem:
•⁠  ⁠Uma função para fazer buscas na internet.
•⁠  ⁠Um comando para escrever ou ler arquivos no seu computador.
•⁠  ⁠Uma API para enviar um e-mail ou salvar dados em um banco de dados.

5.⁠ ⁠MCP (Model Context Protocol)

O Model Context Protocol (MCP) é um padrão aberto que funciona como uma "tomada universal" para conectar os modelos de IA a diferentes fontes de dados e ferramentas. Criado para resolver a bagunça de ter que programar conexões diferentes para cada ferramenta, o MCP permite que desenvolvedores criem servidores de dados (como acesso a repositórios do GitHub ou bancos de dados locais) que qualquer agente de IA compatível possa plugar e usar imediatamente.

6.⁠ ⁠Hooks (Ganchos de Interceptação)

Os Hooks são pontos de controle inseridos no código do sistema que gerencia a IA. Eles servem para interceptar as ações do agente antes ou depois que elas aconteçam. Os hooks são vitais para a segurança e monitoramento do loop, permitindo:
•⁠  ⁠Pre-action Hook: Interromper o agente e pedir aprovação humana antes que ele execute uma ferramenta perigosa (ex: deletar um arquivo).
•⁠  ⁠Post-action Hook: Modificar ou formatar o resultado de uma ferramenta antes que ele seja entregue de volta para a IA analisar.

Como tudo funciona junto: O Cenário Prático

Imagine que você pede para um Agente corrigir um bug no seu site:

[Seu Comando] ➔ Inicia o AGENTE
   │
   ├──> Entra no LOOP:
   │     1. PENSAR: "Preciso ver o erro."
   │     2. AGIR: Usa uma TOOL (ler arquivo de log) via protocolo MCP.
   │     3. OBSERVAR: Analisa o resultado obtido.
   │
   ├──> Validação de Segurança:
   │     - Um HOOK intercepta a ação de salvar o código corrigido e pede sua autorização.
   │
   └──> Gestão de Recursos:
         - O sistema limpa o histórico para não estourar a JANELA DE CONTEXTO.

