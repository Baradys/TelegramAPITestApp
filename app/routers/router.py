from fastapi import APIRouter
from app.routers.auth import AuthRouter
from app.routers.messages import MessagesRouter
from app.routers.profiles import ProfilesRouter
from app.routers.utils import UtilsRouter

router = APIRouter()

AuthRouter(router)
ProfilesRouter(router)
MessagesRouter(router)
UtilsRouter(router)
