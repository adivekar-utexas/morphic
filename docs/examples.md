# Examples

This page provides comprehensive examples demonstrating how to use Morphic in real-world scenarios.

## Basic Examples

### Typed with Default Value Conversion

```python
from morphic import Typed
from typing import List, Dict, Optional, Union
from enum import Enum

# Enum for demonstration
class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

# Typed with comprehensive default value features
class TaskConfig(Typed):
    # Basic type conversion from strings
    max_retries: int = "3"          # String converted to int
    timeout: float = "30.5"         # String converted to float
    enabled: bool = "true"          # String converted to bool

    # String field for demonstration
    category: str = "general"

    # Optional fields
    description: Optional[str] = None

    # Mutable defaults (automatically converted to default_factory)
    tags: List[str] = ["default", "task"]
    metadata: Dict[str, str] = {"created": "auto"}

    # Union types
    identifier: Union[int, str] = "auto-123"  # Tries types in order

    def validate(self):
        if self.max_retries < 0:
            raise ValueError("Retries must be non-negative")
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")

# Hierarchical Typed with nested structures
class DatabaseConfig(Typed):
    host: str = "localhost"
    port: int = "5432"           # String converted to int
    ssl: bool = "true"           # String converted to bool

class ServiceConfig(Typed):
    name: str
    # Nested Typed with dict default (converted automatically)
    database: DatabaseConfig = {
        "host": "prod.db",
        "port": "5433",
        "ssl": "false"
    }
    # List of nested Typeds
    tasks: List[TaskConfig] = [
        {
            "max_retries": "5",
            "timeout": "60.0",
            "category": "high",
            "tags": ["important", "prod"]
        }
    ]

# Usage examples
print("=== Typed Default Value Conversion Demo ===")

# 1. Basic usage with converted defaults
task = TaskConfig()
print(f"Task retries: {task.max_retries} (type: {type(task.max_retries).__name__})")
print(f"Task timeout: {task.timeout} (type: {type(task.timeout).__name__})")
print(f"Task enabled: {task.enabled} (type: {type(task.enabled).__name__})")
print(f"Task category: {task.category} (type: {type(task.category).__name__})")

# 2. Mutable defaults are independent per instance
task1 = TaskConfig()
task2 = TaskConfig()
task1.tags.append("modified")
print(f"Task1 tags: {task1.tags}")
print(f"Task2 tags: {task2.tags}")  # Unchanged - independent copy

# 3. Hierarchical structure with automatic conversion
service = ServiceConfig(name="UserService")
print(f"DB Host: {service.database.host}")
print(f"DB Port: {service.database.port} (type: {type(service.database.port).__name__})")
print(f"DB SSL: {service.database.ssl} (type: {type(service.database.ssl).__name__})")
print(f"Task count: {len(service.tasks)}")
print(f"First task retries: {service.tasks[0].max_retries}")

# 4. from_dict with automatic conversion
external_config = ServiceConfig.from_dict({
    "name": "ExternalService",
    "database": {
        "host": "external.db",
        "port": "3306",    # String converted to int
        "ssl": "true"      # String converted to bool
    },
    "tasks": [
        {
            "max_retries": "10",   # String converted to int
            "timeout": "120.0",    # String converted to float
            "category": "urgent",  # String field
            "enabled": "false"     # String converted to bool
        }
    ]
})

print(f"External DB port: {external_config.database.port}")
print(f"External task category: {external_config.tasks[0].category}")

# 5. Error handling - invalid defaults caught at class definition
try:
    class InvalidConfig(Typed):
        bad_number: int = "not_a_number"  # Raises TypeError immediately

except TypeError as e:
    print(f"Invalid default caught: {e}")

print("=== All Typed features working correctly! ===\n")
```

### Simple Registry Usage

