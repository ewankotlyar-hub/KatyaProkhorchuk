from __future__ import annotations

from pathlib import Path

from fastapi.responses import HTMLResponse


class CatalogPageRenderer:
    def __init__(self, template_path: Path) -> None:
        self.template_path = Path(template_path)

    def render(self) -> HTMLResponse:
        content = self.template_path.read_text(encoding="utf-8")
        return HTMLResponse(content=content)
