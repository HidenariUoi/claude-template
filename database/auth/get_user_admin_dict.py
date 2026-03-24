from typing import Dict

from database.auth.kc_client import keycloak_admin


def get_user_admin_dict() -> Dict[str, bool]:
    """
    Dashアカウントのユーザ名リストを取得する


    Args::
        N/A


    Return::
        user_admin_dict[username, is_admin] (dict[str, bool]): 全ユーザのユーザ名(username)と権限(is_admin)の辞書
    """

    user_admin_dict = {}
    users = keycloak_admin.get_users()
    clients = keycloak_admin.get_clients()
    dash_client_id = None
    for client in clients:
        if client["clientId"] == "dash":
            dash_client_id = client["id"]
            break
    else:
        raise ValueError("dash does not in keyclock client")

    for user in users:
        user_id = user["id"]
        client_roles = keycloak_admin.get_client_roles_of_user(user_id, dash_client_id)
        if client_roles:
            user_name = user["username"]
            user_roles = [role["name"] for role in client_roles]
            is_admin = "app-admin" in user_roles
            user_admin_dict[user_name] = is_admin

    return user_admin_dict
