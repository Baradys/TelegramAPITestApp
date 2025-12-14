import pytest
from unittest.mock import AsyncMock, patch

from app.services.messages import (
    get_unread_messages,
    send_message,
    get_dialogs,
)


# ============================================================================
# Tests for get_unread_messages
# ============================================================================

@pytest.mark.asyncio
async def test_get_unread_messages_profile_not_found(mock_db, fake_logger):
    """Профиль не найден"""
    with patch('app.services.messages.get_tg_profile', new_callable=AsyncMock) as mock_get_profile:
        mock_get_profile.return_value = None

        result = await get_unread_messages(mock_db, user_id=1, phone="+1234567890")

        assert result["status"] == "error"
        assert "Профиль не найден" in result["message"]


@pytest.mark.asyncio
async def test_get_unread_messages_not_authorized(mock_db, mock_profile, fake_logger):
    """Профиль не авторизован"""
    mock_profile.is_authorized = False

    with patch('app.services.messages.get_tg_profile', new_callable=AsyncMock) as mock_get_profile:
        mock_get_profile.return_value = mock_profile

        result = await get_unread_messages(mock_db, user_id=1, phone="+1234567890")

        assert result["status"] == "error"
        assert "не авторизован" in result["message"]


@pytest.mark.asyncio
async def test_get_unread_messages_session_not_found(mock_db, mock_profile, fake_logger):
    """Сессия не найдена"""
    with patch('app.services.messages.get_tg_profile', new_callable=AsyncMock) as mock_get_profile, \
            patch('app.services.messages.get_tg_session', new_callable=AsyncMock) as mock_get_session:
        mock_get_profile.return_value = mock_profile
        mock_get_session.return_value = None

        result = await get_unread_messages(mock_db, user_id=1, phone="+1234567890")

        assert result["status"] == "error"
        assert "Сессия не найдена" in result["message"]


@pytest.mark.asyncio
async def test_get_unread_messages_client_not_authorized(mock_db, mock_profile, mock_session, mock_client, fake_logger):
    """Клиент не авторизован при подключении"""
    mock_client.is_user_authorized = AsyncMock(return_value=False)

    with patch('app.services.messages.get_tg_profile', new_callable=AsyncMock) as mock_get_profile, \
            patch('app.services.messages.get_tg_session', new_callable=AsyncMock) as mock_get_session, \
            patch('app.services.messages._get_client', new_callable=AsyncMock) as mock_get_client, \
            patch('app.services.messages.update_session', new_callable=AsyncMock) as mock_update_session, \
            patch('app.services.messages.update_profile', new_callable=AsyncMock) as mock_update_profile:
        mock_get_profile.return_value = mock_profile
        mock_get_session.return_value = mock_session
        mock_get_client.return_value = (mock_client, mock_session)

        result = await get_unread_messages(mock_db, user_id=1, phone="+1234567890")

        assert result["status"] == "error"
        assert "истекла" in result["message"]
        mock_update_session.assert_called_once()
        mock_update_profile.assert_called_once()


@pytest.mark.asyncio
async def test_get_unread_messages_connection_error(mock_db, mock_profile, mock_session, mock_client, fake_logger):
    """Ошибка подключения к Telegram"""
    mock_client.connect.side_effect = Exception("Connection error")

    with patch('app.services.messages.get_tg_profile', new_callable=AsyncMock) as mock_get_profile, \
            patch('app.services.messages.get_tg_session', new_callable=AsyncMock) as mock_get_session, \
            patch('app.services.messages._get_client', new_callable=AsyncMock) as mock_get_client, \
            patch('app.services.messages.update_session', new_callable=AsyncMock) as mock_update_session, \
            patch('app.services.messages.update_profile', new_callable=AsyncMock) as mock_update_profile:
        mock_get_profile.return_value = mock_profile
        mock_get_session.return_value = mock_session
        mock_get_client.return_value = (mock_client, mock_session)

        result = await get_unread_messages(mock_db, user_id=1, phone="+1234567890")

        assert result["status"] == "error"
        assert "Ошибка подключения" in result["message"]


@pytest.mark.asyncio
async def test_get_unread_messages_success(mock_db, mock_profile, mock_session, mock_client, mock_dialog, mock_message, fake_logger):
    """Успешное получение непрочитанных сообщений"""
    mock_dialog.unread_count = 1
    mock_client.get_dialogs = AsyncMock(return_value=[mock_dialog])
    mock_client.get_messages = AsyncMock(return_value=[mock_message])

    with patch('app.services.messages.get_tg_profile', new_callable=AsyncMock) as mock_get_profile, \
            patch('app.services.messages.get_tg_session', new_callable=AsyncMock) as mock_get_session, \
            patch('app.services.messages._get_client', new_callable=AsyncMock) as mock_get_client:
        mock_get_profile.return_value = mock_profile
        mock_get_session.return_value = mock_session
        mock_get_client.return_value = (mock_client, mock_session)

        result = await get_unread_messages(mock_db, user_id=1, phone="+1234567890")

        assert result["status"] == "success"
        assert result["count"] == 1
        assert len(result["messages"]) == 1
        assert result["messages"][0]["from"] == "John"
        mock_client.send_read_acknowledge.assert_called_once()
        mock_client.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_get_unread_messages_no_unread(mock_db, mock_profile, mock_session, mock_client, mock_dialog, fake_logger):
    """Нет непрочитанных сообщений"""
    mock_dialog.unread_count = 0
    mock_client.get_dialogs = AsyncMock(return_value=[mock_dialog])

    with patch('app.services.messages.get_tg_profile', new_callable=AsyncMock) as mock_get_profile, \
            patch('app.services.messages.get_tg_session', new_callable=AsyncMock) as mock_get_session, \
            patch('app.services.messages._get_client', new_callable=AsyncMock) as mock_get_client:
        mock_get_profile.return_value = mock_profile
        mock_get_session.return_value = mock_session
        mock_get_client.return_value = (mock_client, mock_session)

        result = await get_unread_messages(mock_db, user_id=1, phone="+1234567890")

        assert result["status"] == "success"
        assert result["count"] == 0
        assert len(result["messages"]) == 0


