from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    
    # Rota do Painel do Cliente
    path('dashboard/', views.dashboard, name='dashboard'),

    # Rotas de Login/Logout (Usando as prontas do Django, mas com nosso template)
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('solicitar/', views.solicitar_orcamento, name='solicitar'),
    path('api/salvar_lead/', views.salvar_lead, name='salvar_lead'),
    path('register/', views.register, name='register'),
    path('validar-email/', views.validar_email, name='validar_email'),
    path('reenviar-codigo/', views.reenviar_codigo, name='reenviar_codigo'),
]
