"""
Esquema, carga y validación del banco de casos clínicos.

El banco NO se genera en tiempo de examen. Se produce por separado (con ayuda
de un modelo de lenguaje y tus guías), se revisa, y se guarda como casos.json.
Este módulo se encarga de leerlo y de avisarte si algo está mal.
"""

import json
import os
from collections import Counter
from typing import Any

from jsonschema import Draft7Validator

NIVELES = ["diagnostico", "tratamiento", "prevencion", "pronostico"]
LETRAS = ["A", "B", "C", "D"]

ESQUEMA_BANCO: dict[str, Any] = {
    "type": "array",
    "minItems": 1,
    "items": {
        "type": "object",
        "required": [
            "id",
            "especialidad",
            "tema",
            "guia_origen",
            "tipo",
            "vineta",
            "reactivos",
        ],
        "additionalProperties": False,
        "properties": {
            "id": {"type": "string", "pattern": "^C[0-9]{3,4}$"},
            "especialidad": {"type": "string", "minLength": 3},
            "tema": {"type": "string", "minLength": 3},
            "guia_origen": {"type": "string", "minLength": 5},
            "tipo": {"type": "string", "enum": ["unico", "seriado"]},
            "vineta": {"type": "string", "minLength": 120},
            "reactivos": {
                "type": "array",
                "minItems": 1,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "required": [
                        "enunciado",
                        "opciones",
                        "respuesta_correcta",
                        "retroalimentacion",
                        "nivel",
                    ],
                    "additionalProperties": False,
                    "properties": {
                        "enunciado": {"type": "string", "minLength": 15},
                        "opciones": {
                            "type": "array",
                            "minItems": 4,
                            "maxItems": 4,
                            "items": {"type": "string", "minLength": 2},
                        },
                        "respuesta_correcta": {"type": "string", "enum": LETRAS},
                        "retroalimentacion": {"type": "string", "minLength": 40},
                        "nivel": {"type": "string", "enum": NIVELES},
                    },
                },
            },
        },
    },
}

# Frases de relleno típicas de un banco generado sin leer las guías.
FRASES_SOSPECHOSAS = [
    "sintomatología cardinal",
    "sintomatologia cardinal",
    "valores fuera del rango",
    "hallazgos compatibles con descompensación",
    "según la sección",
    "no especificado",
    "de origen indeterminado",
]


class BancoInvalido(Exception):
    """El archivo casos.json no cumple el esquema o no se pudo leer."""


def cargar_banco(ruta: str) -> list[dict]:
    """Lee y valida casos.json. Lanza BancoInvalido con un mensaje claro."""
    if not os.path.exists(ruta):
        raise BancoInvalido(
            f"No se encontró el archivo '{ruta}'. Genera el banco de casos "
            "antes de iniciar un examen."
        )

    try:
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
    except json.JSONDecodeError as e:
        raise BancoInvalido(f"'{ruta}' no es un JSON válido: {e}") from e

    errores = validar_estructura(datos)
    if errores:
        raise BancoInvalido(
            f"El banco tiene {len(errores)} error(es) de estructura. "
            f"Primero: {errores[0]}"
        )

    ids = [c["id"] for c in datos]
    repetidos = [i for i, n in Counter(ids).items() if n > 1]
    if repetidos:
        raise BancoInvalido(f"Hay IDs de caso repetidos: {', '.join(repetidos)}")

    return datos


def validar_estructura(datos: Any) -> list[str]:
    """Devuelve la lista de errores de esquema, vacía si todo está bien."""
    validador = Draft7Validator(ESQUEMA_BANCO)
    errores = []
    for err in sorted(validador.iter_errors(datos), key=lambda e: list(e.path)):
        ruta = " → ".join(str(p) for p in err.path) or "raíz"
        errores.append(f"[{ruta}] {err.message}")
    return errores


def auditar_banco(casos: list[dict]) -> dict[str, Any]:
    """Revisa la calidad pedagógica del banco, no solo su forma.

    Detecta los dos problemas que arruinan un simulador: que la respuesta
    correcta siempre caiga en la misma letra, y que las viñetas sean plantillas
    vacías sin datos clínicos.
    """
    total_reactivos = 0
    letras = Counter()
    niveles = Counter()
    temas = Counter()
    tipos = Counter()
    vinetas_sospechosas = []
    vinetas_sin_numeros = []

    for caso in casos:
        temas[caso["tema"]] += 1
        tipos[caso["tipo"]] += 1

        vineta_baja = caso["vineta"].lower()
        if any(f in vineta_baja for f in FRASES_SOSPECHOSAS):
            vinetas_sospechosas.append(caso["id"])
        # Una viñeta clínica real trae cifras: edad, signos vitales, laboratorio.
        if sum(ch.isdigit() for ch in caso["vineta"]) < 4:
            vinetas_sin_numeros.append(caso["id"])

        for r in caso["reactivos"]:
            total_reactivos += 1
            letras[r["respuesta_correcta"]] += 1
            niveles[r["nivel"]] += 1

    # Desequilibrio: qué porcentaje ocupa la letra más frecuente.
    peor_letra_pct = (max(letras.values()) / total_reactivos * 100) if total_reactivos else 0

    alertas = []
    if peor_letra_pct > 40:
        letra = letras.most_common(1)[0][0]
        alertas.append(
            f"La respuesta correcta es '{letra}' en el {peor_letra_pct:.0f}% de los "
            "reactivos. Un alumno puede acertar por posición."
        )
    if vinetas_sospechosas:
        alertas.append(
            f"{len(vinetas_sospechosas)} viñeta(s) contienen frases de relleno "
            f"genéricas: {', '.join(vinetas_sospechosas[:8])}"
            + (" …" if len(vinetas_sospechosas) > 8 else "")
        )
    if vinetas_sin_numeros:
        alertas.append(
            f"{len(vinetas_sin_numeros)} viñeta(s) casi no contienen cifras "
            "(edad, signos vitales, laboratorio): "
            f"{', '.join(vinetas_sin_numeros[:8])}"
            + (" …" if len(vinetas_sin_numeros) > 8 else "")
        )
    if len(temas) < 5:
        alertas.append(
            f"Solo hay {len(temas)} tema(s) distintos. El muestreo estratificado "
            "necesita variedad para no repetirle contenido al alumno."
        )

    return {
        "total_casos": len(casos),
        "total_reactivos": total_reactivos,
        "distribucion_letras": dict(letras),
        "distribucion_niveles": dict(niveles),
        "distribucion_temas": dict(temas),
        "distribucion_tipos": dict(tipos),
        "alertas": alertas,
    }
