from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import ProtectedError, Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import FormularioCategoria, FormularioCiudad, FormularioDepartamento
from .models import Categoria, Ciudad, Departamento


def empresa_list(request):
    return render(request, "empresas/empresa_list.html")


class ListaDepartamentos(ListView):
    model = Departamento
    template_name = "empresas/departamento_list.html"
    context_object_name = "departamentos"
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        busqueda = self._texto_busqueda()
        if busqueda:
            queryset = queryset.filter(nombre__icontains=busqueda)
        orden = self._orden_pedido()
        if orden == "asc":
            return queryset.order_by("nombre", "pk")
        if orden == "desc":
            return queryset.order_by("-nombre", "pk")
        return queryset

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.setdefault("formulario_creacion", FormularioDepartamento())
        orden = self._orden_pedido()
        contexto["orden"] = orden
        contexto["busqueda"] = self._texto_busqueda()
        if orden == "asc":
            contexto["orden_siguiente"] = "desc"
            contexto["etiqueta_orden"] = "Ordenar por nombre descendente"
        elif orden == "desc":
            contexto["orden_siguiente"] = ""
            contexto["etiqueta_orden"] = "Volver al orden original"
        else:
            contexto["orden_siguiente"] = "asc"
            contexto["etiqueta_orden"] = "Ordenar por nombre ascendente"
        contexto["consulta_orden"] = self._consulta(orden=contexto["orden_siguiente"])
        pagina = contexto.get("page_obj")
        if pagina is not None and pagina.has_previous():
            contexto["consulta_anterior"] = self._consulta(page=pagina.previous_page_number())
        if pagina is not None and pagina.has_next():
            contexto["consulta_siguiente"] = self._consulta(page=pagina.next_page_number())
        return contexto

    def _orden_pedido(self):
        orden = self.request.GET.get("orden", "")
        if orden in ("asc", "desc"):
            return orden
        return ""

    def _texto_busqueda(self):
        return self.request.GET.get("buscar", "").strip()

    def _consulta(self, **cambios):
        valores = {
            "page": cambios.get("page", ""),
            "orden": self._orden_pedido() if "orden" not in cambios else cambios["orden"],
            "buscar": self._texto_busqueda() if "buscar" not in cambios else cambios["buscar"],
        }
        return urlencode([(clave, valor) for clave, valor in valores.items() if valor])


class _FormularioDepartamentoVista(SuccessMessageMixin):
    model = Departamento
    form_class = FormularioDepartamento
    template_name = "empresas/departamento_form.html"
    success_url = reverse_lazy("departamento-list")


def _textos_de_error(form):
    textos = []
    for errores in form.errors.values():
        for error in errores:
            texto = str(error)
            if texto not in textos:
                textos.append(texto)
    return textos


def _es_solicitud_fetch(request):
    return request.headers.get("X-Solicitud") == "fetch"


def _avisar_errores(request, form):
    for texto in _textos_de_error(form):
        messages.error(request, texto)


class CrearDepartamento(_FormularioDepartamentoVista, CreateView):
    success_message = "Departamento creado."

    def get(self, request, *args, **kwargs):
        return redirect(f"{reverse('departamento-list')}?nuevo=1")

    def form_valid(self, form):
        if _es_solicitud_fetch(self.request):
            self.object = form.save()
            mensaje = self.get_success_message(form.cleaned_data)
            if mensaje:
                messages.success(self.request, mensaje)
            return JsonResponse({"url": str(self.get_success_url())})
        return super().form_valid(form)

    def form_invalid(self, form):
        if _es_solicitud_fetch(self.request):
            return JsonResponse({"errores": _textos_de_error(form)}, status=400)
        _avisar_errores(self.request, form)
        clases = form.fields["nombre"].widget.attrs.get("class", "")
        if "is-invalid" not in clases.split():
            form.fields["nombre"].widget.attrs["class"] = f"{clases} is-invalid".strip()
        listado = ListaDepartamentos()
        listado.setup(self.request)
        listado.object_list = listado.get_queryset()
        contexto = listado.get_context_data(
            formulario_creacion=form,
            abrir_modal=True,
        )
        return render(self.request, listado.template_name, contexto)


