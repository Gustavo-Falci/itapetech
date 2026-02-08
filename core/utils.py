import threading
from django.core.mail import send_mail
from django.conf import settings

class EmailThread(threading.Thread):
    def __init__(self, subject, message, recipient_list):
        self.subject = subject
        self.message = message
        self.recipient_list = recipient_list
        threading.Thread.__init__(self)

    def run(self):
        print(f"--- THREAD: Iniciando envio de e-mail para {self.recipient_list} ---")
        try:
            send_mail(
                self.subject,
                self.message,
                settings.EMAIL_HOST_USER,
                self.recipient_list,
                fail_silently=False
            )
            print("--- THREAD: E-mail enviado com sucesso! ---")
        except Exception as e:
            print(f"--- THREAD ERRO: Falha ao enviar e-mail: {e} ---")