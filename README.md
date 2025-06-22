# Proxmox VE Integration for Home Assistant

A Home Assistant integration for monitoring Proxmox Virtual Environment (PVE) servers, providing real-time status and resource usage information for nodes, VMs, and containers.

## Features

- **Node Monitoring**: Monitor the status and resource usage of Proxmox VE nodes
- **VM Monitoring**: Track individual VM status, CPU, memory, and disk usage
- **Container Monitoring**: Monitor LXC container status and resource utilization
- **Multiple Server Support**: Connect to multiple Proxmox VE servers simultaneously
- **Real-time Updates**: Data updates every 30 seconds
- **Flexible Authentication**: Support for both password and API token authentication

## Installation

### Option 1: Manual Installation (Recommended)

1. Download or clone this repository
2. Copy the `custom_components/proxmox_ve` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant
4. Go to **Settings** → **Devices & Services** → **Add Integration**
5. Search for "Proxmox VE" and follow the setup wizard

### Option 2: HACS Installation

1. Install HACS if you haven't already
2. Add this repository as a custom repository in HACS
3. Install the Proxmox VE integration through HACS
4. Restart Home Assistant
5. Configure the integration through the UI

## Configuration

### Prerequisites

1. **Proxmox VE Server**: A running Proxmox Virtual Environment server
2. **API Access**: A user account with API access enabled
3. **Network Connectivity**: Home Assistant must be able to reach your Proxmox VE server on port 8006

### Setup Wizard

The integration provides a user-friendly setup wizard with the following steps:

#### Step 1: Basic Configuration
- **Host**: Your Proxmox VE server address and port (e.g., `192.168.1.100:8006`)
- **Username**: Your Proxmox VE username (e.g., `root` or `root@pam`)
- **Authentication Method**: Choose between password or token authentication
- **Verify SSL**: Enable/disable SSL certificate verification

#### Step 2A: Password Authentication
- **Password**: Your Proxmox VE user password

#### Step 2B: Token Authentication
- **Token Name**: Name of your API token (e.g., `homeassistant`)
- **Token Value**: The API token value

### Username Format

The integration automatically handles username formatting:
- If you enter just `root`, it will be converted to `root@pam`
- You can also enter the full format directly: `root@pam`, `user@ldap`, etc.

### API Token Setup (Optional)

For enhanced security, you can use API tokens instead of passwords:

1. In Proxmox VE web interface, go to **Datacenter** → **Permissions** → **API Tokens**
2. Create a new token for your user
3. Note the token name and value
4. Use these in the integration configuration

## Sensors Created

The integration creates the following sensors:

### Node Sensors
- **Name**: `Proxmox VE Node {node_name} ({host})`
- **State**: Node status (online, offline, etc.)
- **Attributes**: CPU usage, memory usage, disk usage, uptime

### VM Sensors
- **Name**: `Proxmox VE VM {vm_name} ({host})`
- **State**: VM status (running, stopped, paused, etc.)
- **Attributes**: CPU usage, memory usage, disk usage, uptime, node

### Container Sensors
- **Name**: `Proxmox VE Container {container_name} ({host})`
- **State**: Container status (running, stopped, etc.)
- **Attributes**: CPU usage, memory usage, disk usage, uptime, node

## Multiple Server Support

The integration supports connecting to multiple Proxmox VE servers:
- Each server gets its own set of sensors
- Sensor names include the host address for easy identification
- No naming conflicts between different servers

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Check your username format and credentials
2. **Connection Errors**: Verify host address and network connectivity
3. **No Sensors Appearing**: Check if your Proxmox VE server has VMs/containers

### Debug Information

Enable debug logging by adding this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.proxmox_ve: debug
```

### Test Script

Use the provided `debug_proxmox.py` script to test your connection:

1. Edit the script with your credentials
2. Run: `python3 debug_proxmox.py`
3. Check the output for any errors

## Logo and Branding

The integration includes logo files for proper display in the Home Assistant UI:

- **`icon.png`**: 24x24 pixel icon used in integration cards and lists
- **`logo.png`**: 128x128 pixel logo used on the integration page

These files are based on the official Proxmox logo and are included for proper branding in the Home Assistant interface.

## Requirements

- Home Assistant 2023.8.0 or later
- Python 3.9 or later
- `proxmoxer==2.2.0`
- `requests`

## Support

- **Documentation**: [GitHub Repository](https://github.com/itskodashi/hassio-integrations)
- **Issues**: [GitHub Issues](https://github.com/itskodashi/hassio-integrations/issues)
- **Discussions**: [GitHub Discussions](https://github.com/itskodashi/hassio-integrations/discussions)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Changelog

### Version 0.1.0
- Initial release
- Support for node, VM, and container monitoring
- Password and token authentication
- Multiple server support
- Real-time status updates
- Comprehensive error handling and logging
