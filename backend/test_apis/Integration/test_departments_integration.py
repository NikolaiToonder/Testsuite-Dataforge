import pytest
import uuid
import asyncio


USER_ID = "test-admin-001"
TENANT_ID = "11111111-1111-1111-1111-111111111111"


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def insert_department(db, name, color="#6B7280", active=True, tenant_id=TENANT_ID):
    # Helper function to have less repetetive code 
    dept_id = str(uuid.uuid4())
    run(db.execute(
        """
        INSERT INTO departments (id, tenant_id, name, color, active)
        VALUES ($1::uuid, $2::uuid, $3, $4, $5)
        """,
        dept_id, tenant_id, name, color, active
    ))
    return dept_id


def insert_machine(db, dept_id, eui=None):
    machine_id = str(uuid.uuid4())
    run(db.execute(
        """
        INSERT INTO machines (id, tenant_id, eui, name, department_id)
        VALUES ($1::uuid, $2::uuid, $3, $4, $5::uuid)
        """,
        machine_id, TENANT_ID, eui or uuid.uuid4().hex[:16], "Test Machine", dept_id
    ))
    return machine_id


def get_department(db, dept_id):
    return run(db.fetchrow(
        "SELECT * FROM departments WHERE id = $1::uuid", dept_id
    ))

class TestListDepartments:

    def test_empty_list(self, admin_client):
        data = admin_client.get("/api/departments/list").json()
        assert data == []

    def test_returns_tenant_departments(self, admin_client, db):
        insert_department(db, "Production")
        insert_department(db, "Maintenance")

        data = admin_client.get("/api/departments/list").json()

        names = [d["name"] for d in data]
        assert "Production" in names
        assert "Maintenance" in names

    def test_includes_machine_count(self, admin_client, db):
        dept_id = insert_department(db, "Assembly")
        insert_machine(db, dept_id)
        insert_machine(db, dept_id)

        data = admin_client.get("/api/departments/list").json()

        dept = next(d for d in data if d["name"] == "Assembly")
        assert dept["machine_count"] == 2


class TestCreateDepartment:

    def test_create_success(self, admin_client, db):
        response = admin_client.post("/api/departments/", json={
            "name": "New Department",
            "color": "#FF5733",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Department"
        assert data["color"] == "#FF5733"
        assert get_department(db, data["id"]) is not None

    def test_duplicate_name_fails(self, admin_client, db):
        insert_department(db, "Existing")

        response = admin_client.post("/api/departments/", json={"name": "Existing", "color": "#000000"})

        assert response.status_code == 400

    def test_duplicate_name_case_insensitive(self, admin_client, db):
        insert_department(db, "production")

        response = admin_client.post("/api/departments/", json={"name": "PRODUCTION", "color": "#000000"})

        assert response.status_code == 400


class TestUpdateDepartment:

    def test_rename(self, admin_client, db):
        dept_id = insert_department(db, "Old Name")

        response = admin_client.put(f"/api/departments/{dept_id}", json={"name": "New Name"})

        assert response.status_code == 200
        assert get_department(db, dept_id)["name"] == "New Name"

    def test_not_found(self, admin_client):
        response = admin_client.put(f"/api/departments/{uuid.uuid4()}", json={"name": "X"})

        assert response.status_code == 404

    def test_duplicate_name_fails(self, admin_client, db):
        dept_id = insert_department(db, "Dept A")
        insert_department(db, "Dept B")

        response = admin_client.put(f"/api/departments/{dept_id}", json={"name": "Dept B"})

        assert response.status_code == 400

    def test_no_fields_fails(self, admin_client, db):
        dept_id = insert_department(db, "Unchanged")

        response = admin_client.put(f"/api/departments/{dept_id}", json={})

        assert response.status_code == 400


class TestDeleteDepartment:

    def test_delete_empty_department(self, admin_client, db):
        dept_id = insert_department(db, "Throwaway")

        response = admin_client.delete(f"/api/departments/{dept_id}")

        assert response.status_code == 200
        assert get_department(db, dept_id) is None

    def test_delete_cascades_machines(self, admin_client, db):
        dept_id = insert_department(db, "With Machines")
        machine_id = insert_machine(db, dept_id)

        admin_client.delete(f"/api/departments/{dept_id}")

        machine = run(db.fetchrow(
            "SELECT * FROM machines WHERE id = $1::uuid", machine_id
        ))
        assert machine is None

    def test_not_found(self, admin_client):
        response = admin_client.delete(f"/api/departments/{uuid.uuid4()}")

        assert response.status_code == 404