from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from books_monitor.config import TEMPLATES_DIR

from .page_renderer import CatalogPageRenderer


class WebRouterFactory:
    def __init__(self, renderer: CatalogPageRenderer | None = None) -> None:
        template_path = TEMPLATES_DIR / "catalog.html"
        self.renderer = renderer or CatalogPageRenderer(template_path)

    def create_router(self) -> APIRouter:
        router = APIRouter(tags=["web"])

        @router.get("/", response_class=HTMLResponse, include_in_schema=False)
        async def catalog_page() -> HTMLResponse:
            return self.renderer.render()

        return router
