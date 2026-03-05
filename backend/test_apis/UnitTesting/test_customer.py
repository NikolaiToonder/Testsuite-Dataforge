import pytest
import uuid
from unittest.mock import AsyncMock
from app.libs.tenant_models import MachineCreate, MachineUpdate, TenantOverview, TenantMachinesResponse, Machine


class TestCustomerTenantInfo:
    """Test suite for GET /customer/my-tenant endpoint"""

    def test_get_my_tenant_info_success_admin(self, admin_client, mocker, mock_tenant_info, mock_tenant_overview):
        """Test getting tenant info as admin user"""
        mocker.patch("app.apis.customer.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        mocker.patch("app.apis.customer.get_tenant_overview", new_callable=AsyncMock, return_value=mock_tenant_overview)
        
        response = admin_client.get("/api/customer/my-tenant")
        
        assert response.status_code == 200
        data = response.json()
        assert data["tenant"]["id"] == str(mock_tenant_overview.tenant.id)
        assert data["tenant"]["name"] == mock_tenant_overview.tenant.name
        assert data["machine_count"] == mock_tenant_overview.machine_count

    def test_get_my_tenant_info_no_tenant_association(self, admin_client, mocker):
        """Test getting tenant info when user has no tenant association"""
        mocker.patch("app.apis.customer.get_user_tenant_info", new_callable=AsyncMock, return_value=None)
        
        response = admin_client.get("/api/customer/my-tenant")
        
        assert response.status_code == 404
        assert "User is not associated with any tenant" in response.json()["detail"]


class TestCustomerMachines:
    """Test suite for GET /customer/machines endpoint"""

    def test_get_my_machines_success(self, admin_client, mocker, mock_tenant_info, mock_machine):
        """Test getting all machines for current tenant"""
        mocker.patch("app.apis.customer.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        mocker.patch("app.apis.customer.get_tenant_machines", new_callable=AsyncMock, return_value=[mock_machine])
        
        response = admin_client.get("/api/customer/machines")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert len(data["machines"]) == 1
        assert data["machines"][0]["id"] == str(mock_machine.id)

    def test_get_my_machines_no_tenant_association(self, admin_client, mocker):
        """Test getting machines when user has no tenant association"""
        mocker.patch("app.apis.customer.get_user_tenant_info", new_callable=AsyncMock, return_value=None)
        
        response = admin_client.get("/api/customer/machines")
        
        assert response.status_code == 404


class TestCustomerCreateMachine:
    """Test suite for POST /customer/machines endpoint"""

    def test_create_machine_success(self, admin_client, mocker, mock_tenant_info, mock_machine):
        """Test creating a new machine successfully"""
        machine_data = {
            "eui": "1234567890ABCDEF",
            "name": "New Machine",
            "location": "Floor 1",
            "max_expected_amps": 50.0
        }
        
        mocker.patch("app.apis.customer.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        mocker.patch("app.apis.customer.get_machine_by_eui", new_callable=AsyncMock, return_value=None)
        mocker.patch("app.apis.customer.create_machine", new_callable=AsyncMock, return_value=mock_machine)
        
        response = admin_client.post("/api/customer/machines", json=machine_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["eui"] == mock_machine.eui

    def test_create_machine_duplicate_eui(self, admin_client, mocker, mock_tenant_info, mock_machine):
        """Test creating a machine with duplicate EUI"""
        machine_data = {"eui": "1234567890ABCDEF", "name": "New Machine"}
        
        mocker.patch("app.apis.customer.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        mocker.patch("app.apis.customer.get_machine_by_eui", new_callable=AsyncMock, return_value=mock_machine)
        
        response = admin_client.post("/api/customer/machines", json=machine_data)
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


class TestCustomerGetMachine:
    """Test suite for GET /customer/machines/{machine_id} endpoint"""

    def test_get_machine_success(self, admin_client, mocker, mock_tenant_info, mock_machine):
        """Test getting a specific machine successfully"""
        mocker.patch("app.apis.customer.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        mocker.patch("app.apis.customer.get_machine_by_id", new_callable=AsyncMock, return_value=mock_machine)
        
        response = admin_client.get(f"/api/customer/machines/{mock_machine.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(mock_machine.id)

    def test_get_machine_not_found(self, admin_client, mocker, mock_tenant_info):
        """Test getting a machine that doesn't exist"""
        machine_id = uuid.uuid4()
        
        mocker.patch("app.apis.customer.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        mocker.patch("app.apis.customer.get_machine_by_id", new_callable=AsyncMock, return_value=None)
        
        response = admin_client.get(f"/api/customer/machines/{machine_id}")
        
        assert response.status_code == 404

    def test_get_machine_invalid_id(self, admin_client):
        """Test getting a machine with invalid UUID"""
        response = admin_client.get("/api/customer/machines/invalid-uuid")
        
        assert response.status_code == 404


class TestCustomerUpdateMachine:
    """Test suite for PUT /customer/machines/{machine_id} endpoint"""

    def test_update_machine_success(self, admin_client, mocker, mock_tenant_info, mock_machine):
        """Test updating a machine successfully"""
        update_data = {"name": "Updated Machine Name"}
        
        mocker.patch("app.apis.customer.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        mocker.patch("app.apis.customer.get_machine_by_id", new_callable=AsyncMock, return_value=mock_machine)
        mocker.patch("app.apis.customer.update_machine", new_callable=AsyncMock, return_value=mock_machine)
        
        response = admin_client.put(f"/api/customer/machines/{mock_machine.id}", json=update_data)
        
        assert response.status_code == 200

    def test_update_machine_not_found(self, admin_client, mocker, mock_tenant_info):
        """Test updating a machine that doesn't exist"""
        machine_id = uuid.uuid4()
        update_data = {"name": "Updated Name"}
        
        mocker.patch("app.apis.customer.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        mocker.patch("app.apis.customer.get_machine_by_id", new_callable=AsyncMock, return_value=None)
        
        response = admin_client.put(f"/api/customer/machines/{machine_id}", json=update_data)
        
        assert response.status_code == 404


class TestCustomerDeleteMachine:
    """Test suite for DELETE /customer/machines/{machine_id} endpoint"""

    def test_delete_machine_success(self, admin_client, mocker, mock_tenant_info, mock_machine):
        """Test deleting a machine successfully"""
        mocker.patch("app.apis.customer.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        mocker.patch("app.apis.customer.get_machine_by_id", new_callable=AsyncMock, return_value=mock_machine)
        mocker.patch("app.apis.customer.delete_machine", new_callable=AsyncMock, return_value=None)
        
        response = admin_client.delete(f"/api/customer/machines/{mock_machine.id}")
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

    def test_delete_machine_not_found(self, admin_client, mocker, mock_tenant_info):
        """Test deleting a machine that doesn't exist"""
        machine_id = uuid.uuid4()
        
        mocker.patch("app.apis.customer.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        mocker.patch("app.apis.customer.get_machine_by_id", new_callable=AsyncMock, return_value=None)
        
        response = admin_client.delete(f"/api/customer/machines/{machine_id}")
        
        assert response.status_code == 404