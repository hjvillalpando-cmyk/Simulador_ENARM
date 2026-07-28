"""
Simulador de casos clínicos ENARM — aplicación Streamlit.

Ejecutar con:  streamlit run app.py
"""

import html
import json
import time

import pandas as pd
import plotly.express as px
import streamlit as st

import estilos

from auth import (
    cambiar_password_docente,
    entrar_como_alumno,
    entrar_como_docente,
)
from banco import (
    BancoInvalido,
    auditar_banco,
    cargar_banco,
    casos_por_especialidad,
    especialidades_disponibles,
)
from config import (
    DOCENTE_PASSWORD_INICIAL,
    NOMBRE_INSTITUCION,
    NUM_CASOS_POR_SESION,
    RUTA_BANCO,
    TITULO_APP,
)
from db import Respuesta, Sesion, Usuario, ahora_utc, init_db, obtener_sesion
from motor_examen import (
    calificar,
    construir_examen,
    letra_original,
    seleccionar_casos,
)
from reportes import generar_excel_grupo, generar_pdf_sesion

st.set_page_config(page_title=TITULO_APP, page_icon="🩺", layout="wide")
st.markdown(estilos.CSS, unsafe_allow_html=True)

init_db()


# --------------------------------------------------------------------------- #
# Estado
# --------------------------------------------------------------------------- #
def _estado_inicial():
    st.session_state.setdefault("usuario", None)
    st.session_state.setdefault("rol", None)
    st.session_state.setdefault("pagina", "acceso")
    st.session_state.setdefault("examen", None)
    st.session_state.setdefault("resultado", None)


def cerrar_sesion():
    for clave in ("usuario", "rol", "pagina", "examen", "resultado"):
        st.session_state[clave] = None
    st.session_state["pagina"] = "acceso"


def ir_a(pagina: str):
    st.session_state["pagina"] = pagina


_estado_inicial()


# --------------------------------------------------------------------------- #
# Acceso
# --------------------------------------------------------------------------- #
def pantalla_acceso():
    st.markdown(estilos.encabezado(f"🩺 {TITULO_APP}", NOMBRE_INSTITUCION),
                unsafe_allow_html=True)

    tab_alumno, tab_docente = st.tabs(["Alumnos", "Docente"])

    with tab_alumno:
        st.write(
            "Entra con tu matrícula. Si ya la habías usado antes, "
            "recuperas tu historial."
        )
        with st.form("acceso_alumno"):
            matricula = st.text_input("Matrícula")
            nombre = st.text_input("Nombre completo")
            entrar = st.form_submit_button("Entrar", type="primary")

        if entrar:
            try:
                with obtener_sesion() as db:
                    alumno = entrar_como_alumno(db, matricula, nombre)
                    st.session_state["usuario"] = {
                        "id": alumno.id,
                        "nombre": alumno.nombre,
                        "matricula": alumno.matricula,
                    }
                st.session_state["rol"] = "alumno"
                ir_a("inicio_alumno")
                st.rerun()
            except ValueError as e:
                st.error(str(e))

    with tab_docente:
        with st.form("acceso_docente"):
            usuario_doc = st.text_input("Usuario")
            clave = st.text_input("Contraseña", type="password")
            entrar_doc = st.form_submit_button("Entrar", type="primary")

        if entrar_doc:
            with obtener_sesion() as db:
                docente = entrar_como_docente(db, usuario_doc, clave)
                if docente is None:
                    st.error("Usuario o contraseña incorrectos.")
                else:
                    st.session_state["usuario"] = {
                        "id": docente.id,
                        "nombre": docente.nombre,
                        "matricula": docente.matricula,
                    }
                    st.session_state["rol"] = "docente"
                    ir_a("panel_docente")
                    st.rerun()


