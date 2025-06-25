# Proxmox VE Enhanced Integration for Home Assistant

This custom integration **replaces** the built-in Proxmox VE integration with enhanced functionality including VM/container controls and storage percentage monitoring.

## ✨ Features

### 📊 **Enhanced Monitoring**
- **Storage percentages**: Disk usage and free percentages for nodes, VMs, and containers
- **Comprehensive sensors**: CPU, memory, disk, network, and system metrics
- **Real-time status**: Live monitoring of VM/container states

### 🎮 **VM/Container Controls**
- **Start/Stop**: Power control for VMs and containers
- **Graceful shutdown**: Safe shutdown operations
- **Reboot/Reset**: Restart operations (graceful and forced)
- **Suspend/Resume**: Pause and resume VMs and containers
- **Smart buttons**: Context-aware controls based on current state

### 🏗️ **Modern Architecture**
- **Async operations**: Concurrent API calls for better performance
- **Proper error handling**: Comprehensive error management
- **Type safety**: Full type hints and data models
- **Resource management**: Proper HTTP session handling

## 🚀 Installation

### Method 1: HACS (Recommended)
1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the "+" button
4. Search for "Proxmox VE Enhanced"
5. Install the integration
6. Restart Home Assistant

### Method 2: Manual Installation
1. Copy the `proxmoxve` folder to your `custom_components` directory:
   ```
   config/custom_components/proxmoxve/
   ```
2. Restart Home Assistant
3. The integration will automatically replace the built-in one

## ⚙️ Configuration

### Step 1: Remove Built-in Integration (if already configured)
1. Go to **Settings** → **Devices & Services**
2. Find any existing "Proxmox VE" integration
3. Click the "..." menu and select "Delete"

### Step 2: Add Enhanced Integration
1. Go to **Settings** → **Devices & Services**
2. Click "**+ Add Integration**"
3. Search for "**Proxmox VE**"
4. Follow the configuration flow

### Configuration Options

#### Authentication Methods
- **Password Authentication**: Username + Password
- **Token Authentication**: Username + API Token (recommended)

#### Connection Settings
- **Host**: IP address or hostname of Proxmox server
- **Port**: Default 8006 (change if customized)
- **SSL Verification**: Enable/disable SSL certificate verification
- **Update Interval**: Polling frequency (10-300 seconds)

## 🔧 API Token Setup (Recommended)

### Create API Token in Proxmox
1. Log into Proxmox web interface
2. Go to **Datacenter** → **Permissions** → **API Tokens**
3. Click **Add** to create new token
4. Set **User** to your username
5. Set **Token ID** to something like `homeassistant`
6. **Uncheck** "Privilege Separation"
7. Copy the generated **Token Secret**

### Configure in Home Assistant
- **Username**: `username@pam` (or `username@pve`)
- **Token Name**: The Token ID you created
- **Token Value**: The generated Token Secret

## 📱 Usage

### Sensors
All sensors are automatically created for:
- **Nodes**: CPU, memory, disk usage/percentages, load averages
- **VMs**: CPU, memory, disk usage/percentages, uptime
- **Containers**: CPU, memory, disk usage/percentages, uptime

### Control Buttons
Control buttons appear based on current state:
- **Running** resources: Stop, Shutdown, Reboot, Suspend
- **Stopped** resources: Start  
- **Suspended** resources: Resume

### Device Organization
- Each **node**, **VM**, and **container** appears as a separate device
- **VMs** and **containers** are linked to their parent **node**
- All related sensors and controls are grouped by device

## 🆚 Comparison with Built-in Integration

| Feature | Built-in | Enhanced |
|---------|----------|----------|
| Basic monitoring | ✅ | ✅ |
| Storage percentages | ❌ | ✅ |
| VM/Container controls | ❌ | ✅ |
| Modern async API | ❌ | ✅ |
| Concurrent requests | ❌ | ✅ |
| Type safety | ❌ | ✅ |
| Proper error handling | ❌ | ✅ |
| Button controls | ❌ | ✅ |
| Smart availability | ❌ | ✅ |

## 🔍 Troubleshooting

### Connection Issues
- Verify Proxmox server is accessible from Home Assistant
- Check firewall settings (port 8006)
- Ensure credentials are correct
- Try disabling SSL verification for self-signed certificates

### Permission Issues
- Ensure user has sufficient privileges in Proxmox
- For API tokens, disable "Privilege Separation"
- Check that user can access the resources you want to monitor

### Performance Issues
- Increase update interval if you have many VMs/containers
- Check Proxmox server resources
- Monitor Home Assistant logs for errors

### Logs
Enable debug logging by adding to `configuration.yaml`:
```yaml
logger:
  logs:
    custom_components.proxmoxve: debug
```

## 🤝 Support

- **Issues**: Report bugs and feature requests
- **Documentation**: Check Home Assistant Proxmox VE docs
- **Community**: Home Assistant Community Forum

## 📄 License

This integration is provided as-is under the MIT License.

---

**Note**: This enhanced integration completely replaces the built-in Proxmox VE integration. You cannot run both simultaneously.