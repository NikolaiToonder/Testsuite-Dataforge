import pytest
import uuid
import asyncio
import json




USER_ID = "test-admin-001"

SAMPLE_WIDGETS = [
    {
        "id": "widget-1",
        "type": "power_consumption",
        "position": {"x": 0, "y": 0},
        "size": {"w": 6, "h": 4},
        "settings": {},
    },
    {
        "id": "widget-2",
        "type": "cost_overview",
        "position": {"x": 6, "y": 0},
        "size": {"w": 6, "h": 4},
        "settings": {},
    },
]


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def insert_named_layout(db, name, is_default=False, is_system=False, widgets=None, user_id=USER_ID):
    layout_id = str(uuid.uuid4())
    data = json.dumps({"widgets": widgets or []})
    run(db.execute(
        """
        INSERT INTO named_dashboard_layouts (id, user_id, name, layout_data, is_default, is_system_template)
        VALUES ($1::uuid, $2, $3, $4, $5, $6)
        """,
        layout_id, user_id, name, data, is_default, is_system,
    ))
    return layout_id


def get_layout(db, layout_id):
    return run(db.fetchrow(
        "SELECT * FROM named_dashboard_layouts WHERE id = $1::uuid", layout_id
    ))




class TestLegacyLayout:

    def test_new_user_gets_empty_layout(self, admin_client):
        response = admin_client.get("/api/dashboard-layout/")

        assert response.status_code == 200
        assert response.json()["layout"]["widgets"] == []

    def test_returns_default_layout(self, admin_client, db):
        insert_named_layout(db, "Standard Dashboard", is_default=True, widgets=SAMPLE_WIDGETS)

        data = admin_client.get("/api/dashboard-layout/").json()

        assert len(data["layout"]["widgets"]) == 2

    def test_saving_a_layout(self, admin_client, db):
        admin_client.put("/api/dashboard-layout/", json={"widgets": SAMPLE_WIDGETS})

        row = run(db.fetchrow(
            "SELECT * FROM named_dashboard_layouts WHERE user_id = $1 AND is_default = true",
            USER_ID,
        ))
        assert row is not None
        assert len(json.loads(row["layout_data"])["widgets"]) == 2

    def test_save_twice(self, admin_client, db):
        admin_client.put("/api/dashboard-layout/", json={"widgets": SAMPLE_WIDGETS})
        admin_client.put("/api/dashboard-layout/", json={"widgets": []})

        rows = run(db.fetch(
            "SELECT * FROM named_dashboard_layouts WHERE user_id = $1 AND is_default = true",
            USER_ID,
        ))
        assert len(rows) == 1




class TestBrowsingLayouts:

    def test_user_no_layout(self, admin_client):
        data = admin_client.get("/api/dashboard-layout/named?include_system=false").json()

        assert data["layouts"] == []

    def test_show_all_user_layouts(self, admin_client, db):
        insert_named_layout(db, "Morning View")
        insert_named_layout(db, "Evening View")

        data = admin_client.get("/api/dashboard-layout/named?include_system=false").json()

        names = [l["name"] for l in data["layouts"]]
        assert "Morning View" in names
        assert "Evening View" in names

    def test_default_layout_appears_first(self, admin_client, db):
        insert_named_layout(db, "Secondary")
        insert_named_layout(db, "My Default", is_default=True)

        data = admin_client.get("/api/dashboard-layout/named?include_system=false").json()

        assert data["layouts"][0]["name"] == "My Default"

    def test_fetch_layout_return_widget(self, admin_client, db):
        layout_id = insert_named_layout(db, "Detailed View", widgets=SAMPLE_WIDGETS)

        data = admin_client.get(f"/api/dashboard-layout/named/{layout_id}").json()

        assert data["id"] == layout_id
        assert len(data["widgets"]) == 2

    def test_fetch_layout_404(self, admin_client):
        """Layout doesnt exist"""
        response = admin_client.get(f"/api/dashboard-layout/named/{uuid.uuid4()}")

        assert response.status_code == 404


