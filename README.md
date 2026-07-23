# Simulador de casos clínicos ENARM

Aplicación web para que los estudiantes resuelvan sesiones de casos clínicos
tipo ENARM y el docente siga su avance.

- El alumno entra con matrícula y nombre, sin contraseña.
- Cada sesión presenta 15 casos elegidos al azar entre temas distintos,
  evitando los que ya resolvió en sus últimas dos sesiones.
- La retroalimentación aparece al terminar, reactivo por reactivo, con la
  referencia a la guía.
- El docente ve el avance individual y grupal, y exporta todo a Excel.

---

## Instalación

Necesitas Python 3.11 o superior.

```bash
cd simulador_enarm
python -m venv venv

# Windows
venv\Scripts\activate
# macOS o Linux
source venv/bin/activate

pip install -r requirements.txt
```

Arranca la aplicación:

```bash
streamlit run app.py
```

Se abre en `http://localhost:8501`.

**Acceso docente inicial:** usuario `DOC001`, contraseña `cambiar123`.
Cámbiala en la pestaña Administración antes de compartir la liga.

---

## El banco de casos

El archivo `casos.json` incluye 8 casos de ejemplo para que pruebes el sistema
de inmediato. **No son tu banco definitivo**: están escritos a partir de
contenido general de guías mexicanas y sirven de demostración.

Para generar tus 100 casos desde tus propias guías, sigue `PROMPT_BANCO.md`.

Antes de usar un banco nuevo, revísalo:

```bash
python validar_banco.py casos.json
```

También puedes subir el archivo desde la aplicación, en el panel docente →
Administración → Subir un nuevo casos.json. Ahí se valida antes de reemplazar
el que está en uso.

---

## Publicarlo para tus alumnos

### Streamlit Community Cloud (gratis)

1. Sube la carpeta a un repositorio de GitHub.
2. Entra a `share.streamlit.io`, conecta el repositorio y elige `app.py`.

**Advertencia importante:** en Streamlit Cloud el sistema de archivos es
temporal. Si dejas la base de datos en SQLite, **el avance de tus alumnos se
borra cada vez que la aplicación se reinicia**. Para uso real necesitas una
base de datos externa.

### Base de datos que sí conserva los datos

Crea una base PostgreSQL gratuita en Supabase o Neon, y en Streamlit Cloud ve
a *Settings → Secrets* y agrega:

```toml
DATABASE_URL = "postgresql+psycopg2://usuario:clave@host:5432/basededatos"
DOCENTE_PASSWORD_INICIAL = "la_que_tu_elijas"
NOMBRE_INSTITUCION = "Escuela de Ciencias de la Salud"
```

Y descomenta la línea de `psycopg2-binary` en `requirements.txt`.

Con eso, el mismo código funciona sin cambios: `config.py` lee la variable y
SQLAlchemy se conecta a PostgreSQL en lugar de SQLite.

Si prefieres no depender de la nube, corre la aplicación en una computadora de
la universidad con `streamlit run app.py --server.address 0.0.0.0` y comparte
la IP con los alumnos dentro de la red del campus.

---

## Ajustes rápidos

Todo lo configurable está en `config.py` o se puede pasar como variable de
entorno:

| Variable | Para qué sirve | Valor por defecto |
|---|---|---|
| `NUM_CASOS_POR_SESION` | Casos por sesión | 15 |
| `SESIONES_SIN_REPETIR` | Sesiones hacia atrás que se revisan para no repetir casos | 2 |
| `BARAJAR_OPCIONES` | Reordena A–D en cada reactivo | 1 (activado) |
| `DATABASE_URL` | Conexión a la base de datos | SQLite local |
| `RUTA_BANCO` | Archivo del banco de casos | `casos.json` |

---

## Qué hace cada archivo

| Archivo | Contenido |
|---|---|
| `app.py` | Interfaz: acceso, examen, resultados, panel docente |
| `db.py` | Tablas de usuarios, sesiones y respuestas |
| `auth.py` | Acceso de alumnos y docente, normalización de nombres |
| `banco.py` | Esquema del banco, carga, validación y auditoría de calidad |
| `motor_examen.py` | Selección de casos, barajado de opciones, calificación |
| `reportes.py` | PDF individual y Excel grupal |
| `validar_banco.py` | Revisión del banco desde la terminal |
| `casos.json` | Banco de casos (8 de ejemplo, reemplázalos) |
| `PROMPT_BANCO.md` | Cómo generar tus 100 casos desde las guías |

---

## Decisiones de diseño

**Las opciones se barajan al presentarlas.** Cada vez que se muestra un
reactivo, el orden de A a D se reordena y se recalcula cuál letra es la
correcta. Así, aunque el banco quedara con la respuesta correcta cargada hacia
una letra, el alumno no puede acertar por posición. En la base de datos se
guarda la letra original del banco, no la que se mostró, para que el análisis
de reactivos siga siendo comparable entre sesiones.

**El banco no se genera durante el examen.** Se produce aparte, se valida y se
revisa. Un caso clínico inventado sobre la marcha puede contener un error
peligroso, y el alumno lo va a estudiar como si fuera cierto.

**Los alumnos no tienen contraseña, pero el docente sí.** El acceso sin
contraseña baja la fricción para el alumno, con el costo de que alguien podría
entrar con la matrícula de otro. Como la plataforma es de práctica y no
califica formalmente, la relación cuesta-beneficio se sostiene. El panel
docente sí está protegido porque expone los datos de todo el grupo.

**Se guardan `tema` y `nivel` en cada respuesta.** Aunque ya están en el banco,
duplicarlos en la base de datos permite que el análisis histórico del docente
siga funcionando aunque cambies o reemplaces `casos.json` a mitad del semestre.
