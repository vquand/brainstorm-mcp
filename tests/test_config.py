from __future__ import annotations

import pytest

from server.config import Settings


def test_settings_rejects_non_loopback_host() -> None:
    with pytest.raises(ValueError, match="BRAINSTORM_HOST must stay on loopback"):
        Settings(host="0.0.0.0")