# --------------------------------------------------------------------------- #
# Inicio del alumno
# --------------------------------------------------------------------------- #
def pantalla_inicio_alumno():
    usuario = st.session_state["usuario"]
    st.markdown(
        estilos.encabezado(
            f"Hola, {usuario['nombre'].title()}",
            f"Matrícula {usuario['matricula']}",
        ),
        unsafe_allow_html=True,
    )

    col_izq, col_der = st.columns([3, 2])

    with col_izq:
        st.subheader("Nueva sesión de examen")

        try:
            banco = cargar_banco(RUTA_BANCO)
        except BancoInvalido as e:
            st.error(f"No se puede iniciar el examen. {e}")
            banco = None

        if banco:
            especialidades = especialidades_disponibles(banco)

            # Cuántos casos tiene cada especialidad, para orientar al alumno.
            conteo = {}
            for esp in especialidades:
                conteo[esp] = len(casos_por_especialidad(banco, esp))

            st.write(
                "Elige una **especialidad** para concentrarte en ella, o "
                "practica con todas mezcladas como en el examen real."
            )
            especialidad = st.selectbox(
                "Especialidad",
                especialidades,
                format_func=lambda e: f"{e}  ({conteo[e]} casos)",
            )

            disponibles = conteo[especialidad]
            objetivo = min(NUM_CASOS_POR_SESION, disponibles)

            st.caption(
                f"Esta sesión te presentará {objetivo} caso(s) de "
                f"**{especialidad.lower()}**, elegidos al azar y evitando los "
                "que resolviste hace poco. La retroalimentación aparece al final."
            )

            if disponibles == 0:
                st.warning("Esta especialidad todavía no tiene casos cargados.")
            elif st.button("Iniciar examen", type="primary"):
                casos_filtrados = casos_por_especialidad(banco, especialidad)
                with obtener_sesion() as db:
                    casos = seleccionar_casos(db, usuario["id"], casos_filtrados)
                items = construir_examen(casos)
                st.session_state["examen"] = {
                    "items": items,
                    "respuestas": [None] * len(items),
                    "marcados": [False] * len(items),
                    "tiempos": [0] * len(items),
                    "actual": 0,
                    "inicio_item": time.time(),
                    "inicio_sesion": ahora_utc(),
                    "especialidad": especialidad,
                }
                ir_a("examen")
                st.rerun()

    with col_der:
        st.subheader("Tu historial")
        with obtener_sesion() as db:
            sesiones = (
                db.query(Sesion)
                .filter(Sesion.usuario_id == usuario["id"])
                .order_by(Sesion.fecha_inicio.desc())
                .all()
            )
            datos = [
                {
                    "Fecha": s.fecha_inicio.strftime("%d/%m/%Y %H:%M"),
                    "Puntaje": round(s.puntaje, 1),
                    "Aciertos": f"{s.aciertos}/{s.total_reactivos}",
                }
                for s in sesiones
            ]

        if not datos:
            st.info("Todavía no has presentado ninguna sesión.")
        else:
            promedio = sum(d["Puntaje"] for d in datos) / len(datos)
            st.metric("Promedio", f"{promedio:.1f}%", help="Promedio de todas tus sesiones")
            st.dataframe(pd.DataFrame(datos), hide_index=True, use_container_width=True)
            if len(datos) > 1:
                df = pd.DataFrame(datos[::-1]).reset_index()
                fig = px.line(df, x="index", y="Puntaje", markers=True)
                fig.update_layout(
                    height=220, margin=dict(l=0, r=0, t=10, b=0),
                    xaxis_title="Sesión", yaxis_title="%", yaxis_range=[0, 100],
                )
                st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------------------------------- #
# Examen
# --------------------------------------------------------------------------- #
def _guardar_tiempo(examen):
    """Suma al reactivo actual el tiempo transcurrido desde que se mostró."""
    idx = examen["actual"]
    examen["tiempos"][idx] += int(time.time() - examen["inicio_item"])
    examen["inicio_item"] = time.time()


def _mover_a(examen, destino: int):
    _guardar_tiempo(examen)
    examen["actual"] = destino
    st.rerun()


