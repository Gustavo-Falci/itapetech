from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

UserModel = get_user_model()

class EmailBackend(ModelBackend):
    """
    Autentica o usuário usando o e-mail em vez do username.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Tenta buscar o usuário pelo E-mail
            # (Nota: o parâmetro 'username' recebe o que vem do campo de input, que é o email)
            user = UserModel.objects.get(email=username)
            
        except UserModel.DoesNotExist:
            # Se não achar pelo email, tenta pelo username normal (fallback)
            try:
                user = UserModel.objects.get(username=username)
            except UserModel.DoesNotExist:
                return None

        # Se achou o usuário e a senha bate
        if user.check_password(password):
            return user
        
        return None