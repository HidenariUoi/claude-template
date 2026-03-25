import datetime as dt
import hashlib
import os
import re
from logging import getLogger

import pandas as pd
from dash_enterprise_libraries import dea
from sqlalchemy import (
    ARRAY,
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

import database.auth.kc_client as kc_client
from app import engine
from database.auth.get_user_admin_dict import get_user_admin_dict

HASHED_NAME_LENGTH = 30
logger = getLogger(__name__)
Base = declarative_base()


class Data(Base):
    __tablename__ = "data"

    data_id = Column(Integer, primary_key=True, autoincrement=True)
    hashed_data_name = Column(String, nullable=False, unique=True)
    theme_name_ja = Column(String(length=255), nullable=False)
    sub_theme_name_ja = Column(String(length=255), nullable=False)
    tags = Column(ARRAY(String), nullable=False, default=[])
    description = Column(String, nullable=False, default="")
    created_at = Column(
        DateTime, nullable=False, server_default=func.now()
    )  # データ名が登録された日
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now()
    )  # Excelがアップロード・登録された日


class Auth(Base):
    __tablename__ = "auth"
    __table_args__ = (UniqueConstraint("user_id", "theme_name_ja"), {"extend_existing": True})
    auth_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False)
    theme_name_ja = Column(String(length=255), nullable=False)
    accessable = Column(Boolean, nullable=False)


def read_table_as_df(data_model, conn) -> pd.DataFrame:
    """データベースからテーブルを読み込む"""
    query = f"SELECT * FROM {data_model.__tablename__}"
    df = pd.read_sql(query, conn)
    return df


def read_hashed_data_names() -> list[str]:
    """データベースからハッシュ化されたデータ名の一覧を取得"""
    with Session(engine) as session:
        data_names = session.query(Data.hashed_data_name).all()
    return [name[0] for name in data_names]


def hash_data_name(theme_name: str, sub_theme_name: str) -> str:
    """データ名をハッシュ化する"""
    hashed_name = hashlib.sha256(f"{theme_name}_{sub_theme_name}".encode()).hexdigest()
    return hashed_name[:HASHED_NAME_LENGTH]


def get_theme_and_sub_theme_name(hashed_data_name: str) -> tuple[str, str] | None:
    """ハッシュ化されたデータ名から日本語のデータ名を取得する"""
    with Session(engine) as session:
        data_info = (
            session.query(Data).filter(Data.hashed_data_name == hashed_data_name).one_or_none()
        )

    if data_info is None:
        return None, None
    return data_info.theme_name_ja, data_info.sub_theme_name_ja


def check_hashed_data_exist(hashed_data_name: str) -> bool:
    """対象ハッシュ化データ名が存在するか判定する"""
    with Session(engine) as session:
        exists = session.query(Data).filter(Data.hashed_data_name == hashed_data_name).count() > 0

    return exists


def check_table_exist(table_name: str) -> bool:
    """対象テーブルが存在するか判定する"""
    with Session(engine) as session:
        exists = session.execute(
            f"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='{table_name}')"
        ).scalar()

    return exists


def check_material_encoder_exist(hashed_data_name: str) -> bool:
    """material encoderが存在するか判定する"""
    file_path = os.path.join(
        os.environ["DATA_DIR"], "input_data", hashed_data_name, "material_encoder.joblib"
    )
    return os.path.exists(file_path)


def validate_theme_name(theme_name: str) -> str:
    """テーマ名のバリデーションを行う"""
    invalid_pattern = re.compile(r"[\x00-\x1F\x7F]")  # 制御文字
    error_message = ""

    if theme_name == "" or theme_name is None:
        return "warning", "テーマ名がありません。", False

    if len(theme_name) > 255:
        error_message += "テーマ名は255文字以内で入力してください。"
    if invalid_pattern.search(theme_name):
        error_message += f"{theme_name}: 使用できない制御文字が含まれています。"
    if theme_name[0].isspace():
        error_message += f"{theme_name}: テーマ名の先頭に空白は使用できません。"

    # 既に存在するテーマ名はエラー
    with Session(engine) as session:
        existing_theme = (
            session.query(Data.theme_name_ja).filter(Data.theme_name_ja == theme_name).first()
        )
        if existing_theme:
            error_message += "%s: 既に存在するテーマ名です。" % theme_name

    return error_message