```python
from morphic import Registry
from abc import ABC, abstractmethod

# Base registry class
class Service(Registry, ABC):
    @abstractmethod
    def process(self) -> str:
        pass

# Service classes automatically register when inheriting from Registry
class EmailService(Service):
    def __init__(self, smtp_server: str = "localhost"):
        self.smtp_server = smtp_server

    def process(self) -> str:
        return f"Email service using {self.smtp_server}"

    def send(self, to: str, subject: str, body: str) -> bool:
        print(f"Sending email to {to} via {self.smtp_server}")
        print(f"Subject: {subject}")
        print(f"Body: {body}")
        return True

# Create an instance using the factory
email_service = Service.of("EmailService", smtp_server="mail.example.com")
email_service.send("user@example.com", "Hello", "Welcome to our service!")
```

### AutoEnum Generation

```python
from morphic import Registry, AutoEnum
from abc import ABC, abstractmethod

# Base registry class
class NotificationHandler(Registry, ABC):
    @abstractmethod
    def send(self, message: str) -> None:
        pass

# Handler classes automatically register when inheriting from Registry
class EmailHandler(NotificationHandler):
    def send(self, message: str):
        print(f"Email: {message}")

class SMSHandler(NotificationHandler):
    def send(self, message: str):
        print(f"SMS: {message}")

class PushHandler(NotificationHandler):
    def send(self, message: str):
        print(f"Push notification: {message}")

# Generate enum from registered handlers
HandlerTypes = AutoEnum.create(NotificationHandler)

# Use the enum
for handler_type in HandlerTypes:
    handler = handler_type.value()
    handler.send("Test message")
```

## Intermediate Examples

### Plugin System

```python
from morphic import Registry, AutoEnum, Typed
from abc import ABC, abstractmethod
from typing import Dict, Any, List

# Configuration model with automatic default conversion
class PluginConfig(Typed):
    enabled: bool = "true"      # String converted to bool automatically
    priority: int = "0"         # String converted to int automatically
    settings: Dict[str, Any] = {} # Mutable default automatically handled

    def validate(self):
        if self.priority < 0:
            raise ValueError("Priority must be non-negative")

# Base plugin interface
class Plugin(Registry, ABC):
    def __init__(self, config: PluginConfig):
        self.config = config

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

# Concrete plugins - automatically register when inheriting from Plugin
class LoggingPlugin(Plugin):
    @property
    def name(self) -> str:
        return "Logging Plugin"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if self.config.enabled:
            log_level = self.config.settings.get("level", "INFO")
            print(f"[{log_level}] Processing context: {context}")
        return context

class ValidationPlugin(Plugin):
    @property
    def name(self) -> str:
        return "Validation Plugin"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if self.config.enabled:
            required_fields = self.config.settings.get("required_fields", [])
            for field in required_fields:
                if field not in context:
                    raise ValueError(f"Missing required field: {field}")
            print("Validation passed")
        return context

class TransformPlugin(Plugin):
    @property
    def name(self) -> str:
        return "Transform Plugin"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if self.config.enabled:
            transforms = self.config.settings.get("transforms", {})
            for key, transform_func in transforms.items():
                if key in context:
                    context[key] = transform_func(context[key])
            print("Data transformed")
        return context

# Plugin manager
class PluginManager:
    def __init__(self):
        self.plugins: List[Plugin] = []
        self.plugin_enum = AutoEnum.create(Plugin)

    def register_plugin(self, plugin_name: str, config: PluginConfig):
        """Register a plugin with configuration"""
        plugin = Plugin.of(plugin_name, config=config)
        self.plugins.append(plugin)

    def execute_pipeline(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute all plugins in priority order"""
        # Sort by priority (higher priority first)
        sorted_plugins = sorted(self.plugins, key=lambda p: p.config.priority, reverse=True)

        result = context.copy()
        for plugin in sorted_plugins:
            if plugin.config.enabled:
                print(f"Executing {plugin.name}")
                result = plugin.execute(result)
        return result

    def list_available_plugins(self) -> List[str]:
        """List all available plugin types"""
        return [member.name for member in self.plugin_enum]

# Usage example
manager = PluginManager()

# Configure and register plugins
logging_config = PluginConfig(
    enabled=True,
    priority=1,
    settings={"level": "DEBUG"}
)

validation_config = PluginConfig(
    enabled=True,
    priority=3,
    settings={"required_fields": ["user_id", "action"]}
)

transform_config = PluginConfig(
    enabled=True,
    priority=2,
    settings={"transforms": {"action": str.upper}}
)

manager.register_plugin("LoggingPlugin", logging_config)
manager.register_plugin("ValidationPlugin", validation_config)
manager.register_plugin("TransformPlugin", transform_config)

# Execute the pipeline
test_context = {
    "user_id": "12345",
    "action": "login",
    "timestamp": "2023-10-01T10:00:00Z"
}

try:
    result = manager.execute_pipeline(test_context)
    print(f"Final result: {result}")
except ValueError as e:
    print(f"Pipeline error: {e}")
```

