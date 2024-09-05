import asyncio
from telethon.sync import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest, GetParticipantsRequest, JoinChannelRequest
from telethon.tl.types import Channel, ChannelParticipantsRecent, User
from telethon.errors import UserPrivacyRestrictedError, ChatAdminRequiredError, InviteHashInvalidError
from telethon.tl.types import InputPeerChannel, InputPeerUser
import os
import random

# Substitua pelos seus dados
api_id = 'ID'
api_hash = 'HASH'
session_directory = './sessions'  # Diretório onde as sessões serão armazenadas

# Verifica ou cria o diretório de sessões
if not os.path.exists(session_directory):
    os.makedirs(session_directory)

def load_sessions():
    """Carrega todas as sessões disponíveis no diretório de sessões."""
    sessions = []
    for file in os.listdir(session_directory):
        if file.endswith('.session'):
            session_name = os.path.join(session_directory, file.replace('.session', ''))
            sessions.append(session_name)
    return sessions

async def add_number():
    while True:
        phone_number = input("Digite o número de telefone do novo Telegram: ").strip()
        if phone_number:
            break
        else:
            print("Número de telefone inválido. Tente novamente.")

    new_session = os.path.join(session_directory, f"session_{phone_number}.session")
    new_client = TelegramClient(new_session, api_id, api_hash)
    
    await new_client.connect()
    
    if not await new_client.is_user_authorized():
        await new_client.send_code_request(phone_number)
        while True:
            code = input(f"Digite o código de verificação para {phone_number}: ")
            if code:
                try:
                    await new_client.sign_in(phone_number, code)
                    break
                except Exception as e:
                    print(f"Erro ao autenticar: {e}. Tente novamente.")
            else:
                print("Código de verificação inválido. Tente novamente.")
    
    print(f"Número {phone_number} adicionado com sucesso ao sistema.")
    
    await new_client.disconnect()

async def verify_sessions():
    sessions = load_sessions()
    if not sessions:
        print("Nenhuma sessão encontrada. Adicione um número primeiro.")
        return

    print("Verificando sessões...")
    online_sessions = []
    offline_sessions = []

    for session in sessions:
        client = TelegramClient(session, api_id, api_hash)
        await client.connect()

        if await client.is_user_authorized():
            online_sessions.append(session)
        else:
            offline_sessions.append(session)

        await client.disconnect()

    print(f"Sessões Online: {len(online_sessions)}")
    for session in online_sessions:
        print(f"\033[92m{session}\033[0m")

    print(f"Sessões Offline: {len(offline_sessions)}")
    for session in offline_sessions:
        print(f"\033[91m{session}\033[0m")

async def collect_leads_from_group(client, group):
    leads = []
    offset = 0
    limit = 100
    
    while True:
        participants = await client(GetParticipantsRequest(
            channel=group,
            filter=ChannelParticipantsRecent(),
            offset=offset,
            limit=limit,
            hash=0
        ))
        
        if not participants.users:
            break
        
        for user in participants.users:
            if isinstance(user, User):
                if user.phone:
                    # Adiciona o sinal '+' antes do número do telefone
                    phone_number = f"+{user.phone}"
                    leads.append(phone_number)
                elif user.username:
                    # Adiciona o nome de usuário se o número não estiver disponível
                    username = f"@{user.username}"
                    leads.append(username)
        
        offset += limit
    
    return leads

async def list_and_collect_leads():
    sessions = load_sessions()
    if not sessions:
        print("Nenhuma sessão encontrada. Adicione um número primeiro.")
        return
    
    # Escolher a sessão para listar grupos
    while True:
        print("Sessões disponíveis:")
        for i, session in enumerate(sessions, 1):
            print(f"{i}. {session}")
        try:
            session_choice = int(input("Escolha a sessão para listar os grupos: "))
            if 1 <= session_choice <= len(sessions):
                break
            else:
                print("Escolha inválida. Tente novamente.")
        except ValueError:
            print("Entrada inválida. Por favor, digite um número válido.")
    
    selected_session = sessions[session_choice - 1]
    client = TelegramClient(selected_session, api_id, api_hash)

    await client.connect()

    groups = []
    dialogs = await client.get_dialogs()
    for dialog in dialogs:
        entity = dialog.entity
        if isinstance(entity, Channel) and entity.megagroup:
            groups.append(entity)
    
    if groups:
        print("Grupos disponíveis para coleta de leads:")
        for i, group in enumerate(groups, 1):
            print(f"{i}. {group.title} (ID: {group.id})")
        while True:
            try:
                group_choice = int(input("Escolha um grupo para coletar os leads (digite o número correspondente): "))
                if 1 <= group_choice <= len(groups):
                    selected_group = groups[group_choice - 1]
                    break
                else:
                    print("Escolha inválida. Tente novamente.")
            except ValueError:
                print("Entrada inválida. Por favor, digite um número válido.")
        
        leads = await collect_leads_from_group(client, selected_group)
        
        with open('leads.txt', 'w') as file:
            for lead in leads:
                file.write(f"{lead}\n")
        
        print(f"Leads coletados do grupo '{selected_group.title}' e salvos em 'leads.txt'.")
    else:
        print("Nenhum grupo disponível para coleta de leads.")
    
    await client.disconnect()

