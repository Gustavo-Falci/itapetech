from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# 1. Extensão do usuário para guardar o WhatsApp
class Cliente(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cliente')
    whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp")

    def __str__(self):
        return f"{self.user.first_name} | {self.whatsapp}"

# 2. O computador do cliente (Mantive, caso queira usar no futuro para cadastro de inventário)
class Computador(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=50, choices=[('PC', 'Computador'), ('NB', 'Notebook')], default='NB')
    modelo = models.CharField(max_length=100, help_text="Ex: Dell Inspiron, PC Gamer i5")
    
    def __str__(self):
        return f"{self.modelo} - {self.cliente.user.first_name}"

# 3. Lead (Visitantes que pedem orçamento)
class Lead(models.Model):
    nome = models.CharField(max_length=100)
    modelo = models.CharField(max_length=100)
    servico = models.CharField(max_length=100)
    detalhes = models.TextField()
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    enviado = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.nome} - {self.servico}"

# 4. Serviço (A classe UNIFICADA e corrigida)
class Servico(models.Model):
    # Vincula ao usuário (Cliente logado)
    cliente = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    # Se for um visitante, salvamos o nome aqui
    nome_contato = models.CharField(max_length=100, default="Visitante")
    
    titulo = models.CharField(max_length=100, verbose_name="Serviço")  # Ex: Formatação
    computador = models.CharField(max_length=100, verbose_name="Equipamento") # Ex: Notebook Dell
    descricao = models.TextField(verbose_name="Descrição do Problema")
    
    status = models.CharField(max_length=20, default='Pendente', choices=[
        ('Pendente', 'Pendente'),
        ('Em Andamento', 'Em Andamento'),
        ('Concluido', 'Concluído')
    ])
    
    data = models.DateTimeField(auto_now_add=True) 
    
    def __str__(self):
        usuario = self.cliente.username if self.cliente else self.nome_contato
        return f"{self.titulo} - {usuario}"

# 5. Código de Validação de Email
class CodigoValidacao(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    codigo = models.CharField(max_length=6)
    criado_em = models.DateTimeField(auto_now_add=True) # Importante para a expiração

    def __str__(self):
        return f"Código de {self.user.username}"