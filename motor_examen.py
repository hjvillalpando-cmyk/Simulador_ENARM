"""
Motor del examen: elige los casos de la sesión y arma los reactivos.

Dos decisiones importantes:
1. Muestreo estratificado por tema, excluyendo lo que el alumno vio en sus
   últimas sesiones.
2. Las opciones se barajan al momento de presentarlas. Así, aunque el banco
   tenga la correcta siempre en la misma letra, el alumno no puede adivinar.
"""

import random
from typing import Any

from sqlalchemy.orm import Session

from banco import LETRAS
from config import BARAJAR_OPCIONES, NUM_CASOS_POR_SESION, SESIONES_SIN_REPETIR
from db import Respuesta, Sesion


def casos_recientes_del_alumno(
    db: Session, usuario_id: int, n_sesiones: int = SESIONES_SIN_REPETIR
) -> set[str]:
    """IDs de casos que el alumno vio en sus últimas n sesiones."""
    ultimas = (
        db.query(Sesion.id)
        .filter(Sesion.usuario_id == usuario_id)
        .order_by(Sesion.fecha_inicio.desc())
        .limit(n_sesiones)
        .all()
    )
    ids = [s[0] for s in ultimas]
    if not ids:
        return set()

    filas = (
        db.query(Respuesta.caso_id)
        .filter(Respuesta.sesion_id.in_(ids))
        .distinct()
        .all()
    )
    return {f[0] for f in filas}


def seleccionar_casos(
    db: Session,
    usuario_id: int,
    banco: list[dict],
    num_casos: int = NUM_CASOS_POR_SESION,
) -> list[dict]:
    """Elige `num_casos` repartidos entre temas, evitando repeticiones recientes."""
    vistos = casos_recientes_del_alumno(db, usuario_id)
    elegibles = [c for c in banco if c["id"] not in vistos]

    # Si al filtrar quedan muy pocos, se abre todo el banco.
    if len(elegibles) < num_casos:
        elegibles = list(banco)

    num_casos = min(num_casos, len(elegibles))

    # Agrupar por tema y barajar dentro de cada grupo.
    por_tema: dict[str, list[dict]] = {}
    for caso in elegibles:
        por_tema.setdefault(caso["tema"], []).append(caso)
    for lista in por_tema.values():
        random.shuffle(lista)

    temas = list(por_tema.keys())
    random.shuffle(temas)

    # Ronda robin: un caso de cada tema hasta completar.
    seleccion: list[dict] = []
    while len(seleccion) < num_casos and temas:
        for tema in list(temas):
            if len(seleccion) >= num_casos:
                break
            if por_tema[tema]:
                seleccion.append(por_tema[tema].pop())
            if not por_tema[tema]:
                temas.remove(tema)

    random.shuffle(seleccion)
    return seleccion


def _barajar_opciones(reactivo: dict) -> tuple[list[str], str, list[str]]:
    """Reordena las opciones y recalcula cuál letra es ahora la correcta.

    Devuelve (opciones_mostradas, letra_correcta_mostrada, letras_originales),
    donde letras_originales[i] es la letra original del texto que ahora ocupa
    la posición i. Eso permite guardar en la base de datos la letra original
    del banco y mantener el análisis de reactivos consistente.
    """
    originales = list(reactivo["opciones"])
    idx_correcto_original = LETRAS.index(reactivo["respuesta_correcta"])

    orden = list(range(4))
    if BARAJAR_OPCIONES:
        random.shuffle(orden)

    opciones_mostradas = [originales[i] for i in orden]
    letras_originales = [LETRAS[i] for i in orden]
    letra_correcta_mostrada = LETRAS[orden.index(idx_correcto_original)]

    return opciones_mostradas, letra_correcta_mostrada, letras_originales


def construir_examen(casos: list[dict]) -> list[dict[str, Any]]:
    """Aplana los casos en una lista de reactivos listos para mostrar.

    Cada elemento conserva la referencia a su caso para que la interfaz pueda
    mostrar la viñeta y numerar 'Caso 3 de 15 · Reactivo 2 de 3'.
    """
    items: list[dict[str, Any]] = []

    for num_caso, caso in enumerate(casos, start=1):
        total_reactivos_caso = len(caso["reactivos"])
        for idx, reactivo in enumerate(caso["reactivos"]):
            opciones, correcta, letras_orig = _barajar_opciones(reactivo)
            items.append(
                {
                    "caso_id": caso["id"],
                    "num_caso": num_caso,
                    "total_casos": len(casos),
                    "reactivo_idx": idx,
                    "reactivo_num": idx + 1,
                    "reactivos_en_caso": total_reactivos_caso,
                    "especialidad": caso["especialidad"],
                    "tema": caso["tema"],
                    "guia_origen": caso["guia_origen"],
                    "vineta": caso["vineta"],
                    "enunciado": reactivo["enunciado"],
                    "nivel": reactivo["nivel"],
                    "opciones": opciones,
                    "letra_correcta": correcta,
                    "letras_originales": letras_orig,
                    "retroalimentacion": reactivo["retroalimentacion"],
                }
            )

    return items


def letra_original(item: dict, letra_mostrada: str | None) -> str | None:
    """Convierte la letra que eligió el alumno a la letra original del banco."""
    if letra_mostrada is None:
        return None
    return item["letras_originales"][LETRAS.index(letra_mostrada)]


def calificar(items: list[dict], respuestas: list[str | None]) -> dict[str, Any]:
    """Calcula puntaje global y desgloses por tema y por nivel."""
    total = len(items)
    aciertos = sum(
        1 for i, item in enumerate(items) if respuestas[i] == item["letra_correcta"]
    )

    por_tema: dict[str, dict[str, int]] = {}
    por_nivel: dict[str, dict[str, int]] = {}

    for i, item in enumerate(items):
        acierto = respuestas[i] == item["letra_correcta"]
        for grupo, clave in ((por_tema, item["tema"]), (por_nivel, item["nivel"])):
            registro = grupo.setdefault(clave, {"total": 0, "aciertos": 0})
            registro["total"] += 1
            registro["aciertos"] += int(acierto)

    return {
        "total": total,
        "aciertos": aciertos,
        "puntaje": (aciertos / total * 100) if total else 0.0,
        "sin_contestar": sum(1 for r in respuestas if r is None),
        "por_tema": por_tema,
        "por_nivel": por_nivel,
    }