async def list_admin_groups():
    sessions = load_sessions()
    if not sessions:
        print("Nenhuma sessão encontrada. Adicione um número primeiro.")
        return
    
    admin_groups = []
    
    for session in sessions:
        client = TelegramClient(session, api_id, api_hash)
        
        try:
            await client.connect()

            if not await client.is_user_authorized():
                phone_number = input('Digite o número de telefone para autenticar o bot: ')
                await client.send_code_request(phone_number)
                code = input('Digite o código de verificação: ')
                await client.sign_in(phone_number, code)

            dialogs = await client.get_dialogs()
            for dialog in dialogs:
                entity = dialog.entity
                if isinstance(entity, Channel) and entity.megagroup:
                    try:
                        rights = await client.get_permissions(entity, await client.get_me())
                        if rights.is_admin:
                            admin_groups.append(entity)
                    except Exception as e:
                        print(f"Erro ao verificar permissões no grupo {entity.title}: {e}")

        except Exception as e:
            print(f"Erro: {e}. Verifique a sessão e tente novamente.")
        finally:
            await client.disconnect()

    if admin_groups:
        print("Grupos onde você é admin:")
        for i, group in enumerate(admin_groups, 1):
            print(f"{i}. {group.title} (ID: {group.id})")
        while True:
            try:
                choice = int(input("Escolha um grupo para adicionar os contatos (digite o número correspondente): "))
                if 1 <= choice <= len(admin_groups):
                    selected_group = admin_groups[choice - 1]
                    break
                else:
                    print("Escolha inválida. Tente novamente.")
            except ValueError:
                print("Entrada inválida. Por favor, digite um número válido.")
        
        add_contacts = input(f"Deseja adicionar os contatos ao grupo '{selected_group.title}'? (s/n): ").strip().lower()
        if add_contacts == 's':
            while True:
                try:
                    num_sessions = int(input(f"Quantas sessões deseja usar? (Disponível: {len(sessions)}): "))
                    if 1 <= num_sessions <= len(sessions):
                        await add_leads_to_group(selected_group, sessions[:num_sessions])
                        break
                    else:
                        print("Número de sessões inválido. Tente novamente.")
                except ValueError:
                    print("Entrada inválida. Por favor, digite um número válido.")
        else:
            print("Operação cancelada.")
    else:
        print("Você não é administrador em nenhum grupo.")

async def add_leads_to_group(group, sessions):
    try:
        # Carregar contatos do arquivo leads.txt
        with open('leads.txt', 'r') as file:
            contacts = [line.strip() for line in file.readlines()]
            contacts = [f"+{contact}" if not contact.startswith(('+', '@')) else contact for contact in contacts]

        numbers_per_session = 70
        num_sessions = len(sessions)
        total_contacts = len(contacts)
        current_index = 0

        for i, session in enumerate(sessions):
            if current_index >= total_contacts:
                break

            client = TelegramClient(session, api_id, api_hash)
            await client.connect()

            if not await client.is_user_authorized():
                phone_number = input('Digite o número de telefone para autenticar o bot: ')
                await client.send_code_request(phone_number)
                code = input('Digite o código de verificação: ')
                await client.sign_in(phone_number, code)

            # Obter o canal e garantir que está no formato correto
            try:
                group_entity = await client.get_entity(group)
                if not isinstance(group_entity, Channel):
                    print(f"Entidade do grupo {group} não é um canal válido.")
                    await client.disconnect()
                    continue
                
                input_group = InputPeerChannel(group_entity.id, group_entity.access_hash)
            except Exception as e:
                print(f"Erro ao obter entidade do grupo: {e}")
                await client.disconnect()
                continue

            session_contacts = contacts[current_index:current_index + numbers_per_session]
            current_index += numbers_per_session

            for contact in session_contacts:
                try:
                    print(f"Tentando adicionar {contact} ao grupo...")

                    if contact.startswith('@'):
                        user_entity = await client.get_entity(contact)
                        input_user = InputPeerUser(user_entity.id, user_entity.access_hash)
                        await client(InviteToChannelRequest(
                            channel=input_group,
                            users=[input_user]
                        ))
                    else:
                        await client(InviteToChannelRequest(
                            channel=input_group,
                            users=[contact]
                        ))

                    print(f"Contato {contact} adicionado com sucesso!")

                    with open('adicionado.txt', 'a') as added_file:
                        added_file.write(f"{contact}\n")

                    wait_time = random.uniform(2, 30)
                    print(f"Esperando {wait_time:.2f} segundos antes de adicionar o próximo contato...")
                    await asyncio.sleep(wait_time)

                except UserPrivacyRestrictedError:
                    print(f"Privacidade restrita: {contact}.")
                except ChatAdminRequiredError:
                    print(f"Não é administrador do grupo: {contact}.")
                except Exception as e:
                    print(f"Erro ao adicionar {contact}: {e}")

            await client.disconnect()
            print(f"Sessão {i + 1} ({session}) concluída.")

    except FileNotFoundError:
        print("Arquivo 'leads.txt' não encontrado.")

