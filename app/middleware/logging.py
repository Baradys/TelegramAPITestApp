import json
import logging
import time
import traceback
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class JsonFormatter(logging.Formatter):
    def format(self, record):
        if isinstance(record.msg, dict):
            log_obj = {
                'level': record.levelname,
                'time': self.formatTime(record, '%Y-%m-%d %H:%M:%S'),
            }
            log_obj.update(record.msg)
            return json.dumps(log_obj, ensure_ascii=False)
        else:
            log_obj = {
                'level': record.levelname,
                'message': record.getMessage(),
                'time': self.formatTime(record, '%Y-%m-%d %H:%M:%S'),
            }
            return json.dumps(log_obj, ensure_ascii=False)


logger = logging.getLogger('fastapi_app.middleware')
logger.setLevel(logging.INFO)
logger.propagate = False
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        start = time.perf_counter()

        try:
            response = await call_next(request)
            end = time.perf_counter()
            await self.log(request, response, start, end)
            return response
        except Exception as e:
            end = time.perf_counter()
            await self.log_exception(request, e, start, end)
            raise

    @staticmethod
    async def log(request: Request, response: Response, start: float, end: float):
        request_duration_ms = round((end - start) * 1000, 2)

        # Получение пользователя (если используется аутентификация)
        user = getattr(request.state, 'user', None)
        username = getattr(user, 'email', '') if user else ''

        # Получение IP адреса
        user_ip = request.headers.get('X-Real-IP') or \
                  request.headers.get('X-Forwarded-For', '').split(',')[0] or \
                  request.client.host if request.client else ''

        log_data = {
            'http_code': response.status_code,
            'username': username,
            'user_ip': user_ip,
            'request_method': request.method,
            'request_url': str(request.url),
            'request_path': request.url.path,
            'request_duration_ms': request_duration_ms,
        }

        status_code = response.status_code
        if status_code >= 500:
            logger.error(msg=log_data)
        elif status_code >= 400:
            logger.warning(msg=log_data)
        else:
            logger.info(msg=log_data)

    @staticmethod
    async def log_exception(request: Request, exception: Exception, start: float, end: float):
        request_duration_ms = round((end - start) * 1000, 2)

        user = getattr(request.state, 'user', None)
        username = getattr(user, 'email', '') if user else ''

        user_ip = request.headers.get('X-Real-IP') or \
                  request.headers.get('X-Forwarded-For', '').split(',')[0] or \
                  request.client.host if request.client else ''

        log_data = {
            'http_code': 500,
            'username': username,
            'user_ip': user_ip,
            'request_method': request.method,
            'request_url': str(request.url),
            'request_path': request.url.path,
            'request_duration_ms': request_duration_ms,
            'exception': str(exception),
            'exception_type': type(exception).__name__,
            'traceback': traceback.format_exc(),
        }
        logger.error(msg=log_data)