### Configuration Management System

```python
from morphic import Registry, Typed
from typing import Optional, Dict, Any, Union
import json
import os
from pathlib import Path

# Configuration models with automatic default value conversion
class DatabaseConfig(Typed):
    host: str
    port: int = "5432"        # String converted to int
    username: str
    password: str
    database: str
    pool_size: int = "10"     # String converted to int
    ssl: bool = "true"        # String converted to bool

    def validate(self):
        if not self.username or not self.password:
            raise ValueError("Database credentials are required")
        if self.port < 1 or self.port > 65535:
            raise ValueError("Port must be between 1 and 65535")

class RedisConfig(Typed):
    host: str = "localhost"
    port: int = "6379"        # String converted to int
    password: Optional[str] = None
    db: int = "0"             # String converted to int
    ttl: int = "3600"         # String converted to int

    def validate(self):
        if self.port < 1 or self.port > 65535:
            raise ValueError("Port must be between 1 and 65535")
        if self.ttl < 0:
            raise ValueError("TTL must be non-negative")

class LoggingConfig(Typed):
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    handlers: List[str] = ["console"]  # Mutable default automatically handled

    def validate(self):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.level not in valid_levels:
            raise ValueError(f"Level must be one of {valid_levels}")

# Configuration loaders
class ConfigLoader(Registry, ABC):
    @abstractmethod
    def load(self, path: str) -> Dict[str, Any]:
        pass

# Config loaders automatically register when inheriting from ConfigLoader
class JSONConfigLoader(ConfigLoader):
    def load(self, path: str) -> Dict[str, Any]:
        with open(path, 'r') as f:
            return json.load(f)

class EnvConfigLoader(ConfigLoader):
    def load(self, path: str) -> Dict[str, Any]:
        """Load from environment variables with optional .env file"""
        config = {}

        # Load from .env file if it exists
        if Path(path).exists():
            with open(path, 'r') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value

        # Common configuration from environment
        config['database'] = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', '5432')),
            'username': os.getenv('DB_USER', ''),
            'password': os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME', ''),
            'pool_size': int(os.getenv('DB_POOL_SIZE', '10')),
            'ssl': os.getenv('DB_SSL', 'true').lower() == 'true'
        }

        config['redis'] = {
            'host': os.getenv('REDIS_HOST', 'localhost'),
            'port': int(os.getenv('REDIS_PORT', '6379')),
            'password': os.getenv('REDIS_PASSWORD'),
            'db': int(os.getenv('REDIS_DB', '0')),
            'ttl': int(os.getenv('REDIS_TTL', '3600'))
        }

        config['logging'] = {
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'format': os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            'handlers': os.getenv('LOG_HANDLERS', 'console').split(',')
        }

        return config

# Configuration manager
class ConfigManager:
    def __init__(self):
        self.configs: Dict[str, Union[DatabaseConfig, RedisConfig, LoggingConfig]] = {}

    def load_from_file(self, file_path: str, loader_type: str = "JSONConfigLoader"):
        """Load configuration from file using specified loader"""
        loader = ConfigLoader.of(loader_type)
        raw_config = loader.load(file_path)

        # Create typed configuration objects with automatic conversion
        if 'database' in raw_config:
            # from_dict automatically converts string values to appropriate types
            self.configs['database'] = DatabaseConfig.from_dict(raw_config['database'])

        if 'redis' in raw_config:
            self.configs['redis'] = RedisConfig.from_dict(raw_config['redis'])

        if 'logging' in raw_config:
            self.configs['logging'] = LoggingConfig.from_dict(raw_config['logging'])

    def get_database_config(self) -> DatabaseConfig:
        return self.configs.get('database')

    def get_redis_config(self) -> RedisConfig:
        return self.configs.get('redis')

    def get_logging_config(self) -> LoggingConfig:
        return self.configs.get('logging')

    def validate_all(self) -> bool:
        """Validate all loaded configurations"""
        try:
            if 'database' in self.configs:
                db_config = self.configs['database']
                if not db_config.username or not db_config.password:
                    raise ValueError("Database credentials required")

            if 'redis' in self.configs:
                redis_config = self.configs['redis']
                if redis_config.port < 1 or redis_config.port > 65535:
                    raise ValueError("Invalid Redis port")

            if 'logging' in self.configs:
                logging_config = self.configs['logging']
                valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
                if logging_config.level not in valid_levels:
                    raise ValueError(f"Invalid log level: {logging_config.level}")

            return True
        except Exception as e:
            print(f"Configuration validation failed: {e}")
            return False

# Usage example
config_manager = ConfigManager()

# Example JSON configuration file content:
json_config = {
    "database": {
        "host": "db.example.com",
        "port": 5432,
        "username": "app_user",
        "password": "secure_password",
        "database": "production_db",
        "pool_size": 20,
        "ssl": True
    },
    "redis": {
        "host": "cache.example.com",
        "port": 6379,
        "password": "redis_password",
        "db": 1,
        "ttl": 7200
    },
    "logging": {
        "level": "INFO",
        "handlers": ["console", "file"]
    }
}

# Save example config (in real usage, this would be an actual file)
with open("config.json", "w") as f:
    json.dump(json_config, f, indent=2)

# Load configuration
config_manager.load_from_file("config.json", "JSONConfigLoader")

if config_manager.validate_all():
    db_config = config_manager.get_database_config()
    redis_config = config_manager.get_redis_config()
    logging_config = config_manager.get_logging_config()

    print(f"Database: {db_config.host}:{db_config.port}/{db_config.database}")
    print(f"Redis: {redis_config.host}:{redis_config.port} (TTL: {redis_config.ttl}s)")
    print(f"Logging: {logging_config.level} level with {len(logging_config.handlers)} handlers")

# Clean up example file
os.remove("config.json")
```