class EditarDepartamento(_FormularioDepartamentoVista, UpdateView):
    success_message = "Departamento actualizado."
    extra_context = {
        "titulo": "Editar departamento",
        "texto_boton": "Guardar cambios",
    }

    def get(self, request, *args, **kwargs):
        return redirect("departamento-list")

    def get_form(self, form_class=None):
        formulario = super().get_form(form_class)
        formulario.fields["nombre"].widget.attrs["autofocus"] = True
        return formulario

    def form_valid(self, form):
        if _es_solicitud_fetch(self.request):
            self.object = form.save()
            mensaje = self.get_success_message(form.cleaned_data)
            if mensaje:
                messages.success(self.request, mensaje)
            return JsonResponse({"url": str(self.get_success_url())})
        return super().form_valid(form)

    def form_invalid(self, form):
        if _es_solicitud_fetch(self.request):
            return JsonResponse({"errores": _textos_de_error(form)}, status=400)
        return super().form_invalid(form)


class EliminarDepartamento(DeleteView):
    model = Departamento
    template_name = "empresas/departamento_confirm_delete.html"
    context_object_name = "departamento"
    success_url = reverse_lazy("departamento-list")

    def get(self, request, *args, **kwargs):
        return redirect("departamento-list")

    def form_valid(self, form):
        url = str(self.get_success_url())
        try:
            self.object.delete()
        except ProtectedError:
            texto = (
                "No se puede eliminar el departamento porque tiene ciudades asociadas."
            )
            if _es_solicitud_fetch(self.request):
                return JsonResponse({"errores": [texto]}, status=400)
            messages.error(self.request, texto)
            return redirect(url)
        messages.success(self.request, "Departamento eliminado.")
        if _es_solicitud_fetch(self.request):
            return JsonResponse({"url": url})
        return redirect(url)


