from slowapi import Limiter
from slowapi.util import get_remote_address

# Limiter en memoria, con la IP como clave. Alcanza para una sola instancia
# (el caso de este proyecto). Límite conocido, documentado en el README: con
# varias réplicas hace falta un backend compartido (Redis) para que el conteo
# sea global y no por-proceso.
limiter = Limiter(key_func=get_remote_address)
