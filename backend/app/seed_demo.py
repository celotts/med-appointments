"""Datos de ejemplo para evaluar el panel con informacion creible.

Los tests dejan medicos y citas de cuyo nombre ("Prueba Dashboard", "QA
Reports") se repiten hasta hacer el panel ilegible. Este seed crea un conjunto
pequeno y realista que permite juzgar el diseno: medicos con nombre, especialidad
y horario, y una agenda repartida en estados que de verdad ocurren.

## Por que 12 dias hacia adelante

El panel se juzga sobre todo hacia adelante: un especialista planifica su
proxima semana. Las citas pasadas son necesarias para que las TASAS tengan
denominador (si no, la asistencia sale 0% o se divide por cero), asi que se
generan hacia atras con estados ya resueltos.

Se genera en los dos sentidos a proposito: un panel donde todo esta en pasado
no dice si el usuario puede leer bien una agenda por venir.

Ejecutar:
    cd backend && python -m app.seed_demo
"""

from __future__ import annotations

import asyncio
import random
import sys
import uuid
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

# El proyecto tiene DOS convenciones de import mezcladas y conviven dentro del
# mismo paquete:
#   - `app/core/security.py` hace `from core.config import settings`
#   - `app/core/db.py`       hace `from app.core.config import settings`
# Para que funcionen las dos hacen falta los dos directorios en `sys.path`.
# Es lo mismo que hace `app/main.py:4-7` para la app, aqui para los seeds.
_RAIZ = Path(__file__).resolve().parent.parent  # backend/
for _ruta in (str(_RAIZ), str(_RAIZ / "app")):
    if _ruta not in sys.path:
        sys.path.insert(0, _ruta)

from sqlalchemy import select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from app.core.rbac import ROLE_IDS, SPECIALIST  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402

random.seed(20260930)  # reproducible: dos corridas dan el mismo conjunto

MEDICOS = [
    ("Dra.", "Elena", "Ruiz", "Cardiologia", "cardio"),
    ("Dr.", "Miguel", "Sosa", "Traumatologia", "trauma"),
    ("Dra.", "Ana", "Beltran", "Dermatologia", "derma"),
    ("Dr.", "Julio", "Fuentes", "Neurologia", "neuro"),
]

NOMBRES = [
    "Laura", "Carlos", "Ana", "Miguel", "Sofia", "Jorge", "Elena", "Diego",
    "Paula", "Andres", "Carmen", "Ramon", "Lucia", "Fernando", "Rosa",
    "Ricardo", "Marta", "Alberto", "Gloria", "Sergio",
]

APELLIDOS = [
    "Garcia", "Rodriguez", "Martinez", "Lopez", "Hernandez", "Gonzalez",
    "Perez", "Sanchez", "Ramirez", "Flores", "Morales", "Reyes",
]

MOTIVOS = [
    "Consulta de control",
    "Revision de laboratorio",
    "Dolor toracico",
    "Seguimiento de tratamiento",
    "Primera consulta",
    "Revision post-operatoria",
]


