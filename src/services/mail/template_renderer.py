from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

templates_dir = Path(__file__).parent / 'templates'

env = Environment(
    loader=FileSystemLoader(templates_dir),
)


def render_template(
    template_name: str,
    **context: Any,
) -> str:
    """Отрендерить шаблон письма."""
    template = env.get_template(template_name)

    return template.render(**context)
