import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime


@pytest.fixture(autouse=True)
def mock_asyncpg_connect(mocker):
    """Auto-mock asyncpg.connect for all department tests"""
    mock_conn = AsyncMock()
    mock_conn.close = AsyncMock()
    mocker.patch("asyncpg.connect", return_value=mock_conn)
    return mock_conn


class TestListDepartments:
    """Test suite for GET /departments/list endpoint"""

    def test_list_departments_regular_user(self, admin_client, mocker, mock_db_row, mock_asyncpg_connect, mock_tenant_info):
        """Test listing departments as regular user (tenant-scoped)"""
        mocker.patch("app.apis.departments.is_super_admin_with_auto_register", new_callable=AsyncMock, return_value=False)
        mocker.patch("app.apis.departments.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        
        mock_depts = [
            mock_db_row({
                "id": "dept-1",
                "name": "Production",
                "description": "Production department",
                "color": "#FF5733",
                "active": True,
                "machine_count": 5,
                "sensor_count": 10,
                "created_at": datetime(2024, 1, 1),
                "updated_at": datetime(2024, 1, 1)
            }),
            mock_db_row({
                "id": "dept-2",
                "name": "Quality Control",
                "description": None,
                "color": "#33FF57",
                "active": True,
                "machine_count": 2,
                "sensor_count": 4,
                "created_at": datetime(2024, 1, 2),
                "updated_at": datetime(2024, 1, 2)
            })
        ]
        
        mock_asyncpg_connect.fetch = AsyncMock(return_value=mock_depts)
        
        response = admin_client.get("/api/departments/list")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Production"
        assert data[0]["machine_count"] == 5
        assert data[1]["name"] == "Quality Control"

    def test_list_departments_super_admin(self, admin_client, mocker, mock_db_row, mock_asyncpg_connect):
        """Test listing departments as super admin (all tenants)"""
        mocker.patch("app.apis.departments.is_super_admin_with_auto_register", new_callable=AsyncMock, return_value=True)
        
        mock_depts = [
            mock_db_row({
                "id": "dept-1",
                "name": "Production",
                "description": "Production department",
                "color": "#FF5733",
                "active": True,
                "tenant_name": "Tenant A",
                "machine_count": 5,
                "sensor_count": 10,
                "created_at": datetime(2024, 1, 1),
                "updated_at": datetime(2024, 1, 1)
            }),
            mock_db_row({
                "id": "dept-2",
                "name": "Production",
                "description": "Production department",
                "color": "#33FF57",
                "active": True,
                "tenant_name": "Tenant B",
                "machine_count": 3,
                "sensor_count": 6,
                "created_at": datetime(2024, 1, 2),
                "updated_at": datetime(2024, 1, 2)
            })
        ]
        
        mock_asyncpg_connect.fetch = AsyncMock(return_value=mock_depts)
        
        response = admin_client.get("/api/departments/list")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert "Tenant A" in data[0]["name"]
        assert "Tenant B" in data[1]["name"]


class TestCreateDepartment:
    """Test suite for POST /departments/ endpoint"""

    def test_create_department_success(self, admin_client, mocker, mock_db_row, mock_asyncpg_connect, mock_tenant_info):
        """Test creating a new department"""
        mocker.patch("app.apis.departments.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        
        dept_data = {
            "name": "New Department",
            "description": "Department description",
            "color": "#FF5733"
        }
        
        mock_row = mock_db_row({
            "id": "dept-new",
            "name": "New Department",
            "description": "Department description",
            "color": "#FF5733",
            "active": True,
            "created_at": datetime(2024, 1, 1),
            "updated_at": datetime(2024, 1, 1)
        })
        
        # First fetchrow checks for existing, second returns new department
        mock_asyncpg_connect.fetchrow = AsyncMock(side_effect=[None, mock_row])
        
        response = admin_client.post("/api/departments/", json=dept_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Department"
        assert data["color"] == "#FF5733"
        assert data["machine_count"] == 0
        assert data["sensor_count"] == 0

    def test_create_department_duplicate_name(self, admin_client, mocker, mock_db_row, mock_asyncpg_connect, mock_tenant_info):
        """Test creating department with duplicate name"""
        mocker.patch("app.apis.departments.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        
        dept_data = {
            "name": "Existing Department",
            "color": "#FF5733"
        }
        
        existing_row = mock_db_row({"id": "dept-existing"})
        mock_asyncpg_connect.fetchrow = AsyncMock(return_value=existing_row)
        
        response = admin_client.post("/api/departments/", json=dept_data)
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_department_no_tenant(self, admin_client, mocker):
        """Test creating department when user has no tenant"""
        mocker.patch("app.apis.departments.get_user_tenant_info", new_callable=AsyncMock, return_value=None)
        
        dept_data = {
            "name": "New Department",
            "color": "#FF5733"
        }
        
        response = admin_client.post("/api/departments/", json=dept_data)
        
        assert response.status_code == 404
        assert "not associated with any tenant" in response.json()["detail"]


class TestUpdateDepartment:
    """Test suite for PUT /departments/{department_id} endpoint"""

    def test_update_department_success(self, admin_client, mocker, mock_db_row, mock_asyncpg_connect, mock_tenant_info):
        """Test updating department"""
        mocker.patch("app.apis.departments.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        
        update_data = {
            "name": "Updated Department",
            "description": "Updated description",
            "color": "#33FF57"
        }
        
        existing_row = mock_db_row({"id": "dept-1"})
        updated_row = mock_db_row({
            "id": "dept-1",
            "name": "Updated Department",
            "description": "Updated description",
            "color": "#33FF57",
            "active": True,
            "created_at": datetime(2024, 1, 1),
            "updated_at": datetime(2024, 1, 2)
        })
        counts_row = mock_db_row({
            "machine_count": 5,
            "sensor_count": 10
        })
        
        # fetchrow calls: check exists, check name uniqueness, update, get counts
        mock_asyncpg_connect.fetchrow = AsyncMock(side_effect=[existing_row, None, updated_row, counts_row])
        
        response = admin_client.put("/api/departments/dept-1", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Department"
        assert data["color"] == "#33FF57"

    def test_update_department_not_found(self, admin_client, mocker, mock_asyncpg_connect, mock_tenant_info):
        """Test updating non-existent department"""
        mocker.patch("app.apis.departments.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        
        update_data = {"name": "Updated Name"}
        
        mock_asyncpg_connect.fetchrow = AsyncMock(return_value=None)
        
        response = admin_client.put("/api/departments/nonexistent", json=update_data)
        
        assert response.status_code == 404

    def test_update_department_duplicate_name(self, admin_client, mocker, mock_db_row, mock_asyncpg_connect, mock_tenant_info):
        """Test updating department with duplicate name"""
        mocker.patch("app.apis.departments.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        
        update_data = {"name": "Existing Name"}
        
        existing_row = mock_db_row({"id": "dept-1"})
        duplicate_row = mock_db_row({"id": "dept-2"})
        
        mock_asyncpg_connect.fetchrow = AsyncMock(side_effect=[existing_row, duplicate_row])
        
        response = admin_client.put("/api/departments/dept-1", json=update_data)
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


class TestDeleteDepartment:
    """Test suite for DELETE /departments/{department_id} endpoint"""

    def test_delete_department_success(self, admin_client, mocker, mock_db_row, mock_asyncpg_connect, mock_tenant_info):
        """Test deleting department"""
        mocker.patch("app.apis.departments.is_super_admin_with_auto_register", new_callable=AsyncMock, return_value=False)
        mocker.patch("app.apis.departments.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        
        dept_row = mock_db_row({
            "id": "dept-1",
            "name": "Department to Delete"
        })
        
        # Mock transaction context manager properly
        mock_transaction = MagicMock()
        mock_transaction.__aenter__ = AsyncMock(return_value=mock_transaction)
        mock_transaction.__aexit__ = AsyncMock(return_value=None)
        mock_asyncpg_connect.transaction = MagicMock(return_value=mock_transaction)
        
        # fetchrow for department check, fetchval for counts (3 calls), execute for deletes
        mock_asyncpg_connect.fetchrow = AsyncMock(return_value=dept_row)
        mock_asyncpg_connect.fetchval = AsyncMock(side_effect=[2, 1, 3])  # machine, gateway, hypothesis counts
        mock_asyncpg_connect.execute = AsyncMock()
        
        response = admin_client.delete("/api/departments/dept-1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Department to Delete" in data["message"]

    def test_delete_department_not_found(self, admin_client, mocker, mock_asyncpg_connect, mock_tenant_info):
        """Test deleting non-existent department"""
        mocker.patch("app.apis.departments.is_super_admin_with_auto_register", new_callable=AsyncMock, return_value=False)
        mocker.patch("app.apis.departments.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        
        mock_asyncpg_connect.fetchrow = AsyncMock(return_value=None)
        
        response = admin_client.delete("/api/departments/nonexistent")
        
        assert response.status_code == 404


class TestDepartmentAuthorization:
    """Test suite for department authorization across endpoints"""

    def test_unauthenticated_access_denied(self, unauthenticated_client):
        """Test that unauthenticated requests are rejected"""
        response = unauthenticated_client.get("/api/departments/list")
        assert response.status_code == 401