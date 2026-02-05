# test_auth_endpoints.py
import pytest


def test_auth_debug_as_admin(client, auth_headers):
    """Test auth debug endpoint with default admin user"""
    response = client.get("/api/auth-debug/user-id", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "test-admin-001"


def test_auth_debug_as_user(user_client, auth_headers):
    """Test auth debug endpoint with regular user role"""
    response = user_client.get("/api/auth-debug/user-id", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "test-user-001"


def test_auth_debug_as_readonly(readonly_client, auth_headers):
    """Test auth debug endpoint with readonly role"""
    response = readonly_client.get("/api/auth-debug/user-id", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "test-readonly-001"


def test_auth_debug_unauthenticated(unauthenticated_client):
    """Test that unauthenticated requests are rejected"""
    response = unauthenticated_client.get("/api/auth-debug/user-id")
    
    assert response.status_code == 401