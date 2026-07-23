"""
Revisa un archivo casos.json antes de ponerlo en producción.

Uso:
    python validar_banco.py
    python validar_banco.py mi_banco.json

Revisa dos cosas distintas:
  1. Estructura: que el JSON cumpla el esquema (campos, tipos, longitudes).
  2. Calidad: que la respuesta correcta no caiga siempre en la misma letra y
     que las viñetas contengan datos clínicos reales, no plantillas vacías.
"""

import json
import sys

from banco import auditar_banco, validar_estructura


def main() -> int:
    ruta = sys.argv[1] if len(sys.argv) > 1 else "casos.json"

    try:
        with open(ruta, "r", encoding="utf-8") as f:
            casos = json.load(f)
    except FileNotFoundError:
        print(f"No se encontró el archivo '{ruta}'.")
        return 1
    except json.JSONDecodeError as e:
        print(f"'{ruta}' no es un JSON válido.\n  {e}")
        return 1

    print(f"Archivo: {ruta}\n")

    errores = validar_estructura(casos)
    if errores:
        print(f"ESTRUCTURA: {len(errores)} error(es)\n")
        for e in errores[:25]:
            print(f"  - {e}")
        if len(errores) > 25:
            print(f"  ... y {len(errores) - 25} más")
        return 1

    print("ESTRUCTURA: correcta\n")

    a = auditar_banco(casos)
    print(f"Casos: {a['total_casos']}    Reactivos: {a['total_reactivos']}")
    print(f"Tipos: {a['distribucion_tipos']}")
    print(f"Temas distintos: {len(a['distribucion_temas'])}")
    print()

    print("Respuesta correcta por letra:")
    for letra in ["A", "B", "C", "D"]:
        n = a["distribucion_letras"].get(letra, 0)
        pct = n / a["total_reactivos"] * 100 if a["total_reactivos"] else 0
        barra = "#" * int(pct / 2)
        print(f"  {letra}: {n:4d}  {pct:5.1f}%  {barra}")
    print()

    print("Reactivos por nivel clínico:")
    for nivel, n in sorted(a["distribucion_niveles"].items()):
        print(f"  {nivel:14s} {n}")
    print()

    print("Casos por tema:")
    for tema, n in sorted(a["distribucion_temas"].items(), key=lambda x: -x[1]):
        print(f"  {n:3d}  {tema}")
    print()

    if a["alertas"]:
        print(f"CALIDAD: {len(a['alertas'])} alerta(s)\n")
        for alerta in a["alertas"]:
            print(f"  ! {alerta}")
        return 1

    print("CALIDAD: sin alertas. El banco está listo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
