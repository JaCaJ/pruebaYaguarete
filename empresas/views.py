from django.shortcuts import render


def empresa_list(request):
    return render(request, "empresas/empresa_list.html")