class ListaCiudades(ListView):
    model = Ciudad
    template_name = "empresas/ciudad_list.html"
    context_object_name = "ciudades"
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().select_related("departamento")
        busqueda = self._texto_busqueda()
        if busqueda:
            queryset = queryset.filter(
                Q(nombre__icontains=busqueda)
                | Q(departamento__nombre__icontains=busqueda)
            )
        orden = self._orden_pedido()
        if self._columna_pedida() == "departamento":
            if orden == "asc":
                return queryset.order_by("departamento__nombre", "nombre", "pk")
            if orden == "desc":
                return queryset.order_by("-departamento__nombre", "nombre", "pk")
        if orden == "asc":
            return queryset.order_by("nombre", "pk")
        if orden == "desc":
            return queryset.order_by("-nombre", "pk")
        return queryset

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.setdefault("formulario_creacion", FormularioCiudad())
        contexto["catalogo_departamentos"] = Departamento.objects.order_by("nombre")
        orden = self._orden_pedido()
        columna = self._columna_pedida()
        contexto["orden"] = orden
        contexto["columna"] = columna
        contexto["busqueda"] = self._texto_busqueda()
        cabecera_nombre = self._datos_cabecera(
            orden if columna != "departamento" else "",
            "",
            "nombre",
        )
        cabecera_departamento = self._datos_cabecera(
            orden if columna == "departamento" else "",
            "departamento",
            "departamento",
        )
        contexto["orden_nombre"] = cabecera_nombre["orden"]
        contexto["etiqueta_orden"] = cabecera_nombre["etiqueta"]
        contexto["consulta_orden"] = cabecera_nombre["consulta"]
        contexto["orden_departamento"] = cabecera_departamento["orden"]
        contexto["etiqueta_orden_departamento"] = cabecera_departamento["etiqueta"]
        contexto["consulta_orden_departamento"] = cabecera_departamento["consulta"]
        pagina = contexto.get("page_obj")
        if pagina is not None and pagina.has_previous():
            contexto["consulta_anterior"] = self._consulta(page=pagina.previous_page_number())
        if pagina is not None and pagina.has_next():
            contexto["consulta_siguiente"] = self._consulta(page=pagina.next_page_number())
        return contexto

    def _datos_cabecera(self, orden_visible, columna_enlace, sustantivo):
        if orden_visible == "asc":
            siguiente = "desc"
            etiqueta = f"Ordenar por {sustantivo} descendente"
        elif orden_visible == "desc":
            siguiente = ""
            etiqueta = "Volver al orden original"
        else:
            siguiente = "asc"
            etiqueta = f"Ordenar por {sustantivo} ascendente"
        return {
            "orden": orden_visible,
            "etiqueta": etiqueta,
            "consulta": self._consulta(
                orden=siguiente,
                columna=columna_enlace if siguiente else "",
            ),
        }

    def _orden_pedido(self):
        orden = self.request.GET.get("orden", "")
        if orden in ("asc", "desc"):
            return orden
        return ""

    def _columna_pedida(self):
        if self.request.GET.get("columna") == "departamento" and self._orden_pedido():
            return "departamento"
        return ""

    def _texto_busqueda(self):
        return self.request.GET.get("buscar", "").strip()

    def _consulta(self, **cambios):
        columna = self._columna_pedida() if "columna" not in cambios else cambios["columna"]
        if columna != "departamento":
            columna = ""
        valores = {
            "page": cambios.get("page", ""),
            "orden": self._orden_pedido() if "orden" not in cambios else cambios["orden"],
            "columna": columna,
            "buscar": self._texto_busqueda() if "buscar" not in cambios else cambios["buscar"],
        }
        return urlencode([(clave, valor) for clave, valor in valores.items() if valor])


class _FormularioCiudadVista(SuccessMessageMixin):
    model = Ciudad
    form_class = FormularioCiudad
    template_name = "empresas/ciudad_form.html"
    success_url = reverse_lazy("ciudad-list")


def _marcar_invalidos(form):
    for nombre in form.errors:
        campo = form.fields.get(nombre)
        if campo is None:
            continue
        clases = campo.widget.attrs.get("class", "")
        if "is-invalid" not in clases.split():
            campo.widget.attrs["class"] = f"{clases} is-invalid".strip()


def _respuesta_errores(form):
    return JsonResponse(
        {"errores": _textos_de_error(form), "campos": list(form.errors)},
        status=400,
    )


class CrearCiudad(_FormularioCiudadVista, CreateView):
    success_message = "Ciudad creada."

    def get(self, request, *args, **kwargs):
        return redirect(f"{reverse('ciudad-list')}?nuevo=1")

    def form_valid(self, form):
        if _es_solicitud_fetch(self.request):
            self.object = form.save()
            mensaje = self.get_success_message(form.cleaned_data)
            if mensaje:
                messages.success(self.request, mensaje)
            return JsonResponse({"url": str(self.get_success_url())})
        return super().form_valid(form)

    def form_invalid(self, form):
        if _es_solicitud_fetch(self.request):
            return _respuesta_errores(form)
        _avisar_errores(self.request, form)
        _marcar_invalidos(form)
        listado = ListaCiudades()
        listado.setup(self.request)
        listado.object_list = listado.get_queryset()
        contexto = listado.get_context_data(
            formulario_creacion=form,
            abrir_modal=True,
        )
        return render(self.request, listado.template_name, contexto)


