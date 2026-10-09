from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from axes.handlers.proxy import AxesProxyHandler

from .models import Categoria, Ciudad, Departamento, Empresa


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


class FormularioDepartamento(forms.ModelForm):
    class Meta:
        model = Departamento
        fields = ["nombre"]
        widgets = {
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nombre del departamento",
                }
            ),
        }
        error_messages = {
            "nombre": {
                "required": "El nombre no puede estar vacío.",
                "max_length": "El nombre no puede superar los 120 caracteres.",
            },
        }


class FormularioCiudad(forms.ModelForm):
    class Meta:
        model = Ciudad
        fields = ["nombre", "departamento"]
        widgets = {
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nombre de la ciudad",
                }
            ),
            "departamento": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
        }
        error_messages = {
            "nombre": {
                "required": "El nombre no puede estar vacío.",
                "max_length": "El nombre no puede superar los 120 caracteres.",
            },
            "departamento": {
                "required": "Seleccioná un departamento.",
                "invalid_choice": "Seleccioná un departamento.",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["departamento"].empty_label = "Seleccioná un departamento"
        self.fields["departamento"].queryset = Departamento.objects.order_by("nombre")


class FormularioCategoria(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nombre", "descripcion"]
        widgets = {
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nombre de la categoría",
                }
            ),
            "descripcion": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Descripción de la categoría",
                    "rows": 3,
                }
            ),
        }
        error_messages = {
            "nombre": {
                "required": "El nombre no puede estar vacío.",
                "max_length": "El nombre no puede superar los 100 caracteres.",
            },
            "descripcion": {
                "max_length": "La descripción no puede superar los 255 caracteres.",
            },
        }


class FormularioEmpresa(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = [
            "razon_social",
            "ruc",
            "email",
            "telefono",
            "es_cliente",
            "es_proveedor",
            "activo",
            "categorias",
        ]
        widgets = {
            "razon_social": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Razón social",
                }
            ),
            "ruc": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "RUC, por ejemplo 80012345-0",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Correo electrónico",
                }
            ),
            "telefono": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Teléfono",
                }
            ),
            "es_cliente": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "es_proveedor": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "categorias": forms.SelectMultiple(
                attrs={
                    "class": "form-select",
                }
            ),
        }
        error_messages = {
            "razon_social": {
                "required": "La razón social no puede estar vacía.",
                "max_length": "La razón social no puede superar los 200 caracteres.",
            },
            "ruc": {
                "required": "El RUC no puede estar vacío.",
                "max_length": "El RUC no puede superar los 20 caracteres.",
            },
            "email": {
                "invalid": "Ingresá un email válido.",
                "max_length": "El email no puede superar los 254 caracteres.",
            },
            "telefono": {
                "max_length": "El teléfono no puede superar los 30 caracteres.",
            },
        }

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self.fields["categorias"].queryset = Categoria.objects.order_by("nombre")
        self.fields["categorias"].required = False
        if usuario is not None and not self.instance.pk:
            self.instance.usuario_creacion = usuario
            self.instance.usuario_modificacion = usuario

    def clean(self):
        datos = super().clean()
        if not datos.get("es_cliente") and not datos.get("es_proveedor"):
            raise ValidationError(
                "La empresa debe ser cliente, proveedor o ambas."
            )
        return datos

    def save(self, commit=True):
        if self.usuario is not None and self.instance.pk:
            self.instance.usuario_modificacion = self.usuario
        return super().save(commit=commit)
