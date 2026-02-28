import pytest
from datetime import datetime, timezone, timedelta
from app.apis.production_context import determine_status

# Only function worth testing in production_context, most of the other functionality is best tested with integration tests.
def test_determine_status():
    # Running
    assert determine_status(5.0, datetime.now(timezone.utc).isoformat()) == "running"

    # Stopped
    assert determine_status(0.1, datetime.now(timezone.utc).isoformat()) == "stopped"

    # Offline
    assert determine_status(5.0, None) == "offline"

    # Offline (stale data, >1 hour old)
    old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    assert determine_status(5.0, old_time) == "offline"