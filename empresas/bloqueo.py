def conservar_respuesta_ingreso(solicitud, respuesta_original, credenciales=None):
    """Devuelve la respuesta del formulario para mostrar el aviso de bloqueo ahí.

    django-axes llama esta función con tres argumentos posicionales, en este
    orden: la solicitud, la respuesta original y las credenciales.
    """
    return respuesta_original