def pantalla_examen():
    examen = st.session_state["examen"]
    items = examen["items"]
    idx = examen["actual"]
    item = items[idx]
    total = len(items)

    contestados = sum(1 for r in examen["respuestas"] if r is not None)

    with st.sidebar:
        st.markdown("### Avance")
        st.progress(contestados / total, text=f"{contestados} de {total} contestados")
        st.caption("✓ contestado · 🚩 marcado para revisar")

        columnas = st.columns(5)
        for i in range(total):
            etiqueta = str(i + 1)
            if examen["marcados"][i]:
                etiqueta = f"🚩{i + 1}"
            elif examen["respuestas"][i] is not None:
                etiqueta = f"✓{i + 1}"
            if columnas[i % 5].button(etiqueta, key=f"nav_{i}", use_container_width=True):
                _mover_a(examen, i)

        st.divider()
        if st.button("Terminar y calificar", use_container_width=True):
            _guardar_tiempo(examen)
            finalizar_examen()

    # Encabezado del caso
    st.markdown(
        estilos.chip_tema(item["tema"])
        + estilos.chip_nivel(item["nivel"])
        + f"<span class='pista'>{html.escape(item['especialidad'])}</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='pista' style='margin:10px 0 4px'>Caso {item['num_caso']} de "
        f"{item['total_casos']} · reactivo {item['reactivo_num']} de "
        f"{item['reactivos_en_caso']} de este caso</div>",
        unsafe_allow_html=True,
    )
    st.progress((idx + 1) / total, text=f"Reactivo {idx + 1} de {total}")

    st.markdown(estilos.vineta(item["vineta"]), unsafe_allow_html=True)
    st.write("")
    st.markdown(
        f"<div style='font-size:1.1rem;font-weight:700;color:{estilos.TINTA};"
        f"margin-bottom:6px'>{html.escape(item['enunciado'])}</div>",
        unsafe_allow_html=True,
    )

    letras = ["A", "B", "C", "D"]
    valor_previo = examen["respuestas"][idx]
    indice_previo = letras.index(valor_previo) if valor_previo else None

    eleccion = st.radio(
        "Selecciona una respuesta",
        options=letras,
        index=indice_previo,  # None = sin preseleccionar
        format_func=lambda l: f"{l}) {item['opciones'][letras.index(l)]}",
        key=f"radio_{idx}",
        label_visibility="collapsed",
    )
    examen["respuestas"][idx] = eleccion

    examen["marcados"][idx] = st.checkbox(
        "Marcar para revisar después",
        value=examen["marcados"][idx],
        key=f"marca_{idx}",
    )

    st.divider()
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        if idx > 0 and st.button("← Anterior", use_container_width=True):
            _mover_a(examen, idx - 1)
    with c3:
        if idx < total - 1:
            if st.button("Siguiente →", type="primary", use_container_width=True):
                _mover_a(examen, idx + 1)
        else:
            if st.button("Terminar examen", type="primary", use_container_width=True):
                _guardar_tiempo(examen)
                finalizar_examen()

    if contestados < total:
        st.caption(f"Te faltan {total - contestados} reactivo(s) por contestar.")


def finalizar_examen():
    """Califica, guarda en la base de datos y pasa a la pantalla de resultados."""
    examen = st.session_state["examen"]
    usuario = st.session_state["usuario"]
    items = examen["items"]
    respuestas = examen["respuestas"]

    resumen = calificar(items, respuestas)

    with obtener_sesion() as db:
        sesion = Sesion(
            usuario_id=usuario["id"],
            fecha_inicio=examen["inicio_sesion"],
            fecha_fin=ahora_utc(),
            puntaje=resumen["puntaje"],
            aciertos=resumen["aciertos"],
            total_reactivos=resumen["total"],
            casos_json=json.dumps(sorted({i["caso_id"] for i in items})),
            especialidad=examen.get("especialidad"),
        )
        db.add(sesion)
        db.flush()  # obtiene sesion.id sin cerrar la transacción

        for i, item in enumerate(items):
            db.add(
                Respuesta(
                    sesion_id=sesion.id,
                    caso_id=item["caso_id"],
                    reactivo_idx=item["reactivo_idx"],
                    tema=item["tema"],
                    nivel=item["nivel"],
                    # Se guarda la letra ORIGINAL del banco, no la que se mostró
                    # barajada, para que el análisis de reactivos sea comparable.
                    respuesta_alumno=letra_original(item, respuestas[i]),
                    correcta_bool=respuestas[i] == item["letra_correcta"],
                    segundos_empleados=examen["tiempos"][i],
                )
            )
        sesion_id = sesion.id
        fecha_txt = sesion.fecha_inicio.strftime("%d/%m/%Y %H:%M")

    st.session_state["resultado"] = {
        "sesion_id": sesion_id,
        "fecha": fecha_txt,
        "resumen": resumen,
        "items": items,
        "respuestas": respuestas,
    }
    st.session_state["examen"] = None
    ir_a("resultados")
    st.rerun()


# --------------------------------------------------------------------------- #
# Resultados
# --------------------------------------------------------------------------- #
def _grafica_desglose(datos: dict, titulo: str):
    """Barras apiladas de aciertos y errores por categoría."""
    filas = []
    for clave, d in datos.items():
        filas.append({"Categoría": clave, "Resultado": "Correcto", "Reactivos": d["aciertos"]})
        filas.append(
            {"Categoría": clave, "Resultado": "Incorrecto", "Reactivos": d["total"] - d["aciertos"]}
        )
    df = pd.DataFrame(filas)
    fig = px.bar(
        df, x="Categoría", y="Reactivos", color="Resultado", barmode="stack",
        color_discrete_map={"Correcto": estilos.VERDE, "Incorrecto": estilos.ROJO},
        title=titulo,
    )
    fig.update_layout(
        height=340, margin=dict(l=0, r=0, t=44, b=0), xaxis_title="",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.18, title=""),
    )
    return fig


def _estado_reactivo(item: dict, elegida: str | None) -> str:
    """Clasifica el resultado de un reactivo."""
    if elegida is None:
        return "sin_contestar"
    return "correcta" if elegida == item["letra_correcta"] else "incorrecta"


