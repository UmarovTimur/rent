from sqladmin import BaseView, expose
from starlette.requests import Request
from starlette.responses import RedirectResponse


class RentalCalendarLink(BaseView):
    """A sidebar link that jumps straight to the rental calendar (the Mini App's
    /app/admin, gated by the same admin session — no separate login needed).
    Not a data view: the route just redirects, sqladmin's menu machinery needs a
    registered view to produce a clickable sidebar entry at all.
    """

    name = "Календарь аренды"
    icon = "fa-solid fa-calendar-days"
    identity = "rental-calendar"

    @expose("/rental-calendar", methods=["GET"])
    async def redirect_to_calendar(self, request: Request) -> RedirectResponse:
        return RedirectResponse(url="/app/admin")
