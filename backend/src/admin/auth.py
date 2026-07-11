from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from src.container import container
from src.services.admin_auth import admin_exists, authenticate_admin

SESSION_ADMIN_ID = "admin_user_id"
SESSION_ADMIN_USERNAME = "admin_username"


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = (form.get("username") or "").strip()
        password = form.get("password") or ""

        async with container.database().get_session() as session:
            admin = await authenticate_admin(session, username, password)

        if admin is None:
            return False

        request.session[SESSION_ADMIN_ID] = admin.id
        request.session[SESSION_ADMIN_USERNAME] = admin.username
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        admin_id = request.session.get(SESSION_ADMIN_ID)
        if not admin_id:
            return False

        async with container.database().get_session() as session:
            return await admin_exists(session, int(admin_id))
