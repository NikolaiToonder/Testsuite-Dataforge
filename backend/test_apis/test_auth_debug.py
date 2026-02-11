import pytest

class TestAuthDebug:
    """Test suite for GET /auth-debug/user-id endpoint"""

    def test_get_current_user_id_as_admin(self, admin_client):
        """Test getting user ID when authenticated as an admin"""
        # Note: We assume admin_client already handles the 'Depends(get_current_user)'
        response = admin_client.get("/api/auth-debug/user-id")
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-admin-001"
        assert "message" in data

    def test_get_current_user_id_as_regular_user(self, user_client):
        """Test getting user ID when authenticated as a regular user"""
        response = user_client.get("/api/auth-debug/user-id")
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-user-001"

    def test_get_current_user_id_as_readonly(self, readonly_client):
        """Test getting user ID when authenticated as a readonly user"""
        response = readonly_client.get("/api/auth-debug/user-id")
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-readonly-001"

    def test_get_current_user_id_unauthenticated(self, unauthenticated_client):
        """Test that requests without credentials are rejected with 401"""
        response = unauthenticated_client.get("/api/auth-debug/user-id")
        
        # FastAPI/Depends will automatically return 401 if get_current_user fails
        assert response.status_code == 401