"""
Estilos e identidad visual del simulador.

Toda la apariencia vive aquí para que puedas cambiar colores sin tocar la
lógica. Los colores están fijos (no dependen del modo claro u oscuro del
dispositivo) para que todos los alumnos vean exactamente lo mismo.
"""

import html

# --- Paleta ------------------------------------------------------------------
AZUL = "#2f5d8a"
AZUL_CLARO = "#eaf1f8"
TINTA = "#16202e"
GRIS = "#5b6b7f"
BORDE = "#dde5ee"
PAPEL = "#ffffff"

VERDE = "#12805c"
VERDE_FONDO = "#e4f5ee"
ROJO = "#c0392b"
ROJO_FONDO = "#fdeceb"
AMBAR = "#a06a00"
AMBAR_FONDO = "#fdf3e0"

# Un color por nivel clínico, para que el alumno los distinga de un vistazo.
COLOR_NIVEL = {
    "diagnostico": ("#1f5f8b", "#e3eefa"),
    "tratamiento": ("#6b3fa0", "#f0e9fa"),
    "prevencion": ("#0f7a6c", "#e0f4f1"),
    "pronostico": ("#a85b00", "#fceee0"),
}

ETIQUETA_NIVEL = {
    "diagnostico": "Diagnóstico",
    "tratamiento": "Tratamiento",
    "prevencion": "Prevención",
    "pronostico": "Pronóstico",
}


def color_por_puntaje(puntaje: float) -> tuple[str, str, str]:
    """Devuelve (color, fondo, mensaje) según la calificación obtenida."""
    if puntaje >= 80:
        return VERDE, VERDE_FONDO, "Excelente desempeño"
    if puntaje >= 60:
        return AMBAR, AMBAR_FONDO, "Vas bien, hay temas por reforzar"
    return ROJO, ROJO_FONDO, "Necesitas repasar antes del siguiente intento"


# --- CSS global --------------------------------------------------------------
CSS = f"""
<style>
  .stApp {{ background: #f7f9fc; }}

  /* Tipografía un poco más cómoda para leer viñetas largas */
  .block-container {{ padding-top: 2.2rem; max-width: 1150px; }}

  h1, h2, h3, h4 {{ color: {TINTA}; letter-spacing: -0.01em; }}

  /* Botones */
  .stButton > button {{
    border-radius: 8px;
    border: 1px solid {BORDE};
    font-weight: 600;
    transition: all .15s ease;
  }}
  .stButton > button:hover {{
    border-color: {AZUL};
    color: {AZUL};
  }}

  /* Opciones de respuesta con más aire */
  div[role="radiogroup"] > label {{
    background: {PAPEL};
    border: 1px solid {BORDE};
    border-radius: 9px;
    padding: 11px 14px;
    margin-bottom: 8px;
    width: 100%;
    transition: all .12s ease;
  }}
  div[role="radiogroup"] > label:hover {{
    border-color: {AZUL};
    background: {AZUL_CLARO};
  }}

  /* Métricas */
  div[data-testid="stMetric"] {{
    background: {PAPEL};
    border: 1px solid {BORDE};
    border-radius: 11px;
    padding: 14px 16px;
  }}

  /* Encabezado de la aplicación */
  .enc {{
    background: linear-gradient(120deg, {AZUL} 0%, #4a7fb5 100%);
    color: #fff;
    padding: 26px 30px;
    border-radius: 14px;
    margin-bottom: 22px;
  }}
  .enc h1 {{ color: #fff; margin: 0; font-size: 1.72rem; }}
  .enc p {{ color: #d8e6f5; margin: 6px 0 0; font-size: .95rem; }}

  /* Viñeta del caso clínico */
  .vineta {{
    background: {PAPEL};
    border: 1px solid {BORDE};
    border-left: 5px solid {AZUL};
    color: {TINTA};
    padding: 18px 22px;
    border-radius: 10px;
    line-height: 1.68;
    font-size: 1.03rem;
  }}

  /* Etiquetas de tema y nivel */
  .chip {{
    display: inline-block;
    padding: 3px 11px;
    border-radius: 20px;
    font-size: .76rem;
    font-weight: 700;
    letter-spacing: .02em;
    margin-right: 7px;
  }}

  /* Tarjeta de repaso */
  .tarjeta {{
    background: {PAPEL};
    border: 1px solid {BORDE};
    border-radius: 14px;
    padding: 26px 30px;
    min-height: 260px;
    box-shadow: 0 2px 14px rgba(22,32,46,.07);
  }}
  .tarjeta .pregunta {{
    font-size: 1.13rem;
    font-weight: 700;
    color: {TINTA};
    margin: 16px 0 14px;
    line-height: 1.5;
  }}
  .tarjeta .texto {{ color: {TINTA}; line-height: 1.65; }}
  .tarjeta .fuente {{
    color: {GRIS};
    font-size: .8rem;
    margin-top: 18px;
    padding-top: 12px;
    border-top: 1px dashed {BORDE};
  }}

  .opcion {{
    padding: 9px 13px;
    border-radius: 8px;
    margin-bottom: 7px;
    border: 1px solid {BORDE};
    color: {TINTA};
    line-height: 1.5;
  }}
  .opcion .letra {{ font-weight: 800; margin-right: 8px; }}

  .bloque-retro {{
    background: {AZUL_CLARO};
    border-left: 4px solid {AZUL};
    color: {TINTA};
    padding: 15px 18px;
    border-radius: 8px;
    line-height: 1.65;
    margin-top: 6px;
  }}

  .veredicto {{
    display: inline-block;
    padding: 7px 16px;
    border-radius: 8px;
    font-weight: 800;
    font-size: .92rem;
    margin-bottom: 4px;
  }}

  .marcador {{
    text-align: center;
    padding: 26px 20px;
    border-radius: 14px;
    margin-bottom: 6px;
  }}
  .marcador .cifra {{ font-size: 3.4rem; font-weight: 800; line-height: 1; }}
  .marcador .leyenda {{ font-size: 1rem; font-weight: 600; margin-top: 8px; }}

  /* Barra de tarjetas ya revisadas */
  .pista {{ color: {GRIS}; font-size: .86rem; }}
</style>
"""


