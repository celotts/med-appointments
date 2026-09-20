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
    """Configuración visual de prueba"""
    return {
        "proximity_rank_1": MockVisualConfig("proximity_rank_1", "Próxima 1", "#10B981", 1),
        "proximity_rank_2": MockVisualConfig("proximity_rank_2", "Próxima 2", "#3B82F6", 2),
        "proximity_rank_3": MockVisualConfig("proximity_rank_3", "Próxima 3", "#F59E0B", 3),
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
        appt = MockAppointment(1, "PENDIENTE", now - timedelta(minutes=20))
        code, is_delayed = compute_visual_indicator(appt, mock_config)
        assert code == "delayed"
        assert is_delayed is True
    
    def test_not_delayed_within_tolerance(self, mock_config, now):
        """Cita dentro de tolerancia -> no delayed"""
        from core.crud_visual_indicator import compute_visual_indicator
        appt = MockAppointment(1, "PENDIENTE", now + timedelta(minutes=5))
        code, is_delayed = compute_visual_indicator(appt, mock_config)
        assert code != "delayed"
        assert is_delayed is False
    
    def test_confirmed_not_delayed_within_tolerance(self, mock_config, now):
        """CONFIRMADA dentro de tolerancia -> no delayed"""
        from core.crud_visual_indicator import compute_visual_indicator
        appt = MockAppointment(1, "CONFIRMADA", now + timedelta(minutes=5))
        code, is_delayed = compute_visual_indicator(appt, mock_config)
        assert code != "delayed"
        assert is_delayed is False
    
    def test_rescheduled_delayed(self, mock_config, now):
        """REAGENDADA pasado tolerancia -> delayed"""
        from core.crud_visual_indicator import compute_visual_indicator
        appt = MockAppointment(1, "REAGENDADA", now - timedelta(minutes=20))
        code, is_delayed = compute_visual_indicator(appt, mock_config)
        assert code == "delayed"
        assert is_delayed is True
    
    def test_completed_not_delayed(self, mock_config, now):
        """COMPLETADA nunca esta delayed"""
        from core.crud_visual_indicator import compute_visual_indicator
        appt = MockAppointment(1, "COMPLETADA", now - timedelta(minutes=20))
        code, is_delayed = compute_visual_indicator(appt, mock_config)
        assert code == "completed"
        assert is_delayed is False
    
    def test_cancelled_not_delayed(self, mock_config, now):
        """CANCELADA nunca esta delayed"""
        from core.crud_visual_indicator import compute_visual_indicator
        appt = MockAppointment(1, "CANCELADA", now - timedelta(minutes=20))
        code, is_delayed = compute_visual_indicator(appt, mock_config)
        assert code == "cancelled"
        assert is_delayed is False
    
    def test_rescheduled_delayed(self, mock_config, now):
        """REAGENDADA pasado tolerancia -> delayed"""
        from core.crud_visual_indicator import compute_visual_indicator
        appt = MockAppointment(1, "REAGENDADA", now - timedelta(minutes=20))
        code, is_delayed = compute_visual_indicator(appt, mock_config)
        assert code == "delayed"
        assert is_delayed is True


class TestConstants:
    def test_statuses_that_occupy(self):
        from core.crud_visual_indicator import STATUSES_THAT_OCCUPY
        assert "PENDIENTE" in STATUSES_THAT_OCCUPY
        assert "CONFIRMADA" in STATUSES_THAT_OCCUPY
        assert "REAGENDADA" in STATUSES_THAT_OCCUPY
        assert "CANCELADA" not in STATUSES_THAT_OCCUPY
        assert "COMPLETADA" not in STATUSES_THAT_OCCUPY
    
    def test_terminal_statuses(self):
        from core.crud_visual_indicator import TERMINAL_STATUSES
        assert "CANCELADA" in TERMINAL_STATUSES
        assert "COMPLETADA" in TERMINAL_STATUSES
        assert "PENDIENTE" not in TERMINAL_STATUSES
        assert "CONFIRMADA" not in TERMINAL_STATUSES


class TestEnrichAppointmentsWithVisuals:
    """Tests para enrich_appointments_with_visuals"""
    
    @pytest.fixture
    def mock_config(self):
        """Configuración visual de prueba"""
        return {
            "proximity_rank_1": type('Config', (), {'code': 'proximity_rank_1', 'label': 'Próxima 1', 'hex_color': '#10B981', 'sort_order': 1}),
            "proximity_rank_2": MockVisualConfig("proximity_rank_2", "Próxima 2", "#3B82F6", 2),
            "proximity_rank_3": MockVisualConfig("proximity_rank_3", "Próxima 3", "#F59E0B", 3),
            "delayed": MockVisualConfig("delayed", "Demorada", "#EF4444", 0),
            "pending": MockVisualConfig("pending", "Pendiente", "#6B7280", 10),
            "confirmed": MockVisualConfig("confirmed", "Confirmada", "#3B82F6", 5),
            "completed": MockVisualConfig("completed", "Completada", "#10B981", 20),
            "cancelled": MockVisualConfig("cancelled", "Cancelada", "#EF4444", 30),
            "rescheduled": MockVisualConfig("rescheduled", "Reagendada", "#F59E0B", 15),
        }
    
    @pytest.fixture
    def now(self):
        return datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_delayed_priority_first(self, mock_config, now):
        """Citas demoradas van primero"""
        from core.crud_visual_indicator import enrich_appointments_with_visuals
        
        appt_delayed = MockAppointment(1, "PENDIENTE", now - timedelta(minutes=20))
        appt_normal = MockAppointment(2, "CONFIRMADA", now + timedelta(hours=1))
        
        appointments = [appt_normal, appt_delayed]
        enriched = await enrich_appointments_with_visuals(None, appointments)
        
        # La demorada debe ir primera
        assert enriched[0].id == 1
        assert enriched[0].is_delayed is True
        assert enriched[0].visual_indicator["code"] == "delayed"
        assert enriched[1].id == 2
        assert enriched[1].is_delayed is False
    
    @pytest.mark.asyncio
    async def test_proximity_ranking_top_3(self, mock_config):
        """Top 3 futuras más cercanas -> proximity_rank_1,2,3"""
        now = datetime.now(timezone.utc)
        
        appts = [
            MockAppointment(1, "PENDIENTE", now + timedelta(hours=3)),
            MockAppointment(2, "CONFIRMADA", now + timedelta(hours=1)),
            MockAppointment(3, "PENDIENTE", now + timedelta(minutes=30)),
            MockAppointment(4, "PENDIENTE", now + timedelta(hours=2)),
            MockAppointment(5, "CONFIRMADA", now + timedelta(days=1)),
        ]
        
        from core.crud_visual_indicator import enrich_appointments_with_visuals
        import core.crud_visual_indicator as cvi
        cvi.get_visual_config = AsyncMock(return_value={
            "proximity_rank_1": type('Config', (), {'code': 'proximity_rank_1', 'label': 'Próxima 1', 'hex_color': '#10B981', 'sort_order': 1}),
            "proximity_rank_2": type('Config', (), {'code': 'proximity_rank_2', 'label': 'Próxima 2', 'hex_color': '#3B82F6', 'sort_order': 2}),
            "proximity_rank_3": type('Config', (), {'code': 'proximity_rank_3', 'label': 'Próxima 3', 'hex_color': '#F59E0B', 'sort_order': 3}),
            "pending": type('Config', (), {'code': 'pending', 'label': 'Pendiente', 'hex_color': '#6B7280', 'sort_order': 10}),
            "confirmed": type('Config', (), {'code': 'confirmed', 'label': 'Confirmada', 'hex_color': '#3B82F6', 'sort_order': 5}),
        })
        
        enriched = await enrich_appointments_with_visuals(None, appts)
        
        # Top 3 más cercanas deben tener proximity_rank
        proximity_ranks = [a.visual_indicator.get("code") for a in enriched if a.visual_indicator.get("code", "").startswith("proximity_rank")]
        assert len(proximity_ranks) == 3
        assert "proximity_rank_1" in proximity_ranks
        assert "proximity_rank_2" in proximity_ranks
        assert "proximity_rank_3" in proximity_ranks
        
        # La más cercana debe ser rank_1
        first = min(enriched, key=lambda a: a.start_datetime)
        assert first.visual_indicator["code"] == "proximity_rank_1"
    
    @pytest.mark.asyncio
    async def test_disabled_group_before_proximity(self, mock_config):
        """Demoradas van antes que proximity"""
        now = datetime.now(timezone.utc)
        
        appt_delayed = MockAppointment(1, "PENDIENTE", now - timedelta(minutes=20))
        appt_proximity = MockAppointment(2, "PENDIENTE", now + timedelta(minutes=30))
        
        from core.crud_visual_indicator import enrich_appointments_with_visuals
        import core.crud_visual_indicator as cvi
        cvi.get_visual_config = AsyncMock(return_value={
            "delayed": type('Config', (), {'code': 'delayed', 'label': 'Demorada', 'hex_color': '#EF4444', 'sort_order': 0}),
            "proximity_rank_1": type('Config', (), {'code': 'proximity_rank_1', 'label': 'Próxima 1', 'hex_color': '#10B981', 'sort_order': 1}),
            "pending": type('Config', (), {'code': 'pending', 'label': 'Pendiente', 'hex_color': '#6B7280', 'sort_order': 10}),
        })
        
        appointments = [appt_proximity, appt_delayed]
        enriched = await enrich_appointments_with_visuals(None, appointments)
        
        # Delayed debe ir primero
        assert enriched[0].id == 1
        assert enriched[0].visual_indicator["code"] == "delayed"
        assert enriched[1].id == 2
        assert enriched[1].visual_indicator["code"] == "proximity_rank_1"


class TestConstants:
    def test_statuses_that_occupy(self):
        from core.crud_visual_indicator import STATUSES_THAT_OCCUPY
        assert "PENDIENTE" in STATUSES_THAT_OCCUPY
        assert "CONFIRMADA" in STATUSES_THAT_OCCUPY
        assert "REAGENDADA" in STATUSES_THAT_OCCUPY
        assert "CANCELADA" not in STATUSES_THAT_OCCUPY
        assert "COMPLETADA" not in STATUSES_THAT_OCCUPY
    
    def test_disabled_group_is_excluded(self):
        from core.crud_visual_indicator import STATUSES_THAT_OCCUPY
        assert "CANCELADA" not in STATUSES_THAT_OCCUPY
        assert "COMPLETADA" not in STATUSES_THAT_OCCUPY
    
    def test_terminal_statuses(self):
        from core.crud_visual_indicator import TERMINAL_STATUSES
        assert "CANCELADA" in TERMINAL_STATUSES
        assert "COMPLETADA" in TERMINAL_STATUSES
        assert "PENDIENTE" not in TERMINAL_STATUSES
        assert "CONFIRMADA" not in TERMINAL_STATUSES
    
    def test_terminal_statuses_excluded_from_occupy(self):
        from core.crud_visual_indicator import STATUSES_THAT_OCCUPY, TERMINAL_STATUSES
        for status in TERMINAL_STATUSES:
            assert status not in STATUSES_THAT_OCCUPY