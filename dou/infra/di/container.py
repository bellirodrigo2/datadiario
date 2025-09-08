from typing import Any

from dependency_injector import containers, providers


class ApplicationContainer(containers.DeclarativeContainer):
    """Application container with proper dependency-injector configuration."""
    
    # Configuration provider
    config = providers.Configuration()
    
    # You can load from various sources:
    # config.from_env()  # From environment variables
    # config.from_yaml("config.yaml")  # From YAML file
    # config.from_ini("config.ini")    # From INI file
    # config.from_dict({"key": "value"})  # From dictionary


class Container:
    """Legacy container wrapper for backward compatibility."""
    _instance = None
    _container = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._container = containers.DynamicContainer()
        return cls._instance

    def provide(self, name: str, provider: providers.Provider[Any]) -> None:
        setattr(self._container, name, provider)

    def inject(self, name: str) -> Any:
        return getattr(self._container, name)()
