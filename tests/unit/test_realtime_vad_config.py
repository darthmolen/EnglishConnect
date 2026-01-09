"""Tests for Realtime API VAD configuration.

TDD Task 4: Verify VAD config changes based on voice mode.
"""

import pytest


def test_vad_config_disabled_for_push_to_talk():
    """Push-to-talk mode should have no VAD (client controls start/stop)."""
    from app.services.realtime_session import get_turn_detection_config

    config = get_turn_detection_config(voice_mode="push-to-talk")

    assert config is None


def test_vad_config_enabled_for_active_mode():
    """Active mode should have VAD with adjusted sensitivity."""
    from app.services.realtime_session import get_turn_detection_config

    config = get_turn_detection_config(voice_mode="active")

    assert config["type"] == "server_vad"
    assert config["threshold"] == 0.6  # Less sensitive than default 0.5
    assert config["silence_duration_ms"] == 800  # Wait longer than default 500
    assert config["prefix_padding_ms"] == 500  # Capture more than default 300


def test_vad_config_default_is_active():
    """Unknown mode should default to active mode VAD config."""
    from app.services.realtime_session import get_turn_detection_config

    config = get_turn_detection_config(voice_mode="unknown")

    # Should return VAD config (not None) for unknown modes
    assert config is not None
    assert config["type"] == "server_vad"
