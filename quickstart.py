import os
import json
import anthropic

# client = anthropic.Anthropic()

# message = client.messages.create(
#     model="claude-opus-5-5",
#     max_tokens=1000,
#     messages=[
#         {
#             "role": "user",
#             "content": "Write a short story about a robot learning to love."
#         }
#     ],
# )

# for block in message.content:
#     if block.type == "text":
#         print(block.text)


class FileSystemMCPServer:
    """"
    Simula um servidor MCP expondo ferramentas de sistema de arquivos para o agente autônomo.
    """
    def __init__(self):
        # Estado inicial do nosso ambiente de simulação
        self.files = {
            "quickstart.py": "def calcular_total(preco, imposto):\n    return preco - imposto # BUG: Deveria somar o imposto!"
        }

    def get_tools_definitions(self):
        """
        Retorna as definições das ferramentas disponíveis no servidor MCP.
        """
        return [
            {
                "name": "ler_arquivo",
                "description": "Lê o conteúdo de um arquivo.",
                "input_schema": {
                    "type": "object",
                    "properties": {"filename": {"type": "string"}},
                    "required": ["filename"]
                }
            },
            {
                "name": "gravar_arquivo",
                "description": "Substitui o conteúdo de um arquivo com o código corrigido.",
                "input_schema": {
                    "type": "object",

                    "properties": {
                        "filename": {"type": "string"},
                        "conteudo": {"type": "string"}
                    },
                    "required": ["filename", "conteudo"]
                }
            }
        ]

    def execute_tool(self, name, arguments):
        """Executa a ferramenta solicitada pelo Agente."""
        if name == "ler_arquivo":
            fname = arguments["filename"]
            return self.files.get(fname, f"Erro: Arquivo {fname} não encontrado.")
        elif name == "gravar_arquivo":
            fname = arguments["filename"]
            self.files[fname] = arguments["conteudo"]
            return f"Sucesso: Arquivo {fname} atualizado."
    
        return "Erro: Ferramenta desconhecida."



# =====================================================================
# 5. HOOKS (GANCHOS DE INTERCEPTAÇÃO)
# =====================================================================
class AgentHooks:
    @staticmethod
    def pre_action_hook(tool_name, arguments):
        """
        Hook de segurança para interceptar o uso de ferramentas.
        Retorna True se a ação for permitida, False caso contrário.
        Human-in-the-loop: Intercepta ações críticas antes de rodar.
        """
        print(f"\n🛡️[HOOK - PRE-ACTION] Agente quer executar a ferramenta: '{tool_name}'")
        print(f"Argumentos: {arguments}")
        
        # Se for uma ação destrutiva/gravação, exige confirmação do usuário
        if tool_name == "gravar_arquivo":
            confirmacao = input(f"⚠️ [PRE-ACTION HOOK] Você está prestes a gravar um arquivo. Deseja continuar? (s/n): ")
            return confirmacao.lower() == "s"

        return True  # Acoes de leitura passam direto            

    @staticmethod
    def post_action_hook(tool_name, raw_result):
        """
        Modifica ou audita o output da ferramenta antes de enviar ao modelo.
        """
        # Exemplo: Loga a saída da ferramenta
        print(f"📊 [HOOK - POST-ACTION] Resposta da ferramenta capturada com sucesso.")
        return raw_result


