from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.forms.utils import ErrorList
from axes.handlers.proxy import AxesProxyHandler

from .models import (
    MENSAJE_EMAIL_O_TELEFONO,
    Categoria,
    Ciudad,
    Contacto,
    Departamento,
    Direccion,
    Empresa,
)


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


class FormularioContacto(forms.ModelForm):
    class Meta:
        model = Contacto
        fields = ["nombre", "apellido", "empresa", "email", "telefono", "cargo"]
        widgets = {
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nombre",
                }
            ),
            "apellido": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Apellido",
                }
            ),
            "empresa": forms.Select(attrs={"class": "form-select"}),
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
            "cargo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Cargo",
                }
            ),
        }
        error_messages = {
            "nombre": {
                "required": "El nombre no puede estar vacío.",
                "max_length": "El nombre no puede superar los 100 caracteres.",
            },
            "apellido": {
                "required": "El apellido no puede estar vacío.",
                "max_length": "El apellido no puede superar los 100 caracteres.",
            },
            "empresa": {
                "required": "Seleccioná una empresa.",
                "invalid_choice": "Seleccioná una empresa.",
            },
            "email": {
                "invalid": "Ingresá un email válido.",
                "max_length": "El email no puede superar los 254 caracteres.",
            },
            "telefono": {
                "max_length": "El teléfono no puede superar los 30 caracteres.",
            },
            "cargo": {
                "max_length": "El cargo no puede superar los 100 caracteres.",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["empresa"].empty_label = "Seleccioná una empresa"
        self.fields["empresa"].queryset = Empresa.objects.order_by("razon_social")

    def clean(self):
        datos = super().clean()
        if "email" in self.errors or "telefono" in self.errors:
            return datos
        email = (datos.get("email") or "").strip()
        telefono = (datos.get("telefono") or "").strip()
        if email or telefono:
            return datos
        raise ValidationError(
            {
                "email": MENSAJE_EMAIL_O_TELEFONO,
                "telefono": MENSAJE_EMAIL_O_TELEFONO,
            }
        )

    def _post_clean(self):
        super()._post_clean()
        self._depurar_aviso_de_contacto()

    def _depurar_aviso_de_contacto(self):
        mensaje = MENSAJE_EMAIL_O_TELEFONO
        hay_otro_error = any(
            str(error) != mensaje
            for nombre in ("email", "telefono")
            for error in self.errors.get(nombre, ())
        )
        for nombre in ("email", "telefono"):
            if nombre not in self.errors:
                continue
            restantes = []
            ya_aviso = False
            for error in self.errors[nombre]:
                texto = str(error)
                if texto == mensaje and (hay_otro_error or ya_aviso):
                    continue
                if texto == mensaje:
                    ya_aviso = True
                restantes.append(error)
            if restantes:
                self.errors[nombre] = ErrorList(restantes)
            else:
                del self.errors[nombre]


def _etiqueta_contacto(contacto):
    return f"{contacto.nombre} {contacto.apellido} — {contacto.empresa.razon_social}"


def _etiqueta_ciudad(ciudad):
    return f"{ciudad.nombre} ({ciudad.departamento.nombre})"


class FormularioDireccion(forms.ModelForm):
    class Meta:
        model = Direccion
        fields = ["direccion", "tipo", "codigo_postal", "contacto", "ciudad"]
        widgets = {
            "direccion": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Calle y número",
                }
            ),
            "tipo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Laboral, comercial o particular",
                }
            ),
            "codigo_postal": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Código postal",
                }
            ),
            "contacto": forms.Select(attrs={"class": "form-select"}),
            "ciudad": forms.Select(attrs={"class": "form-select"}),
        }
        error_messages = {
            "direccion": {
                "required": "La dirección no puede estar vacía.",
                "max_length": "La dirección no puede superar los 255 caracteres.",
            },
            "tipo": {
                "required": "El tipo no puede estar vacío.",
                "max_length": "El tipo no puede superar los 40 caracteres.",
            },
            "codigo_postal": {
                "max_length": "El código postal no puede superar los 20 caracteres.",
            },
            "contacto": {
                "required": "Seleccioná un contacto.",
                "invalid_choice": "Seleccioná un contacto.",
            },
            "ciudad": {
                "required": "Seleccioná una ciudad.",
                "invalid_choice": "Seleccioná una ciudad.",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["contacto"].empty_label = "Seleccioná un contacto"
        self.fields["contacto"].queryset = Contacto.objects.select_related(
            "empresa"
        ).order_by("apellido", "nombre")
        self.fields["contacto"].label_from_instance = _etiqueta_contacto
        self.fields["ciudad"].empty_label = "Seleccioná una ciudad"
        self.fields["ciudad"].queryset = Ciudad.objects.select_related(
            "departamento"
        ).order_by("departamento__nombre", "nombre")
        self.fields["ciudad"].label_from_instance = _etiqueta_ciudad

    def _post_clean(self):
        super()._post_clean()
        self._depurar_aviso_de_vacio()

    def _depurar_aviso_de_vacio(self):
        mensajes = {
            "direccion": "La dirección no puede estar vacía.",
            "tipo": "El tipo no puede estar vacío.",
        }
        for nombre, mensaje in mensajes.items():
            if nombre not in self.errors or len(self.errors[nombre]) < 2:
                continue
            restantes = [
                error for error in self.errors[nombre] if str(error) != mensaje
            ]
            if restantes:
                self.errors[nombre] = ErrorList(restantes)