def validate_data_name(theme_name: str, sub_theme_name: str) -> str:
    """データ名のバリデーションを行う"""
    invalid_pattern = re.compile(r"[\x00-\x1F\x7F]")  # 制御文字
    error_message = ""

    # --- テーマ名のチェック ---
    if theme_name == "" or theme_name is None:
        return "warning", "テーマ名がありません。", False

    if len(theme_name) > 255:
        error_message += "テーマ名は255文字以内で入力してください。"
    if invalid_pattern.search(theme_name):
        error_message += f"{theme_name}: 使用できない制御文字が含まれています。"
    if theme_name[0].isspace():
        error_message += f"{theme_name}: テーマ名の先頭に空白は使用できません。"

    # --- サブテーマ名のチェック ---
    if sub_theme_name == "" or sub_theme_name is None:
        return "warning", "サブテーマ名がありません。", False

    if len(sub_theme_name) > 255:
        error_message += "サブテーマ名は255文字以内で入力してください。"
    if invalid_pattern.search(sub_theme_name):
        error_message += f"{sub_theme_name}: 使用できない制御文字が含まれています。"
    if sub_theme_name[0].isspace():
        error_message += f"{sub_theme_name}: サブテーマ名の先頭に空白は使用できません。"

    # --- データ名のチェック ---
    hashed_data_name = hash_data_name(theme_name, sub_theme_name)
    exist_theme_name = get_theme_and_sub_theme_name(hashed_data_name)[0]
    if exist_theme_name is not None:
        error_message += (
            "すでに登録されているデータ名です。テーマ名とサブテーマ名を変更してください。"
        )

    return error_message


def add_data_name(theme_name, sub_theme_name, tags, description):
    """データ名を追加"""
    with Session(engine) as session:
        hashed_data_name = hash_data_name(theme_name, sub_theme_name)
        data_info = Data(
            hashed_data_name=hashed_data_name,
            theme_name_ja=theme_name,
            sub_theme_name_ja=sub_theme_name,
            tags=tags,
            description=description,
        )
        session.add(data_info)
        session.flush()  # データベースに反映してIDを取得可能にする

        current_user_name = dea.get_username()
        keycloak_admin = kc_client.keycloak_admin

        user_admin_dict = get_user_admin_dict()
        for user_name, is_admin in user_admin_dict.items():
            # admin権限を持つユーザーにはアクセス権限を付与する
            is_accessable = is_admin or user_name == current_user_name
            user_id = keycloak_admin.get_user_id(user_name)

            # Authテーブルに既に同じtheme_name_jaが存在するか確認
            existing_auth = (
                session.query(Auth)
                .filter(Auth.user_id == user_id, Auth.theme_name_ja == theme_name)
                .first()
            )

            if not existing_auth:
                auth_info = Auth(
                    user_id=user_id,
                    theme_name_ja=theme_name,
                    accessable=is_accessable,
                )
                session.add(auth_info)
        session.commit()
    return


def delete_data_name(hashed_data_name: str) -> bool:
    """データ名を削除"""
    with Session(engine) as session:
        # data_id を取得
        data_info = (
            session.query(Data).filter(Data.hashed_data_name == hashed_data_name).one_or_none()
        )
        if data_info is None:
            return False

        theme_name = data_info.theme_name_ja
        session.query(Data).filter(Data.hashed_data_name == hashed_data_name).delete()
        remaining_data = session.query(Data).filter(Data.theme_name_ja == theme_name).first()

        if remaining_data is None:
            # 他に同じ theme_name_ja を持つデータがない場合のみ Auth を削除
            session.query(Auth).filter(Auth.theme_name_ja == theme_name).delete(
                synchronize_session=False
            )

        session.commit()
    return True


def updated_data_updated_datetime(data_name: str) -> None:
    """データが更新された日時を、dataテーブルのupdated_atカラムに更新する"""
    with Session(engine) as session:
        session.query(Data).filter(Data.hashed_data_name == data_name).update(
            {Data.updated_at: dt.datetime.now()},
            synchronize_session=False,
        )
        session.commit()