# --- Tarjetas de repaso ----------------------------------------------------- #
def _tarjetas_filtradas(items, respuestas, filtro: str) -> list[int]:
    """Índices de los reactivos que entran en el filtro elegido."""
    indices = []
    for i, item in enumerate(items):
        estado = _estado_reactivo(item, respuestas[i])
        if filtro == "Solo las que fallé" and estado == "correcta":
            continue
        if filtro == "Solo las que acerté" and estado != "correcta":
            continue
        indices.append(i)
    return indices


def repaso_con_tarjetas(items, respuestas):
    """Repaso tipo flash card: primero la pregunta, luego la respuesta."""
    st.session_state.setdefault("flash_i", 0)
    st.session_state.setdefault("flash_ver", False)
    st.session_state.setdefault("flash_filtro", "Todas")

    filtro = st.radio(
        "Mostrar",
        ["Todas", "Solo las que fallé", "Solo las que acerté"],
        horizontal=True,
        key="flash_filtro",
        label_visibility="collapsed",
    )

    if st.session_state.get("_flash_filtro_previo") != filtro:
        st.session_state["_flash_filtro_previo"] = filtro
        st.session_state["flash_i"] = 0
        st.session_state["flash_ver"] = False

    indices = _tarjetas_filtradas(items, respuestas, filtro)
    if not indices:
        st.success("No hay tarjetas en este filtro. ¡Contestaste todo bien!")
        return

    # Si el filtro cambió y el índice se salió de rango, se reinicia.
    if st.session_state["flash_i"] >= len(indices):
        st.session_state["flash_i"] = 0

    pos = st.session_state["flash_i"]
    i = indices[pos]
    item = items[i]
    elegida = respuestas[i]
    correcta = item["letra_correcta"]
    estado = _estado_reactivo(item, elegida)
    letras = ["A", "B", "C", "D"]

    st.markdown(
        f"<div class='pista'>Tarjeta {pos + 1} de {len(indices)} · "
        f"Caso {item['num_caso']}</div>",
        unsafe_allow_html=True,
    )
    st.progress((pos + 1) / len(indices))

    # --- Cara frontal: el caso y la pregunta ---
    cuerpo = (
        estilos.chip_tema(item["tema"])
        + estilos.chip_nivel(item["nivel"])
        + f"<div style='margin-top:16px' class='texto'>{html.escape(item['vineta'])}</div>"
        + f"<div class='pregunta'>{html.escape(item['enunciado'])}</div>"
    )

    if not st.session_state["flash_ver"]:
        # Aún no se revela: las opciones se ven neutras, para volver a pensarla.
        for k, texto in enumerate(item["opciones"]):
            cuerpo += estilos.opcion(letras[k], texto)
        cuerpo += (
            "<div class='fuente'>Piensa tu respuesta y voltea la tarjeta "
            "para comprobarla.</div>"
        )
    else:
        # --- Cara posterior: la respuesta y el porqué ---
        cuerpo += estilos.veredicto(estado) + "<div style='height:10px'></div>"
        for k, texto in enumerate(item["opciones"]):
            letra = letras[k]
            if letra == correcta:
                marca = "correcta"
            elif letra == elegida:
                marca = "elegida_mal"
            else:
                marca = "neutro"
            cuerpo += estilos.opcion(letra, texto, marca)
        if estado == "sin_contestar":
            cuerpo += (
                f"<div style='color:{estilos.AMBAR};font-size:.88rem;margin:6px 0'>"
                "Dejaste este reactivo en blanco.</div>"
            )
        cuerpo += (
            "<div style='height:12px'></div>"
            f"<div class='bloque-retro'>{html.escape(item['retroalimentacion'])}</div>"
            f"<div class='fuente'>Fuente: {html.escape(item['guia_origen'])}</div>"
        )

    st.markdown(f"<div class='tarjeta'>{cuerpo}</div>", unsafe_allow_html=True)
    st.write("")

    c1, c2, c3 = st.columns([1, 1.6, 1])
    with c1:
        if st.button("← Anterior", use_container_width=True, disabled=pos == 0):
            st.session_state["flash_i"] -= 1
            st.session_state["flash_ver"] = False
            st.rerun()
    with c2:
        etiqueta = "Ocultar respuesta" if st.session_state["flash_ver"] else "Ver respuesta"
        if st.button(etiqueta, type="primary", use_container_width=True):
            st.session_state["flash_ver"] = not st.session_state["flash_ver"]
            st.rerun()
    with c3:
        ultima = pos == len(indices) - 1
        if st.button("Siguiente →", use_container_width=True, disabled=ultima):
            st.session_state["flash_i"] += 1
            st.session_state["flash_ver"] = False
            st.rerun()

    if pos == len(indices) - 1 and st.session_state["flash_ver"]:
        st.success("Terminaste el repaso de esta sesión.")


