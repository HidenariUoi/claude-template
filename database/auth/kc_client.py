import os

from keycloak import KeycloakAdmin

host = os.environ["DASH_DOMAIN_BASE"]

username = os.environ["KEYCLOAK_ADMIN_NAME"]
password = os.environ["KEYCLOAK_ADMIN_PASSWD"]
keycloak_url = f"https://auth-{host}/auth/"
keycloak_admin = KeycloakAdmin(
    server_url=keycloak_url,
    username=username,
    password=password,
    user_realm_name="master",
    realm_name="dash",
)


def attach_role(role_name, user_id):
    dash_client_id = keycloak_admin.get_client_id("dash")
    va_role_id = keycloak_admin.get_client_role_id(client_id=dash_client_id, role_name=role_name)
    va_role = {
        "id": va_role_id,
        "name": role_name,
        "composite": False,
        "clientRole": True,
        "containerId": dash_client_id,
    }
    keycloak_admin.assign_client_role(client_id=dash_client_id, user_id=user_id, roles=va_role)


def create_user(username, email, group, password, roles):
    try:
        new_user = keycloak_admin.create_user(
            {
                "email": email,
                "username": username,
                "enabled": True,
                "credentials": [
                    {
                        "value": password,
                        "type": "password",
                        "temporary": True,
                    }
                ],
            },
            exist_ok=False,
        )
        user_id = keycloak_admin.get_user_id(username)
        if not isinstance(roles, str):
            for role in roles:
                print("Attaching new role")
                attach_role(role, new_user)

        groups = keycloak_admin.get_groups()
        matched_group = next((g for g in groups if g["name"] == group), None)
        if matched_group:
            keycloak_admin.group_user_add(user_id=user_id, group_id=matched_group["id"])
            print(f"User added to group: {group}")
        else:
            print(f"\033[93mGroup '{group}' not found.\033[0m")
        return True, ""

    except Exception as e:
        print(
            f"\033[91mCan't create user with this username: {username}."
            f" You can see the reason under this message.\033[0m"
        )
        print(e)
        return False, str(e)


def list_all_users():
    try:
        formatted_users = []
        dash_client_id = keycloak_admin.get_client_id("dash")
        users = keycloak_admin.get_users()
        for user in users:
            user_id = user["id"]
            roles = keycloak_admin.get_client_roles_of_user(
                client_id=dash_client_id, user_id=user_id
            )
            groups = keycloak_admin.get_user_groups(user_id)
            formatted_users.append(
                {
                    "ID": user.get("id", ""),
                    "Name": user.get("username", ""),
                    "Group": [group["name"] for group in groups] if groups else "",
                    "Email": user.get("email", ""),
                    "Roles": ", ".join([role["name"] for role in roles]) if roles else "",
                }
            )
        return formatted_users

    except Exception as e:
        print(f"\033[91mError fetching Keycloak users: {e}\033[0m")
        return []


def delete_user(user_id):
    try:
        keycloak_admin.delete_user(user_id)
        print(f"User {user_id} deleted successfully.")
        return True
    except Exception as e:
        print(f"\033[91mFailed to delete user {user_id}: {e}\033[0m")
        return False
