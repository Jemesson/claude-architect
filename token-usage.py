""""
Para a certificação Claude Architect Foundation,
o design pattern oficial da Anthropic descarta strings improvisadas (como PENSAMENTO: ou AÇÃO:)
e adota estritamente o Claude SDK com a API nativa de Tool Use (Computer Use / Function Calling).

Na arquitetura oficial da Anthropic, o fluxo do loop é controlado inspecionando o stop_reason retornado pelo Claude.
Se o stop_reason == "tool_use", o loop intercepta a chamada, executa o código e envia a resposta de volta
com o bloco estruturado tool_result.
"""

import time
from typing import List, Dict, Any

def get_tools_definitions():
    """"
    Retorna a lista de definições de ferramentas disponíveis.
    Na certificação, lembre-se: as ferramentas são passadas como JSON Schema no parâmetro 'tools' da chamada de mensagens do Claude.
    """
    return [
        {
            "name": "fetch_framework_details",
            "description": "Busca as informações sobre novos frameworks internos da Anthropic.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "framework_name": {"type": "string", "description": "Nome do framework a pesquisar."}
                },
                "required": ["framework_name"]
            }
        },
        {
            "name": "calculate_budget",
            "description": "Executa cálculos matemáticos financeiros com taxas",
            "input_schema": {
                "type": "object",
                "properties": {
                    "base_amount": {"type": "number", "description": "Valor base para o cálculo."},
                    "tax_rate": {"type": "number", "description": "Taxa percentual em decimal (ex: 0.2 para 20%)."}
                },
                "required": ["base_amount", "tax_rate"]
            }
        }
    ]

def execute_tool(name: str, arguments: Dict[str, Any]) -> str:
    """
    Simula a execução total da ferramenta após decisão do Claude.
    """
    if name == "fetch_framework_details":
        name_param = arguments.get("framework_name", "").lower()
        if "claude" in name_param:
            return "Resultado da ferramenta 'Claude' é o codinome de homologação para agentes autônomos da Anthropic."
        
        return f"Resultado da ferramenta '{name_param}' não encontrado."

    elif name == "calculate_budget":
        base_amount = arguments.get("base_amount", 0)
        tax_rate = arguments.get("tax_rate", 0)

        return f"🔢Resultado do cálculo: Base {base_amount}, Taxa {tax_rate*100}%, Total {base_amount * (1 + tax_rate)}."
            
    return "⚙️ [EXECUTE_TOOL] ferramenta não implementada."


class MockToolUseBlock:
    """"
    Simula exatamente os objetos de resposta retornados por client.messages.create()
    """
    def __init__(self, id: str, tool_name: str, input: Dict[str, Any]):
        self.id = id
        self.type = "tool_use"
        self.name = tool_name
        self.input = input

class MockMessageResponse:
    def __init__(self, content: List[Any], stop_reason: str):
        self.content = content         
        self.stop_reason = stop_reason


class MockAnthropicClient:
    """
    Simula o comportamento do client.messages.create para fins de arquitetura.
    """
    def __init__(self):
        self.turn = 0

    def create(self, model: str, messages: List[Dict], tools: List[Dict], max_tokens: int) -> MockMessageResponse:
        self.turn += 1
        
        if self.turn == 1:
            # Claude decide que precisa chamar a primeira ferramenta
            tool_block = MockToolUseBlock("call_1", "fetch_framework_details", {"framework_name": "Claude"})
            return MockMessageResponse(
                content=[tool_block],
                stop_reason="tool_use"
            )
        elif self.turn == 2:
            # Após receber o resultado, Claude decide chamar a segunda ferramenta
            tool_block = MockToolUseBlock("call_2", "calculate_budget", {"base_amount": 1500, "tax_rate": 0.20})
            return MockMessageResponse(
                content=[tool_block],
                stop_reason="tool_use"
            )
        else:
            # Com todos os dados coletados, Claude encerra o turno entregando a resposta final
            class TextBlock:
                def __init__(self, text): self.text = text; self.type = "text"
            
            final_text = "Com base nas ferramentas executadas, 'Claude' refere-se ao codinome de homologação de agentes. O orçamento final com os 20% de taxa aplicados é de 1800.0."
            return MockMessageResponse(
                content=[TextBlock(final_text)],
                stop_reason="end_turn"
            )

class AnthropicSDKLoopController:
    def __init__(self, max_loops: int = 5):
        self.client = MockAnthropicClient()
        self.max_loops = max_loops
        self.messages_history: List[Dict[str, Any]] = []

    def run_workflow(self, prompt: str):
        print(f"🚀 Iniciando Loop Nativo SDK com objetivo: {prompt}\n")
        
        # O histórico inicial segue o padrão de mensagens do SDK da Anthropic
        self.messages_history.append(
            {
                "role": "user",
                "content": prompt
            }
        )

        counter = 0
        while counter < self.max_loops:
            counter += 1
            print(f"⏱️ [SDK Step #{counter}] Enviando histórico ao Claude...")

            # Chamada padrão da API da Anthropic
            response = self.client.create(
                model="claude-3-5-sonnet-20241022",
                messages=self.messages_history,
                tools=get_tools_definitions(),
                max_tokens=2000
            )

            # Estrutura exigida pela Anthropic: Adicionar a resposta do assistente (que pode conter a Tool Use) ao histórico
            assistant_content_block = []
            for block in response.content:
                if block.type == "text":
                    assistant_content_block.append({"type": "text", "text": block.text})
                    print(f"🤖 Claude (Texto): {block.text}")
                elif block.type == "tool_use":
                    assistant_content_block.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input
                    })
                    print(f"🛠️ Claude solicitou Tool: {block.name} | Args: {block.input}")

            self.messages_history.append(
                {
                    "role": "assistant",
                    "content": assistant_content_block
                }
            )

            # CRITÉRIO DE PARADA OFICIAL: Se o stop_reason for end_turn, o Claude terminou o raciocínio
            if response.stop_reason == "end_turn":
                print("\n✅ [TERMINATION LOGIC] Fluxo encerrado pelo Claude (end_turn). Objetivo atingido.")
                break

            # TRATAMENTO DE FERRAMENTA (Se stop_reason == "tool_use")
            if response.stop_reason == "tool_use":
                tool_results_blocks = []
                
                # Executa cada tool_use solicitada pelo modelo
                for block in assistant_content_block:
                    if block["type"] == "tool_use":
                        # Executa o código Python determinístico correspondente
                        result_output = execute_tool(block["name"], block["input"])
                        print(f"📝 Resultado da Execução -> {result_output}")
                        
                        # Constrói o bloco de resposta estruturado exato exigido pelo SDK da Anthropic
                        tool_results_blocks.append({
                            "type": "tool_result",
                            "tool_use_id": block["id"],
                            "content": result_output
                        })
                
                # Alimenta o histórico de volta com o papel 'user' contendo os blocos de 'tool_result'
                self.messages_history.append({"role": "user", "content": tool_results_blocks})
            
            time.sleep(0.5)
        else:
            print("\n🛑 [GUARDRAIL] Interrompido: Estourou o limite máximo de segurança de loops!")


if __name__ == "__main__":
    orchestrator = AnthropicSDKLoopController()
    
    prompt = "Explique o significado do codinome 'Claude' e calcule o orçamento final aplicando uma taxa de 20% sobre 1500."
    orchestrator.run_workflow(prompt)
