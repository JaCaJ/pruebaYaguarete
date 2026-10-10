from django.contrib import admin

from .models import Categoria, Ciudad, Contacto, Departamento, Empresa


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


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "descripcion")
    search_fields = ("nombre", "descripcion")
    ordering = ("nombre",)


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = (
        "razon_social",
        "ruc",
        "es_cliente",
        "es_proveedor",
        "activo",
    )
    list_filter = ("es_cliente", "es_proveedor", "activo", "categorias")
    search_fields = ("razon_social", "ruc", "email")
    filter_horizontal = ("categorias",)
    ordering = ("razon_social",)


@admin.register(Contacto)
class ContactoAdmin(admin.ModelAdmin):
    list_display = ("apellido", "nombre", "empresa", "email", "cargo")
    list_filter = ("empresa",)
    search_fields = ("nombre", "apellido", "email", "cargo", "empresa__razon_social")
    ordering = ("apellido", "nombre")
