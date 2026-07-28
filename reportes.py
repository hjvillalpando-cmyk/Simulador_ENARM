"""
Reportes descargables: PDF individual para el alumno, Excel grupal para el docente.
"""

import io

import pandas as pd
from fpdf import FPDF
from sqlalchemy.orm import Session

from config import NOMBRE_INSTITUCION
from db import Respuesta, Sesion, Usuario


def _latin(texto) -> str:
    """Las fuentes base de FPDF solo manejan latin-1.

    Sustituye lo que no se pueda representar en vez de reventar el reporte.
    """
    return str(texto).encode("latin-1", "replace").decode("latin-1")


class _ReportePDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 12)
        self.cell(
            0,
            8,
            _latin("Simulador de casos clínicos ENARM — Informe de sesión"),
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.set_font("Helvetica", "", 8)
        self.set_text_color(110, 110, 110)
        self.cell(0, 4, _latin(NOMBRE_INSTITUCION), align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.set_draw_color(210, 210, 210)
        self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
        self.ln(6)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(
            0,
            8,
            _latin(f"Página {self.page_no()} de {{nb}} · Documento de uso académico"),
            align="C",
        )


def generar_pdf_sesion(
    nombre: str,
    matricula: str,
    sesion_id: int,
    resumen: dict,
    items: list[dict],
    respuestas: list[str | None],
    fecha: str,
) -> bytes:
    """Arma el PDF con el desglose completo de la sesión."""
    pdf = _ReportePDF()
    pdf.alias_nb_pages()  # sin esto el {nb} del pie sale literal
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # Ficha del alumno
    pdf.set_fill_color(243, 245, 248)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, _latin(f"{nombre}   ·   Matrícula {matricula}"), fill=True,
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(
        0,
        6,
        _latin(
            f"Sesión #{sesion_id}   ·   {fecha}   ·   Calificación "
            f"{resumen['puntaje']:.1f}%  ({resumen['aciertos']}/{resumen['total']} aciertos)"
        ),
        fill=True,
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(5)

    # Desglose por tema
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, _latin("Desempeño por tema"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    for tema, d in sorted(resumen["por_tema"].items()):
        pct = d["aciertos"] / d["total"] * 100
        pdf.cell(
            0, 5,
            _latin(f"   {tema}: {d['aciertos']}/{d['total']}  ({pct:.0f}%)"),
            new_x="LMARGIN", new_y="NEXT",
        )
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, _latin("Desempeño por nivel clínico"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    for nivel, d in sorted(resumen["por_nivel"].items()):
        pct = d["aciertos"] / d["total"] * 100
        pdf.cell(
            0, 5,
            _latin(f"   {nivel.capitalize()}: {d['aciertos']}/{d['total']}  ({pct:.0f}%)"),
            new_x="LMARGIN", new_y="NEXT",
        )
    pdf.ln(5)

    # Repaso reactivo por reactivo
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, _latin("Retroalimentación"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    caso_impreso = None
    for i, item in enumerate(items):
        if item["caso_id"] != caso_impreso:
            caso_impreso = item["caso_id"]
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_fill_color(232, 237, 245)
            pdf.multi_cell(
                0, 5,
                _latin(f"Caso {item['num_caso']} · {item['tema']} ({item['especialidad']})"),
                fill=True, new_x="LMARGIN", new_y="NEXT",
            )
            pdf.set_font("Helvetica", "I", 8)
            pdf.multi_cell(0, 4, _latin(item["vineta"]), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(110, 110, 110)
            pdf.multi_cell(0, 4, _latin(f"Fuente: {item['guia_origen']}"), new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
            pdf.ln(1)

        elegida = respuestas[i]
        correcta = item["letra_correcta"]
        acerto = elegida == correcta

        pdf.set_font("Helvetica", "B", 8)
        pdf.multi_cell(
            0, 4,
            _latin(f"[{'CORRECTO' if acerto else 'INCORRECTO'}] "
                   f"({item['nivel'].capitalize()}) {item['enunciado']}"),
            new_x="LMARGIN", new_y="NEXT",
        )
        pdf.set_font("Helvetica", "", 8)
        texto_elegida = (
            f"{elegida}) {item['opciones'][ord(elegida) - 65]}" if elegida else "sin contestar"
        )
        pdf.multi_cell(0, 4, _latin(f"   Tu respuesta: {texto_elegida}"), new_x="LMARGIN", new_y="NEXT")
        pdf.multi_cell(
            0, 4,
            _latin(f"   Respuesta correcta: {correcta}) {item['opciones'][ord(correcta) - 65]}"),
            new_x="LMARGIN", new_y="NEXT",
        )
        pdf.set_font("Helvetica", "I", 8)
        pdf.multi_cell(0, 4, _latin(f"   {item['retroalimentacion']}"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    return bytes(pdf.output())


def generar_excel_grupo(db: Session) -> bytes:
    """Excel de cuatro hojas con el panorama completo del grupo."""
    alumnos = db.query(Usuario).filter(Usuario.rol == "alumno").all()

    filas_alumnos = []
    for a in alumnos:
        sesiones = a.sesiones
        n = len(sesiones)
        promedio = sum(s.puntaje for s in sesiones) / n if n else 0.0
        ultima = max((s.fecha_inicio for s in sesiones), default=None)
        primera_mitad = [s.puntaje for s in sorted(sesiones, key=lambda x: x.fecha_inicio)][: n // 2]
        segunda_mitad = [s.puntaje for s in sorted(sesiones, key=lambda x: x.fecha_inicio)][n // 2:]
        tendencia = (
            (sum(segunda_mitad) / len(segunda_mitad)) - (sum(primera_mitad) / len(primera_mitad))
            if primera_mitad and segunda_mitad
            else None
        )
        filas_alumnos.append(
            {
                "Matrícula": a.matricula,
                "Nombre": a.nombre,
                "Sesiones": n,
                "Promedio (%)": round(promedio, 1),
                "Mejor (%)": round(max((s.puntaje for s in sesiones), default=0), 1),
                "Última sesión": ultima.strftime("%Y-%m-%d %H:%M") if ultima else "",
                "Tendencia (pts)": round(tendencia, 1) if tendencia is not None else "",
            }
        )
    df_alumnos = pd.DataFrame(filas_alumnos).sort_values("Nombre") if filas_alumnos else pd.DataFrame()

    # Sesiones
    sesiones = db.query(Sesion).join(Usuario).all()
    df_sesiones = pd.DataFrame(
        [
            {
                "Sesión": s.id,
                "Matrícula": s.usuario.matricula,
                "Nombre": s.usuario.nombre,
                "Fecha": s.fecha_inicio.strftime("%Y-%m-%d %H:%M"),
                "Especialidad": s.especialidad or "Todas las especialidades",
                "Puntaje (%)": round(s.puntaje, 1),
                "Aciertos": s.aciertos,
                "Reactivos": s.total_reactivos,
            }
            for s in sesiones
        ]
    )

    # Respuestas individuales
    respuestas = db.query(Respuesta).all()
    df_respuestas = pd.DataFrame(
        [
            {
                "Sesión": r.sesion_id,
                "Caso": r.caso_id,
                "Reactivo": r.reactivo_idx + 1,
                "Tema": r.tema,
                "Nivel": r.nivel,
                "Respuesta": r.respuesta_alumno or "sin contestar",
                "Resultado": "Correcto" if r.correcta_bool else "Incorrecto",
                "Segundos": r.segundos_empleados,
            }
            for r in respuestas
        ]
    )

    # Análisis de reactivos
    if not df_respuestas.empty:
        df_analisis = (
            df_respuestas.assign(_ok=lambda d: (d["Resultado"] == "Correcto").astype(int))
            .groupby(["Caso", "Reactivo", "Tema", "Nivel"], as_index=False)
            .agg(Presentaciones=("_ok", "count"),
                 Aciertos=("_ok", "sum"),
                 Segundos_promedio=("Segundos", "mean"))
        )
        df_analisis["Tasa de error (%)"] = (
            (1 - df_analisis["Aciertos"] / df_analisis["Presentaciones"]) * 100
        ).round(1)
        df_analisis["Segundos_promedio"] = df_analisis["Segundos_promedio"].round(0)
        df_analisis = df_analisis.sort_values("Tasa de error (%)", ascending=False)
    else:
        df_analisis = pd.DataFrame()

    salida = io.BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        for df, hoja in (
            (df_alumnos, "Alumnos"),
            (df_sesiones, "Sesiones"),
            (df_analisis, "Análisis de reactivos"),
            (df_respuestas, "Respuestas"),
        ):
            (df if not df.empty else pd.DataFrame({"Sin datos": []})).to_excel(
                writer, sheet_name=hoja, index=False
            )

    return salida.getvalue()
