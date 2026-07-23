"""
Configuración central del simulador.

Todo lo que quieras ajustar sin tocar el resto del código está aquí.
Las variables se pueden sobrescribir con variables de entorno o con
`.streamlit/secrets.toml` al desplegar en la nube.
"""

import os

# --- Base de datos -----------------------------------------------------------
# SQLite sirve para pruebas locales. En Streamlit Cloud el archivo se BORRA
# en cada reinicio, así que ahí debes definir DATABASE_URL apuntando a
# PostgreSQL (Supabase, Neon, o el servidor de la universidad).
# Ejemplo: postgresql+psycopg2://usuario:clave@host:5432/basededatos
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///simulador_enarm.db")

# --- Examen ------------------------------------------------------------------
# Número de CASOS por sesión. Un caso seriado incluye 2-3 reactivos,
# así que el total de reactivos por sesión será mayor que este número.
NUM_CASOS_POR_SESION = int(os.getenv("NUM_CASOS_POR_SESION", "15"))

# Cuántas sesiones hacia atrás se revisan para no repetirle casos al alumno.
SESIONES_SIN_REPETIR = int(os.getenv("SESIONES_SIN_REPETIR", "2"))

# Baraja el orden de las opciones en cada reactivo. Déjalo en True: impide
# que un alumno adivine por posición si el banco quedó desbalanceado.
BARAJAR_OPCIONES = os.getenv("BARAJAR_OPCIONES", "1") == "1"

# --- Banco de casos ----------------------------------------------------------
RUTA_BANCO = os.getenv("RUTA_BANCO", "casos.json")

# --- Acceso docente ----------------------------------------------------------
DOCENTE_MATRICULA = os.getenv("DOCENTE_MATRICULA", "DOC001")
DOCENTE_NOMBRE = os.getenv("DOCENTE_NOMBRE", "DOCENTE")
# Cambia esto antes de publicar la aplicación.
DOCENTE_PASSWORD_INICIAL = os.getenv("DOCENTE_PASSWORD_INICIAL", "cambiar123")

# --- Identidad institucional -------------------------------------------------
NOMBRE_INSTITUCION = os.getenv("NOMBRE_INSTITUCION", "Licenciatura en Medicina")
TITULO_APP = os.getenv("TITULO_APP", "Simulador de casos clínicos ENARM")