## Advanced Examples

### Event-Driven Architecture

```python
from morphic import Registry, AutoEnum, Typed
from typing import Any, Dict, List, Callable
from datetime import datetime
import asyncio

# Event model
class Event(Typed):
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime = datetime.now()
    source: str = "system"

# Event handler interface
class EventHandler(Registry, ABC):
    @abstractmethod
    def can_handle(self, event: Event) -> bool:
        pass

    @abstractmethod
    async def handle(self, event: Event) -> None:
        pass

# Concrete event handlers - automatically register when inheriting from EventHandler
class UserEventHandler(EventHandler):
    def can_handle(self, event: Event) -> bool:
        return event.event_type.startswith("user.")

    async def handle(self, event: Event) -> None:
        print(f"Handling user event: {event.event_type}")
        # Simulate async processing
        await asyncio.sleep(0.1)
        print(f"User event processed: {event.data}")

class OrderEventHandler(EventHandler):
    def can_handle(self, event: Event) -> bool:
        return event.event_type.startswith("order.")

    async def handle(self, event: Event) -> None:
        print(f"Handling order event: {event.event_type}")
        await asyncio.sleep(0.2)
        print(f"Order event processed: {event.data}")

class PaymentEventHandler(EventHandler):
    def can_handle(self, event: Event) -> bool:
        return event.event_type.startswith("payment.")

    async def handle(self, event: Event) -> None:
        print(f"Handling payment event: {event.event_type}")
        await asyncio.sleep(0.15)
        print(f"Payment event processed: {event.data}")

# Event bus
class EventBus:
    def __init__(self):
        self.handlers: List[EventHandler] = []
        self.handler_enum = AutoEnum.create(EventHandler)

    def register_handler(self, handler_name: str):
        """Register an event handler"""
        handler = EventHandler.of(handler_name)
        self.handlers.append(handler)

    def register_all_handlers(self):
        """Register all available event handlers"""
        for handler_type in self.handler_enum:
            handler = handler_type.value()
            self.handlers.append(handler)

    async def publish(self, event: Event):
        """Publish an event to all capable handlers"""
        print(f"Publishing event: {event.event_type}")

        # Find all handlers that can handle this event
        capable_handlers = [h for h in self.handlers if h.can_handle(event)]

        if not capable_handlers:
            print(f"No handlers found for event type: {event.event_type}")
            return

        # Handle events concurrently
        tasks = [handler.handle(event) for handler in capable_handlers]
        await asyncio.gather(*tasks)

        print(f"Event {event.event_type} processing completed")

# Usage example
async def main():
    event_bus = EventBus()

    # Register specific handlers
    event_bus.register_handler("UserEventHandler")
    event_bus.register_handler("OrderEventHandler")
    event_bus.register_handler("PaymentEventHandler")

    # Create and publish events
    events = [
        Event(event_type="user.registered", data={"user_id": "123", "email": "user@example.com"}),
        Event(event_type="order.created", data={"order_id": "456", "total": 99.99}),
        Event(event_type="payment.processed", data={"payment_id": "789", "amount": 99.99}),
        Event(event_type="system.maintenance", data={"message": "Scheduled maintenance"})
    ]

    for event in events:
        await event_bus.publish(event)
        print("---")

# Run the example
if __name__ == "__main__":
    asyncio.run(main())
```

