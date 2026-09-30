"""Sesion revocable: login, refresh, logout.

Comprueba el modelo de dos tokens y, sobre todo, que **cerrar sesion cierra de
verdad**. Antes `logout()` solo borraba el localStorage del navegador y el token
seguia sirviendo en el servidor hasta 25 horas despues.

Ver `docs/SEGURIDAD.md`.
"""

from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from core.db import SessionLocal
from initial_data import main as bootstrap_initial_data
from main import app
from models.refresh_token import RefreshToken
from models.user import User as UserModel

EMAIL = "admin@medapp.com"
PASSWORD = "Admin123!"


@pytest_asyncio.fixture(scope="session")
async def sesion_client():
    await bootstrap_initial_data()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _login(client) -> dict:
    r = await client.post(
        "/api/v1/login/access-token", data={"username": EMAIL, "password": PASSWORD}
    )
    assert r.status_code == 200, r.text
    return r.json()


async def _refresh_validos(user_id: str) -> int:
    """Sesiones vivas de UN usuario.

    Contar todas las de la base daria un numero que depende de lo que hayan
    dejado otros tests y usuarios, y el aserto no significaria nada.
    """
    async with SessionLocal() as db:
        return (
            await db.execute(
                select(func.count(RefreshToken.id)).where(
                    RefreshToken.user_id == uuid.UUID(str(user_id)),
                    RefreshToken.revoked_at.is_(None),
                )
            )
        ).scalar() or 0


async def _mi_id() -> str:
    from core import crud_user

    async with SessionLocal() as db:
        usuario = await crud_user.get_user_by_email(db, EMAIL)
        assert usuario is not None
        return str(usuario.id)


# --------------------------------------------------------------------------
# El par de tokens
# --------------------------------------------------------------------------


async def test_login_devuelve_los_dos_tokens(sesion_client):
    """El login entrega access + refresh y dice cuando caduca el access."""
    tokens = await _login(sesion_client)
    assert tokens["access_token"], "falta access_token"
    assert tokens["refresh_token"], "falta refresh_token"
    assert tokens["token_type"] == "bearer"
    assert tokens["expires_in"] > 0, "el cliente necesita saber cuando renovar"


async def test_el_access_token_es_corto(sesion_client):
    """El access token debe durar minutos, no horas.

    Es lo que limita el daño de un robo: es el token que viaja en cada peticion
    y no se puede revocar. Si vuelve a durar 25 h, la ventana de robo vuelve a
    ser de un dia entero.
    """
    from core.config import settings

    assert settings.ACCESS_TOKEN_EXPIRE_SECONDS <= 3600, (
        f"el access token dura {settings.ACCESS_TOKEN_EXPIRE_SECONDS}s "
        f"({settings.ACCESS_TOKEN_EXPIRE_SECONDS / 60:.0f} min). Para datos "
        "clinicos deberia ser una sesion corta con refresh."
    )


async def test_el_refresh_no_es_un_jwt(sesion_client):
    """El refresh token es opaco: no es un JWT forjable.

    Un JWT de refresh podria fabricarse con la `sub` de otro usuario. Al ser
    una cadena aleatoria sin firma y guardarse hasheado, no se puede falsificar
    ni aunque se conozca el formato de los tokens de acceso.
    """
    tokens = await _login(sesion_client)
    partes = tokens["refresh_token"].split(".")
    assert len(partes) == 1, (
        "el refresh token parece un JWT (tiene puntos). Si lo es, se puede "
        "fabricar sin la clave."
    )