# ============================================================================
# Tests for send_message
# ============================================================================

@pytest.mark.asyncio
async def test_send_message_profile_not_found(mock_db, fake_logger):
    """Профиль не найден"""
    with patch('app.services.messages.get_tg_profile', new_callable=AsyncMock) as mock_get_profile:
        mock_get_profile.return_value = None

        result = await send_message(mock_db, user_id=1, phone="+1234567890", text="Hi", tg_receiver="123")

        assert result["status"] == "error"
        assert "Профиль не найден" in result["message"]


@pytest.mark.asyncio
async def test_send_message_success(mock_db, mock_profile, mock_session, mock_client, fake_logger):
    """Успешная отправка сообщения"""
    entity = AsyncMock()
    mock_client.get_entity = AsyncMock(return_value=entity)

    with patch('app.services.messages.get_tg_profile', new_callable=AsyncMock) as mock_get_profile, \
            patch('app.services.messages.get_tg_session', new_callable=AsyncMock) as mock_get_session, \
            patch('app.services.messages._get_client', new_callable=AsyncMock) as mock_get_client:
        mock_get_profile.return_value = mock_profile
        mock_get_session.return_value = mock_session
        mock_get_client.return_value = (mock_client, mock_session)

        result = await send_message(mock_db, user_id=1, phone="+1234567890", text="Hi", tg_receiver="123")

        assert result["status"] == "success"
        mock_client.get_entity.assert_called_once_with(123)  # Число, а не строка
        mock_client.send_message.assert_called_once_with(entity, "Hi")
        mock_client.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_send_message_entity_not_found(mock_db, mock_profile, mock_session, mock_client, fake_logger):
    """Сущность не найдена"""
    mock_client.get_entity.side_effect = ValueError("Entity not found")

    with patch('app.services.messages.get_tg_profile', new_callable=AsyncMock) as mock_get_profile, \
            patch('app.services.messages.get_tg_session', new_callable=AsyncMock) as mock_get_session, \
            patch('app.services.messages._get_client', new_callable=AsyncMock) as mock_get_client:
        mock_get_profile.return_value = mock_profile
        mock_get_session.return_value = mock_session
        mock_get_client.return_value = (mock_client, mock_session)

        result = await send_message(mock_db, user_id=1, phone="+1234567890", text="Hi", tg_receiver="invalid")

        assert result["status"] == "error"


# ============================================================================
# Tests for get_dialogs
# ============================================================================

@pytest.mark.asyncio
async def test_get_dialogs_profile_not_found(mock_db, fake_logger):
    """Профиль не найден"""
    with patch('app.services.messages.get_tg_profile', new_callable=AsyncMock) as mock_get_profile:
        mock_get_profile.return_value = None

        result = await get_dialogs(user_id=1, phone="+1234567890", db=mock_db)

        assert result["status"] == "error"
        assert "Профиль не найден" in result["message"]


@pytest.mark.asyncio
async def test_get_dialogs_success(mock_db, mock_profile, mock_session, mock_client, mock_dialog, fake_logger):
    """Успешное получение диалогов"""
    mock_client.get_dialogs = AsyncMock(return_value=[mock_dialog])

    with patch('app.services.messages.get_tg_profile', new_callable=AsyncMock) as mock_get_profile, \
            patch('app.services.messages.get_tg_session', new_callable=AsyncMock) as mock_get_session, \
            patch('app.services.messages._get_client', new_callable=AsyncMock) as mock_get_client:
        mock_get_profile.return_value = mock_profile
        mock_get_session.return_value = mock_session
        mock_get_client.return_value = (mock_client, mock_session)

        result = await get_dialogs(user_id=1, phone="+1234567890", db=mock_db)

        assert result["status"] == "success"
        assert len(result["dialogs"]) == 1
        assert result["dialogs"][0]["name"] == "Test Chat"
        assert result["dialogs"][0]["unread_count"] == 2
        mock_client.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_get_dialogs_empty(mock_db, mock_profile, mock_session, mock_client, fake_logger):
    """Диалогов нет"""
    mock_client.get_dialogs = AsyncMock(return_value=[])

    with patch('app.services.messages.get_tg_profile', new_callable=AsyncMock) as mock_get_profile, \
            patch('app.services.messages.get_tg_session', new_callable=AsyncMock) as mock_get_session, \
            patch('app.services.messages._get_client', new_callable=AsyncMock) as mock_get_client:
        mock_get_profile.return_value = mock_profile
        mock_get_session.return_value = mock_session
        mock_get_client.return_value = (mock_client, mock_session)

        result = await get_dialogs(user_id=1, phone="+1234567890", db=mock_db)

        assert result["status"] == "success"
        assert len(result["dialogs"]) == 0