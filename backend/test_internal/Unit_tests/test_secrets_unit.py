import pytest
from unittest.mock import MagicMock, patch
import httpx

from app.internal.secrets import (
    fetch_deployment_secrets_v2,
    fetch_and_inject_secrets,
)


class TestFetchDeploymentSecretsV2:
    def test_retries_on_failure_then_succeeds(self):
        import base64
        encoded = base64.urlsafe_b64encode(b"value").decode("utf-8")

        fail_response = MagicMock()
        fail_response.status_code = 500

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "secrets": [{"name": "KEY", "valueBase64": encoded}]
        }

        mock_client = MagicMock()
        mock_client.get.side_effect = [fail_response, fail_response, success_response]

        with patch("app.internal.secrets.get_dbapi_client", return_value=mock_client):
            with patch("time.sleep"):
                result = fetch_deployment_secrets_v2("deployment-123")

        assert result == {"KEY": "value"}
        assert mock_client.get.call_count == 3

    #important to test retry limits since they usually come with bugs
    def test_gives_up_after_5_attempts(self):
        fail_response = MagicMock()
        fail_response.status_code = 500
        fail_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=fail_response
        )

        mock_client = MagicMock()
        mock_client.get.return_value = fail_response

        with patch("app.internal.secrets.get_dbapi_client", return_value=mock_client):
            with patch("time.sleep"):
                with pytest.raises(httpx.HTTPStatusError):
                    fetch_deployment_secrets_v2("deployment-123")

        assert mock_client.get.call_count == 5


class TestFetchAndInjectSecrets:
    def test_raises_on_unexpected_service_type(self, monkeypatch):
        monkeypatch.setenv("DATABUTTON_SERVICE_TYPE", "unexpected")
        with pytest.raises(RuntimeError, match="Unexpected environment"):
            fetch_and_inject_secrets()

    def test_raises_for_undeployed_prodx(self, monkeypatch):
        monkeypatch.setenv("DATABUTTON_SERVICE_TYPE", "prodx")
        monkeypatch.delenv("DATABUTTON_DEPLOYMENT_ID", raising=False)
        with pytest.raises(RuntimeError, match="Unexpected undeployed prodx app"):
            fetch_and_inject_secrets()