from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from .models import Servico
from django.conf import settings
from .models import CodigoValidacao
from django.utils import timezone
from .utils import EmailThread
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
import json
import random
import re

def index(request):
    return render(request, 'core/index.html')

@login_required # Só deixa entrar se estiver logado
def dashboard(request):
    # Tenta pegar o cliente ligado ao usuário logado
    try:
        # Busca os serviços feitos nos computadores desse cliente
        servicos = Servico.objects.filter(cliente=request.user).order_by('-data')
    except:
        # Se o usuário não tiver perfil de cliente ainda
        servicos = []

    return render(request, 'core/dashboard.html', {'servicos': servicos})

def solicitar_orcamento(request):
    return render(request, 'core/solicitar.html')

def salvar_lead(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            
            # Lógica Inteligente:
            usuario = None
            nome_para_salvar = dados['nome'] # Pega o nome que veio do formulário

            # Se estiver logado, vinculamos a conta
            if request.user.is_authenticated:
                usuario = request.user
                nome_para_salvar = usuario.first_name

            # 2. SALVA NO BANCO (Usando o modelo Servico)
            novo_servico = Servico.objects.create(
                cliente=usuario,
                nome_contato=nome_para_salvar, # Aqui fazemos o vínculo com o Dashboard!
                titulo=dados['servico'],      # No banco chama 'titulo', no JSON chama 'servico'
                computador=dados['modelo'],   # No banco chama 'computador', no JSON chama 'modelo'
                descricao=dados['detalhes']   # No banco chama 'descricao', no JSON chama 'detalhes'
            )
            
            # 3. DISPARA O E-MAIL (Mantive sua lógica, que está ótima!)
            # Note que usamos dados['nome'] para o email, mesmo que não salve no banco se for anônimo
            assunto = f"🚨 Novo Lead: {dados['nome']} - {dados['servico']}"
            mensagem = f"""
            Alerta de novo cliente no site!
            
            Nome: {dados['nome']} {(f'(Usuário Logado)' if usuario else '(Visitante)')}
            Equipamento: {dados['modelo']}
            Serviço: {dados['servico']}
            Detalhes: {dados['detalhes']}
            """
            
            EmailThread(
                assunto, 
                mensagem, 
                [settings.EMAIL_HOST_RECEIPT]
            ).start()

            return JsonResponse({'status': 'sucesso', 'id': novo_servico.id})
            
        except Exception as e:
            return JsonResponse({'status': 'erro', 'msg': str(e)}, status=400)
            
    return JsonResponse({'status': 'erro'}, status=400)

def register(request):
    if request.method == 'POST':
        print("--- DEBUG: Recebi um POST no Registro ---")

        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # Dicionário de contexto para manter os dados preenchidos em caso de erro
        contexto_dados = {
            'full_name': full_name,
            'email': email
        }

        # --- VALIDAÇÕES DE SENHA ---
        if password != confirm_password:
             return render(request, 'core/register.html', {**contexto_dados, 'error': 'As senhas não coincidem.'})

        if len(password) < 8:
            return render(request, 'core/register.html', {**contexto_dados, 'error': 'A senha deve ter no mínimo 8 caracteres.'})

        if not re.search(r'[A-Z]', password):
            return render(request, 'core/register.html', {**contexto_dados, 'error': 'A senha deve ter pelo menos uma letra MAIÚSCULA.'})

        if not re.search(r'[a-z]', password):
            return render(request, 'core/register.html', {**contexto_dados, 'error': 'A senha deve ter pelo menos uma letra minúscula.'})

        if not re.search(r'[0-9]', password):
            return render(request, 'core/register.html', {**contexto_dados, 'error': 'A senha deve ter pelo menos um número.'})

        # --- VERIFICAÇÃO DE USUÁRIO EXISTENTE ---
        usuario_existente = User.objects.filter(email=email).first()

        if usuario_existente:
            # CASO 1: Usuário existe e JÁ ESTÁ ATIVO
            if usuario_existente.is_active:
                return render(request, 'core/register.html', {**contexto_dados, 'error': 'Este e-mail já possui uma conta ativa. Faça login.'})
            
            # CASO 2: Usuário existe mas ESTÁ INATIVO (Limbo)
            else:
                # Verifica senha para garantir que é o dono da conta tentando reenviar
                if usuario_existente.check_password(password):
                    print("--- DEBUG: Usuário inativo encontrado. Reenviando código... ---")
                    
                    novo_codigo = str(random.randint(100000, 999999))
                    
                    # Atualiza ou Cria o código
                    obj, created = CodigoValidacao.objects.update_or_create(
                        user=usuario_existente,
                        defaults={'codigo': novo_codigo}
                    )
                    
                    # FORÇA a atualização da data para renovar os 10 minutos
                    obj.criado_em = timezone.now()
                    obj.save()
                    
                    # Reenvia e-mail
                    assunto = 'Continue seu cadastro - ITape Tech'
                    mensagem = f'Seu código de verificação é: {novo_codigo}'
                    EmailThread(assunto, mensagem, [email]).start()
                    
                    request.session['email_validacao'] = email
                    return redirect('validar_email')
                
                else:
                    # Usuário inativo existe, mas errou a senha
                    return render(request, 'core/register.html', {**contexto_dados, 'error': 'E-mail já cadastrado (Pendente). Use a senha correta ou faça login.'})

        # --- CENÁRIO: USUÁRIO NOVO (Criação) ---
        else:
            try:
                # 1. Cria usuário INATIVO
                user = User.objects.create_user(username=email, email=email, password=password)
                user.first_name = full_name
                user.is_active = False # Importante
                user.save()

                # 2. Gera Código
                codigo_gerado = str(random.randint(100000, 999999))
                CodigoValidacao.objects.create(user=user, codigo=codigo_gerado)

                # 3. Envia E-mail
                assunto = 'Confirme sua conta - ITape Tech'
                mensagem = f'Olá, {full_name}!\n\nSeu código de verificação é: {codigo_gerado}'
                
                EmailThread(assunto, mensagem, [email]).start()

                # 4. Redireciona
                request.session['email_validacao'] = email
                return redirect('validar_email')

            except Exception as e:
                print(f"--- DEBUG: ERRO CRÍTICO: {e}")
                # Limpeza de segurança
                if 'user' in locals() and user.pk:
                    user.delete()
                return render(request, 'core/register.html', {**contexto_dados, 'error': 'Erro ao realizar cadastro. Tente novamente.'})

    return render(request, 'core/register.html')

def validar_email(request):
    # Recupera o email da sessão
    email = request.session.get('email_validacao')
    
    # --- NOVO: CÁLCULO DO TEMPO RESTANTE (Para bloquear o botão no F5) ---
    tempo_restante = 0
    
    if email:
        try:
            # Tenta buscar o registro de validação para calcular o tempo
            user_temp = User.objects.get(email=email)
            validacao_temp = CodigoValidacao.objects.filter(user=user_temp).first()
            
            if validacao_temp:
                # Calcula quantos segundos passaram desde que o código foi gerado
                segundos_passados = (timezone.now() - validacao_temp.criado_em).total_seconds()
                
                # Se passou menos de 90 segundos, calcula quanto falta para acabar o cooldown
                if segundos_passados < 90:
                    tempo_restante = int(90 - segundos_passados)
                    
        except User.DoesNotExist:
            pass
    # ---------------------------------------------------------------------

    if request.method == 'POST':
        codigo_digitado = request.POST.get('codigo')

        if not email:
            return redirect('register')

        try:
            user = User.objects.get(email=email)
            validacao = CodigoValidacao.objects.get(user=user)

            # Validade do Código (10 minutos para expirar o token)
            tempo_limite_codigo = timedelta(minutes=10)

            if timezone.now() > (validacao.criado_em + tempo_limite_codigo):
                return render(request, 'core/validar_email.html', {
                    'error': 'Este código expirou! Por favor, solicite um novo.',
                    'tempo_restante': tempo_restante # Mantém o botão bloqueado se necessário
                })

            if validacao.codigo == codigo_digitado:
                # Código correto! Ativar usuário
                user.is_active = True
                user.save()
                validacao.delete()
                
                messages.success(request, 'Conta ativada com sucesso! Faça login.')
                return redirect('login') 
            else:
                return render(request, 'core/validar_email.html', {
                    'error': 'Código incorreto!',
                    'tempo_restante': tempo_restante
                })

        except CodigoValidacao.DoesNotExist:
             return render(request, 'core/validar_email.html', {
                 'error': 'Código não encontrado ou expirado',
                 'tempo_restante': tempo_restante
             })

    # Renderização do GET (Passando o tempo calculado)
    return render(request, 'core/validar_email.html', {'tempo_restante': tempo_restante})

def reenviar_codigo(request):
    email = request.session.get('email_validacao')

    # Se não tiver e-mail na sessão
    if not email:
        return JsonResponse({'status': 'error', 'message': 'Sessão expirada. Faça login.'}, status=400)

    try:
        user = User.objects.get(email=email)
        
        # Busca o último código gerado
        validacao_anterior = CodigoValidacao.objects.filter(user=user).first()
        
        # --- LÓGICA DO TIMEOUT (90 SEGUNDOS) ---
        if validacao_anterior:
            agora = timezone.now()
            # Calcula a diferença em segundos
            tempo_passado = (agora - validacao_anterior.criado_em).total_seconds()
            
            if tempo_passado < 90:
                segundos_restantes = int(90 - tempo_passado)
                # Retornamos o tempo exato no JSON ('wait') para o JS usar
                return JsonResponse({
                    'status': 'error', 
                    'message': f'Aguarde {segundos_restantes}s para reenviar.',
                    'wait': segundos_restantes 
                }, status=429)
        # ---------------------------------------

        # Gera novo código
        novo_codigo = str(random.randint(100000, 999999))
        
        # Atualiza a data de criação para AGORA (reinicia o timer)
        CodigoValidacao.objects.update_or_create(
            user=user,
            defaults={'codigo': novo_codigo, 'criado_em': timezone.now()}
        )

        # Envia o e-mail (Thread)
        assunto = 'Reenvio de código - ITape Tech'
        mensagem = f'Seu novo código de verificação é: {novo_codigo}'
        EmailThread(assunto, mensagem, [email]).start()

        return JsonResponse({'status': 'success', 'message': 'Novo código enviado!'})

    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Usuário não encontrado.'}, status=404)
    except Exception as e:
        # Captura erros genéricos para não travar o botão
        print(f"ERRO REENVIO: {e}")
        return JsonResponse({'status': 'error', 'message': 'Erro interno do servidor.'}, status=500)

def login_view(request):
    if request.method == 'POST':
        print("--- DEBUG LOGIN ---")
        email = request.POST.get('email')
        password = request.POST.get('password')
        print(f"Tentando logar com: {email}")

        # Tenta autenticar
        # Importante: passamos 'username=email' porque o backend espera o argumento 'username'
        user = authenticate(request, username=email, password=password)
        
        print(f"Resultado do authenticate: {user}")

        if user is not None:
            if user.is_active:
                login(request, user)
                print("Login realizado! Redirecionando...")
                return redirect('dashboard')
            else:
                print("Usuário existe e senha correta, mas INATIVO.")
                request.session['email_validacao'] = email
                return redirect('validar_email')
        else:
            print("Authenticate retornou None. Verificando inatividade manual...")
            # Fallback manual para conta inativa
            try:
                usuario_teste = User.objects.get(email=email)
                if usuario_teste.check_password(password):
                    if not usuario_teste.is_active:
                        print("Usuário achado manualmente e senha ok. Redirecionando para validar.")
                        request.session['email_validacao'] = email
                        return redirect('validar_email')
                else:
                    print("Senha incorreta.")
            except User.DoesNotExist:
                print("E-mail não existe no banco.")

            return render(request, 'core/login.html', {'error': 'E-mail ou senha incorretos.'})

    return render(request, 'core/login.html')

def logout_view(request):
    logout(request)
    return redirect('index')