import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

# === Настройка переменных окружения ===
os.environ.setdefault("API_ID", "123456")
os.environ.setdefault("API_HASH", "test_api_hash")
os.environ.setdefault("TELEGRAM_SESSION_NAME", "test_session")
os.environ.setdefault("DATABASE_URL", "localhost")
os.environ.setdefault("DATABASE_PORT", "5432")
os.environ.setdefault("DATABASE_NAME", "test_db")
os.environ.setdefault("DATABASE_USER", "test_user")
os.environ.setdefault("DATABASE_PASSWORD", "test_pass")
os.environ.setdefault("SECRET_KEY", "test_secret_key")

from app.services import auth


# === Settings & Logger ===

@pytest.fixture
def fake_settings(monkeypatch):
    """Гибкая подмена настроек"""
    class Settings:
        TELEGRAM_API_ID = 123456
        TELEGRAM_API_HASH = "test_api_hash"
        TELEGRAM_SESSION_NAME = "test_session"

    monkeypatch.setattr(auth, "settings", Settings())
    return Settings()


@pytest.fixture
def fake_logger(monkeypatch):
    """
    Подмена логгера:
    - ничего не пишет «наружу»
    - можно проверять, какие сообщения залогировались.
    """
    class FakeLogger:
        def __init__(self):
            self.infos = []
            self.errors = []
            self.debugs = []

        def info(self, msg, *args, **kwargs):
            self.infos.append(msg)

        def error(self, msg, *args, **kwargs):
            self.errors.append(msg)

        def debug(self, msg, *args, **kwargs):
            self.debugs.append(msg)

    logger = FakeLogger()
    monkeypatch.setattr(auth, "logger", logger)
    return logger


# === Fake Client ===

@pytest.fixture
def fake_client_class(monkeypatch):
    """
    Подмена класса клиента, который использует auth‑модуль.
    Можно добавлять методы/поля по мере роста функциональности.
    """
    class FakeClient:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            self.connected = False
            self.profile = {"id": 1, "name": "Test User"}
            self.sent_codes = []
            self.password_required = False
            self.correct_code = "12345"
            self.correct_password = "password"

        async def connect(self):
            self.connected = True

        async def send_code(self, phone: str):
            self.sent_codes.append(phone)
            return {"phone_code_hash": "hash-123"}

        async def sign_in(self, phone: str = None, code: str = None, phone_code_hash: str = None, password: str = None):
            if code and code != self.correct_code:
                raise ValueError("Invalid code")
            if password and self.password_required and password != self.correct_password:
                raise ValueError("Invalid password")
            return {"user_id": 1}

        async def check_password(self, password: str):
            if self.password_required and password != self.correct_password:
                raise ValueError("Invalid password")
            return {"user_id": 1}

        async def get_profiles(self):
            return [self.profile]

        async def disconnect(self):
            self.connected = False

    monkeypatch.setattr(auth, "ClientClass", FakeClient)
    return FakeClient


# === Database & Models ===

@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_user():
    user = AsyncMock()
    user.id = 1
    return user


# === Auth Fixtures ===

@pytest.fixture
def mock_profile(request):
    """Profile для всех тестов с гибким состоянием"""
    profile = AsyncMock()
    profile.id = 1
    profile.user_id = 1
    profile.phone = "+1234567890"
    profile.username = "test_profile"

    # Проверяем точнее: если в пути есть test_messages.py
    is_messages_test = "test_messages" in request.node.nodeid
    profile.is_authorized = is_messages_test

    profile.phone_code_hash = None
    profile.first_name = "Test"
    profile.last_name = "User"
    profile.created_at = datetime.now()
    profile.last_login = None
    return profile


@pytest.fixture
def mock_client(request):
    """AsyncMock client для всех тестов"""
    client = AsyncMock()
    client.is_connected = MagicMock(return_value=False)
    client.connect = AsyncMock()

    # Проверяем точнее: если в пути есть test_messages.py
    is_messages_test = "test_messages" in request.node.nodeid
    client.is_user_authorized = AsyncMock(return_value=is_messages_test)

    client.send_code_request = AsyncMock(
        return_value=AsyncMock(phone_code_hash="hash-123")
    )
    client.sign_in = AsyncMock(return_value={"user_id": 1})
    client.get_me = AsyncMock(return_value=AsyncMock(
        first_name="Test",
        last_name="User",
        username="test_username"
    ))
    client.session = AsyncMock()
    client.session.save = AsyncMock(return_value="new_session_string")

    # Методы для messages
    client.get_dialogs = AsyncMock()
    client.get_messages = AsyncMock()
    client.send_read_acknowledge = AsyncMock()
    client.send_message = AsyncMock()
    client.get_entity = AsyncMock()
    client.iter_dialogs = AsyncMock()
    client.disconnect = AsyncMock()

    return client


# === Messages Fixtures ===

@pytest.fixture
def mock_profile_messages():
    """Profile для тестов messages"""
    profile = AsyncMock()
    profile.id = 1
    profile.user_id = 1
    profile.username = "test_profile"
    profile.is_authorized = True
    return profile


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.id = 1
    session.profile_username = "test_profile"
    session.is_active = True
    session.session_string = "old_session"
    return session


@pytest.fixture
def mock_client_messages():
    """AsyncMock client для тестов messages"""
    client = AsyncMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.is_user_authorized = AsyncMock(return_value=True)
    client.get_dialogs = AsyncMock()
    client.get_messages = AsyncMock()
    client.send_read_acknowledge = AsyncMock()
    client.send_message = AsyncMock()
    client.get_entity = AsyncMock()
    client.iter_dialogs = AsyncMock()
    client.session = AsyncMock()
    client.session.save = AsyncMock(return_value="new_session_string")
    return client


@pytest.fixture
def mock_dialog():
    dialog = AsyncMock()
    dialog.id = 123
    dialog.name = "Test Chat"
    dialog.unread_count = 2
    dialog.is_group = False
    dialog.is_channel = False
    dialog.entity = AsyncMock(id=123)
    return dialog


@pytest.fixture
def mock_message():
    msg = AsyncMock()
    msg.id = 1
    msg.text = "Test message"
    msg.date = datetime.now()
    msg.sender_id = 456
    msg.sender = AsyncMock(first_name="John", username="john_doe")
    return msg