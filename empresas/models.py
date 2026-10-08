from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F
from django.db.models.functions import Length, Lower, Trim
from django.db.models.lookups import GreaterThan
from django.urls import reverse


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
