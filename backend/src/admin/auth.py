from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from src.container import container
from src.services import login_ratelimit
from src.services.admin_auth import admin_exists, authenticate_admin

SESSION_ADMIN_ID = "admin_user_id"
SESSION_ADMIN_USERNAME = "admin_username"


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = (form.get("username") or "").strip()
        password = form.get("password") or ""
        client_ip = request.client.host if request.client else ""

        if await login_ratelimit.is_locked_out(username, client_ip):
            return False

        async with container.database().get_session() as session:
            admin = await authenticate_admin(session, username, password)

        if admin is None:
            await login_ratelimit.register_failure(username, client_ip)
            return False

        await login_ratelimit.reset(username, client_ip)
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
