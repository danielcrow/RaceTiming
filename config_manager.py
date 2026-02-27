"""
System Configuration Manager
Manages application configuration stored in database
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from database import get_session, engine
from datetime import datetime
import json
import os

Base = declarative_base()


class SystemConfig(Base):
    """System configuration settings"""
    __tablename__ = 'system_config'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    description = Column(Text)
    category = Column(String(50))  # database, webhook, llrp, general
    is_sensitive = Column(Boolean, default=False)  # Hide value in UI
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String(100), default='system')


class ConfigManager:
    """Manages system configuration"""
    
    # Default configuration values
    DEFAULTS = {
        # Database Configuration
        'db_host': {
            'value': 'localhost',
            'description': 'PostgreSQL database host',
            'category': 'database',
            'is_sensitive': False
        },
        'db_port': {
            'value': '5432',
            'description': 'PostgreSQL database port',
            'category': 'database',
            'is_sensitive': False
        },
        'db_name': {
            'value': 'race_timing',
            'description': 'PostgreSQL database name',
            'category': 'database',
            'is_sensitive': False
        },
        'db_user': {
            'value': 'postgres',
            'description': 'PostgreSQL database user',
            'category': 'database',
            'is_sensitive': False
        },
        'db_password': {
            'value': '',
            'description': 'PostgreSQL database password',
            'category': 'database',
            'is_sensitive': True
        },
        
        # Webhook Configuration
        'results_publish_url': {
            'value': 'http://localhost:5002',
            'description': 'URL of the public results site',
            'category': 'webhook',
            'is_sensitive': False
        },
        'webhook_secret': {
            'value': 'change-this-secret-key',
            'description': 'Webhook authentication secret',
            'category': 'webhook',
            'is_sensitive': True
        },
        'webhook_timeout': {
            'value': '10',
            'description': 'Webhook request timeout in seconds',
            'category': 'webhook',
            'is_sensitive': False
        },
        'webhook_retry_attempts': {
            'value': '3',
            'description': 'Number of retry attempts for failed webhooks',
            'category': 'webhook',
            'is_sensitive': False
        },
        
        # LLRP Configuration
        'llrp_default_port': {
            'value': '5084',
            'description': 'Default LLRP reader port',
            'category': 'llrp',
            'is_sensitive': False
        },
        'llrp_cooldown_seconds': {
            'value': '5',
            'description': 'Default cooldown between tag reads (seconds)',
            'category': 'llrp',
            'is_sensitive': False
        },
        'llrp_connection_timeout': {
            'value': '30',
            'description': 'LLRP connection timeout (seconds)',
            'category': 'llrp',
            'is_sensitive': False
        },
        
        # General Configuration
        'app_name': {
            'value': 'Race Timing System',
            'description': 'Application name',
            'category': 'general',
            'is_sensitive': False
        },
        'app_timezone': {
            'value': 'UTC',
            'description': 'Application timezone',
            'category': 'general',
            'is_sensitive': False
        },
        'enable_auto_publish': {
            'value': 'false',
            'description': 'Automatically publish results after race completion',
            'category': 'general',
            'is_sensitive': False
        }
    }
    
    def __init__(self):
        self.session = get_session()
        self._ensure_table_exists()
        self._initialize_defaults()
    
    def _ensure_table_exists(self):
        """Create config table if it doesn't exist"""
        try:
            Base.metadata.create_all(engine)
        except Exception as e:
            print(f"Error creating config table: {e}")
    
    def _initialize_defaults(self):
        """Initialize default configuration values if they don't exist"""
        for key, config in self.DEFAULTS.items():
            existing = self.session.query(SystemConfig).filter_by(key=key).first()
            if not existing:
                # Check if environment variable exists
                env_key = key.upper()
                env_value = os.getenv(env_key)
                
                config_entry = SystemConfig(
                    key=key,
                    value=env_value if env_value else config['value'],
                    description=config['description'],
                    category=config['category'],
                    is_sensitive=config['is_sensitive']
                )
                self.session.add(config_entry)
        
        try:
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            print(f"Error initializing config: {e}")
    
    def get(self, key, default=None):
        """Get configuration value"""
        config = self.session.query(SystemConfig).filter_by(key=key).first()
        if config:
            return config.value
        return default
    
    def get_int(self, key, default=0):
        """Get configuration value as integer"""
        value = self.get(key)
        try:
            return int(value) if value else default
        except (ValueError, TypeError):
            return default
    
    def get_bool(self, key, default=False):
        """Get configuration value as boolean"""
        value = self.get(key)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')
    
    def set(self, key, value, updated_by='admin'):
        """Set configuration value"""
        config = self.session.query(SystemConfig).filter_by(key=key).first()
        if config:
            config.value = str(value)
            config.updated_at = datetime.utcnow()
            config.updated_by = updated_by
        else:
            # Create new config entry
            config = SystemConfig(
                key=key,
                value=str(value),
                updated_by=updated_by
            )
            self.session.add(config)
        
        try:
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            print(f"Error setting config {key}: {e}")
            return False
    
    def get_all(self, category=None):
        """Get all configuration values, optionally filtered by category"""
        query = self.session.query(SystemConfig)
        if category:
            query = query.filter_by(category=category)
        
        configs = query.all()
        return [{
            'key': c.key,
            'value': '********' if c.is_sensitive else c.value,
            'actual_value': c.value,  # For internal use
            'description': c.description,
            'category': c.category,
            'is_sensitive': c.is_sensitive,
            'updated_at': c.updated_at.isoformat() if c.updated_at else None,
            'updated_by': c.updated_by
        } for c in configs]
    
    def get_by_category(self):
        """Get all configurations grouped by category"""
        configs = self.get_all()
        grouped = {}
        for config in configs:
            category = config['category'] or 'general'
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(config)
        return grouped
    
    def update_multiple(self, updates, updated_by='admin'):
        """Update multiple configuration values at once"""
        success_count = 0
        errors = []
        
        for key, value in updates.items():
            if self.set(key, value, updated_by):
                success_count += 1
            else:
                errors.append(key)
        
        return {
            'success': success_count,
            'errors': errors,
            'total': len(updates)
        }
    
    def reset_to_defaults(self, category=None):
        """Reset configuration to default values"""
        defaults_to_reset = self.DEFAULTS
        if category:
            defaults_to_reset = {k: v for k, v in self.DEFAULTS.items() 
                               if v['category'] == category}
        
        for key, config in defaults_to_reset.items():
            self.set(key, config['value'], 'system')
        
        return len(defaults_to_reset)
    
    def export_config(self, include_sensitive=False):
        """Export configuration as JSON"""
        configs = self.get_all()
        export_data = {}
        
        for config in configs:
            if config['is_sensitive'] and not include_sensitive:
                continue
            export_data[config['key']] = {
                'value': config['actual_value'] if include_sensitive else config['value'],
                'description': config['description'],
                'category': config['category']
            }
        
        return json.dumps(export_data, indent=2)
    
    def import_config(self, json_data, updated_by='admin'):
        """Import configuration from JSON"""
        try:
            data = json.loads(json_data) if isinstance(json_data, str) else json_data
            updates = {key: value['value'] for key, value in data.items()}
            return self.update_multiple(updates, updated_by)
        except Exception as e:
            return {'success': 0, 'errors': [str(e)], 'total': 0}
    
    def close(self):
        """Close database session"""
        self.session.close()


# Singleton instance
_config_manager = None

def get_config_manager():
    """Get or create ConfigManager singleton"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

# Made with Bob
