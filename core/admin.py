from django.contrib import admin
from .models import Cliente, Computador, Servico, Lead

admin.site.register(Cliente)
admin.site.register(Computador)
admin.site.register(Servico)
admin.site.register(Lead)
