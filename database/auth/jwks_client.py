import base64
import os
from functools import cache

import jwt
from jwt import PyJWKClient

jwks_url = os.getenv("DASH_JWKS_URL", "")
jwks_client = PyJWKClient(jwks_url)


@cache
def get_public_key():
    """
    公開鍵の取得
    """
    # 複数種類の公開鍵を利用する想定をしていないので、キャッシュしている
    return jwks_client.get_signing_keys()[0].key


def get_user_data(request):
    public_key = get_public_key()
    jwt_token = base64.b64decode(request.cookies["kcToken"]).decode("utf-8")
    decoded_token = jwt.decode(
        jwt_token, public_key, algorithms=["RS256"], audience="account"
    )  # , audience='Dash'
    return decoded_token


def get_is_app_admin(request):
    decoded_token = get_user_data(request)
    roles = decoded_token["resource_access"]["dash"]["roles"]
    is_admin = "app-admin" in roles
    return is_admin
