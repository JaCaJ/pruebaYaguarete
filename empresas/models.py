import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Length, Lower, Trim
from django.db.models.lookups import GreaterThan
from django.urls import reverse

_FORMATO_RUC = re.compile(r"^(?:\d{1,8}-\d|\d{2,9})$")
MENSAJE_EMAIL_O_TELEFONO = "Indicá un email o un teléfono."


class Departamento(models.Model):
    nombre = models.CharField(
        "Nombre",
        max_length=120,
        unique=True,
        error_messages={
            "unique": "Ya existe un departamento con ese nombre.",
        },
    )

    class Meta:
        db_table = "departamentos"
        ordering = ["nombre"]
        verbose_name = "departamento"
        verbose_name_plural = "departamentos"
        constraints = [
            models.CheckConstraint(
                condition=GreaterThan(Length(Trim(F("nombre"))), 0),
                name="ck_departamentos_nombre_no_vacio",
                violation_error_message="El nombre no puede estar vacío.",
            ),
            models.UniqueConstraint(
                Lower("nombre"),
                name="uq_departamentos_nombre_sin_mayusculas",
                violation_error_message="Ya existe un departamento con ese nombre.",
            ),
        ]

    def __str__(self):
        return self.nombre

    def clean(self):
        super().clean()
        self.nombre = (self.nombre or "").strip()
        if not self.nombre:
            raise ValidationError({"nombre": "El nombre no puede estar vacío."})
        repetidos = Departamento.objects.filter(nombre__iexact=self.nombre)
        if self.pk:
            repetidos = repetidos.exclude(pk=self.pk)
        if repetidos.exists():
            raise ValidationError(
                {"nombre": "Ya existe un departamento con ese nombre."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("departamento-editar", kwargs={"pk": self.pk})


class Ciudad(models.Model):
    nombre = models.CharField("Nombre", max_length=120)
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT,
        related_name="ciudades",
        verbose_name="Departamento",
    )

    class Meta:
        db_table = "ciudades"
        ordering = ["nombre"]
        verbose_name = "ciudad"
        verbose_name_plural = "ciudades"
        constraints = [
            models.CheckConstraint(
                condition=GreaterThan(Length(Trim(F("nombre"))), 0),
                name="ck_ciudades_nombre_no_vacio",
                violation_error_message="El nombre no puede estar vacío.",
            ),
            models.UniqueConstraint(
                fields=["departamento", "nombre"],
                name="uq_ciudades_nombre_departamento",
                violation_error_message=(
                    "Ya existe una ciudad con ese nombre en ese departamento."
                ),
            ),
            models.UniqueConstraint(
                Lower("nombre"),
                F("departamento"),
                name="uq_ciudades_nombre_departamento_sin_mayusculas",
                violation_error_message=(
                    "Ya existe una ciudad con ese nombre en ese departamento."
                ),
            ),
        ]

    def __str__(self):
        return self.nombre

    def clean(self):
        super().clean()
        self.nombre = (self.nombre or "").strip()
        if not self.nombre:
            raise ValidationError({"nombre": "El nombre no puede estar vacío."})
        if not self.departamento_id:
            raise ValidationError({"departamento": "Seleccioná un departamento."})
        repetidos = Ciudad.objects.filter(
            nombre__iexact=self.nombre,
            departamento_id=self.departamento_id,
        )
        if self.pk:
            repetidos = repetidos.exclude(pk=self.pk)
        if repetidos.exists():
            raise ValidationError(
                {
                    "nombre": (
                        "Ya existe una ciudad con ese nombre en ese departamento."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("ciudad-editar", kwargs={"pk": self.pk})


class Categoria(models.Model):
    nombre = models.CharField(
        "Nombre",
        max_length=100,
        unique=True,
        error_messages={
            "unique": "Ya existe una categoría con ese nombre.",
        },
    )
    descripcion = models.CharField("Descripción", max_length=255, blank=True, default="")

    class Meta:
        db_table = "categorias"
        ordering = ["nombre"]
        verbose_name = "categoría"
        verbose_name_plural = "categorías"
        constraints = [
            models.CheckConstraint(
                condition=GreaterThan(Length(Trim(F("nombre"))), 0),
                name="ck_categorias_nombre_no_vacio",
                violation_error_message="El nombre no puede estar vacío.",
            ),
            models.UniqueConstraint(
                Lower("nombre"),
                name="uq_categorias_nombre_sin_mayusculas",
                violation_error_message="Ya existe una categoría con ese nombre.",
            ),
        ]

    def __str__(self):
        return self.nombre

    def clean(self):
        super().clean()
        self.nombre = (self.nombre or "").strip()
        self.descripcion = (self.descripcion or "").strip()
        if not self.nombre:
            raise ValidationError({"nombre": "El nombre no puede estar vacío."})
        repetidos = Categoria.objects.filter(nombre__iexact=self.nombre)
        if self.pk:
            repetidos = repetidos.exclude(pk=self.pk)
        if repetidos.exists():
            raise ValidationError(
                {"nombre": "Ya existe una categoría con ese nombre."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("categoria-editar", kwargs={"pk": self.pk})


class Empresa(models.Model):
    razon_social = models.CharField("Razón social", max_length=200)
    ruc = models.CharField(
        "RUC",
        max_length=20,
        unique=True,
        error_messages={
            "unique": "Ya existe una empresa con ese RUC.",
        },
    )
    email = models.EmailField("Email", max_length=254, blank=True, default="")
    telefono = models.CharField("Teléfono", max_length=30, blank=True, default="")
    es_cliente = models.BooleanField("Es cliente", default=False)
    es_proveedor = models.BooleanField("Es proveedor", default=False)
    activo = models.BooleanField("Activo", default=True)
    categorias = models.ManyToManyField(
        Categoria,
        related_name="empresas",
        blank=True,
        verbose_name="Categorías",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    usuario_creacion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="empresas_creadas",
        verbose_name="Usuario de creación",
    )
    usuario_modificacion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="empresas_modificadas",
        verbose_name="Usuario de modificación",
    )

    class Meta:
        db_table = "empresas"
        ordering = ["razon_social", "pk"]
        verbose_name = "empresa"
        verbose_name_plural = "empresas"
        constraints = [
            models.CheckConstraint(
                condition=GreaterThan(Length(Trim(F("razon_social"))), 0),
                name="ck_empresas_razon_social_no_vacia",
                violation_error_message="La razón social no puede estar vacía.",
            ),
            models.CheckConstraint(
                condition=GreaterThan(Length(Trim(F("ruc"))), 0),
                name="ck_empresas_ruc_no_vacio",
                violation_error_message="El RUC no puede estar vacío.",
            ),
            models.CheckConstraint(
                condition=Q(es_cliente=True) | Q(es_proveedor=True),
                name="ck_empresas_cliente_o_proveedor",
                violation_error_message=(
                    "La empresa debe ser cliente, proveedor o ambas."
                ),
            ),
        ]
        indexes = [
            models.Index(fields=["razon_social"], name="idx_empresas_razon_social"),
            models.Index(fields=["email"], name="idx_empresas_email"),
            models.Index(fields=["es_cliente"], name="idx_empresas_es_cliente"),
            models.Index(fields=["es_proveedor"], name="idx_empresas_es_proveedor"),
            models.Index(fields=["activo"], name="idx_empresas_activo"),
        ]

    def __str__(self):
        return self.razon_social

    def clean(self):
        super().clean()
        self.razon_social = (self.razon_social or "").strip()
        if not self.razon_social:
            raise ValidationError(
                {"razon_social": "La razón social no puede estar vacía."}
            )
        self.telefono = (self.telefono or "").strip()
        self.email = (self.email or "").strip()

        self.ruc = re.sub(r"\s+", "", (self.ruc or "").strip())
        if not self.ruc:
            raise ValidationError({"ruc": "El RUC no puede estar vacío."})
        if not _FORMATO_RUC.fullmatch(self.ruc):
            raise ValidationError({"ruc": "Ingresá un RUC válido."})

        repetidos = Empresa.objects.filter(ruc__iexact=self.ruc)
        if self.pk:
            repetidos = repetidos.exclude(pk=self.pk)
        if repetidos.exists():
            raise ValidationError({"ruc": "Ya existe una empresa con ese RUC."})

        if not self.es_cliente and not self.es_proveedor:
            raise ValidationError(
                "La empresa debe ser cliente, proveedor o ambas."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("empresa-editar", kwargs={"pk": self.pk})


class Contacto(models.Model):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name="contactos",
        verbose_name="Empresa",
    )
    nombre = models.CharField("Nombre", max_length=100)
    apellido = models.CharField("Apellido", max_length=100)
    email = models.EmailField("Email", max_length=254, blank=True, default="")
    telefono = models.CharField("Teléfono", max_length=30, blank=True, default="")
    cargo = models.CharField("Cargo", max_length=100, blank=True, default="")

    class Meta:
        db_table = "contactos"
        ordering = ["apellido", "nombre", "pk"]
        verbose_name = "contacto"
        verbose_name_plural = "contactos"
        constraints = [
            models.CheckConstraint(
                condition=GreaterThan(Length(Trim(F("nombre"))), 0),
                name="ck_contactos_nombre_no_vacio",
                violation_error_message="El nombre no puede estar vacío.",
            ),
            models.CheckConstraint(
                condition=GreaterThan(Length(Trim(F("apellido"))), 0),
                name="ck_contactos_apellido_no_vacio",
                violation_error_message="El apellido no puede estar vacío.",
            ),
            models.CheckConstraint(
                condition=(
                    GreaterThan(Length(Trim(F("email"))), 0)
                    | GreaterThan(Length(Trim(F("telefono"))), 0)
                ),
                name="ck_contactos_email_o_telefono",
                violation_error_message=MENSAJE_EMAIL_O_TELEFONO,
            ),
        ]
        indexes = [
            models.Index(fields=["empresa"], name="idx_contactos_empresa"),
        ]

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

    def clean(self):
        super().clean()
        self.nombre = (self.nombre or "").strip()
        self.apellido = (self.apellido or "").strip()
        self.telefono = (self.telefono or "").strip()
        self.cargo = (self.cargo or "").strip()
        self.email = (self.email or "").strip()
        if not self.nombre:
            raise ValidationError({"nombre": "El nombre no puede estar vacío."})
        if not self.apellido:
            raise ValidationError({"apellido": "El apellido no puede estar vacío."})
        if not self.empresa_id:
            raise ValidationError({"empresa": "Seleccioná una empresa."})
        if not self.email and not self.telefono:
            raise ValidationError(
                {
                    "email": MENSAJE_EMAIL_O_TELEFONO,
                    "telefono": MENSAJE_EMAIL_O_TELEFONO,
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("contacto-editar", kwargs={"pk": self.pk})