def chip(texto: str, color: str, fondo: str) -> str:
    """Etiqueta redondeada de color."""
    return (
        f"<span class='chip' style='color:{color};background:{fondo}'>"
        f"{html.escape(str(texto))}</span>"
    )


def chip_nivel(nivel: str) -> str:
    """Etiqueta del nivel clínico con su color correspondiente."""
    color, fondo = COLOR_NIVEL.get(nivel, (GRIS, "#eef1f5"))
    return chip(ETIQUETA_NIVEL.get(nivel, nivel.capitalize()), color, fondo)


def chip_tema(tema: str) -> str:
    """Etiqueta del tema del caso."""
    return chip(tema, AZUL, AZUL_CLARO)


def encabezado(titulo: str, subtitulo: str = "") -> str:
    """Banda superior con degradado."""
    sub = f"<p>{html.escape(subtitulo)}</p>" if subtitulo else ""
    return f"<div class='enc'><h1>{html.escape(titulo)}</h1>{sub}</div>"


def vineta(texto: str) -> str:
    """Recuadro del caso clínico."""
    return f"<div class='vineta'>{html.escape(texto)}</div>"


def opcion(letra: str, texto: str, estado: str = "neutro") -> str:
    """Una opción de respuesta.

    estado: 'correcta', 'elegida_mal' o 'neutro'.
    """
    if estado == "correcta":
        estilo = f"background:{VERDE_FONDO};border-color:{VERDE};color:{VERDE}"
        marca = " ✓"
    elif estado == "elegida_mal":
        estilo = f"background:{ROJO_FONDO};border-color:{ROJO};color:{ROJO}"
        marca = " ✕"
    else:
        estilo = ""
        marca = ""
    return (
        f"<div class='opcion' style='{estilo}'>"
        f"<span class='letra'>{letra})</span>{html.escape(texto)}{marca}</div>"
    )


def veredicto(estado: str) -> str:
    """Sello de resultado del reactivo."""
    mapa = {
        "correcta": ("Respondiste bien", VERDE, VERDE_FONDO),
        "incorrecta": ("Respondiste mal", ROJO, ROJO_FONDO),
        "sin_contestar": ("No contestaste", AMBAR, AMBAR_FONDO),
    }
    texto, color, fondo = mapa[estado]
    return (
        f"<span class='veredicto' style='color:{color};background:{fondo}'>"
        f"{texto}</span>"
    )


def marcador(puntaje: float, aciertos: int, total: int) -> str:
    """Bloque grande con la calificación de la sesión."""
    color, fondo, mensaje = color_por_puntaje(puntaje)
    return (
        f"<div class='marcador' style='background:{fondo}'>"
        f"<div class='cifra' style='color:{color}'>{puntaje:.0f}%</div>"
        f"<div class='leyenda' style='color:{color}'>{mensaje}</div>"
        f"<div style='color:{color};opacity:.8;font-size:.9rem;margin-top:4px'>"
        f"{aciertos} de {total} reactivos correctos</div></div>"
    )
