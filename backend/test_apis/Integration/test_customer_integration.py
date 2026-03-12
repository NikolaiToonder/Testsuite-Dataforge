import pytest
import uuid
import asyncio
from unittest.mock import AsyncMock
from app.libs.tenant_models import MachineCreate, MachineUpdate, TenantOverview, TenantMachinesResponse, Machine


def db_execute(db, query, *args):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(db.execute(query, *args))


def db_fetchrow(db, query, *args):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(db.fetchrow(query, *args))


class TestCustomerTenantInfo:
    """Test suite for GET /customer/my-tenant endpoint"""

    def test_get_my_tenant_info_success_admin(self, admin_client, db):
        """Test getting tenant info as admin user """
        tenant_id = "11111111-1111-1111-1111-111111111111"
        
        # Insert some test machines to get realistic counts
        db_execute(db,
            """
            INSERT INTO machines (id, tenant_id, eui, name) 
            VALUES 
                ($1::uuid, $2::uuid, 'EUI001', 'Machine 1'),
                ($3::uuid, $2::uuid, 'EUI002', 'Machine 2')
            """,
            str(uuid.uuid4()), tenant_id, str(uuid.uuid4())
        )
        
        response = admin_client.get("/api/customer/my-tenant")
        
        assert response.status_code == 200
        data = response.json()
        assert data["tenant"]["id"] == tenant_id
        assert data["tenant"]["name"] == "Test Tenant"
        assert data["machine_count"] == 2

    def test_get_my_tenant_info_no_tenant(self, admin_client, mocker):
        """Test getting tenant info when user has no tenant association"""
        mocker.patch("app.apis.customer.get_user_tenant_info", new_callable=AsyncMock, return_value=None)
        
        response = admin_client.get("/api/customer/my-tenant")
        
        assert response.status_code == 404
        assert "User is not associated with any tenant" in response.json()["detail"]


class TestCustomerMachines:
    """Test suite for GET /customer/machines endpoint"""

    def test_get_my_machines_success(self, admin_client, db):
        """Test getting all machines for current tenant"""
        tenant_id = "11111111-1111-1111-1111-111111111111"
        machine_id_1 = str(uuid.uuid4())
        machine_id_2 = str(uuid.uuid4())
        
        db_execute(db,
            """
            INSERT INTO machines (id, tenant_id, eui, name, location) 
            VALUES 
                ($1::uuid, $2::uuid, 'AABBCCDD11223344', 'Machine Alpha', 'Floor 1'),
                ($3::uuid, $2::uuid, 'EEFF001122334455', 'Machine Beta', 'Floor 2')
            """,
            machine_id_1, tenant_id, machine_id_2
        )
        
        response = admin_client.get("/api/customer/machines")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert len(data["machines"]) == 2
        machine_ids = [m["id"] for m in data["machines"]]
        assert machine_id_1 in machine_ids
        assert machine_id_2 in machine_ids

    def test_get_my_machines_no_tenant_association(self, admin_client, mocker):
        """Test getting machines when user has no tenant association"""
        mocker.patch("app.apis.customer.get_user_tenant_info", new_callable=AsyncMock, return_value=None)
        
        response = admin_client.get("/api/customer/machines")
        
        assert response.status_code == 404


