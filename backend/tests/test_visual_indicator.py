"""Tests for visual indicator logic"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from core.crud_visual_indicator import (
    compute_visual_indicator,
    enrich_appointments_with_visuals,
    DEFAULT_DELAY_TOLERANCE_MINUTES,
    STATUSES_THAT_OCCUPY,
    TERMINAL_STATUSES,
)


class MockAppointment:
    def __init__(self, id: int, status_code: str, start_dt: datetime):
        self.id = id
        self.status = MagicMock(code=status_code)
        self.start_datetime = start_dt
        self.visual_indicator = None
        self.is_delayed = False
        self.minutes_until = None


class MockVisualConfig:
    def __init__(self, code: str, label: str, hex_color: str, sort_order: int = 0):
        self.code = code
        self.label = label
        self.hex_color = hex_color
        self.sort_order = sort_order


@pytest.fixture
def mock_config():
    """Configuracion visual de prueba"""
    return {
        "proximity_rank_1": MockVisualConfig("proximity_rank_1", "Proxima 1", "#10B981", 1),
        "proximity_rank_2": MockVisualConfig("proximity_rank_2", "Proxima 2", "#3B82F6", 2),
        "proximity_rank_3": MockVisualConfig("proximity_rank_3", "Proxima 3", "#F59E0B", 3),
        "delayed": MockVisualConfig("delayed", "Demorada", "#EF4444", 0),
        "pending": MockVisualConfig("pending", "Pendiente", "#6B7280", 10),
        "confirmed": MockVisualConfig("confirmed", "Confirmada", "#3B82F6", 5),
        "completed": MockVisualConfig("completed", "Completada", "#10B981", 20),
        "cancelled": MockVisualConfig("cancelled", "Cancelada", "#EF4444", 30),
        "rescheduled": MockVisualConfig("rescheduled", "Reagendada", "#F59E0B", 15),
    }


@pytest.fixture
def now():
    return datetime.now(timezone.utc)


class TestComputeVisualIndicator:
    """Tests para compute_visual_indicator"""
    
    def test_delayed_appointment(self, mock_config, now):
        """Cita demorada (paso tolerancia) -> delayed"""
        from core.crud_visual_indicator import compute_visual_indicator
        appt = MockAppointment(1, "PENDING", now - timedelta(minutes=20))
        code, is_delayed = compute_visual_indicator(appt, mock_config)
        assert code == "delayed"
        assert is_delayed is True
    
    def test_not_delayed_within_tolerance(self, mock_config, now):
        """Cita dentro de tolerancia -> no delayed"""
        from core.crud_visual_indicator import compute_visual_indicator
        appt = MockAppointment(1, "PENDING", now + timedelta(minutes=5))
        code, is_delayed = compute_visual_indicator(appt, mock_config)
        assert code != "delayed"
        assert is_delayed is False
    
    def test_confirmed_not_delayed_within_tolerance(self, mock_config, now):
        """CONFIRMED dentro de tolerancia -> no delayed"""
        from core.crud_visual_indicator import compute_visual_indicator
        appt = MockAppointment(1, "CONFIRMED", now + timedelta(minutes=5))
        code, is_delayed = compute_visual_indicator(appt, mock_config)
        assert code != "delayed"
        assert is_delayed is False
    
    def test_rescheduled_delayed(self, mock_config, now):
        """RESCHEDULED pasado tolerancia -> delayed"""
        from core.crud_visual_indicator import compute_visual_indicator
        appt = MockAppointment(1, "RESCHEDULED", now - timedelta(minutes=20))
        code, is_delayed = compute_visual_indicator(appt, mock_config)
        assert code == "delayed"
        assert is_delayed is True
    
    def test_completed_not_delayed(self, mock_config, now):
        """COMPLETED nunca esta delayed"""
        from core.crud_visual_indicator import compute_visual_indicator
        appt = MockAppointment(1, "COMPLETED", now - timedelta(minutes=20))
        code, is_delayed = compute_visual_indicator(appt, mock_config)
        assert code == "completed"
        assert is_delayed is False
    
    def test_cancelled_not_delayed(self, mock_config, now):
        """CANCELLED nunca esta delayed"""
        from core.crud_visual_indicator import compute_visual_indicator
        appt = MockAppointment(1, "CANCELLED", now - timedelta(minutes=20))
        code, is_delayed = compute_visual_indicator(appt, mock_config)
        assert code == "cancelled"
        assert is_delayed is False


class TestConstants:
    def test_statuses_that_occupy(self):
        from core.crud_visual_indicator import STATUSES_THAT_OCCUPY
        assert "PENDING" in STATUSES_THAT_OCCUPY
        assert "CONFIRMED" in STATUSES_THAT_OCCUPY
        assert "RESCHEDULED" in STATUSES_THAT_OCCUPY
        assert "CANCELLED" not in STATUSES_THAT_OCCUPY
        assert "COMPLETED" not in STATUSES_THAT_OCCUPY
    
    def test_terminal_statuses(self):
        from core.crud_visual_indicator import TERMINAL_STATUSES
        assert "CANCELLED" in TERMINAL_STATUSES
        assert "COMPLETED" in TERMINAL_STATUSES
        assert "PENDING" not in TERMINAL_STATUSES
        assert "CONFIRMED" not in TERMINAL_STATUSES
