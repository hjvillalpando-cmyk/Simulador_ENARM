"""
Acceso de usuarios.

El alumno entra solo con matrícula y nombre: si la matrícula ya existe se
recupera su historial, si no existe se crea el registro. El docente sí usa
contraseña porque ve los datos de todo el grupo.
"""

import re
import unicodedata

import bcrypt
from sqlalchemy.orm import Session

from db import Usuario

PATRON_MATRICULA = re.compile(r"^[A-Z0-9\-_]{4,20}$")


def _a_bytes(password: str) -> bytes:
    """bcrypt no acepta contraseñas de más de 72 bytes; se recorta."""
    return password.encode("utf-8")[:72]


def generar_hash(password: str) -> str:
    """Devuelve el hash bcrypt de una contraseña."""
    return bcrypt.hashpw(_a_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verificar_password(password: str, hash_guardado: str | None) -> bool:
    """Compara una contraseña con su hash. Devuelve False si no hay hash."""
    if not hash_guardado:
        return False
    try:
        return bcrypt.checkpw(_a_bytes(password), hash_guardado.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def normalizar_texto(texto: str) -> str:
    """Quita acentos, colapsa espacios y pasa a mayúsculas.

    Sirve para que 'José  Pérez' y 'jose perez' sean el mismo registro.
    """
    if not texto:
        return ""
    texto = " ".join(texto.split())
    descompuesto = unicodedata.normalize("NFD", texto)
    sin_acentos = "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")
    return sin_acentos.upper()


def normalizar_matricula(matricula: str) -> str:
    """Deja la matrícula sin espacios y en mayúsculas."""
    return (matricula or "").strip().replace(" ", "").upper()


def validar_matricula(matricula: str) -> bool:
    """Acepta 4 a 20 caracteres alfanuméricos, guion y guion bajo."""
    return bool(PATRON_MATRICULA.match(matricula))


def entrar_como_alumno(db: Session, matricula: str, nombre: str) -> Usuario:
    """Recupera o crea al alumno. Lanza ValueError con un mensaje legible."""
    mat = normalizar_matricula(matricula)
    nom = normalizar_texto(nombre)

    if not validar_matricula(mat):
        raise ValueError(
            "La matrícula debe tener entre 4 y 20 caracteres, sin espacios "
            "ni signos de puntuación."
        )
    if len(nom.split()) < 2:
        raise ValueError("Escribe tu nombre y al menos un apellido.")

    usuario = db.query(Usuario).filter(Usuario.matricula == mat).first()

    if usuario is not None:
        if usuario.rol != "alumno":
            raise ValueError("Esa matrícula pertenece a una cuenta docente.")
        # Si el alumno escribió su nombre distinto, conservamos el registrado.
        return usuario

    nuevo = Usuario(matricula=mat, nombre=nom, rol="alumno", password_hash=None)
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


def entrar_como_docente(db: Session, matricula: str, password: str) -> Usuario | None:
    """Devuelve el docente si las credenciales son válidas, o None."""
    mat = normalizar_matricula(matricula)
    usuario = (
        db.query(Usuario)
        .filter(Usuario.matricula == mat, Usuario.rol == "docente")
        .first()
    )
    if usuario and verificar_password(password, usuario.password_hash):
        return usuario
    return None


def cambiar_password_docente(db: Session, usuario_id: int, nueva: str) -> None:
    """Actualiza la contraseña del docente. Mínimo 8 caracteres."""
    if len(nueva) < 8:
        raise ValueError("La contraseña nueva debe tener al menos 8 caracteres.")
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if usuario is None:
        raise ValueError("No se encontró el usuario.")
    usuario.password_hash = generar_hash(nueva)
    db.commit()