async def add_leads_to_group_from_file():
    while True:
        if os.path.exists('leads.txt'):
            break
        else:
            print("Arquivo 'leads.txt' não encontrado. Certifique-se de ter coletado os leads.")
            await asyncio.sleep(5)
    
    await list_admin_groups()

def update_leads_file():
    # Ler os nomes dos arquivos
    try:
        with open('adicionado.txt', 'r') as added_file:
            added_names = set(line.strip() for line in added_file if line.strip())

        with open('leads.txt', 'r') as leads_file:
            leads_names = set(line.strip() for line in leads_file if line.strip())
        
        # Remover os nomes que estão em ambos os arquivos
        updated_leads_names = leads_names - added_names
        
        # Escrever os nomes atualizados de volta no arquivo leads.txt
        with open('leads.txt', 'w') as leads_file:
            for name in updated_leads_names:
                leads_file.write(f"{name}\n")
        
        print("Arquivo leads.txt atualizado com sucesso.")
    
    except FileNotFoundError as e:
        print(f"Erro: {e}")

async def join_group_if_not_member(client, group_link):
    try:
        # Verificar se já é membro do grupo
        group_entity = await client.get_entity(group_link)
        input_group = InputPeerChannel(group_entity.id, group_entity.access_hash)

        in_group = False
        async for dialog in client.iter_dialogs():
            if dialog.entity.id == group_entity.id:
                in_group = True
                break

        if not in_group:
            print(f"Entrando no grupo '{group_entity.title}'...")
            await client(JoinChannelRequest(input_group))
            print(f"Entrou no grupo '{group_entity.title}' com sucesso.")
        else:
            print(f"Já é membro do grupo '{group_entity.title}'.")

        return input_group

    except InviteHashInvalidError:
        print(f"Erro: Convite inválido para o grupo {group_link}. Verifique se o link ou ID do grupo está correto.")
        return None
    except Exception as e:
        print(f"Erro ao verificar ou entrar no grupo: {e}")
        return None

async def manage_sessions_and_join_group(group_link, session_names):
    for i, session_name in enumerate(session_names):
        session_path = os.path.join(session_directory, f"{session_name}.session")
        if not os.path.exists(session_path):
            print(f"Arquivo de sessão não encontrado: {session_path}.")
            continue

        client = TelegramClient(session_path, api_id, api_hash)
        await client.connect()

        if not await client.is_user_authorized():
            phone_number = input(f'Digite o número de telefone para autenticar o bot na sessão {session_name}: ')
            await client.send_code_request(phone_number)
            code = input('Digite o código de verificação: ')
            await client.sign_in(phone_number, code)

        # Verificar e entrar no grupo se necessário
        await join_group_if_not_member(client, group_link)

        await client.disconnect()
        print(f"Sessão {i + 1} ({session_name}) verificada/conectada ao grupo.")


def exibir_art_ascii():
    print("""
       ##    #####    ####    ##   ##           ######    #####
            ##   ##    ##     ###  ##            ##  ##  ##   ##
      ###   ##   ##    ##     #### ##  ######    ##  ##  ##   ##
       ##   ##   ##    ##     ## ####   ##  ##   #####   ##   ##
       ##   ##   ##    ##     ##  ###   ##  ##   ## ##   ##   ##
   ##  ##   ##   ##    ##     ##   ##   #####    ##  ##  ##   ##
   ##  ##    #####    ####    ##   ##   ##      #### ##   #####
    ####                               ####'
    """)

def menu():
    exibir_art_ascii()
    while True:
        print("\nMenu:")
        print("1. Adicionar número de telefone")
        print("2. Verificar sessões")
        print("3. Coletar leads de grupos")
        print("4. Adicionar leads a grupo a partir do arquivo")
        print("5 - Atualizar arquivo de leads (remover adicionados)")
        print("6 - Adicionar SESSIONS ao grupo")
        print("0. Sair")
        choice = input("Escolha uma opção: ")

        if choice == '1':
            asyncio.run(add_number())
        elif choice == '2':
            asyncio.run(verify_sessions())
        elif choice == '3':
            asyncio.run(list_and_collect_leads())
        elif choice == '4':
            asyncio.run(add_leads_to_group_from_file())
        elif choice == "5":
            update_leads_file()
        elif choice == '6':
            group = input("Digite o ID ou link do grupo: ")
            sessions_input = input("Digite os nomes das sessões separados por vírgula: ")
            sessions = [session.strip() for session in sessions_input.split(',')]
            asyncio.run(manage_sessions_and_join_group(group, sessions))
        elif choice == '0':
            break
        else:
            print("Opção inválida. Tente novamente.")    
        

if __name__ == "__main__":
    menu()