class TestCustomerCreateMachine:
    """Test suite for POST /customer/machines endpoint"""

    def test_create_machine_success(self, admin_client, db):
        """Test creating a new machine successfully"""
        machine_data = {
            "eui": "1234567890ABCDEF",
            "name": "New Machine",
            "location": "Floor 1",
            "max_expected_amps": 50.0
        }
        
        response = admin_client.post("/api/customer/machines", json=machine_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["eui"] == "1234567890ABCDEF"
        assert data["name"] == "New Machine"
        assert data["location"] == "Floor 1"
        
        # Verify it was actually inserted into the database
        result = db_fetchrow(db,
            "SELECT * FROM machines WHERE eui = $1",
            "1234567890ABCDEF"
        )
        assert result is not None
        assert result["name"] == "New Machine"

    def test_create_machine_duplicate_eui(self, admin_client, db):
        """Test creating a machine with duplicate EUI"""
        tenant_id = "11111111-1111-1111-1111-111111111111"
        
        # Insert existing machine
        db_execute(db,
            "INSERT INTO machines (id, tenant_id, eui, name) VALUES ($1::uuid, $2::uuid, $3, $4)",
            str(uuid.uuid4()), tenant_id, "1234567890ABCDEF", "Existing Machine"
        )
        
        machine_data = {"eui": "1234567890ABCDEF", "name": "New Machine"}
        
        response = admin_client.post("/api/customer/machines", json=machine_data)
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


class TestCustomerGetMachine:
    """Test suite for GET /customer/machines/{machine_id} endpoint"""
    
    def test_get_machine_success(self, admin_client, db):
        """Test getting a specific machine successfully"""
        machine_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        tenant_id = "11111111-1111-1111-1111-111111111111"
        
        db_execute(db,
            "INSERT INTO machines (id, tenant_id, eui, name, location) VALUES ($1::uuid, $2::uuid, $3, $4, $5)",
            machine_id, tenant_id, "ABCDEF1234567890", "Test Machine", "Floor 1",
        )
        
        response = admin_client.get(f"/api/customer/machines/{machine_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == machine_id
        assert data["name"] == "Test Machine"
        assert data["eui"] == "ABCDEF1234567890"

    def test_get_machine_not_found(self, admin_client):
        """Test getting a machine that doesn't exist - uses real DB (empty machines table)"""
        machine_id = uuid.uuid4()

        response = admin_client.get(f"/api/customer/machines/{machine_id}")

        assert response.status_code == 404

    def test_get_machine_invalid_id(self, admin_client):
        """Test getting a machine with invalid UUID"""
        response = admin_client.get("/api/customer/machines/invalid-uuid")
        
        assert response.status_code == 400


class TestCustomerUpdateMachine:
    """Test suite for PUT /customer/machines/{machine_id} endpoint"""

    def test_update_machine_success(self, admin_client, db):
        """Test updating a machine successfully"""
        machine_id = str(uuid.uuid4())
        tenant_id = "11111111-1111-1111-1111-111111111111"
        
        # Insert initial machine
        db_execute(db,
            "INSERT INTO machines (id, tenant_id, eui, name, location) VALUES ($1::uuid, $2::uuid, $3, $4, $5)",
            machine_id, tenant_id, "UPDATE001122334455", "Original Name", "Floor 1"
        )
        
        update_data = {"name": "Updated Machine Name", "location": "Floor 3"}
        
        response = admin_client.put(f"/api/customer/machines/{machine_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Machine Name"
        assert data["location"] == "Floor 3"
        
        # Verify the update in database
        result = db_fetchrow(db,
            "SELECT * FROM machines WHERE id = $1::uuid",
            machine_id
        )
        assert result["name"] == "Updated Machine Name"
        assert result["location"] == "Floor 3"

    def test_update_machine_not_found(self, admin_client):
        """Test updating a machine that doesn't exist - uses real DB (empty machines table)"""
        machine_id = uuid.uuid4()
        update_data = {"name": "Updated Name"}
        
        response = admin_client.put(f"/api/customer/machines/{machine_id}", json=update_data)
        
        assert response.status_code == 404


class TestCustomerDeleteMachine:
    """Test suite for DELETE /customer/machines/{machine_id} endpoint"""

    def test_delete_machine_success(self, admin_client, db):
        """Test deleting a machine successfully"""
        machine_id = str(uuid.uuid4())
        tenant_id = "11111111-1111-1111-1111-111111111111"
        
        # Insert machine to delete
        db_execute(db,
            "INSERT INTO machines (id, tenant_id, eui, name) VALUES ($1::uuid, $2::uuid, $3, $4)",
            machine_id, tenant_id, "DELETE1122334455", "Machine to Delete"
        )
        
        response = admin_client.delete(f"/api/customer/machines/{machine_id}")
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
        
        result = db_fetchrow(db,
            "SELECT * FROM machines WHERE id = $1::uuid",
            machine_id
        )
        assert result is None

    def test_delete_machine_not_found(self, admin_client):
        """Test deleting a machine that doesn't exist"""
        machine_id = uuid.uuid4()
        
        response = admin_client.delete(f"/api/customer/machines/{machine_id}")
        
        assert response.status_code == 404