class EditarCiudad(_FormularioCiudadVista, UpdateView):
    success_message = "Ciudad actualizada."
    extra_context = {
        "titulo": "Editar ciudad",
        "texto_boton": "Guardar cambios",
    }

    def get(self, request, *args, **kwargs):
        return redirect("ciudad-list")

    def get_form(self, form_class=None):
        formulario = super().get_form(form_class)
        formulario.fields["nombre"].widget.attrs["autofocus"] = True
        return formulario

    def form_valid(self, form):
        if _es_solicitud_fetch(self.request):
            self.object = form.save()
            mensaje = self.get_success_message(form.cleaned_data)
            if mensaje:
                messages.success(self.request, mensaje)
            return JsonResponse({"url": str(self.get_success_url())})
        return super().form_valid(form)

    def form_invalid(self, form):
        if _es_solicitud_fetch(self.request):
            return _respuesta_errores(form)
        return super().form_invalid(form)


class EliminarCiudad(DeleteView):
    model = Ciudad
    template_name = "empresas/ciudad_confirm_delete.html"
    context_object_name = "ciudad"
    success_url = reverse_lazy("ciudad-list")

    def get(self, request, *args, **kwargs):
        return redirect("ciudad-list")

    def form_valid(self, form):
        messages.success(self.request, "Ciudad eliminada.")
        if _es_solicitud_fetch(self.request):
            url = str(self.get_success_url())
            self.object.delete()
            return JsonResponse({"url": url})
        return super().form_valid(form)


class ListaCategorias(ListView):
    model = Categoria
    template_name = "empresas/categoria_list.html"
    context_object_name = "categorias"
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        busqueda = self._texto_busqueda()
        if busqueda:
            queryset = queryset.filter(
                Q(nombre__icontains=busqueda) | Q(descripcion__icontains=busqueda)
            )
        orden = self._orden_pedido()
        if self._columna_pedida() == "descripcion":
            if orden == "asc":
                return queryset.order_by("descripcion", "nombre", "pk")
            if orden == "desc":
                return queryset.order_by("-descripcion", "nombre", "pk")
        if orden == "asc":
            return queryset.order_by("nombre", "pk")
        if orden == "desc":
            return queryset.order_by("-nombre", "pk")
        return queryset

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.setdefault("formulario_creacion", FormularioCategoria())
        orden = self._orden_pedido()
        columna = self._columna_pedida()
        contexto["orden"] = orden
        contexto["columna"] = columna
        contexto["busqueda"] = self._texto_busqueda()
        cabecera_nombre = self._datos_cabecera(
            orden if columna != "descripcion" else "",
            "",
            "nombre",
        )
        cabecera_descripcion = self._datos_cabecera(
            orden if columna == "descripcion" else "",
            "descripcion",
            "descripción",
        )
        contexto["orden_nombre"] = cabecera_nombre["orden"]
        contexto["etiqueta_orden"] = cabecera_nombre["etiqueta"]
        contexto["consulta_orden"] = cabecera_nombre["consulta"]
        contexto["orden_descripcion"] = cabecera_descripcion["orden"]
        contexto["etiqueta_orden_descripcion"] = cabecera_descripcion["etiqueta"]
        contexto["consulta_orden_descripcion"] = cabecera_descripcion["consulta"]
        pagina = contexto.get("page_obj")
        if pagina is not None and pagina.has_previous():
            contexto["consulta_anterior"] = self._consulta(page=pagina.previous_page_number())
        if pagina is not None and pagina.has_next():
            contexto["consulta_siguiente"] = self._consulta(page=pagina.next_page_number())
        return contexto

    def _datos_cabecera(self, orden_visible, columna_enlace, sustantivo):
        if orden_visible == "asc":
            siguiente = "desc"
            etiqueta = f"Ordenar por {sustantivo} descendente"
        elif orden_visible == "desc":
            siguiente = ""
            etiqueta = "Volver al orden original"
        else:
            siguiente = "asc"
            etiqueta = f"Ordenar por {sustantivo} ascendente"
        return {
            "orden": orden_visible,
            "etiqueta": etiqueta,
            "consulta": self._consulta(
                orden=siguiente,
                columna=columna_enlace if siguiente else "",
            ),
        }

    def _orden_pedido(self):
        orden = self.request.GET.get("orden", "")
        if orden in ("asc", "desc"):
            return orden
        return ""

    def _columna_pedida(self):
        if self.request.GET.get("columna") == "descripcion" and self._orden_pedido():
            return "descripcion"
        return ""

    def _texto_busqueda(self):
        return self.request.GET.get("buscar", "").strip()

    def _consulta(self, **cambios):
        columna = self._columna_pedida() if "columna" not in cambios else cambios["columna"]
        if columna != "descripcion":
            columna = ""
        valores = {
            "page": cambios.get("page", ""),
            "orden": self._orden_pedido() if "orden" not in cambios else cambios["orden"],
            "columna": columna,
            "buscar": self._texto_busqueda() if "buscar" not in cambios else cambios["buscar"],
        }
        return urlencode([(clave, valor) for clave, valor in valores.items() if valor])