class TestCreatingLayouts:

    def test_create_layout_to_db(self, admin_client, db):
        response = admin_client.post("/api/dashboard-layout/named", json={
            "name": "New Layout",
            "widgets": SAMPLE_WIDGETS,
        })

        print(response.json())

        assert response.status_code == 200
        assert response.json()["name"] == "New Layout"
        assert get_layout(db, response.json()["id"]) is not None

    def test_create_layout_duplicate(self, admin_client, db):
        insert_named_layout(db, "My Layout")

        response = admin_client.post("/api/dashboard-layout/named", json={
            "name": "My Layout",
            "widgets": [],
        })

        assert response.status_code == 400

    def test_new_default_layout(self, admin_client, db):
        """Test if creating a new layout and putting it as default demotes the old one"""
        old_id = insert_named_layout(db, "Old Default", is_default=True)

        admin_client.post("/api/dashboard-layout/named", json={
            "name": "New Default",
            "widgets": [],
            "is_default": True,
        })

        assert get_layout(db, old_id)["is_default"] is False


class TestEditingLayouts:

    def test_rename_layout(self, admin_client, db):
        layout_id = insert_named_layout(db, "Old Name")

        response = admin_client.put(
            f"/api/dashboard-layout/named/{layout_id}",
            json={"name": "New Name"},
        )

        assert response.status_code == 200
        assert get_layout(db, layout_id)["name"] == "New Name"

    def test_rename_layout_duplicate(self, admin_client, db):
        layout_id = insert_named_layout(db, "Layout A")
        insert_named_layout(db, "Layout B")

        response = admin_client.put(
            f"/api/dashboard-layout/named/{layout_id}",
            json={"name": "Layout B"},
        )

        assert response.status_code == 400

    def test_edit_system_template(self, admin_client, db):
        """User should not be able to edit the system layout"""
        layout_id = insert_named_layout(db, "System Template", is_system=True)

        response = admin_client.put(
            f"/api/dashboard-layout/named/{layout_id}",
            json={"name": "Hacked Name"},
        )

        assert response.status_code == 403

    def test_promotion_demotes(self, admin_client, db):
        """Same thing as last class almost, checks if a new promotion demotes the old layout"""
        old_id = insert_named_layout(db, "Old Default", is_default=True)
        new_id = insert_named_layout(db, "Soon to be Default")

        admin_client.put(f"/api/dashboard-layout/named/{new_id}", json={"is_default": True})

        assert get_layout(db, old_id)["is_default"] is False




class TestDeletingLayouts:

    def test_delete_layout(self, admin_client, db):
        layout_id = insert_named_layout(db, "Throwaway")

        response = admin_client.delete(f"/api/dashboard-layout/named/{layout_id}")

        assert response.status_code == 200
        assert get_layout(db, layout_id) is None

    def test_delete_nonexistant_layout(self, admin_client):
        response = admin_client.delete(f"/api/dashboard-layout/named/{uuid.uuid4()}")

        assert response.status_code == 404

    def test_delete_system_layout(self, admin_client, db):
        layout_id = insert_named_layout(db, "Protected Template", is_system=True)

        response = admin_client.delete(f"/api/dashboard-layout/named/{layout_id}")

        assert response.status_code == 403


class TestCopyingLayouts:

    def test_copy_layout(self, admin_client, db):
        original_id = insert_named_layout(db, "Original", widgets=SAMPLE_WIDGETS)

        response = admin_client.post(
            f"/api/dashboard-layout/named/{original_id}/copy?name=My+Copy"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "My Copy"
        assert data["id"] != original_id
        assert data["is_default"] is False
        assert len(data["widgets"]) == 2

    def test_copy_system_template(self, admin_client, db):
        template_id = insert_named_layout(db, "System Template", is_system=True, user_id="system")

        response = admin_client.post(
            f"/api/dashboard-layout/named/{template_id}/copy?name=My+Version"
        )

        assert response.status_code == 200
        assert response.json()["is_system_template"] is False

    def test_copy_duplicate_name(self, admin_client, db):
        original_id = insert_named_layout(db, "Original")
        insert_named_layout(db, "Taken Name")

        response = admin_client.post(
            f"/api/dashboard-layout/named/{original_id}/copy?name=Taken+Name"
        )

        assert response.status_code == 400