from pydantic import BaseModel


class Token(BaseModel):
    """
    Par de tokens que devuelve el login.

    `access_token` es un JWT corto (15 min por defecto) que viaja en cada
    peticion. `refresh_token` es opaco, dura mas y se puede revocar.

    `expires_in` (segundos) viaja con la respuesta para que el cliente sepa
    cuando renovar, en vez de calcularlo adivinando.
    """

    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
