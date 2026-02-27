# System Configuration Guide

## Overview

The Race Timing System now includes a comprehensive web-based configuration interface that allows administrators to manage system settings without editing configuration files or environment variables directly.

## Accessing the Configuration Screen

1. Start the Race Timing System
2. Navigate to: **http://localhost:5001/system-config**
3. Or click the **⚙️ Config** link in the navigation menu

## Configuration Categories

### 🗄️ Database Configuration

Manage PostgreSQL database connection settings:

- **Database Host**: PostgreSQL server hostname or IP address (default: localhost)
- **Database Port**: PostgreSQL server port (default: 5432)
- **Database Name**: Name of the database (default: race_timing)
- **Database User**: Database username (default: postgres)
- **Database Password**: Database password (stored securely, masked in UI)

**Actions:**
- **Save Database Settings**: Apply changes to database configuration
- **Test Connection**: Verify database connectivity with current settings
- **Reset to Defaults**: Restore default database settings

### 🔗 Webhook Configuration

Configure results publishing to the public results site:

- **Results Site URL**: URL of the public results website (default: http://localhost:5002)
- **Webhook Secret**: Authentication secret for webhook requests (must match results site)
- **Request Timeout**: Timeout for webhook HTTP requests in seconds (default: 10)
- **Retry Attempts**: Number of retry attempts for failed webhooks (default: 3)

**Actions:**
- **Save Webhook Settings**: Apply changes to webhook configuration
- **Test Webhook**: Verify connectivity to results site
- **Reset to Defaults**: Restore default webhook settings

### 📡 LLRP Configuration

Configure default settings for LLRP RFID readers:

- **Default LLRP Port**: Default port for LLRP reader connections (default: 5084)
- **Tag Read Cooldown**: Minimum time between reads of the same tag in seconds (default: 5)
- **Connection Timeout**: Timeout for LLRP reader connections in seconds (default: 30)

**Actions:**
- **Save LLRP Settings**: Apply changes to LLRP configuration
- **Reset to Defaults**: Restore default LLRP settings

### ⚙️ General Configuration

General application settings:

- **Application Name**: Display name for the application (default: Race Timing System)
- **Timezone**: Application timezone (default: UTC)
- **Auto-Publish Results**: Automatically publish results after race completion (default: Disabled)

**Actions:**
- **Save General Settings**: Apply changes to general configuration
- **Reset to Defaults**: Restore default general settings

## Features

### 🔒 Security

- **Sensitive Fields**: Passwords and secrets are masked in the UI (shown as ••••••••)
- **Toggle Visibility**: Click the 👁️ icon to temporarily show/hide sensitive values
- **Secure Storage**: All configuration is stored securely in the database
- **Audit Trail**: Configuration changes are tracked with timestamps and user information

### ✅ Validation & Testing

- **Test Database Connection**: Verify database settings before saving
- **Test Webhook Connection**: Verify results site connectivity
- **Real-time Feedback**: Immediate success/error messages for all operations
- **Form Validation**: Client-side validation prevents invalid inputs

### 🔄 Configuration Management

- **Live Updates**: Changes take effect immediately (some may require restart)
- **Category Reset**: Reset entire categories to default values
- **Import/Export**: Configuration can be exported and imported (via API)
- **Environment Override**: Environment variables take precedence over database settings

## Technical Details

### Database Storage

Configuration is stored in the `system_config` table with the following structure:

```sql
CREATE TABLE system_config (
    id INTEGER PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,
    description TEXT,
    category VARCHAR(50),
    is_sensitive BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP,
    updated_by VARCHAR(100)
);
```

### Configuration Manager

The `ConfigManager` class (`config_manager.py`) provides:

- **get(key, default)**: Get configuration value
- **get_int(key, default)**: Get configuration as integer
- **get_bool(key, default)**: Get configuration as boolean
- **set(key, value, updated_by)**: Set configuration value
- **get_all(category)**: Get all configurations, optionally filtered by category
- **update_multiple(updates, updated_by)**: Update multiple values at once
- **reset_to_defaults(category)**: Reset to default values
- **export_config(include_sensitive)**: Export configuration as JSON
- **import_config(json_data, updated_by)**: Import configuration from JSON

### API Endpoints

#### GET /api/system-config
Get all system configuration values

**Response:**
```json
{
    "db_host": "localhost",
    "db_port": "5432",
    "webhook_secret": "********",
    ...
}
```

#### POST /api/system-config
Update system configuration

**Request:**
```json
{
    "db_host": "192.168.1.100",
    "db_port": "5432",
    "webhook_timeout": "15"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Successfully updated 3 settings"
}
```

#### POST /api/system-config/test-database
Test database connection with current settings

**Response:**
```json
{
    "success": true,
    "message": "Database connection successful"
}
```

#### POST /api/system-config/test-webhook
Test webhook connection to results site

**Response:**
```json
{
    "success": true,
    "message": "Webhook connection successful",
    "response": {
        "status": "ok",
        "timestamp": "2026-02-25T18:00:00.000Z"
    }
}
```

#### POST /api/system-config/reset/{category}
Reset configuration category to defaults

**Parameters:**
- `category`: database, webhook, llrp, or general

**Response:**
```json
{
    "success": true,
    "message": "Reset 5 settings to defaults"
}
```

## Usage Examples

### Changing Database Connection

1. Navigate to **Database** tab
2. Update host, port, database name, user, and password
3. Click **Test Connection** to verify settings
4. Click **Save Database Settings** to apply changes
5. Restart the application for changes to take effect

### Configuring Webhook Publishing

1. Navigate to **Webhooks** tab
2. Set **Results Site URL** to your public results site URL
3. Set **Webhook Secret** (must match the secret on results site)
4. Click **Test Webhook** to verify connectivity
5. Click **Save Webhook Settings** to apply changes

### Setting Up LLRP Readers

1. Navigate to **LLRP** tab
2. Configure default port and cooldown settings
3. Click **Save LLRP Settings**
4. Individual LLRP stations can override these defaults

## Environment Variables vs Database Configuration

The system supports both environment variables and database configuration:

1. **Environment variables** take precedence (if set)
2. **Database configuration** is used if no environment variable exists
3. **Default values** are used if neither is set

This allows for:
- **Development**: Use database configuration for easy changes
- **Production**: Use environment variables for security and deployment
- **Hybrid**: Mix both approaches as needed

## Best Practices

### Security

1. **Change Default Secrets**: Always change webhook_secret from default value
2. **Use Strong Passwords**: Use complex database passwords
3. **Limit Access**: Restrict access to configuration screen to administrators only
4. **Regular Backups**: Export configuration regularly for backup

### Performance

1. **Test Before Saving**: Always test database and webhook connections before saving
2. **Monitor Timeouts**: Adjust timeout values based on network conditions
3. **Optimize Cooldown**: Set LLRP cooldown based on race requirements

### Maintenance

1. **Document Changes**: Keep track of configuration changes
2. **Test After Changes**: Verify system functionality after configuration updates
3. **Use Reset Carefully**: Resetting to defaults will lose custom settings
4. **Export Configuration**: Export configuration before major changes

## Troubleshooting

### Database Connection Fails

1. Verify database server is running
2. Check host and port are correct
3. Verify username and password
4. Ensure database exists
5. Check firewall settings

### Webhook Connection Fails

1. Verify results site is running
2. Check URL is correct and accessible
3. Verify webhook secret matches on both systems
4. Check network connectivity
5. Review timeout settings

### Configuration Not Saving

1. Check for error messages in the UI
2. Verify database connection is working
3. Check application logs for errors
4. Ensure you have write permissions

### Changes Not Taking Effect

1. Some changes require application restart
2. Clear browser cache
3. Check if environment variables are overriding database settings
4. Verify configuration was actually saved (check database)

## Migration from Environment Variables

If you're currently using environment variables (`.env` file), you can migrate to database configuration:

1. Start the application (it will initialize defaults from environment variables)
2. Navigate to configuration screen
3. Verify all settings are correct
4. Optionally remove settings from `.env` file
5. Settings in database will now be used

## Support

For issues or questions about system configuration:

1. Check this guide
2. Review application logs
3. Test connections using built-in test functions
4. Check IMPROVEMENTS_PLAN.md for known issues and future enhancements

## Future Enhancements

Planned improvements (see IMPROVEMENTS_PLAN.md for details):

- Configuration versioning and rollback
- Configuration templates for different environments
- Bulk import/export via UI
- Configuration validation rules
- Email notifications for configuration changes
- Configuration change approval workflow
- Multi-user access control