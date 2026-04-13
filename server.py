import os
import json
import sys
from mcp.server.fastmcp import FastMCP

# ✨ IA-chan
mcp = FastMCP("HistoriaVarillas")

# 📂 rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "fundacion.json")


# 🧪 chequeo inicial (NO bloquea, pero explica TODO)
def verificar_estado():
    print("\n🔍 === VERIFICACIÓN INICIAL ===", file=sys.stderr)
    print(f"📂 Buscando archivo en:\n{DATA_FILE}", file=sys.stderr)

    if not os.path.exists(DATA_FILE):
        print("\n❌ ERROR: archivo NO encontrado", file=sys.stderr)
        print("💡 Posibles problemas:", file=sys.stderr)
        print("   - No creaste 'fundacion.json'", file=sys.stderr)
        print("   - Está en otra carpeta", file=sys.stderr)
        print("   - Se llama distinto (ej: fundacion.json.txt)", file=sys.stderr)
        print("   - Windows oculta extensiones", file=sys.stderr)

        print("\n🛠️ SOLUCIÓN:", file=sys.stderr)
        print("👉 Creá un archivo llamado EXACTAMENTE:", file=sys.stderr)
        print("   fundacion.json", file=sys.stderr)
        print("👉 Y ponelo en la MISMA carpeta que server.py\n", file=sys.stderr)
        return

    print("✅ Archivo encontrado", file=sys.stderr)

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            datos = json.load(f)

        print("✅ JSON válido", file=sys.stderr)

        # 🔍 validar contenido
        campos = ["documento", "contenido", "autor", "tags"]
        faltantes = [c for c in campos if c not in datos]

        if faltantes:
            print("\n⚠️ Faltan campos en el JSON:", file=sys.stderr)
            print(f"👉 {faltantes}", file=sys.stderr)
        else:
            print("✅ Estructura completa", file=sys.stderr)

    except json.JSONDecodeError:
        print("\n❌ ERROR: JSON malformado", file=sys.stderr)
        print("💡 Revisá:", file=sys.stderr)
        print("   - Comas (,)", file=sys.stderr)
        print("   - Llaves {}", file=sys.stderr)
        print("   - Comillas \" \"", file=sys.stderr)

    except Exception as e:
        print(f"\n💥 Error inesperado: {e}", file=sys.stderr)

    print("🔍 === FIN VERIFICACIÓN ===\n", file=sys.stderr)


# 🎀 tool MCP
@mcp.tool()
def consultar_fundacion_las_varillas() -> str:
    try:
        if not os.path.exists(DATA_FILE):
            return (
                "❌ No existe fundacion.json\n"
                "👉 Crealo en la misma carpeta que server.py"
            )

        with open(DATA_FILE, "r", encoding="utf-8") as f:
            datos = json.load(f)

        return (
            f"📄 Documento : {datos.get('documento','Sin título')}\n"
            f"📝 Contenido : {datos.get('contenido','Sin contenido')}\n"
            f"✍️ Autor     : {datos.get('autor','Desconocido')}\n"
            f"🏷️ Tags      : {', '.join(datos.get('tags', []))}"
        )

    except json.JSONDecodeError:
        return "😵 El JSON está roto. Revisá formato."
    except Exception as e:
        return f"💥 Error: {str(e)}"


# 🚀 arranque SIEMPRE
if __name__ == "__main__":
    verificar_estado()

    print("🌸 Servidor MCP corriendo (aunque haya errores)", file=sys.stderr)
    print("💡 Listo para recibir consultas...", file=sys.stderr)

    mcp.run(transport="stdio")