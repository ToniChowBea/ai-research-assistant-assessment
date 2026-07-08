import logging
import inngest
import inngest.fast_api

from research_assistant.config import get_settings


_dev_url = get_settings().inngest_api_base

# ----- Inngest Client -----------
inngest_client = inngest.Inngest(
    app_id="ai-research-assistant",
    is_production=False,
    api_base_url=_dev_url,
    event_api_base_url=_dev_url,
    logger=logging.getLogger("research-assistant"),
)