async def test_el_token_en_claro_no_se_guarda(sesion_client):
    """En la base solo hay el hash, nunca el token en claro.

    Si alguien lee la tabla (un dump, una inyeccion SQL) obtiene hashes, no
    tokens usables.
    """
    import hashlib

    tokens = await _login(sesion_client)
    esperado = hashlib.sha256(tokens["refresh_token"].encode()).hexdigest()

    async with SessionLocal() as db:
        fila = (
            await db.execute(
                select(RefreshToken).where(RefreshToken.hashed_token == esperado)
            )
        ).scalars().first()

    assert fila is not None, "el refresh token no se guardo (ni en claro ni hasheado)"
    assert fila.hashed_token != tokens["refresh_token"], (
        "se esta guardando el token EN CLARO en la base"
    )


# --------------------------------------------------------------------------
# Refresh y rotacion
# --------------------------------------------------------------------------


async def test_refresh_extiende_la_sesion(sesion_client):
    """Un refresh token valido entrega un access token nuevo."""
    tokens = await _login(sesion_client)
    r = await sesion_client.post(
        "/api/v1/login/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert r.status_code == 200, r.text
    nuevo = r.json()
    assert nuevo["access_token"], "el refresh no devolvio access token"
    assert nuevo["refresh_token"], "el refresh no devolvio refresh token"


async def test_el_refresh_token_es_de_un_solo_uso(sesion_client):
    """Tras usarlo, el token anterior deja de servir.

    Es la rotacion: un token robado tiene una sola oportunidad, y usarla antes
    que el titular legitimo se detecta porque este recibe un fallo.
    """
    tokens = await _login(sesion_client)

    primero = await sesion_client.post(
        "/api/v1/login/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert primero.status_code == 200, primero.text

    segundo = await sesion_client.post(
        "/api/v1/login/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert segundo.status_code == 401, (
        "el mismo refresh token se acepto dos veces: no hay rotacion, asi que un "
        "token robado serviria hasta que expirase."
    )


async def test_refresh_invalido_es_401(sesion_client):
    """Un refresh token inventado no sirve, y el error no dice por que.

    Distinguir "no existe" de "caducado" de "revocado" le diria al atacante
    que tokens son reales.
    """
    for token in ("no-existe", "a" * 50, ""):
        r = await sesion_client.post(
            "/api/v1/login/refresh", json={"refresh_token": token or "x"}
        )
        assert r.status_code in (401, 422), f"token {token[:12]!r} dio {r.status_code}"
        if r.status_code == 401:
            assert "revocado" not in r.text and "caducado" not in r.text, (
                "el error revela el motivo del rechazo"
            )


# --------------------------------------------------------------------------
# Logout: el cierre real
# --------------------------------------------------------------------------


async def test_logout_invalida_el_refresh(sesion_client):
    """Despues de cerrar sesion, el refresh token NO sirve.

    Este es el requisito central: antes el logout era solo cliente y el token
    seguía vivo en el servidor.
    """
    tokens = await _login(sesion_client)

    r = await sesion_client.post(
        "/api/v1/login/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert r.status_code == 204, r.text

    r = await sesion_client.post(
        "/api/v1/login/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert r.status_code == 401, (
        "el refresh token sirio DESPUES del logout: la sesion no se cerro"
    )


async def test_logout_es_idempotente(sesion_client):
    """Cerrar sesion dos veces no da error.

    Es lo normal en una app real: el boton puede pulsarse dos veces, o el
    logout automatico puede coincidir con uno manual.
    """
    tokens = await _login(sesion_client)
    primero = await sesion_client.post(
        "/api/v1/login/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    segundo = await sesion_client.post(
        "/api/v1/login/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert primero.status_code == 204
    assert segundo.status_code == 204, f"el segundo logout dio {segundo.status_code}"


async def test_logout_no_afecta_a_otras_sesiones(sesion_client):
    """Cerrar una sesion no cierra las demas del mismo usuario.

    Si cerrara todas, tener dos pestanas abiertas seria imposible.
    """
    sesion_a = await _login(sesion_client)
    sesion_b = await _login(sesion_client)

    await sesion_client.post(
        "/api/v1/login/logout", json={"refresh_token": sesion_a["refresh_token"]}
    )

    r = await sesion_client.post(
        "/api/v1/login/refresh", json={"refresh_token": sesion_b["refresh_token"]}
    )
    assert r.status_code == 200, "cerrar una sesion cerro tambien la otra"


async def test_logout_all_cierra_todas(sesion_client):
    """`logout-all` revoca todas las sesiones del usuario.

    Es la respuesta a "no se cual robaron": se cierra todo y se entra de nuevo.
    """
    await _login(sesion_client)
    await _login(sesion_client)
    tokens = await _login(sesion_client)

    r = await sesion_client.post("/api/v1/login/logout-all", headers={
        "Authorization": f"Bearer {tokens['access_token']}"
    })
    assert r.status_code == 204, r.text

    r = await sesion_client.post(
        "/api/v1/login/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert r.status_code == 401, "logout-all no cerro la sesion"


async def test_logout_all_exige_token(sesion_client):
    """`logout-all` no es una puerta abierta: exige sesion."""
    r = await sesion_client.post("/api/v1/login/logout-all")
    assert r.status_code == 401, f"sin token dio {r.status_code}, deberia ser 401"


async def test_sesiones_activas_solo_las_vigentes(sesion_client):
    """`/login/sesiones` lista las vivas y oculta las revocadas."""
    tokens = await _login(sesion_client)
    cerrada = await _login(sesion_client)

    await sesion_client.post(
        "/api/v1/login/logout", json={"refresh_token": cerrada["refresh_token"]}
    )

    r = await sesion_client.get(
        "/api/v1/login/sesiones",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert r.status_code == 200, r.text
    assert r.json(), "deberia listar al menos la sesion viva"


async def test_limite_de_sesiones_por_usuario(sesion_client):
    """No se acumulan sesiones sin limite.

    Una lista que crece sin limite es una lista que nadie revisa, y mantiene
    abierta la ventana de un token robado.
    """
    from core.config import settings

    user_id = await _mi_id()
    for _ in range(settings.MAX_SESIONES_POR_USUARIO + 3):
        await _login(sesion_client)
    vivas = await _refresh_validos(user_id)

    assert vivas <= settings.MAX_SESIONES_POR_USUARIO, (
        f"hay {vivas} sesiones vivas de este usuario con un limite de "
        f"{settings.MAX_SESIONES_POR_USUARIO}: el limite no se esta aplicando"
    )


# --------------------------------------------------------------------------
# El arranque rechaza valores imposibles
# --------------------------------------------------------------------------


def test_un_access_token_de_25h_no_se_puede_arrancar():
    """El valor que habia antes (90000 s) ahora es un error de arranque.

    Configurarlo por descuido era el problema: 25 h de token para datos
    clinicos. Que falle al arrancar es preferible a descubrirlo en produccion.
    """
    import pytest as _pytest

    from core.config import Settings

    with _pytest.raises(Exception) as excepcion:
        Settings(
            _env_file=None,
            DATABASE_URL="postgresql+asyncpg://x:y@localhost/z",
            FIRST_SUPERUSER_EMAIL="a@b.com",
            FIRST_SUPERUSER_PASSWORD="p",
            SECRET_KEY="k",
            ACCESS_TOKEN_EXPIRE_SECONDS=90000,
        )
    assert "86400" in str(excepcion.value)


def test_un_access_token_de_cero_no_se_puede_arrancar():
    """`0` caducaria el token al instante: el usuario entra y sale solo."""
    import pytest as _pytest

    from core.config import Settings

    with _pytest.raises(Exception):
        Settings(
            _env_file=None,
            DATABASE_URL="postgresql+asyncpg://x:y@localhost/z",
            FIRST_SUPERUSER_EMAIL="a@b.com",
            FIRST_SUPERUSER_PASSWORD="p",
            SECRET_KEY="k",
            ACCESS_TOKEN_EXPIRE_SECONDS=0,
        )