def lista_completa(items, respuestas):
    """Vista compacta: todos los reactivos en acordeón."""
    letras = ["A", "B", "C", "D"]
    caso_actual = None

    for i, item in enumerate(items):
        if item["caso_id"] != caso_actual:
            caso_actual = item["caso_id"]
            st.markdown(
                f"<div style='margin:18px 0 8px'>{estilos.chip_tema(item['tema'])}"
                f"<span style='color:{estilos.GRIS};font-size:.85rem'>"
                f"Caso {item['num_caso']}</span></div>",
                unsafe_allow_html=True,
            )

        elegida = respuestas[i]
        estado = _estado_reactivo(item, elegida)
        icono = {"correcta": "✅", "incorrecta": "❌", "sin_contestar": "⬜"}[estado]

        with st.expander(f"{icono}  {item['enunciado']}"):
            st.markdown(estilos.vineta(item["vineta"]), unsafe_allow_html=True)
            st.write("")
            bloque = ""
            for k, texto in enumerate(item["opciones"]):
                letra = letras[k]
                if letra == item["letra_correcta"]:
                    marca = "correcta"
                elif letra == elegida:
                    marca = "elegida_mal"
                else:
                    marca = "neutro"
                bloque += estilos.opcion(letra, texto, marca)
            bloque += (
                f"<div class='bloque-retro'>{html.escape(item['retroalimentacion'])}</div>"
            )
            st.markdown(bloque, unsafe_allow_html=True)
            st.caption(f"Fuente: {item['guia_origen']} · {estilos.ETIQUETA_NIVEL.get(item['nivel'], item['nivel'])}")


