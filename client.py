import asyncio
import json
import os
import sys
import requests
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ─── Configuración ────────────────────────────────────────────────────────────

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

OLLAMA_URL  = "http://localhost:11434"
OLLAMA_MODEL = leer_archivo_ia("model.txt", "llama3:latest")

# ─── Helpers ──────────────────────────────────────────────────────────────────

def verificar_ollama() -> bool:
    """Verifica si Ollama está corriendo."""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False

def llamar_ollama(messages: list, tools: list = None) -> dict:
    """
    Envía una conversación a Ollama y devuelve la respuesta.
    
    Nota: Ollama's /api/chat no soporta tools nativamente.
    Para function calling, usar /api/generate con prompts estructurados.
    """
    # Convertir messages a un prompt estructurado para /api/generate
    # ya que Ollama no soporta tools en /api/chat
    prompt = _messages_a_prompt(messages)
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=180  # 3 minutos para prompts largos
        )
        response.raise_for_status()
        data = response.json()
        
        # Convertir respuesta de /api/generate al formato esperado
        return {
            "message": {
                "content": data.get("response", ""),
                "tool_calls": []  # Ollama no retorna tool_calls en /api/generate
            }
        }
    except requests.exceptions.Timeout:
        print("⏱️ Ollama tardó demasiado. Intenta con un prompt más corto.")
        return {"message": {"content": "Timeout", "tool_calls": []}}
    except requests.exceptions.ConnectionError:
        print(f"❌ No se puede conectar a Ollama en {OLLAMA_URL}")
        return {"message": {"content": "Conexión rechazada", "tool_calls": []}}
    except Exception as e:
        print(f"💥 Error: {str(e)}")
        return {"message": {"content": str(e), "tool_calls": []}}


def _messages_a_prompt(messages: list) -> str:
    """Convierte un historial de mensajes a un prompt para /api/generate."""
    prompt_parts = []
    
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")
        
        if role == "system":
            prompt_parts.append(f"Sistema: {content}\n")
        elif role == "user":
            prompt_parts.append(f"Usuario: {content}\n")
        elif role == "assistant":
            prompt_parts.append(f"Asistente: {content}\n")
        elif role == "tool":
            prompt_parts.append(f"Herramienta: {content}\n")
    
    return "\n".join(prompt_parts) + "\nAsistente: "


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


# ─── Lógica principal ────────────────────────────────────────────────────────

async def main():
    print("=== Cliente MCP - Historia de Las Varillas ===\n")

    # 0. Verificar que Ollama esté disponible
    print("Verificando Ollama...")
    if not verificar_ollama():
        print(f"❌ ERROR: Ollama no está disponible en {OLLAMA_URL}")
        print("   Asegúrate de que Ollama está corriendo: ollama serve")
        return

    print(f"✅ Ollama disponible. Modelo: {OLLAMA_MODEL}\n")

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

            # 3. Inicializar historial de conversación
            nombre = leer_archivo_ia("nombre.txt", "Asistente Histórico")
            personalidad = leer_archivo_ia("personalidad.txt", "Eres una IA amable.")
            instrucciones = leer_archivo_ia("instrucciones.txt", "")
            conocimiento = leer_archivo_ia("conocimiento.txt", "")
            
            system_prompt = f"Tu nombre es {nombre}.\n\nPersonalidad:\n{personalidad}\n\nInstrucciones:\n{instrucciones}\n\nConocimiento adicional y contexto:\n{conocimiento}"
            messages = [{"role": "system", "content": system_prompt}]
            
            # 4. Bucle de conversación
            while True:
                pregunta = input("Vos: ").strip()
                if pregunta.lower() in ("salir", "exit", "quit"):
                    print("¡Hasta luego!")
                    break
                if not pregunta:
                    continue

                messages.append({"role": "user", "content": pregunta})

                # 5. Bucle de razonamiento (agentic loop)
                print(f"\nIA: ", end="", flush=True)
                respuesta = llamar_ollama(messages)
                mensaje = respuesta.get("message", {})
                contenido = mensaje.get('content', '(sin respuesta)').strip()
                
                print(contenido)
                print()
                
                messages.append({"role": "assistant", "content": contenido})


if __name__ == "__main__":
    asyncio.run(main())
