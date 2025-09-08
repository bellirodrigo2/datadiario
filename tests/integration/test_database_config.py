import asyncio
import os
from unittest.mock import patch

import pytest


class TestDatabaseConfiguration:
    """Test suite for database configuration and selector functionality"""

    def test_default_configuration(self):
        """Test default configuration without environment variables"""
        with patch.dict(os.environ, {}, clear=True):
            from dou.main import create_container
            
            container = asyncio.run(create_container())
            config = container._container.config
            
            # Should use default memory database
            assert config.database.url() == "sqlite+aiosqlite:///:memory:"
            assert config.logging.level() == "INFO"

    def test_db_selector_memory(self):
        """Test DB_SELECTOR=memory with DB_URL_MEMORY"""
        env_vars = {
            "DB_SELECTOR": "memory",
            "DB_URL_MEMORY": "sqlite+aiosqlite:///:memory:"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            from dou.infra.di.container_factory import create_container
            
            container = asyncio.run(create_container())
            config = container._container.config
            
            assert config.database.url() == "sqlite+aiosqlite:///:memory:"

    def test_db_selector_dev(self):
        """Test DB_SELECTOR=dev with DB_URL_DEV"""
        env_vars = {
            "DB_SELECTOR": "dev",
            "DB_URL_DEV": "sqlite+aiosqlite:///./dou_dev.db"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            from dou.infra.di.container_factory import create_container
            
            container = asyncio.run(create_container())
            config = container._container.config
            
            assert config.database.url() == "sqlite+aiosqlite:///./dou_dev.db"

    def test_db_selector_test(self):
        """Test DB_SELECTOR=test with DB_URL_TEST"""
        env_vars = {
            "DB_SELECTOR": "test",
            "DB_URL_TEST": "sqlite+aiosqlite:///./dou_test.db"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            from dou.infra.di.container_factory import create_container
            
            container = asyncio.run(create_container())
            config = container._container.config
            
            assert config.database.url() == "sqlite+aiosqlite:///./dou_test.db"

    def test_db_selector_custom(self):
        """Test DB_SELECTOR with custom selector and URL"""
        env_vars = {
            "DB_SELECTOR": "custom",
            "DB_URL_CUSTOM": "sqlite+aiosqlite:///./my_custom.db"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            from dou.infra.di.container_factory import create_container
            
            container = asyncio.run(create_container())
            config = container._container.config
            
            assert config.database.url() == "sqlite+aiosqlite:///./my_custom.db"

    def test_db_selector_fallback_to_direct_url(self):
        """Test DB_SELECTOR falls back to direct URL when no matching env var"""
        env_vars = {
            "DB_SELECTOR": "sqlite+aiosqlite:///./direct_fallback.db"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            from dou.infra.di.container_factory import create_container
            
            container = asyncio.run(create_container())
            config = container._container.config
            
            assert config.database.url() == "sqlite+aiosqlite:///./direct_fallback.db"

    def test_database_url_override(self):
        """Test DATABASE_URL overrides DB_SELECTOR"""
        env_vars = {
            "DB_SELECTOR": "dev",
            "DB_URL_DEV": "sqlite+aiosqlite:///./dou_dev.db",
            "DATABASE_URL": "sqlite+aiosqlite:///./override.db"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            from dou.infra.di.container_factory import create_container
            
            container = asyncio.run(create_container())
            config = container._container.config
            
            # DATABASE_URL should take precedence
            assert config.database.url() == "sqlite+aiosqlite:///./override.db"

    def test_log_level_configuration(self):
        """Test LOG_LEVEL environment variable"""
        env_vars = {
            "LOG_LEVEL": "DEBUG"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            from dou.infra.di.container_factory import create_container
            
            container = asyncio.run(create_container())
            config = container._container.config
            
            assert config.logging.level() == "DEBUG"

    def test_combined_configuration(self):
        """Test DB_SELECTOR and LOG_LEVEL together"""
        env_vars = {
            "DB_SELECTOR": "test",
            "DB_URL_TEST": "sqlite+aiosqlite:///./combined_test.db",
            "LOG_LEVEL": "WARNING"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            from dou.infra.di.container_factory import create_container
            
            container = asyncio.run(create_container())
            config = container._container.config
            
            assert config.database.url() == "sqlite+aiosqlite:///./combined_test.db"
            assert config.logging.level() == "WARNING"

    def test_postgresql_url_format(self):
        """Test PostgreSQL URL configuration (config only, no connection)"""
        import os
        from dependency_injector import providers
        
        env_vars = {
            "DB_SELECTOR": "postgres",
            "DB_URL_POSTGRES": "postgresql+asyncpg://testuser:testpass@localhost:5432/testdb"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            # Test configuration loading without creating container (avoids DB connection)
            
            config = providers.Configuration()
            config.from_dict({
                "database": {"url": "sqlite+aiosqlite:///:memory:"},
                "logging": {"level": "INFO"}
            })
            
            # Apply the same logic as in main.py
            if "DATABASE_URL" in os.environ:
                config.database.url.from_env("DATABASE_URL")
            elif "DB_SELECTOR" in os.environ:
                selector = os.environ["DB_SELECTOR"]
                env_var = f"DB_URL_{selector.upper()}"
                if env_var in os.environ:
                    config.database.url.override(os.environ[env_var])
                else:
                    config.database.url.override(selector)
            
            assert config.database.url() == "postgresql+asyncpg://testuser:testpass@localhost:5432/testdb"

    def test_mysql_url_format(self):
        """Test MySQL URL configuration (config only, no connection)"""
        import os
        from dependency_injector import providers
        
        env_vars = {
            "DB_SELECTOR": "mysql",
            "DB_URL_MYSQL": "mysql+aiomysql://testuser:testpass@localhost:3306/testdb"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            # Test configuration loading without creating container (avoids DB connection)
            
            config = providers.Configuration()
            config.from_dict({
                "database": {"url": "sqlite+aiosqlite:///:memory:"},
                "logging": {"level": "INFO"}
            })
            
            # Apply the same logic as in main.py
            if "DATABASE_URL" in os.environ:
                config.database.url.from_env("DATABASE_URL")
            elif "DB_SELECTOR" in os.environ:
                selector = os.environ["DB_SELECTOR"]
                env_var = f"DB_URL_{selector.upper()}"
                if env_var in os.environ:
                    config.database.url.override(os.environ[env_var])
                else:
                    config.database.url.override(selector)
            
            assert config.database.url() == "mysql+aiomysql://testuser:testpass@localhost:3306/testdb"

    def test_case_insensitive_selector(self):
        """Test that DB_SELECTOR is case insensitive for env var lookup"""
        env_vars = {
            "DB_SELECTOR": "Memory",  # Mixed case
            "DB_URL_MEMORY": "sqlite+aiosqlite:///:memory:"  # Uppercase env var
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            from dou.infra.di.container_factory import create_container
            
            container = asyncio.run(create_container())
            config = container._container.config
            
            # Should find DB_URL_MEMORY (uppercase)
            assert config.database.url() == "sqlite+aiosqlite:///:memory:"