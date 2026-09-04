"""FinOps Data Provider Factory.

Instantiates either RuntimeFinOpsDataProvider or DemoFinOpsDataProvider
based on the configured finops_data_mode or per-request override.
"""

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.finops.base import FinOpsDataProvider
from app.services.finops.demo_provider import DemoFinOpsDataProvider
from app.services.finops.runtime_provider import RuntimeFinOpsDataProvider


def get_finops_provider(db: Session, mode: str | None = None) -> FinOpsDataProvider:
    """Resolve and instantiate the appropriate FinOps data provider.

    Resolution order:
    1. Explicit `mode` parameter if provided ('runtime' or 'demo').
    2. `settings.finops_data_mode` from application configuration.
    3. Default to 'runtime'.
    """
    selected_mode = (mode or get_settings().finops_data_mode or "runtime").strip().lower()

    if selected_mode == "demo":
        return DemoFinOpsDataProvider(db=db)

    return RuntimeFinOpsDataProvider(db=db)