async def main() -> None:  # noqa: C901
    from app.models.appointment import Appointment
    from app.models.appointment_status import AppointmentStatus
    from app.models.doctor import Doctor
    from app.models.doctor_schedule import DoctorSchedule
    from app.models.patient import Patient
    from app.models.specialty import Specialty
    from app.models.user import User as UserModel

    async with SessionLocal() as db:
        # --- Catalogo de estados y especialidades ---------------------------
        estados = {
            s.code: s.id
            for s in (await db.execute(select(AppointmentStatus))).scalars().all()
        }
        if "PENDIENTE" not in estados:
            print("Faltan los estados de cita. Ejecuta: make seed")
            return
        especialidades = (
            await db.execute(select(Specialty))
        ).scalars().all()
        if not especialidades:
            print("Faltan especialidades. Ejecuta: make seed")
            return
        print(f"Estados: {len(estados)}  Especialidades: {len(especialidades)}")

        admin = (
            await db.execute(
                select(UserModel).where(
                    UserModel.email == settings.FIRST_SUPERUSER_EMAIL
                )
            )
        ).scalars().first()
        if admin is None:
            print("No hay superusuario. Arranca la API una vez.")
            return
        admin_id = admin.id

        # --- Medicos con usuario -------------------------------------------
        medicos = []
        for i, (trat, nombre, apellido, especialidad, prefijo) in enumerate(MEDICOS):
            email = f"{prefijo}.demo@medapp.com"
            existente = (
                await db.execute(select(UserModel).where(UserModel.email == email))
            ).scalars().first()
            # Reentrante: si el usuario ya existe de una corrida anterior se
            # reutiliza su ficha de `doctors` en vez de saltarselo. Sin esto, una
            # corrida interrumpida dejaba medicos sin agenda y la siguiente no
            # los completaba.
            if existente:
                ficha = (
                    await db.execute(select(Doctor).where(Doctor.email == email))
                ).scalars().first()
                if ficha:
                    ficha_id = ficha.id
                    usuario_id_existente = existente.id
                    tiene_horario = (
                        await db.execute(
                            select(DoctorSchedule).where(
                                DoctorSchedule.doctor_id == ficha_id
                            ).limit(1)
                        )
                    ).scalars().first()
                    medicos.append(ficha_id)
                    if not tiene_horario:
                        for dia_semana in range(5):
                            db.add(
                                DoctorSchedule(
                                    doctor_id=ficha_id,
                                    user_id=usuario_id_existente,
                                    day_of_week=dia_semana,
                                    start_time=time(9, 0),
                                    end_time=time(17, 0),
                                    slot_duration_minutes=30,
                                )
                            )
                        print(f"  ~ {nombre} {apellido}: horario completado")
                    else:
                        print(f"  = {nombre} {apellido}: ya existia")
                    continue

            usuario = UserModel(
                id=uuid.uuid4(),
                email=email,
                full_name=f"{trat} {nombre} {apellido}",
                password=get_password_hash("Demo1234!"),
                role_id=ROLE_IDS[SPECIALIST],
                is_active=True,
                is_specialist=True,
            )
            db.add(usuario)
            await db.flush()

            doctor = Doctor(
                specialty_id=especialidades[i % len(especialidades)].id,
                first_name=nombre,
                last_name=apellido,
                document_number=f"DEMO-DOC-{i:03d}",
                professional_license=f"DEMO-LIC-{i:03d}",
                email=email,
                phone="+525550001100",
            )
            db.add(doctor)
            await db.flush()

            # Horario de lunes a viernes, 9:00 a 17:00 en bloques de 30 min.
            # Sin esto `ocupacion_pct` sale None y el panel no muestra nada util.
            #
            # Los ids se copian a variables ANTES del flush siguiente: tras un
            # flush la sesion expira los objetos y leer `doctor.id` o
            # `usuario.id` lanza MissingGreenlet (la misma trampa que
            # documenta `docs/AUDITORIA.md`).
            doctor_id = doctor.id
            usuario_id = usuario.id
            for dia_semana in range(5):
                db.add(
                    DoctorSchedule(
                        doctor_id=doctor_id,
                        user_id=usuario_id,
                        day_of_week=dia_semana,
                        start_time=time(9, 0),
                        end_time=time(17, 0),
                        slot_duration_minutes=30,
                    )
                )
            medicos.append(doctor_id)
            print(f"  + {trat} {nombre} {apellido}  ({email} / Demo1234!)")

        await db.commit()

        if not medicos:
            print("No hay medicos disponibles.")
            return

        # --- Pacientes ------------------------------------------------------
        pacientes = []
        for i in range(24):
            documento = f"DEMO-PAT-{i:03d}"
            if (
                await db.execute(
                    select(Patient).where(Patient.document_number == documento)
                )
            ).scalars().first():
                continue
            p = Patient(
                first_name=random.choice(NOMBRES),
                last_name=random.choice(APELLIDOS),
                document_number=documento,
                birth_date=date(
                    random.randint(1955, 2004),
                    random.randint(1, 12),
                    random.randint(1, 28),
                ),
                email=f"paciente.demo.{i:03d}@medapp.com",
                phone=f"+5255500020{i:02d}",
            )
            db.add(p)
            await db.flush()
            # Id a variable antes del siguiente flush: leerlo despues lanzaria
            # MissingGreenlet. Ver la nota de `docs/AUDITORIA.md`.
            pacientes.append(p.id)
        await db.commit()
        if not pacientes:
            existentes = (await db.execute(select(Patient.id))).scalars().all()
            pacientes = list(existentes)
        print(f"Pacientes disponibles: {len(pacientes)}")

        # --- Agenda --------------------------------------------------------
        # Estados ya resueltos hacia atras, estados vivos hacia adelante. Sin
        # los primeros las tasas salen siempre en 0%, y un panel donde todo esta
        # en pasado no permite juzgar si se lee bien una agenda por venir.
        CREADAS = 0
        hoy = date.today()
        for offset in range(-14, 13):
            dia = hoy + timedelta(days=offset)
            if dia.weekday() >= 5:
                continue  # sin horario el fin de semana: no se agenda
            for doctor_id in medicos:
                # 3-6 citas por medico y dia laborable
                for _ in range(random.randint(3, 6)):
                    # Horarios dentro del turno 9:00-17:00. Sin el tope, 9 + 15
                    # daba la hora 24, que no existe.
                    hora = 9 + random.choice([0, 1, 2, 4, 5, 6, 8])
                    # Hora local, no UTC. El seed grababa `tzinfo=timezone.utc`
                    # y el navegador, que pinta en hora local, mostraba las
                    # citas a las 03:00 en lugar de las 09:00 escritas. Un seed
                    # que produce horas absurdas no sirve para evaluar nada.
                    inicio = datetime.combine(
                        dia, time(hora, random.choice([0, 30]))
                    ).astimezone()
                    fin = inicio + timedelta(minutes=random.choice([30, 45, 60]))

                    if offset < 0:
                        codigo = random.choices(
                            ["ATENDIDA", "CANCELADA"],
                            weights=[82, 18],
                        )[0]
                    elif offset == 0:
                        # Hoy: mezcla de lo que ya paso y lo que viene.
                        codigo = random.choices(
                            ["ATENDIDA", "EN ESPERA", "EN PROCESO", "PENDIENTE", "CONFIRMADA", "CANCELADA"],
                            weights=[30, 10, 5, 25, 25, 5],
                        )[0]
                    else:
                        codigo = random.choices(
                            ["PENDIENTE", "CONFIRMADA"], weights=[60, 40]
                        )[0]

                    db.add(
                        Appointment(
                            # `pacientes` y `medicos` son listas de IDs, no de
                            # objetos: leer un atributo ORM aqui lanzaria
                            # MissingGreenlet.
                            patient_id=random.choice(pacientes),
                            doctor_id=doctor_id,
                            user_id=admin_id,
                            status_id=estados[codigo],
                            start_datetime=inicio,
                            end_datetime=fin,
                            reason=random.choice(MOTIVOS),
                        )
                    )
                    CREADAS += 1
        await db.commit()
        print(f"Citas creadas: {CREADAS}")


if __name__ == "__main__":
    asyncio.run(main())
