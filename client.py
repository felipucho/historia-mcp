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

def llamar_ollama(prompt: str) -> str:
    """
    Envía un prompt a Ollama y devuelve la respuesta.
    """
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
        return data.get("response", "").strip()
        
    except requests.exceptions.Timeout:
        return "⏱️ Ollama tardó demasiado. Intenta con un prompt más corto."
    except requests.exceptions.ConnectionError:
        return f"❌ No se puede conectar a Ollama en {OLLAMA_URL}"
    except Exception as e:
        return f"💥 Error: {str(e)}"


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

            print(f"Herramientas disponibles: {[t.name for t in tools_mcp]}\n")

            # 3. Inicializar historial de conversación
            nombre = leer_archivo_ia("nombre.txt", "Asistente Histórico")
            personalidad = leer_archivo_ia("personalidad.txt", "Eres una IA amable.")
            instrucciones = leer_archivo_ia("instrucciones.txt", "")
            conocimiento = leer_archivo_ia("conocimiento.txt", "")
            
            system_prompt = f"Tu nombre es {nombre}.\n\nPersonalidad:\n{personalidad}\n\nInstrucciones:\n{instrucciones}\n\nConocimiento adicional y contexto:\n{conocimiento}"
            
            # 4. Bucle de conversación
            while True:
                pregunta = input("Vos: ").strip()
                if pregunta.lower() in ("salir", "exit", "quit"):
                    print("¡Hasta luego!")
                    break
                if not pregunta:
                    continue

                # 5. Decidir si necesitamos datos del JSON
                print(f"\n[Buscando información...]")
                
                # Intentar leer datos del JSON
                datos_json = None
                try:
                    resultado = await session.call_tool("consultar_fundacion_las_varillas", arguments={})
                    if resultado.content:
                        datos_json = resultado.content[0].text
                except Exception as e:
                    print(f"⚠️ No se pudo acceder a los datos: {e}")

                # 6. Construir prompt con contexto
                if datos_json:
                    prompt = f"""{system_prompt}

DATOS DEL ARCHIVO fundacion.json:
{datos_json}

---

Usuario: {pregunta}

Responde basándote en los datos proporcionados anteriormente. Si la pregunta no está relacionada con Las Varillas o con los datos disponibles, indica que no tienes información al respecto.

Asistente:"""
                else:
                    prompt = f"""{system_prompt}

---

Usuario: {pregunta}

Asistente:"""

                # 7. Llamar a Ollama con el contexto
                respuesta = llamar_ollama(prompt)
                print(f"\nIA: {respuesta}\n")


if __name__ == "__main__":
    asyncio.run(main())
