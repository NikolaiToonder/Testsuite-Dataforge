import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime


@pytest.fixture(autouse=True)
def mock_asyncpg_connect(mocker):
    """Auto-mock asyncpg.connect for all dashboard-layout tests"""
    mock_conn = AsyncMock()
    mock_conn.close = AsyncMock()
    mocker.patch("asyncpg.connect", return_value=mock_conn)
    return mock_conn


class TestGetDashboardLayout:
    """Test suite for GET /dashboard-layout/ endpoint"""

    def test_get_dashboard_layout_with_named_default(self, admin_client, mock_db_row, mock_asyncpg_connect):
        """Test getting dashboard layout with default named layout"""
        layout_data = {
            "widgets": [
                {
                    "id": "widget-1",
                    "type": "power_consumption",
                    "position": {"x": 0, "y": 0},
                    "size": {"w": 6, "h": 4},
                    "settings": {}
                }
            ]
        }
        
        mock_row = mock_db_row({
            "layout_data": layout_data,
            "updated_at": datetime(2024, 1, 1, 12, 0, 0)
        })
        mock_asyncpg_connect.fetchrow = AsyncMock(return_value=mock_row)
        
        response = admin_client.get("/api/dashboard-layout/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["layout"]["widgets"]) == 1
        assert data["layout"]["widgets"][0]["id"] == "widget-1"

    def test_get_dashboard_layout_empty(self, admin_client, mock_asyncpg_connect):
        """Test getting dashboard layout when no layout exists"""
        mock_asyncpg_connect.fetchrow = AsyncMock(return_value=None)
        
        response = admin_client.get("/api/dashboard-layout/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["layout"]["widgets"] == []

    def test_get_dashboard_layout_fallback_to_old_table(self, admin_client, mock_db_row, mock_asyncpg_connect):
        """Test fallback to old user_dashboard_layouts table"""
        layout_data = {"widgets": []}
        mock_row = mock_db_row({
            "layout_data": layout_data,
            "updated_at": datetime(2024, 1, 1, 12, 0, 0)
        })
        
        # First call returns None, second returns old layout
        mock_asyncpg_connect.fetchrow = AsyncMock(side_effect=[None, mock_row])
        
        response = admin_client.get("/api/dashboard-layout/")
        
        assert response.status_code == 200
        assert mock_asyncpg_connect.fetchrow.call_count == 2


class TestUpdateDashboardLayout:
    """Test suite for PUT /dashboard-layout/ endpoint"""

    def test_update_dashboard_layout_new(self, admin_client, mock_db_row, mock_asyncpg_connect):
        """Test updating dashboard layout (creating new default)"""
        update_data = {
            "widgets": [
                {
                    "id": "widget-1",
                    "type": "power_consumption",
                    "position": {"x": 0, "y": 0},
                    "size": {"w": 6, "h": 4},
                    "settings": {}
                }
            ]
        }
        
        mock_row = mock_db_row({"updated_at": datetime(2024, 1, 1, 12, 0, 0)})
        
        # fetchrow for checking existing, then for insert
        mock_asyncpg_connect.fetchrow = AsyncMock(side_effect=[None, mock_row])
        mock_asyncpg_connect.execute = AsyncMock()
        
        response = admin_client.put("/api/dashboard-layout/", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "updated_at" in data

    def test_update_dashboard_layout_existing(self, admin_client, mock_db_row, mock_asyncpg_connect):
        """Test updating existing default layout"""
        update_data = {
            "widgets": [
                {
                    "id": "widget-2",
                    "type": "cost_overview",
                    "position": {"x": 6, "y": 0},
                    "size": {"w": 6, "h": 4},
                    "settings": {}
                }
            ]
        }
        
        existing_row = mock_db_row({"id": "layout-123"})
        updated_row = mock_db_row({"updated_at": datetime(2024, 1, 2, 12, 0, 0)})
        
        mock_asyncpg_connect.fetchrow = AsyncMock(side_effect=[existing_row, updated_row])
        mock_asyncpg_connect.execute = AsyncMock()
        
        response = admin_client.put("/api/dashboard-layout/", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestListNamedLayouts:
    """Test suite for GET /dashboard-layout/named endpoint"""

    def test_list_named_layouts_success(self, admin_client, mock_db_row, mock_asyncpg_connect):
        """Test listing named layouts"""
        mock_rows = [
            mock_db_row({
                "id": "layout-1",
                "name": "Default Layout",
                "description": "My default",
                "is_default": True,
                "is_system_template": False,
                "created_at": datetime(2024, 1, 1),
                "updated_at": datetime(2024, 1, 1)
            }),
            mock_db_row({
                "id": "layout-2",
                "name": "Custom Layout",
                "description": None,
                "is_default": False,
                "is_system_template": False,
                "created_at": datetime(2024, 1, 2),
                "updated_at": datetime(2024, 1, 2)
            })
        ]
        
        mock_asyncpg_connect.fetch = AsyncMock(return_value=mock_rows)
        
        response = admin_client.get("/api/dashboard-layout/named")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["layouts"]) == 2
        assert data["layouts"][0]["name"] == "Default Layout"

    def test_list_named_layouts_exclude_system(self, admin_client, mock_asyncpg_connect):
        """Test listing named layouts excluding system templates"""
        mock_asyncpg_connect.fetch = AsyncMock(return_value=[])
        
        response = admin_client.get("/api/dashboard-layout/named?include_system=false")
        
        assert response.status_code == 200
        data = response.json()
        assert data["layouts"] == []


class TestGetNamedLayout:
    """Test suite for GET /dashboard-layout/named/{layout_id} endpoint"""

    def test_get_named_layout_success(self, admin_client, mock_db_row, mock_asyncpg_connect):
        """Test getting specific named layout"""
        layout_data = {
            "widgets": [
                {
                    "id": "widget-1",
                    "type": "power_consumption",
                    "position": {"x": 0, "y": 0},
                    "size": {"w": 6, "h": 4},
                    "settings": {}
                }
            ]
        }
        
        mock_row = mock_db_row({
            "id": "layout-123",
            "name": "My Layout",
            "description": "Test layout",
            "layout_data": layout_data,
            "is_default": True,
            "is_system_template": False,
            "created_at": datetime(2024, 1, 1),
            "updated_at": datetime(2024, 1, 1)
        })
        
        mock_asyncpg_connect.fetchrow = AsyncMock(return_value=mock_row)
        
        response = admin_client.get("/api/dashboard-layout/named/layout-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "layout-123"
        assert data["name"] == "My Layout"
        assert len(data["widgets"]) == 1

    def test_get_named_layout_not_found(self, admin_client, mock_asyncpg_connect):
        """Test getting non-existent layout"""
        mock_asyncpg_connect.fetchrow = AsyncMock(return_value=None)
        
        response = admin_client.get("/api/dashboard-layout/named/nonexistent")
        
        assert response.status_code == 404


class TestCreateNamedLayout:
    """Test suite for POST /dashboard-layout/named endpoint"""

    def test_create_named_layout_success(self, admin_client, mock_db_row, mock_asyncpg_connect):
        """Test creating new named layout"""
        layout_data = {
            "name": "New Layout",
            "description": "My new layout",
            "widgets": [
                {
                    "id": "widget-1",
                    "type": "power_consumption",
                    "position": {"x": 0, "y": 0},
                    "size": {"w": 6, "h": 4},
                    "settings": {}
                }
            ],
            "is_default": False
        }
        
        mock_row = mock_db_row({
            "id": "layout-new",
            "name": "New Layout",
            "description": "My new layout",
            "layout_data": {"widgets": layout_data["widgets"]},
            "is_default": False,
            "is_system_template": False,
            "created_at": datetime(2024, 1, 1),
            "updated_at": datetime(2024, 1, 1)
        })
        
        # First fetchrow checks for existing name, second returns created layout
        mock_asyncpg_connect.fetchrow = AsyncMock(side_effect=[None, mock_row])
        mock_asyncpg_connect.execute = AsyncMock()
        
        response = admin_client.post("/api/dashboard-layout/named", json=layout_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Layout"
        assert data["is_default"] is False

    def test_create_named_layout_duplicate_name(self, admin_client, mock_db_row, mock_asyncpg_connect):
        """Test creating layout with duplicate name"""
        layout_data = {
            "name": "Existing Layout",
            "widgets": []
        }
        
        existing_row = mock_db_row({"id": "layout-existing"})
        mock_asyncpg_connect.fetchrow = AsyncMock(return_value=existing_row)
        
        response = admin_client.post("/api/dashboard-layout/named", json=layout_data)
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_named_layout_as_default(self, admin_client, mock_db_row, mock_asyncpg_connect):
        """Test creating layout as default (unsets other defaults)"""
        layout_data = {
            "name": "New Default",
            "widgets": [],
            "is_default": True
        }
        
        mock_row = mock_db_row({
            "id": "layout-new",
            "name": "New Default",
            "description": None,
            "layout_data": {"widgets": []},
            "is_default": True,
            "is_system_template": False,
            "created_at": datetime(2024, 1, 1),
            "updated_at": datetime(2024, 1, 1)
        })
        
        mock_asyncpg_connect.fetchrow = AsyncMock(side_effect=[None, mock_row])
        mock_asyncpg_connect.execute = AsyncMock()
        
        response = admin_client.post("/api/dashboard-layout/named", json=layout_data)
        
        assert response.status_code == 200
        # Verify that execute was called to unset other defaults
        assert mock_asyncpg_connect.execute.called


class TestUpdateNamedLayout:
    """Test suite for PUT /dashboard-layout/named/{layout_id} endpoint"""

    def test_update_named_layout_success(self, admin_client, mock_db_row, mock_asyncpg_connect):
        """Test updating named layout"""
        update_data = {
            "name": "Updated Layout Name"
        }
        
        existing_row = mock_db_row({
            "id": "layout-123",
            "is_system_template": False
        })
        
        updated_row = mock_db_row({
            "id": "layout-123",
            "name": "Updated Layout Name",
            "description": "Test",
            "layout_data": {"widgets": []},
            "is_default": False,
            "is_system_template": False,
            "created_at": datetime(2024, 1, 1),
            "updated_at": datetime(2024, 1, 2)
        })
        
        mock_asyncpg_connect.fetchrow = AsyncMock(side_effect=[existing_row, updated_row])
        
        response = admin_client.put("/api/dashboard-layout/named/layout-123", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Layout Name"

    def test_update_named_layout_not_found(self, admin_client, mock_asyncpg_connect):
        """Test updating non-existent layout"""
        update_data = {"name": "Updated"}
        
        mock_asyncpg_connect.fetchrow = AsyncMock(return_value=None)
        
        response = admin_client.put("/api/dashboard-layout/named/nonexistent", json=update_data)
        
        assert response.status_code == 404

    def test_update_named_layout_system_template(self, admin_client, mock_db_row, mock_asyncpg_connect):
        """Test that system templates cannot be modified"""
        update_data = {"name": "Updated"}
        
        system_row = mock_db_row({
            "id": "layout-system",
            "is_system_template": True
        })
        
        mock_asyncpg_connect.fetchrow = AsyncMock(return_value=system_row)
        
        response = admin_client.put("/api/dashboard-layout/named/layout-system", json=update_data)
        
        assert response.status_code == 403
        assert "system templates" in response.json()["detail"]

    def test_update_named_layout_duplicate_name(self, admin_client, mock_db_row, mock_asyncpg_connect):
        """Test updating layout with duplicate name"""
        update_data = {"name": "Existing Name"}
        
        existing_row = mock_db_row({
            "id": "layout-123",
            "is_system_template": False
        })
        
        duplicate_check = mock_db_row({"id": "layout-other"})
        
        mock_asyncpg_connect.fetchrow = AsyncMock(side_effect=[existing_row, duplicate_check])
        
        response = admin_client.put("/api/dashboard-layout/named/layout-123", json=update_data)
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_update_named_layout_set_as_default(self, admin_client, mock_db_row, mock_asyncpg_connect):
        """Test setting layout as default"""
        update_data = {"is_default": True}
        
        existing_row = mock_db_row({
            "id": "layout-123",
            "is_system_template": False
        })
        
        updated_row = mock_db_row({
            "id": "layout-123",
            "name": "Layout",
            "description": None,
            "layout_data": {"widgets": []},
            "is_default": True,
            "is_system_template": False,
            "created_at": datetime(2024, 1, 1),
            "updated_at": datetime(2024, 1, 2)
        })
        
        mock_asyncpg_connect.fetchrow = AsyncMock(side_effect=[existing_row, updated_row])
        mock_asyncpg_connect.execute = AsyncMock()
        
        response = admin_client.put("/api/dashboard-layout/named/layout-123", json=update_data)
        
        assert response.status_code == 200
        # Verify that execute was called to unset other defaults
        assert mock_asyncpg_connect.execute.called


class TestDeleteNamedLayout:
    """Test suite for DELETE /dashboard-layout/named/{layout_id} endpoint"""

    def test_delete_named_layout_success(self, admin_client, mock_db_row, mock_asyncpg_connect):
        """Test deleting named layout"""
        existing_row = mock_db_row({
            "id": "layout-123",
            "is_system_template": False,
            "name": "My Layout"
        })
        
        mock_asyncpg_connect.fetchrow = AsyncMock(return_value=existing_row)
        mock_asyncpg_connect.execute = AsyncMock()
        
        response = admin_client.delete("/api/dashboard-layout/named/layout-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "deleted successfully" in data["message"]

    def test_delete_named_layout_not_found(self, admin_client, mock_asyncpg_connect):
        """Test deleting non-existent layout"""
        mock_asyncpg_connect.fetchrow = AsyncMock(return_value=None)
        
        response = admin_client.delete("/api/dashboard-layout/named/nonexistent")
        
        assert response.status_code == 404

    def test_delete_named_layout_system_template(self, admin_client, mock_db_row, mock_asyncpg_connect):
        """Test that system templates cannot be deleted"""
        system_row = mock_db_row({
            "id": "layout-system",
            "is_system_template": True,
            "name": "System Template"
        })
        
        mock_asyncpg_connect.fetchrow = AsyncMock(return_value=system_row)
        
        response = admin_client.delete("/api/dashboard-layout/named/layout-system")
        
        assert response.status_code == 403
        assert "system templates" in response.json()["detail"]


class TestCopyLayout:
    """Test suite for POST /dashboard-layout/named/{layout_id}/copy endpoint"""

    def test_copy_layout_success(self, admin_client, mock_db_row, mock_asyncpg_connect):
        """Test copying layout"""
        source_layout_data = {
            "widgets": [
                {
                    "id": "widget-1",
                    "type": "power_consumption",
                    "position": {"x": 0, "y": 0},
                    "size": {"w": 6, "h": 4},
                    "settings": {}
                }
            ]
        }
        
        source_row = mock_db_row({
            "name": "Original Layout",
            "description": "Original",
            "layout_data": source_layout_data
        })
        
        copied_row = mock_db_row({
            "id": "layout-copy",
            "name": "Copy of Layout",
            "description": "Copy of Original Layout",
            "layout_data": source_layout_data,
            "is_default": False,
            "is_system_template": False,
            "created_at": datetime(2024, 1, 2),
            "updated_at": datetime(2024, 1, 2)
        })
        
        # fetchrow calls: source layout, check existing name, create copy
        mock_asyncpg_connect.fetchrow = AsyncMock(side_effect=[source_row, None, copied_row])
        
        response = admin_client.post("/api/dashboard-layout/named/layout-123/copy?name=Copy of Layout")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Copy of Layout"
        assert len(data["widgets"]) == 1

    def test_copy_layout_source_not_found(self, admin_client, mock_asyncpg_connect):
        """Test copying non-existent layout"""
        mock_asyncpg_connect.fetchrow = AsyncMock(return_value=None)
        
        response = admin_client.post("/api/dashboard-layout/named/nonexistent/copy?name=Copy")
        
        assert response.status_code == 404

    def test_copy_layout_duplicate_name(self, admin_client, mock_db_row, mock_asyncpg_connect):
        """Test copying with duplicate name"""
        source_row = mock_db_row({
            "name": "Original",
            "description": None,
            "layout_data": {"widgets": []}
        })
        
        existing_row = mock_db_row({"id": "layout-existing"})
        
        mock_asyncpg_connect.fetchrow = AsyncMock(side_effect=[source_row, existing_row])
        
        response = admin_client.post("/api/dashboard-layout/named/layout-123/copy?name=Existing")
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]