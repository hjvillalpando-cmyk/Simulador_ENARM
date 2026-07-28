"""
Modelos de base de datos y utilidades de conexión.

Usa SQLAlchemy 2.x. Funciona igual con SQLite (local) y PostgreSQL (nube)
según lo que contenga config.DATABASE_URL.
"""

from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from config import DATABASE_URL

# SQLite necesita check_same_thread=False porque Streamlit usa varios hilos.
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def ahora_utc() -> datetime:
    """Fecha y hora actual en UTC (reemplaza a datetime.utcnow, deprecado)."""
    return datetime.now(timezone.utc)


class Usuario(Base):
    """Alumno o docente. Los alumnos no tienen contraseña."""

    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    matricula = Column(String(50), unique=True, nullable=False, index=True)
    nombre = Column(String(150), nullable=False)
    rol = Column(String(20), nullable=False, default="alumno")  # alumno | docente
    password_hash = Column(String(255), nullable=True)
    creado_en = Column(DateTime(timezone=True), default=ahora_utc, nullable=False)

    sesiones = relationship(
        "Sesion", back_populates="usuario", cascade="all, delete-orphan"
    )


class Sesion(Base):
    """Un intento completo de examen (15 casos por defecto)."""

    __tablename__ = "sesiones"

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    fecha_inicio = Column(DateTime(timezone=True), default=ahora_utc, nullable=False)
    fecha_fin = Column(DateTime(timezone=True), nullable=True)
    puntaje = Column(Float, default=0.0, nullable=False)
    total_reactivos = Column(Integer, default=0, nullable=False)
    aciertos = Column(Integer, default=0, nullable=False)
    casos_json = Column(Text, nullable=True)  # lista de IDs de caso, en JSON
    especialidad = Column(String(80), nullable=True)  # con qué filtro se generó

    usuario = relationship("Usuario", back_populates="sesiones")
    respuestas = relationship(
        "Respuesta", back_populates="sesion", cascade="all, delete-orphan"
    )


class Respuesta(Base):
    """Una respuesta a un reactivo concreto.

    Guardamos `tema` y `nivel` aquí (aunque estén en el banco) para que el
    análisis del docente siga funcionando si el banco de casos cambia.
    """

    __tablename__ = "respuestas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sesion_id = Column(Integer, ForeignKey("sesiones.id"), nullable=False, index=True)
    caso_id = Column(String(50), nullable=False, index=True)
    reactivo_idx = Column(Integer, nullable=False)
    tema = Column(String(150), nullable=True)
    nivel = Column(String(30), nullable=True)
    respuesta_alumno = Column(String(10), nullable=True)  # None = sin contestar
    correcta_bool = Column(Boolean, nullable=False, default=False)
    segundos_empleados = Column(Integer, default=0, nullable=False)

    sesion = relationship("Sesion", back_populates="respuestas")


@contextmanager
def obtener_sesion():
    """Context manager que abre y cierra la sesión de base de datos.

    Uso:
        with obtener_sesion() as db:
            db.query(Usuario).all()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _migrar_columnas() -> None:
    """Agrega columnas nuevas a bases de datos que ya existían.

    create_all() crea tablas que faltan, pero no altera tablas existentes. Para
    quienes ya tenían la app publicada, esto añade la columna 'especialidad'
    sin borrar ni un dato. Es seguro ejecutarlo siempre: si la columna ya está,
    no hace nada.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "sesiones" not in inspector.get_table_names():
        return
    columnas = {c["name"] for c in inspector.get_columns("sesiones")}
    if "especialidad" not in columnas:
        tipo = "VARCHAR(80)"
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE sesiones ADD COLUMN especialidad {tipo}"))


def init_db() -> None:
    """Crea las tablas y el usuario docente inicial si no existe."""
    Base.metadata.create_all(bind=engine)
    _migrar_columnas()

    from auth import generar_hash  # import local para evitar ciclo
    from config import DOCENTE_MATRICULA, DOCENTE_NOMBRE, DOCENTE_PASSWORD_INICIAL

    with obtener_sesion() as db:
        existe = db.query(Usuario).filter(Usuario.rol == "docente").first()
        if existe is None:
            db.add(
                Usuario(
                    matricula=DOCENTE_MATRICULA.strip().upper(),
                    nombre=DOCENTE_NOMBRE.strip().upper(),
                    rol="docente",
                    password_hash=generar_hash(DOCENTE_PASSWORD_INICIAL),
                )
            )
