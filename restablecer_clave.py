"""
Restablece la contraseña del docente.

Úsalo cuando no recuerdes la contraseña o cuando cambiaste
DOCENTE_PASSWORD_INICIAL después de que la cuenta ya se había creado
(en ese caso el valor nuevo no se aplica solo).

Uso:
    python restablecer_clave.py

Si trabajas contra la base de datos en la nube, primero exporta la conexión:
    export DATABASE_URL="postgresql+psycopg2://usuario:clave@host:5432/base"
    python restablecer_clave.py
"""

import getpass
import sys

from auth import generar_hash
from config import DATABASE_URL, DOCENTE_MATRICULA
from db import Usuario, init_db, obtener_sesion


def main() -> int:
    destino = "SQLite local" if DATABASE_URL.startswith("sqlite") else "base de datos remota"
    print(f"Conectando a: {destino}\n")

    init_db()

    with obtener_sesion() as db:
        docentes = db.query(Usuario).filter(Usuario.rol == "docente").all()

        if not docentes:
            print("No hay ninguna cuenta docente. Se creará una nueva.")
            matricula = DOCENTE_MATRICULA
        elif len(docentes) == 1:
            matricula = docentes[0].matricula
            print(f"Cuenta docente encontrada: {matricula} ({docentes[0].nombre})")
        else:
            print("Hay varias cuentas docentes:")
            for i, d in enumerate(docentes, 1):
                print(f"  {i}. {d.matricula} — {d.nombre}")
            try:
                eleccion = int(input("\n¿Cuál quieres restablecer? (número): "))
                matricula = docentes[eleccion - 1].matricula
            except (ValueError, IndexError):
                print("Opción no válida.")
                return 1

        nueva = getpass.getpass("\nContraseña nueva (no se muestra al escribir): ")
        repetir = getpass.getpass("Repítela: ")

        if nueva != repetir:
            print("\nLas contraseñas no coinciden. No se cambió nada.")
            return 1
        if len(nueva) < 8:
            print("\nLa contraseña debe tener al menos 8 caracteres. No se cambió nada.")
            return 1

        usuario = db.query(Usuario).filter(Usuario.matricula == matricula).first()
        if usuario is None:
            usuario = Usuario(
                matricula=matricula,
                nombre="DOCENTE",
                rol="docente",
                password_hash=generar_hash(nueva),
            )
            db.add(usuario)
        else:
            usuario.password_hash = generar_hash(nueva)

    print(f"\nListo. Entra con el usuario {matricula} y tu contraseña nueva.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
