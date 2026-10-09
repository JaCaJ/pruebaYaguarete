from django.contrib import admin

from .models import Ciudad, Departamento


@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)
    ordering = ("nombre",)


@admin.register(Ciudad)
class CiudadAdmin(admin.ModelAdmin):
    list_display = ("nombre", "departamento")
    list_filter = ("departamento",)
    search_fields = ("nombre", "departamento__nombre")
    ordering = ("nombre",)
