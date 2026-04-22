import json
import pytest
from pathlib import Path
from app.internal.config import Config
from app.internal.pathutils import (
    src_path, read_router_config, find_submodules, RouterConfigs
)


class TestSrcPath:
    def test_src_path_returns_config_directory(self):
        cfg = Config(DEVX_BACKEND_DIR="/test/backend")
        
        result = src_path(cfg)
        
        assert result == Path("/test/backend")


class TestReadRouterConfig:
    def test_returns_none_when_file_does_not_exist(self, tmp_path):
        cfg = Config(DEVX_BACKEND_DIR=str(tmp_path))
        
        result = read_router_config(cfg)
        
        assert result is None

    def test_parses_router_config_from_file(self, tmp_path):
        config_content = {
            "routers": {
                "admin": {"disableAuth": False},
                "public": {"disableAuth": True}
            }
        }
        config_file = tmp_path / "routers.json"
        config_file.write_text(json.dumps(config_content))
        
        cfg = Config(DEVX_BACKEND_DIR=str(tmp_path))
        result = read_router_config(cfg)
        
        assert isinstance(result, RouterConfigs)
        assert "admin" in result.routers
        assert result.routers["admin"].disableAuth is False


class TestFindSubmodules:
    def test_find_submodules_old_pattern(self, tmp_path):
        # Old pattern: app/apis/{name}/__init__.py
        backend_dir = tmp_path / "backend"
        backend_dir.mkdir()
        apis_dir = backend_dir / "app" / "apis"
        apis_dir.mkdir(parents=True)
        
        (apis_dir / "users").mkdir()
        (apis_dir / "users" / "__init__.py").write_text("")
        (apis_dir / "products").mkdir()
        (apis_dir / "products" / "__init__.py").write_text("")
        
        cfg = Config(DEVX_BACKEND_DIR=str(backend_dir), DISABLE_API_AS_INIT_PY=False)
        module_prefix, submodules = find_submodules(cfg)
        
        assert module_prefix == "app.apis."
        assert set(submodules) == {"users", "products"}

    def test_find_submodules_new_pattern(self, tmp_path):
        # New pattern: app/apis/{name}.py
        backend_dir = tmp_path / "backend"
        backend_dir.mkdir()
        apis_dir = backend_dir / "app" / "apis"
        apis_dir.mkdir(parents=True)
        
        (apis_dir / "__init__.py").write_text("")
        (apis_dir / "users.py").write_text("")
        (apis_dir / "products.py").write_text("")
        
        cfg = Config(DEVX_BACKEND_DIR=str(backend_dir), DISABLE_API_AS_INIT_PY=True)
        module_prefix, submodules = find_submodules(cfg)
        
        assert module_prefix == "app.apis."
        assert set(submodules) == {"users", "products"}
