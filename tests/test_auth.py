import pytest
from unittest.mock import AsyncMock, patch

from app.services.auth import (
    start_auth,
    verify_code,
    verify_password,
    get_user_profiles,
)


# ============================================================================
# Tests for start_auth
# ============================================================================

@pytest.mark.asyncio
async def test_start_auth_user_not_found(mock_db, fake_logger):
    """Пользователь не найден"""
    with patch('app.services.auth.get_user_by_id', new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = None

        result = await start_auth(mock_db, user_id=999, phone="+1234567890")

        assert result["status"] == "error"
        assert "Пользователь не найден" in result["message"]


@pytest.mark.asyncio
async def test_start_auth_phone_already_used(mock_db, mock_user, fake_logger):
    """Номер уже используется другим пользователем"""
    other_profile = AsyncMock(user_id=999)

    with patch('app.services.auth.get_user_by_id', new_callable=AsyncMock) as mock_get_user, \
            patch('app.services.auth.get_profile_by_phone', new_callable=AsyncMock) as mock_get_profile:
        mock_get_user.return_value = mock_user
        mock_get_profile.return_value = other_profile

        result = await start_auth(mock_db, user_id=1, phone="+1234567890")

        assert result["status"] == "error"
        assert "уже используется" in result["message"]


@pytest.mark.asyncio
async def test_start_auth_already_authorized(mock_db, mock_user, mock_profile, fake_logger):
    """Профиль уже авторизован"""
    mock_profile.is_authorized = True

    with patch('app.services.auth.get_user_by_id', new_callable=AsyncMock) as mock_get_user, \
            patch('app.services.auth.get_profile_by_phone', new_callable=AsyncMock) as mock_get_profile_by_phone, \
            patch('app.services.auth.get_profile_by_user_and_phone', new_callable=AsyncMock) as mock_get_profile:
        mock_get_user.return_value = mock_user
        mock_get_profile_by_phone.return_value = None
        mock_get_profile.return_value = mock_profile

        result = await start_auth(mock_db, user_id=1, phone="+1234567890")

        assert result["status"] == "already_authorized"


@pytest.mark.asyncio
async def test_start_auth_success(mock_db, mock_user, mock_profile, mock_client, fake_logger):
    """Успешное начало авторизации"""
    with patch('app.services.auth.get_user_by_id', new_callable=AsyncMock) as mock_get_user, \
            patch('app.services.auth.get_profile_by_phone', new_callable=AsyncMock) as mock_get_profile_by_phone, \
            patch('app.services.auth.get_profile_by_user_and_phone', new_callable=AsyncMock) as mock_get_profile, \
            patch('app.services.auth.create_profile', new_callable=AsyncMock) as mock_create_profile, \
            patch('app.services.auth._get_client', new_callable=AsyncMock) as mock_get_client, \
            patch('app.services.auth.update_profile', new_callable=AsyncMock) as mock_update_profile:
        mock_get_user.return_value = mock_user
        mock_get_profile_by_phone.return_value = None
        mock_get_profile.return_value = None
        mock_create_profile.return_value = mock_profile
        mock_get_client.return_value = (mock_client, None)
        mock_update_profile.return_value = mock_profile

        result = await start_auth(mock_db, user_id=1, phone="+1234567890")

        assert result["status"] == "code_sent"
        assert result["phone"] == "+1234567890"
        mock_client.send_code_request.assert_called_once_with("+1234567890")


# ============================================================================
# Tests for verify_code
# ============================================================================

@pytest.mark.asyncio
async def test_verify_code_profile_not_found(mock_db):
    """Профиль не найден"""

    with patch('app.services.auth.get_profile_by_user_and_phone', new_callable=AsyncMock) as mock_get_profile:
        mock_get_profile.return_value = None

        result = await verify_code(mock_db, user_id=1, phone='+1234567890', code="12345")

        assert result["status"] == "error"
        assert "Профиль не найден" in result["message"]

@pytest.mark.asyncio
async def test_verify_code_no_phone_code_hash(mock_db, mock_profile):
    """Нет phone_code_hash"""
    mock_profile.phone_code_hash = None

    with patch('app.services.auth.get_profile_by_user_and_phone', new_callable=AsyncMock) as mock_get_profile:
        mock_get_profile.return_value = mock_profile

        result = await verify_code(mock_db, user_id=1, phone='+1234567890', code="12345")

        assert result["status"] == "error"
        assert "запроси код" in result["message"]


@pytest.mark.asyncio
async def test_verify_code_success(mock_db, mock_profile, mock_client, fake_logger):
    """Успешная проверка кода"""
    mock_profile.phone_code_hash = "hash-123"
    session_record = AsyncMock()

    with patch('app.services.auth.get_profile_by_user_and_phone', new_callable=AsyncMock) as mock_get_profile, \
            patch('app.services.auth._get_client', new_callable=AsyncMock) as mock_get_client, \
            patch('app.services.auth.update_session', new_callable=AsyncMock) as mock_update_session, \
            patch('app.services.auth.update_profile', new_callable=AsyncMock) as mock_update_profile:
        mock_get_profile.return_value = mock_profile
        mock_get_client.return_value = (mock_client, session_record)
        mock_update_profile.return_value = mock_profile

        result = await verify_code(mock_db, user_id=1, code="12345", phone='+1234567890')

        assert result["status"] == "success"
        assert result["message"] == "Авторизация успешна"
        mock_update_session.assert_called_once()
        mock_update_profile.assert_called_once()


@pytest.mark.asyncio
async def test_verify_code_invalid_code(mock_db, mock_profile, mock_client, fake_logger):
    """Неверный код"""
    mock_profile.phone_code_hash = "hash-123"
    mock_client.sign_in.side_effect = Exception("Invalid code")
    session_record = AsyncMock()

    with patch('app.services.auth.get_tg_profile', new_callable=AsyncMock) as mock_get_profile, \
            patch('app.services.auth._get_client', new_callable=AsyncMock) as mock_get_client:
        mock_get_profile.return_value = mock_profile
        mock_get_client.return_value = (mock_client, session_record)

        result = await verify_code(mock_db, user_id=1, code="99999", phone='+1234567890')

        assert result["status"] == "error"


# ============================================================================
# Tests for verify_password
# ============================================================================

@pytest.mark.asyncio
async def test_verify_password_success(mock_db, mock_profile, mock_client_full, mock_session_record):
    """Успешная проверка пароля"""
    mock_profile.phone_code_hash = "hash-123"

    with patch('app.services.auth.get_profile_by_user_and_phone', new_callable=AsyncMock) as mock_get_profile, \
            patch('app.services.auth._get_client', new_callable=AsyncMock) as mock_get_client, \
            patch('app.services.auth.update_session', new_callable=AsyncMock) as mock_update_session, \
            patch('app.services.auth.update_profile', new_callable=AsyncMock) as mock_update_profile:
        mock_get_profile.return_value = mock_profile
        mock_get_client.return_value = (mock_client_full, mock_session_record)
        mock_update_profile.return_value = mock_profile

        result = await verify_password(mock_db, user_id=1, phone='+1234567890', password="pass123")

        assert result["status"] == "success"
        assert result["message"] == "Авторизация успешна"
        mock_client_full.sign_in.assert_called_once_with(password="pass123")
        mock_update_session.assert_called_once()


# ============================================================================
# Tests for get_user_profiles
# ============================================================================

@pytest.mark.asyncio
async def test_get_user_profiles_success(mock_db, mock_profile, fake_logger):
    """Успешное получение профилей"""
    with patch('app.services.auth.get_users_profiles', new_callable=AsyncMock) as mock_get_profiles:
        mock_get_profiles.return_value = [mock_profile]

        result = await get_user_profiles(mock_db, user_id=1)

        assert result["status"] == "success"
        assert len(result["profiles"]) == 1
        assert result["profiles"][0]["phone"] == "+1234567890"


@pytest.mark.asyncio
async def test_get_user_profiles_empty(mock_db, fake_logger):
    """Профилей нет"""
    with patch('app.services.auth.get_users_profiles', new_callable=AsyncMock) as mock_get_profiles:
        mock_get_profiles.return_value = []

        result = await get_user_profiles(mock_db, user_id=1)

        assert result["status"] == "success"
        assert len(result["profiles"]) == 0


@pytest.mark.asyncio
async def test_get_user_profiles_error(mock_db, fake_logger):
    """Ошибка при получении профилей"""
    with patch('app.services.auth.get_users_profiles', new_callable=AsyncMock) as mock_get_profiles:
        mock_get_profiles.side_effect = Exception("DB error")

        result = await get_user_profiles(mock_db, user_id=1)

        assert result["status"] == "error"
        assert "DB error" in result["message"]