### Factory Pattern with Validation

```python
from morphic import Registry, Typed, AutoEnum
from typing import Optional, Dict, Any, Protocol
from abc import ABC, abstractmethod

# Connection configuration models
class DatabaseConnectionConfig(Typed):
    host: str
    port: int
    username: str
    password: str
    database: str
    timeout: float = 30.0

    def validate(self):
        if self.port < 1 or self.port > 65535:
            raise ValueError("Port must be between 1 and 65535")

class APIConnectionConfig(Typed):
    base_url: str
    api_key: str
    timeout: float = 30.0
    retries: int = 3

    def validate(self):
        if not self.base_url.startswith(("http://", "https://")):
            raise ValueError("Base URL must start with http:// or https://")

# Connection interface
class Connection(Protocol):
    def connect(self) -> bool:
        ...

    def disconnect(self) -> None:
        ...

    def is_connected(self) -> bool:
        ...

# Base connection class
class BaseConnection(Registry, ABC):
    def __init__(self, config: Typed):
        self.config = config
        self._connected = False

    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    def is_connected(self) -> bool:
        return self._connected

# Concrete connection implementations - automatically register when inheriting from BaseConnection
class PostgreSQLConnection(BaseConnection):
    def __init__(self, config: DatabaseConnectionConfig):
        super().__init__(config)

    def connect(self) -> bool:
        print(f"Connecting to PostgreSQL at {self.config.host}:{self.config.port}")
        # Simulate connection
        self._connected = True
        return True

    def disconnect(self) -> None:
        print("Disconnecting from PostgreSQL")
        self._connected = False

class MySQLConnection(BaseConnection):
    def __init__(self, config: DatabaseConnectionConfig):
        super().__init__(config)

    def connect(self) -> bool:
        print(f"Connecting to MySQL at {self.config.host}:{self.config.port}")
        self._connected = True
        return True

    def disconnect(self) -> None:
        print("Disconnecting from MySQL")
        self._connected = False

class RESTAPIConnection(BaseConnection):
    def __init__(self, config: APIConnectionConfig):
        super().__init__(config)

    def connect(self) -> bool:
        print(f"Connecting to REST API at {self.config.base_url}")
        self._connected = True
        return True

    def disconnect(self) -> None:
        print("Disconnecting from REST API")
        self._connected = False

# Connection factory with validation
class ConnectionFactory:
    _config_map = {
        "PostgreSQLConnection": DatabaseConnectionConfig,
        "MySQLConnection": DatabaseConnectionConfig,
        "RESTAPIConnection": APIConnectionConfig
    }

    @classmethod
    def create_connection(
        cls,
        connection_type: str,
        config_data: Dict[str, Any]
    ) -> BaseConnection:
        """Create a connection with validated configuration"""

        # Get the appropriate config class
        config_class = cls._config_map.get(connection_type)
        if not config_class:
            available_types = list(cls._config_map.keys())
            raise ValueError(f"Unknown connection type: {connection_type}. "
                           f"Available types: {available_types}")

        # Validate and create configuration
        try:
            config = config_class(**config_data)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid configuration for {connection_type}: {e}")

        # Create the connection instance
        return BaseConnection.of(connection_type, config=config)

    @classmethod
    def get_available_types(cls) -> List[str]:
        """Get all available connection types"""
        return list(cls._config_map.keys())

    @classmethod
    def get_config_template(cls, connection_type: str) -> Dict[str, Any]:
        """Get a configuration template for a connection type"""
        config_class = cls._config_map.get(connection_type)
        if not config_class:
            raise ValueError(f"Unknown connection type: {connection_type}")

        # Get field annotations to create template
        annotations = getattr(config_class, "__annotations__", {})
        template = {}

        for field_name, field_type in annotations.items():
            # Create example values based on type
            if field_type == str:
                template[field_name] = f"example_{field_name}"
            elif field_type == int:
                template[field_name] = 0
            elif field_type == float:
                template[field_name] = 0.0
            elif field_type == bool:
                template[field_name] = True
            else:
                template[field_name] = None

        return template

# Connection manager
class ConnectionManager:
    def __init__(self):
        self.connections: Dict[str, BaseConnection] = {}

    def add_connection(self, name: str, connection_type: str, config_data: Dict[str, Any]):
        """Add a connection to the manager"""
        connection = ConnectionFactory.create_connection(connection_type, config_data)
        self.connections[name] = connection

    def connect_all(self):
        """Connect all managed connections"""
        for name, connection in self.connections.items():
            if connection.connect():
                print(f"Successfully connected: {name}")
            else:
                print(f"Failed to connect: {name}")

    def disconnect_all(self):
        """Disconnect all connections"""
        for name, connection in self.connections.items():
            connection.disconnect()
            print(f"Disconnected: {name}")

    def get_connection_status(self) -> Dict[str, bool]:
        """Get connection status for all connections"""
        return {name: conn.is_connected() for name, conn in self.connections.items()}

# Usage example
def main():
    factory = ConnectionFactory()

    # Show available connection types
    print("Available connection types:")
    for conn_type in factory.get_available_types():
        print(f"  - {conn_type}")

    print("\nConfiguration templates:")
    for conn_type in factory.get_available_types():
        template = factory.get_config_template(conn_type)
        print(f"  {conn_type}: {template}")

    # Create connection manager
    manager = ConnectionManager()

    # Add database connections
    try:
        manager.add_connection("primary_db", "PostgreSQLConnection", {
            "host": "db1.example.com",
            "port": 5432,
            "username": "app_user",
            "password": "secure_password",
            "database": "production_db",
            "timeout": 30.0
        })

        manager.add_connection("analytics_db", "MySQLConnection", {
            "host": "analytics.example.com",
            "port": 3306,
            "username": "analytics_user",
            "password": "analytics_password",
            "database": "analytics_db",
            "timeout": 45.0
        })

        manager.add_connection("api_service", "RESTAPIConnection", {
            "base_url": "https://api.example.com",
            "api_key": "your-api-key-here",
            "timeout": 60.0,
            "retries": 5
        })

        print("\nConnecting to all services...")
        manager.connect_all()

        print("\nConnection status:")
        status = manager.get_connection_status()
        for name, connected in status.items():
            print(f"  {name}: {'Connected' if connected else 'Disconnected'}")

        print("\nDisconnecting all services...")
        manager.disconnect_all()

    except ValueError as e:
        print(f"Configuration error: {e}")

if __name__ == "__main__":
    main()
```

These examples demonstrate the power and flexibility of Morphic for building robust, maintainable Python applications with dynamic class management, type safety, and clean architectural patterns.