def get_data_info(data_name: str) -> Data | None:
    """データ名に対応するデータ情報を取得する"""
    with Session(engine) as session:
        data_info = session.query(Data).filter(Data.hashed_data_name == data_name).one_or_none()

    return data_info


def get_list_accessable_data_info(user_name) -> list[Data]:
    """ユーザーがアクセス可能なデータ名の一覧を取得"""
    with Session(engine) as session:
        keycloak_admin = kc_client.keycloak_admin
        user_id = keycloak_admin.get_user_id(user_name)

        keycloak_admin = kc_client.keycloak_admin
        user_id = keycloak_admin.get_user_id(user_name)

        user_auth_info = session.query(Auth).filter(Auth.user_id == user_id).cte("user_auth_info")
        user_accessable_data_info = (
            session.query(Data)
            .join(user_auth_info, Data.theme_name_ja == user_auth_info.c.theme_name_ja)
            .filter(user_auth_info.c.accessable.is_(True))
            .all()
        )
        if len(user_accessable_data_info) == 0:
            return []

    return user_accessable_data_info


def update_data_tags_and_description(data_name: str, tags: list[str], description: str) -> bool:
    """指定されたデータ名のレコードのタグと説明文を更新する"""
    with Session(engine) as session:
        # データを取得
        data_info = session.query(Data).filter(Data.hashed_data_name == data_name).one_or_none()
        if data_info is None:
            return False

        # タグと説明文を更新
        session.query(Data).filter(Data.hashed_data_name == data_name).update(
            {"tags": tags, "description": description},
            synchronize_session=False,
        )
        session.commit()

    return True


def get_access_info() -> pd.DataFrame:
    """アクセス権限情報を取得"""

    users = kc_client.list_all_users()
    with engine.begin() as conn:
        users = kc_client.list_all_users()
        df_user = pd.DataFrame(
            [{"user_id": user["ID"], "user_name": user["Name"]} for user in users]
        )
        df_auth = read_table_as_df(Auth, conn)

    df = pd.merge(df_auth, df_user, on="user_id")
    df = df[["user_name", "theme_name_ja", "accessable"]]

    return df


def update_auth(user_name: str, theme_name_ja: str, accessable: bool) -> bool:
    """権限情報を更新する"""
    keycloak_admin = kc_client.keycloak_admin
    user_id = keycloak_admin.get_user_id(user_name)
    with Session(engine) as session:
        try:
            auth_info = (
                session.query(Auth)
                .filter(Auth.user_id == user_id, Auth.theme_name_ja == theme_name_ja)
                .first()
            )
            if auth_info:
                auth_info.accessable = accessable
            else:
                auth_info = Auth(
                    user_id=user_id, theme_name_ja=theme_name_ja, accessable=accessable
                )
                session.add(auth_info)
            session.commit()
            return True
        except Exception as e:
            logger.error(f"Error occurred while updating auth record: {e}")
            session.rollback()
            raise


def delete_auth_record(user_name: str | None = None, theme_name_ja: str | None = None) -> bool:
    """権限情報を削除する"""
    with Session(engine) as session:
        if user_name is None and theme_name_ja is None:
            raise ValueError("Either user_name or theme_name_ja must be provided.")
        if user_name is not None:
            keycloak_admin = kc_client.keycloak_admin
            user_id = keycloak_admin.get_user_id(user_name)
            session.query(Auth).filter(Auth.user_id == user_id).delete()
        if theme_name_ja is not None:
            session.query(Auth).filter(Auth.theme_name_ja == theme_name_ja).delete()

        if user_name is None and theme_name_ja is None:
            raise ValueError("Either user_name or theme_name_ja must be provided.")
        if user_name is not None:
            keycloak_admin = kc_client.keycloak_admin
            user_id = keycloak_admin.get_user_id(user_name)
            session.query(Auth).filter(Auth.user_id == user_id).delete()
        if theme_name_ja is not None:
            session.query(Auth).filter(Auth.theme_name_ja == theme_name_ja).delete()

        session.commit()
    return True
