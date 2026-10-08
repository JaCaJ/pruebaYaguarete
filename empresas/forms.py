from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from axes.handlers.proxy import AxesProxyHandler


class FormularioIngreso(AuthenticationForm):
    # invalid_login e inactive las busca AuthenticationForm por ese nombre.
    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "Usuario o contraseña incorrectos.",
        "inactive": "Esta cuenta está inactiva.",
        "bloqueado": settings.AXES_COOLOFF_MESSAGE,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Usuario"
        self.fields["username"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "Tu usuario",
                "autocomplete": "username",
                "autofocus": True,
            }
        )
        self.fields["password"].label = "Contraseña"
        self.fields["password"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "Tu contraseña",
                "autocomplete": "current-password",
            }
        )

    def _esta_bloqueado(self):
        nombre_usuario = self.data.get("username")
        if not nombre_usuario or self.request is None:
            return False
        return AxesProxyHandler.is_locked(
            self.request, credentials={"username": nombre_usuario}
        )

    def clean(self):
        if self._esta_bloqueado():
            raise ValidationError(
                self.error_messages["bloqueado"],
                code="bloqueado",
            )
        try:
            return super().clean()
        except ValidationError:
            if self._esta_bloqueado():
                raise ValidationError(
                    self.error_messages["bloqueado"],
                    code="bloqueado",
                ) from None
            raise
