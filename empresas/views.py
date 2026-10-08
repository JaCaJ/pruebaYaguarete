from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import FormularioDepartamento
from .models import Departamento


def empresa_list(request):
    return render(request, "empresas/empresa_list.html")


class ListaDepartamentos(ListView):
    model = Departamento
    template_name = "empresas/departamento_list.html"
    context_object_name = "departamentos"
    paginate_by = 10

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.setdefault("formulario_creacion", FormularioDepartamento())
        return contexto


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

    def get_form(self, form_class=None):
        formulario = super().get_form(form_class)
        formulario.fields["nombre"].widget.attrs["autofocus"] = True
        return formulario


class EliminarDepartamento(DeleteView):
    model = Departamento
    template_name = "empresas/departamento_confirm_delete.html"
    context_object_name = "departamento"
    success_url = reverse_lazy("departamento-list")

    def get(self, request, *args, **kwargs):
        return redirect("departamento-list")

    def form_valid(self, form):
        messages.success(self.request, "Departamento eliminado.")
        if _es_solicitud_fetch(self.request):
            url = str(self.get_success_url())
            self.object.delete()
            return JsonResponse({"url": url})
        return super().form_valid(form)
