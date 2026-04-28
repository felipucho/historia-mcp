import asyncio
import json
import os
import sys
import requests
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ─── Configuración ───────────────────────────────────────────────────────────

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
PYTHON_PATH = sys.executable
SERVER_SCRIPT = os.path.join(BASE_DIR, "server.py")

# ─── Configuración de la IA ──────────────────────────────────────────────────
IA_CONFIG_DIR = os.path.join(BASE_DIR, "ia_config")

def leer_archivo_ia(nombre_archivo, default=""):
    """Lee un archivo de configuración de texto si existe."""
    ruta = os.path.join(IA_CONFIG_DIR, nombre_archivo)
    if os.path.exists(ruta):
        with open(ruta, "r", encoding="utf-8") as f:
            return f.read().strip()
    return default

OLLAMA_URL  = "http://localhost:11434/api/chat"
OLLAMA_MODEL = leer_archivo_ia("model.txt", "qwen3-vl:8b")

# ─── Helpers ─────────────────────────────────────────────────────────────────

def llamar_ollama(messages: list, tools: list) -> dict:
    """Envía una conversación a Ollama y devuelve la respuesta."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "tools": tools,
        "stream": False,
    }
    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    response.raise_for_status()
    return response.json()


def herramientas_mcp_a_ollama(mcp_tools) -> list:
    """Convierte las herramientas MCP al formato que entiende Ollama."""
    ollama_tools = []
    for tool in mcp_tools:
        ollama_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema or {"type": "object", "properties": {}},
            },
        })
    return ollama_tools


# ─── Lógica principal ─────────────────────────────────────────────────────────

async def main():
    print("=== Cliente MCP - Historia de Las Varillas ===\n")

    # 1. Conectar con el servidor MCP (lo lanza automáticamente via stdio)
    server_params = StdioServerParameters(
        command=PYTHON_PATH,
        args=[SERVER_SCRIPT],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 2. Obtener herramientas disponibles del servidor
            tools_result = await session.list_tools()
            tools_mcp = tools_result.tools
            tools_ollama = herramientas_mcp_a_ollama(tools_mcp)

            print(f"Herramientas disponibles: {[t.name for t in tools_mcp]}\n")

            # 3. Bucle de conversación
            # 3. Inicializar historial de conversación leyendo los archivos de configuración
            nombre = leer_archivo_ia("nombre.txt", "Asistente Histórico")
            personalidad = leer_archivo_ia("personalidad.txt", "Eres una IA amable.")
            instrucciones = leer_archivo_ia("instrucciones.txt", "")
            conocimiento = leer_archivo_ia("conocimiento.txt", "")
            
            system_prompt = f"Tu nombre es {nombre}.\n\nPersonalidad:\n{personalidad}\n\nInstrucciones:\n{instrucciones}\n\nConocimiento adicional y contexto:\n{conocimiento}"
            messages = [{"role": "system", "content": system_prompt}]
            
            while True:
                pregunta = input("Vos: ").strip()
                if pregunta.lower() in ("salir", "exit", "quit"):
                    print("¡Hasta luego!")
                    break
                if not pregunta:
                    continue

                messages.append({"role": "user", "content": pregunta})

                # 4. Bucle de razonamiento (agentic loop)
                while True:
                    respuesta = llamar_ollama(messages, tools_ollama)
                    mensaje = respuesta.get("message", {})

                    tool_calls = mensaje.get("tool_calls", [])

                    # Si Ollama NO pide ninguna herramienta → respuesta final
                    if not tool_calls:
                        print(f"\nIA: {mensaje.get('content', '(sin respuesta)')}\n")
                        break

                    # Si Ollama pide una herramienta → ejecutarla en el servidor MCP
                    messages.append({"role": "assistant", "content": "", "tool_calls": tool_calls})

                    for call in tool_calls:
                        nombre = call["function"]["name"]
                        args   = call["function"].get("arguments", {})
                        if isinstance(args, str):
                            args = json.loads(args) if args else {}

                        print(f"[Usando herramienta: {nombre}]")

                        resultado = await session.call_tool(nombre, arguments=args)
                        contenido = resultado.content[0].text if resultado.content else "Sin resultado"

                        messages.append({
                            "role": "tool",
                            "content": contenido,
                        })

                    # Volver a enviar a Ollama con el resultado de la herramienta


if __name__ == "__main__":
    asyncio.run(main())