#=====================================================================
# 2. AGENTE & 3. LOOP (CICLO DE EXECUÇÃO) + JANELA DE CONTEXTO
# =====================================================================
class AutonomousAgent:
    def __init__(self, api_key):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.mcp = FileSystemMCPServer()
        self.hooks = AgentHooks()

        # Janela de contexto (Histórico do Loop)
        self.messages = []
        self.max_loop_iterations = 5

    def manage_context_window(self):
        """
        Em produção, os arquitetos limpam ou sumarizam mensagens antigas 
        para economizar tokens e evitar estourar a Janela de Contexto (Context Window).
        """
        # Mantem apenas as últimas interações se o histórico
        # ficar muito longo
        if (len(self.messages) > 10):
            print(f"✂️[CONTEXT WINDOW] Reduzingo histórico para preservar tokens da janela.")
            self.messages = [self.messages[0]] + self.messages[-6:]

    def run(self, objetivo):
        """
        Loop principal do agente autônomo.
        """
        print(f"🤖 Agente Inicializado com Objetivo: '{objetivo}'")
        message = {
            "role": "user",
            "content": objetivo
        }
        self.messages.append(message)

        # Loop de execução do agente autônomo
        for i in range(1, self.max_loop_iterations + 1):
            print(f"\n🔄 --- INICIANDO ITERAÇÃO DO LOOP #{i} ---")
            self.manage_context_window()

            print(f"\n💬 Context Window atualizado.")

            # Chamada do Claude enviando as ferramentas
            # disponíveis do MCP
            print(f"Messages = {self.messages}")
            response = self.client.messages.create(
                model="claude-haiku-5-5",
                max_tokens=2000,
                messages=self.messages,
                tools=self.mcp.get_tools_definitions()
            )

            print(f"\n💬 [CLAUDE RESPONSE]: O Agente recebeu a resposta do Claude com {len(response.content)} blocos de conteúdo.")
            # Adiciona a resposta do Claude a Janela de Contexto
            # Convertendo os blocos de conteudo da API
            # para o formato de histórico do agente autônomo
            content_list = []
            tools_requests = []

            print(f"[CONTENT] Response content: {response.content}")
            for block in response.content:
                if block.type == "text":
                    content_list.append({
                        "type": "text",
                        "text": block.text
                    })
                elif block.type == "tool_use":
                    tool_use_block = {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input
                    }
                    # O tool_use precisa ficar no histórico do assistant:
                    # cada tool_result da próxima mensagem referencia este id
                    content_list.append(tool_use_block)
                    tools_requests.append(tool_use_block)

            self.messages.append({
                "role": "assistant",
                "content": content_list,
            })

            if not tools_requests:
                print("\n🏁 [LOOP FINALIZADO]: O Agente concluiu o objetivo de forma autônoma.")
                break

            # Processando o uso de ferramentas solicitado pelo Claude dentro do Loop
            tools_responses = []
            for tool_use in tools_requests:
                id, name, input = tool_use["id"], tool_use["name"], tool_use["input"]

                print(f"\n🛠️ [TOOL USE]: O Agente solicitou o uso da ferramenta '{name}' com os argumentos: {input}")
                
                # Execução do 5. Pre-Action Hook (Segurança / Aprovação)
                if not self.hooks.pre_action_hook(name, input):
                    print(f"\n❌ [PRE-ACTION HOOK]: O uso da ferramenta '{name}' foi bloqueado pelo Hook de Segurança.")
                    result = "Erro: Operação bloqueada por razões de segurança."
                else:
                    # Executa a ferramenta mapeada via MCP
                    raw_result = self.mcp.execute_tool(name, input)
                    
                    # Execução do 5. Post-Action Hook (Tratamento)
                    result = self.hooks.post_action_hook(name, raw_result)

                tools_responses.append({
                    "type": "tool_result",
                    "tool_use_id": id,
                    "content": result
                })

            # Alimenta a Janela de contexto com 
            # resultado da ferramenta para a próxima iteração do Loop
            self.messages.append({
                "role": "user",
                "content": tools_responses
            })


if __name__ == "__main__":
    # Inicializa o agente autônomo com a chave de API
    api_key = os.getenv("ANTHROPIC_API_KEY")
    agent = AutonomousAgent(api_key=api_key)

    # Define o objetivo do agente
    objetivo = """"
    Analise o arquivo 'quickstart.py', verifique se a lógica da função está correta de "
    acordo com o comentário do código. Se houver um bug, corrija o arquivo."
    """

    # Executa o agente autônomo
    agent.run(objetivo)

    # Mostra o estado final do arquivo simulado no servidor MCP
    print("\n✅[ESTADO FINAL] Conteúdo de 'quickstart.py' após a execução do agente:")
    print(agent.mcp.files["quickstart.py"])