def pantalla_resultados():
    res = st.session_state["resultado"]
    usuario = st.session_state["usuario"]
    resumen = res["resumen"]
    items = res["items"]
    respuestas = res["respuestas"]

    st.markdown(
        estilos.encabezado(
            "Resultados de la sesión",
            f"{usuario['nombre'].title()} · {res['fecha']}",
        ),
        unsafe_allow_html=True,
    )

    c_marc, c_datos = st.columns([1, 2])
    with c_marc:
        st.markdown(
            estilos.marcador(resumen["puntaje"], resumen["aciertos"], resumen["total"]),
            unsafe_allow_html=True,
        )
    with c_datos:
        d1, d2, d3 = st.columns(3)
        d1.metric("Casos", len({i["caso_id"] for i in items}))
        d2.metric("Reactivos", resumen["total"])
        d3.metric("Sin contestar", resumen["sin_contestar"])

        debiles = sorted(
            t for t, d in resumen["por_tema"].items() if d["aciertos"] / d["total"] < 0.6
        )
        fuertes = sorted(
            t for t, d in resumen["por_tema"].items() if d["aciertos"] / d["total"] == 1.0
        )
        if debiles:
            st.markdown(
                "**Para repasar:** "
                + " ".join(estilos.chip(t, estilos.ROJO, estilos.ROJO_FONDO) for t in debiles),
                unsafe_allow_html=True,
            )
        if fuertes:
            st.markdown(
                "**Dominados:** "
                + " ".join(estilos.chip(t, estilos.VERDE, estilos.VERDE_FONDO) for t in fuertes),
                unsafe_allow_html=True,
            )

    st.write("")
    t_tarjetas, t_graficas, t_lista = st.tabs(
        ["Tarjetas de repaso", "Tu desempeño", "Lista completa"]
    )

    with t_tarjetas:
        st.caption(
            "Vuelve a pensar cada caso antes de voltear la tarjeta. "
            "Es la parte que de verdad hace que se te quede."
        )
        repaso_con_tarjetas(items, respuestas)

    with t_graficas:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(
                _grafica_desglose(resumen["por_tema"], "Por tema"),
                use_container_width=True,
            )
        with col2:
            niveles = {
                estilos.ETIQUETA_NIVEL.get(k, k): v for k, v in resumen["por_nivel"].items()
            }
            st.plotly_chart(
                _grafica_desglose(niveles, "Por nivel clínico"),
                use_container_width=True,
            )

    with t_lista:
        lista_completa(items, respuestas)

    st.divider()
    pdf_bytes = generar_pdf_sesion(
        nombre=usuario["nombre"],
        matricula=usuario["matricula"],
        sesion_id=res["sesion_id"],
        resumen=resumen,
        items=items,
        respuestas=respuestas,
        fecha=res["fecha"],
    )
    c_pdf, c_volver = st.columns(2)
    c_pdf.download_button(
        "Descargar informe en PDF",
        data=pdf_bytes,
        file_name=f"ENARM_sesion_{res['sesion_id']}_{usuario['matricula']}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
    if c_volver.button("Volver al inicio", type="primary", use_container_width=True):
        for k in ("flash_i", "flash_ver", "_flash_filtro_previo"):
            st.session_state.pop(k, None)
        ir_a("inicio_alumno")
        st.rerun()


# --------------------------------------------------------------------------- #
# Panel docente
# --------------------------------------------------------------------------- #
def pantalla_panel_docente():
    st.markdown(
        estilos.encabezado("Panel docente", NOMBRE_INSTITUCION),
        unsafe_allow_html=True,
    )

    if DOCENTE_PASSWORD_INICIAL == "cambiar123":
        st.warning(
            "Estás usando la contraseña inicial. Cámbiala en la pestaña "
            "**Administración** antes de compartir la aplicación."
        )

    t_grupo, t_alumno, t_reactivos, t_admin = st.tabs(
        ["Grupo", "Por alumno", "Reactivos", "Administración"]
    )

    with obtener_sesion() as db:
        alumnos = db.query(Usuario).filter(Usuario.rol == "alumno").order_by(Usuario.nombre).all()
        sesiones = db.query(Sesion).all()
        respuestas = db.query(Respuesta).all()

        datos_alumnos = [
            {
                "id": a.id,
                "matricula": a.matricula,
                "nombre": a.nombre,
                "sesiones": len(a.sesiones),
                "promedio": (sum(s.puntaje for s in a.sesiones) / len(a.sesiones))
                if a.sesiones else 0.0,
                "ultima": max((s.fecha_inicio for s in a.sesiones), default=None),
            }
            for a in alumnos
        ]
        datos_sesiones = [
            {
                "usuario_id": s.usuario_id,
                "fecha": s.fecha_inicio,
                "puntaje": s.puntaje,
                "aciertos": s.aciertos,
                "total": s.total_reactivos,
                "especialidad": s.especialidad or "Todas las especialidades",
            }
            for s in sesiones
        ]
        datos_respuestas = [
            {
                "usuario_id": r.sesion.usuario_id,
                "caso_id": r.caso_id,
                "reactivo": r.reactivo_idx + 1,
                "tema": r.tema,
                "nivel": r.nivel,
                "correcta": r.correcta_bool,
                "segundos": r.segundos_empleados,
            }
            for r in respuestas
        ]
        excel_bytes = generar_excel_grupo(db)

    # --- Grupo ---
    with t_grupo:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Alumnos", len(datos_alumnos))
        c2.metric("Sesiones", len(datos_sesiones))
        prom = (
            sum(s["puntaje"] for s in datos_sesiones) / len(datos_sesiones)
            if datos_sesiones else 0.0
        )
        c3.metric("Promedio del grupo", f"{prom:.1f}%")
        activos = sum(1 for a in datos_alumnos if a["sesiones"] > 0)
        c4.metric("Han presentado", f"{activos} de {len(datos_alumnos)}")

        if datos_alumnos:
            df = pd.DataFrame(
                [
                    {
                        "Matrícula": a["matricula"],
                        "Nombre": a["nombre"].title(),
                        "Sesiones": a["sesiones"],
                        "Promedio (%)": round(a["promedio"], 1),
                        "Última sesión": a["ultima"].strftime("%d/%m/%Y %H:%M")
                        if a["ultima"] else "—",
                    }
                    for a in datos_alumnos
                ]
            )
            st.dataframe(df, hide_index=True, use_container_width=True)

        if datos_respuestas:
            df_r = pd.DataFrame(datos_respuestas)
            por_tema = (
                df_r.groupby("tema", as_index=False)
                .agg(Reactivos=("correcta", "count"), Aciertos=("correcta", "sum"))
            )
            por_tema["Aciertos (%)"] = (
                por_tema["Aciertos"] / por_tema["Reactivos"] * 100
            ).round(1)
            por_tema = por_tema.sort_values("Aciertos (%)")
            fig = px.bar(
                por_tema, x="Aciertos (%)", y="tema", orientation="h",
                title="Desempeño del grupo por tema (de menor a mayor)",
            )
            fig.update_layout(height=max(300, 28 * len(por_tema)), yaxis_title="",
                              xaxis_range=[0, 100], margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)

        st.download_button(
            "Descargar reporte del grupo (Excel)",
            data=excel_bytes,
            file_name="reporte_grupo_enarm.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # --- Por alumno ---
    with t_alumno:
        if not datos_alumnos:
            st.info("Aún no hay alumnos registrados.")
        else:
            opciones = {
                f"{a['nombre'].title()} ({a['matricula']})": a["id"] for a in datos_alumnos
            }
            elegido = st.selectbox("Alumno", list(opciones.keys()))
            uid = opciones[elegido]

            ses_alumno = sorted(
                [s for s in datos_sesiones if s["usuario_id"] == uid],
                key=lambda s: s["fecha"],
            )
            if not ses_alumno:
                st.info("Este alumno todavía no ha presentado ninguna sesión.")
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric("Sesiones", len(ses_alumno))
                c2.metric(
                    "Promedio",
                    f"{sum(s['puntaje'] for s in ses_alumno) / len(ses_alumno):.1f}%",
                )
                delta = (
                    ses_alumno[-1]["puntaje"] - ses_alumno[0]["puntaje"]
                    if len(ses_alumno) > 1 else 0
                )
                c3.metric("Última", f"{ses_alumno[-1]['puntaje']:.1f}%",
                          delta=f"{delta:+.1f} pts desde la primera")

                df_s = pd.DataFrame(
                    [
                        {"Sesión": i + 1, "Fecha": s["fecha"].strftime("%d/%m/%Y"),
                         "Puntaje": round(s["puntaje"], 1),
                         "Especialidad": s["especialidad"]}
                        for i, s in enumerate(ses_alumno)
                    ]
                )
                fig = px.line(df_s, x="Sesión", y="Puntaje", markers=True,
                              hover_data=["Fecha", "Especialidad"],
                              title="Curva de aprendizaje")
                fig.update_layout(height=300, yaxis_range=[0, 100],
                                  margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig, use_container_width=True)

                # Avance por especialidad: cuántas sesiones y qué promedio
                # lleva el alumno en cada una.
                por_esp = (
                    df_s.groupby("Especialidad", as_index=False)
                    .agg(Sesiones=("Puntaje", "count"),
                         Promedio=("Puntaje", "mean"),
                         Mejor=("Puntaje", "max"))
                )
                por_esp["Promedio"] = por_esp["Promedio"].round(1)
                st.markdown("**Avance por especialidad**")
                st.dataframe(
                    por_esp.sort_values("Promedio"),
                    hide_index=True, use_container_width=True,
                )

                resp_alumno = [r for r in datos_respuestas if r["usuario_id"] == uid]
                if resp_alumno:
                    df_ra = pd.DataFrame(resp_alumno)
                    resumen_tema = (
                        df_ra.groupby("tema", as_index=False)
                        .agg(Reactivos=("correcta", "count"),
                             Aciertos=("correcta", "sum"),
                             Segundos=("segundos", "mean"))
                    )
                    resumen_tema["Aciertos (%)"] = (
                        resumen_tema["Aciertos"] / resumen_tema["Reactivos"] * 100
                    ).round(1)
                    resumen_tema["Segundos"] = resumen_tema["Segundos"].round(0)
                    st.markdown("**Desempeño por tema**")
                    st.dataframe(
                        resumen_tema.sort_values("Aciertos (%)").rename(
                            columns={"tema": "Tema", "Segundos": "Segundos por reactivo"}
                        ),
                        hide_index=True, use_container_width=True,
                    )

    # --- Reactivos ---
    with t_reactivos:
        st.write(
            "Reactivos con mayor tasa de error. Sirven para decidir qué temas "
            "reforzar en clase y para detectar reactivos mal redactados."
        )
        if not datos_respuestas:
            st.info("Todavía no hay respuestas registradas.")
        else:
            df_r = pd.DataFrame(datos_respuestas)
            analisis = (
                df_r.groupby(["caso_id", "reactivo", "tema", "nivel"], as_index=False)
                .agg(Presentaciones=("correcta", "count"),
                     Aciertos=("correcta", "sum"),
                     Segundos=("segundos", "mean"))
            )
            analisis["Tasa de error (%)"] = (
                (1 - analisis["Aciertos"] / analisis["Presentaciones"]) * 100
            ).round(1)
            analisis["Segundos"] = analisis["Segundos"].round(0)
            analisis = analisis.rename(
                columns={"caso_id": "Caso", "reactivo": "Reactivo",
                         "tema": "Tema", "nivel": "Nivel",
                         "Segundos": "Segundos promedio"}
            ).sort_values("Tasa de error (%)", ascending=False)

            minimo = st.slider("Mostrar solo reactivos presentados al menos N veces",
                               1, 10, 1)
            st.dataframe(
                analisis[analisis["Presentaciones"] >= minimo],
                hide_index=True, use_container_width=True,
            )
            st.caption(
                "Un reactivo con más de 80% de error casi siempre está mal "
                "redactado o tiene dos opciones defendibles. Vale la pena revisarlo."
            )

    # --- Administración ---
    with t_admin:
        st.subheader("Banco de casos")
        try:
            banco = cargar_banco(RUTA_BANCO)
            auditoria = auditar_banco(banco)
            c1, c2, c3 = st.columns(3)
            c1.metric("Casos", auditoria["total_casos"])
            c2.metric("Reactivos", auditoria["total_reactivos"])
            c3.metric("Temas", len(auditoria["distribucion_temas"]))

            st.write("**Distribución de la respuesta correcta**")
            st.write(
                " · ".join(
                    f"{letra}: {n}" for letra, n in sorted(auditoria["distribucion_letras"].items())
                )
            )
            for alerta in auditoria["alertas"]:
                st.warning(alerta)
            if not auditoria["alertas"]:
                st.success("El banco pasó todas las revisiones de calidad.")
        except BancoInvalido as e:
            st.error(str(e))

        archivo = st.file_uploader("Subir un nuevo casos.json", type=["json"])
        if archivo is not None and st.button("Reemplazar banco de casos"):
            contenido = archivo.read().decode("utf-8")
            try:
                import json as _json

                from banco import validar_estructura

                datos = _json.loads(contenido)
                errores = validar_estructura(datos)
                if errores:
                    st.error(f"El archivo tiene {len(errores)} error(es). Primero: {errores[0]}")
                else:
                    with open(RUTA_BANCO, "w", encoding="utf-8") as f:
                        f.write(contenido)
                    st.success("Banco reemplazado. Recarga la página para verlo.")
            except Exception as e:
                st.error(f"No se pudo procesar el archivo: {e}")

        st.divider()
        st.subheader("Fusionar registros duplicados")
        st.caption(
            "Si un alumno se registró dos veces con matrículas distintas, "
            "aquí puedes pasar todas sus sesiones a un solo registro."
        )
        if len(datos_alumnos) >= 2:
            etiquetas = {
                f"{a['nombre'].title()} ({a['matricula']}) — {a['sesiones']} sesión(es)": a["id"]
                for a in datos_alumnos
            }
            col_o, col_d = st.columns(2)
            origen_txt = col_o.selectbox("Registro que se elimina", list(etiquetas.keys()))
            destino_opciones = [k for k in etiquetas if etiquetas[k] != etiquetas[origen_txt]]
            destino_txt = col_d.selectbox("Registro que se conserva", destino_opciones)

            confirmar = st.checkbox("Entiendo que esta acción no se puede deshacer")
            if st.button("Fusionar", disabled=not confirmar):
                id_origen, id_destino = etiquetas[origen_txt], etiquetas[destino_txt]
                with obtener_sesion() as db:
                    # Primero se mueven las sesiones, luego se borra el usuario
                    # con delete a nivel SQL para que la cascada ORM no arrastre
                    # las sesiones recién transferidas.
                    db.query(Sesion).filter(Sesion.usuario_id == id_origen).update(
                        {"usuario_id": id_destino}, synchronize_session=False
                    )
                    db.flush()
                    db.query(Usuario).filter(Usuario.id == id_origen).delete(
                        synchronize_session=False
                    )
                st.success("Registros fusionados.")
                st.rerun()
        else:
            st.info("Se necesitan al menos dos alumnos registrados.")

        st.divider()
        st.subheader("Cambiar contraseña")
        with st.form("cambio_clave"):
            nueva = st.text_input("Contraseña nueva", type="password")
            repetir = st.text_input("Repetir contraseña", type="password")
            guardar = st.form_submit_button("Guardar")
        if guardar:
            if nueva != repetir:
                st.error("Las contraseñas no coinciden.")
            else:
                try:
                    with obtener_sesion() as db:
                        cambiar_password_docente(db, st.session_state["usuario"]["id"], nueva)
                    st.success("Contraseña actualizada.")
                except ValueError as e:
                    st.error(str(e))


# --------------------------------------------------------------------------- #
# Enrutador
# --------------------------------------------------------------------------- #
def main():
    if st.session_state["usuario"]:
        with st.sidebar:
            st.markdown(f"**{st.session_state['usuario']['nombre'].title()}**")
            st.caption(st.session_state["rol"].capitalize())
            if st.session_state["pagina"] != "examen":
                if st.button("Salir", use_container_width=True):
                    cerrar_sesion()
                    st.rerun()
            st.divider()

    pagina = st.session_state["pagina"]
    if pagina == "acceso":
        pantalla_acceso()
    elif pagina == "inicio_alumno":
        pantalla_inicio_alumno()
    elif pagina == "examen":
        pantalla_examen()
    elif pagina == "resultados":
        pantalla_resultados()
    elif pagina == "panel_docente":
        pantalla_panel_docente()
    else:
        cerrar_sesion()
        pantalla_acceso()


if __name__ == "__main__":
    main()
