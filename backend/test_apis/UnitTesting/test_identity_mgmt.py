from unittest.mock import AsyncMock

def test_get_my_tenant_info_success(admin_client, mocker, mock_tenant_info, mock_tenant_overview):
    """Test getting tenant info"""
    mocker.patch(
        "app.apis.customer.get_user_tenant_info",
        new_callable=AsyncMock,
        return_value=mock_tenant_info
    )
    
    mocker.patch(
        "app.apis.customer.get_tenant_overview",
        new_callable=AsyncMock,
        return_value=mock_tenant_overview
    )
    
    response = admin_client.get("/api/customer/my-tenant")
    
    assert response.status_code == 200
    data = response.json()
    assert data["tenant"]["name"] == "Innoveria AS"
    assert data["machine_count"] == 5