class _FormularioCategoriaVista(SuccessMessageMixin):
    model = Categoria
    form_class = FormularioCategoria
    template_name = "empresas/categoria_form.html"
    success_url = reverse_lazy("categoria-list")


class CrearCategoria(_FormularioCategoriaVista, CreateView):
    success_message = "Categoría creada."

    def get(self, request, *args, **kwargs):
        return redirect(f"{reverse('categoria-list')}?nuevo=1")

    def form_valid(self, form):
        if _es_solicitud_fetch(self.request):
            self.object = form.save()
            mensaje = self.get_success_message(form.cleaned_data)
            if mensaje:
                messages.success(self.request, mensaje)
            return JsonResponse({"url": str(self.get_success_url())})
        return super().form_valid(form)

    def form_invalid(self, form):
        if _es_solicitud_fetch(self.request):
            return _respuesta_errores(form)
        _avisar_errores(self.request, form)
        _marcar_invalidos(form)
        listado = ListaCategorias()
        listado.setup(self.request)
        listado.object_list = listado.get_queryset()
        contexto = listado.get_context_data(
            formulario_creacion=form,
            abrir_modal=True,
        )
        return render(self.request, listado.template_name, contexto)


class EditarCategoria(_FormularioCategoriaVista, UpdateView):
    success_message = "Categoría actualizada."
    extra_context = {
        "titulo": "Editar categoría",
        "texto_boton": "Guardar cambios",
    }

    def get(self, request, *args, **kwargs):
        return redirect("categoria-list")

    def get_form(self, form_class=None):
        formulario = super().get_form(form_class)
        formulario.fields["nombre"].widget.attrs["autofocus"] = True
        return formulario

    def form_valid(self, form):
        if _es_solicitud_fetch(self.request):
            self.object = form.save()
            mensaje = self.get_success_message(form.cleaned_data)
            if mensaje:
                messages.success(self.request, mensaje)
            return JsonResponse({"url": str(self.get_success_url())})
        return super().form_valid(form)

    def form_invalid(self, form):
        if _es_solicitud_fetch(self.request):
            return _respuesta_errores(form)
        return super().form_invalid(form)


class EliminarCategoria(DeleteView):
    model = Categoria
    template_name = "empresas/categoria_confirm_delete.html"
    context_object_name = "categoria"
    success_url = reverse_lazy("categoria-list")

    def get(self, request, *args, **kwargs):
        return redirect("categoria-list")

    def form_valid(self, form):
        url = str(self.get_success_url())
        try:
            self.object.delete()
        except ProtectedError:
            texto = (
                "No se puede eliminar la categoría porque tiene empresas asociadas."
            )
            if _es_solicitud_fetch(self.request):
                return JsonResponse({"errores": [texto]}, status=400)
            messages.error(self.request, texto)
            return redirect(url)
        messages.success(self.request, "Categoría eliminada.")
        if _es_solicitud_fetch(self.request):
            return JsonResponse({"url": url})
        return redirect(url)
