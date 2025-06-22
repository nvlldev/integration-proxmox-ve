# Proxmox Integration Troubleshooting Guide

If you're not seeing any devices or entities appearing in Home Assistant, follow these steps to diagnose and fix the issue.

## Step 1: Check Home Assistant Logs

First, check the Home Assistant logs for any error messages:

1. Go to **Settings** → **System** → **Logs**
2. Look for any errors related to "proxmox" or "Proxmox"
3. Common error messages and solutions:

### Authentication Errors
```
Error fetching Proxmox data: AuthenticationError
```
**Solution**: Check your username and password/token credentials in the integration configuration.

### Connection Errors
```
Error fetching Proxmox data: ConnectionError
```
**Solution**: 
- Verify the Proxmox host address and port (usually `your-server:8006`)
- Check if SSL verification is enabled/disabled correctly
- Ensure your Home Assistant can reach the Proxmox server

### No Entities Found
```
No Proxmox entities found to create
```
**Solution**: This usually means the API connection is working but no resources were found. Check if you have any VMs or containers on your Proxmox server.

## Step 2: Fix Username Format Issues

### Common Error: `401 Unauthorized: no such user ('root!root@pam')`

This error indicates that the username format is incorrect. The Proxmox API expects usernames in the format `username@realm`.

**Solutions**:

1. **In the Integration Configuration**:
   - Go to **Settings** → **Devices & Services**
   - Find your Proxmox integration and click **Configure**
   - Update the username to include the realm:
     - Use `root@pam` instead of just `root`
     - Use `youruser@pam` instead of just `youruser`
   - Save the configuration

2. **Alternative: Let the integration auto-format**:
   - The integration now automatically adds `@pam` if no realm is specified
   - You can enter just `root` and it will be converted to `root@pam`

3. **For different realms**:
   - If using LDAP: `username@ldap`
   - If using Active Directory: `username@ad`
   - If using other authentication methods, check your Proxmox configuration

### Testing Username Format

Use the debug script to test your username format:

1. Edit `debug_proxmox.py` with your credentials
2. Run: `python3 debug_proxmox.py`
3. Check if the username is being formatted correctly

## Step 3: Token Authentication Issues

### Common Error: `401 Unauthorized: no such user ('root@pam!root@pam')`

This error occurs when using token authentication and indicates that the token is being constructed incorrectly. The integration now properly handles token authentication.

**Solutions**:

1. **Verify Token Format**:
   - Token name should be just the token name (e.g., `hass`)
   - Token value should be the full token value from Proxmox
   - The integration will automatically construct the proper token ID format

2. **Check Token Permissions**:
   - Ensure the token has the necessary permissions in Proxmox
   - The token should have access to read node, VM, and container information

3. **Test Token Authentication**:
   - Use the debug script with token authentication enabled
   - Edit `debug_proxmox.py` and uncomment the token lines:
     ```python
     token_name = "hass"  # Your token name
     token_value = "your-token-value"  # Your token value
     ```

4. **Token Creation in Proxmox**:
   - Go to **Datacenter** → **Permissions** → **API Tokens**
   - Create a new token for your user
   - Set appropriate permissions (at minimum: Datacenter.Read)
   - Copy both the token name and value

## Step 4: Test API Connection

Use the provided debug script to test your Proxmox API connection:

1. Edit `debug_proxmox.py` and update the credentials:
   ```python
   host = "your-proxmox-host:8006"  # e.g., "192.168.1.100:8006"
   username = "your-username"       # e.g., "root@pam" or just "root"
   password = "your-password"
   
   # For token authentication:
   # token_name = "hass"
   # token_value = "your-token-value"
   ```

2. Run the script:
   ```bash
   python3 debug_proxmox.py
   ```

3. If the script works, you should see output like:
   ```
   ✓ Found 1 nodes:
     - pve (status: online)
   Node: pve
     VMs: 2
       - Home Assistant (ID: 100, Status: running)
       - Docker Server (ID: 101, Status: stopped)
     Containers: 1
       - Web Server (ID: 102, Status: running)
   ```

## Step 5: Check Integration Configuration

1. Go to **Settings** → **Devices & Services**
2. Find your Proxmox integration and click on it
3. Click **Configure**
4. Verify all settings are correct:
   - **Host**: Should include port (e.g., `192.168.1.100:8006`)
   - **Username**: Should be in format `username@realm` (e.g., `root@pam`)
   - **Password/Token**: Your authentication credentials
   - **Verify SSL**: Should match your Proxmox SSL setup

## Step 6: Restart and Reload

1. **Restart Home Assistant**: Go to **Settings** → **System** → **Restart**
2. **Reload the Integration**: 
   - Go to **Settings** → **Devices & Services**
   - Find Proxmox integration
   - Click the three dots menu → **Reload**

## Step 7: Check Entity Registration

If the API connection works but entities still don't appear:

1. Go to **Settings** → **Devices & Services** → **Entities**
2. Search for "proxmox" in the filter
3. If entities exist but are disabled, enable them

## Step 8: Enable Debug Logging

To get more detailed logs, add this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.proxmox: debug
```

Then restart Home Assistant and check the logs again.

## Common Issues and Solutions

### Issue: "No Proxmox entities found to create"
**Possible Causes**:
- Proxmox server has no VMs or containers
- API user doesn't have permission to view resources
- Network connectivity issues

**Solutions**:
1. Verify you have VMs/containers on your Proxmox server
2. Check API user permissions in Proxmox
3. Test network connectivity from Home Assistant to Proxmox

### Issue: Entities appear but show "unknown" status
**Possible Causes**:
- API user has limited permissions
- Proxmox server is overloaded
- Network latency issues

**Solutions**:
1. Grant more permissions to the API user
2. Check Proxmox server performance
3. Increase the update interval in the code (currently 30 seconds)

### Issue: Integration fails to load
**Possible Causes**:
- Missing dependencies
- Configuration errors
- Home Assistant version incompatibility

**Solutions**:
1. Check that `proxmoxer` and `requests` are installed
2. Verify configuration format
3. Ensure Home Assistant version is compatible

## Getting Help

If you're still having issues:

1. Check the [GitHub Issues](https://github.com/itskodashi/hassio-integrations/issues) for similar problems
2. Create a new issue with:
   - Home Assistant version
   - Proxmox version
   - Error messages from logs
   - Output from the debug script
   - Your configuration (without sensitive credentials)

## Debug Information

When reporting issues, please include:

1. **Home Assistant Version**: Found in **Settings** → **System** → **Info**
2. **Proxmox Version**: Found in Proxmox web interface
3. **Integration Version**: Check the manifest.json file
4. **Logs**: Copy relevant error messages
5. **Debug Script Output**: Run `debug_proxmox.py` and share the output
6. **Configuration**: Your integration settings (without passwords)

## Recent Changes Made

The following improvements were made to fix sensor issues:

- ✅ Fixed coordinator setup and data handling
- ✅ Added proper error handling and fallback values
- ✅ Fixed API endpoints for VMs and containers
- ✅ **Separated VMs and containers into distinct sensor types**
- ✅ Added comprehensive logging for debugging
- ✅ Improved entity creation logic
- ✅ Enhanced sensor naming and organization
- ✅ **Prevented naming conflicts for multiple Proxmox servers**
- ✅ Added host information to sensor names and attributes
- ✅ **Fixed username format validation and auto-correction**
- ✅ **Added better authentication error handling**

## Expected Behavior

After a successful setup, you should see:

- **Node sensors**: One sensor per Proxmox node showing status and resource usage
- **VM sensors**: One sensor per VM showing status and resource usage  
- **Container sensors**: One sensor per LXC container showing status and resource usage

Each sensor will update every 30 seconds with current status and resource information.

### Sensor Naming Convention:
- **Nodes**: `Proxmox Node {node_name} ({host})`
- **VMs**: `Proxmox VM {vm_name} ({host})`
- **Containers**: `Proxmox Container {container_name} ({host})`

### Sensor Types:
- **Node sensors**: Show overall node status and resource utilization
- **VM sensors**: Show individual VM status, CPU, memory, and disk usage
- **Container sensors**: Show individual container status, CPU, memory, and disk usage

All sensors include attributes with detailed resource information, the node they belong to, and the Proxmox host they're connected to.

## LXC Containers Not Showing Up

If you can see nodes and VMs but not LXC containers, here are the most common causes and solutions:

### 1. Check API Permissions

The user account needs specific permissions to access LXC containers:

**Required Permissions:**
- `Datastore.AllocateSpace` - To read container information
- `VM.Allocate` - To access container data
- `VM.Audit` - To read container status

**To check/fix permissions:**
1. Log into Proxmox web interface
2. Go to Datacenter → Permissions → Users
3. Select your user
4. Go to "Permissions" tab
5. Ensure the user has the required permissions on the nodes

### 2. Check Proxmox Version

Different Proxmox versions use different field names for container IDs:

- **Proxmox 6.x and earlier**: Uses `vmid` field
- **Proxmox 7.x and later**: Uses `id` field

The integration now handles both field names automatically.

### 3. Enable Debug Logging

To see detailed information about what's happening:

1. In Home Assistant, go to **Configuration** → **Settings** → **System**
2. Click on **Logs**
3. Add this to your `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.proxmox: debug
```

4. Restart Home Assistant
5. Check the logs for container-related messages

### 4. Test API Access Directly

You can test the API access using the provided test script:

1. Update `test_proxmox_api.py` with your credentials
2. Run: `python3 test_proxmox_api.py`
3. Check if containers are listed in the output

### 5. Check Container Status

LXC containers might not show up if they're in certain states:
- Check if containers are actually running or stopped
- Some containers might be in "locked" or "error" states

### 6. Network/Firewall Issues

Ensure the Home Assistant instance can reach the Proxmox API:
- Test connectivity: `telnet your-proxmox-host 8006`
- Check if any firewalls are blocking the connection

### 7. SSL Certificate Issues

If using HTTPS:
- Try setting `verify_ssl: false` in the integration configuration
- Or ensure valid SSL certificates are installed

### 8. Common Error Messages

**"Failed to fetch LXC containers"**
- Usually indicates permission issues
- Check user permissions in Proxmox

**"Container missing both 'id' and 'vmid' fields"**
- Indicates API response format issue
- Check Proxmox version compatibility

**"No containers found"**
- No LXC containers exist on the node
- Or containers exist but user lacks permissions

### 9. Manual API Test

You can test the API manually using curl:

```bash
# For password authentication
curl -k -u "username@realm:password" \
  "https://your-proxmox-host:8006/api2/json/nodes/your-node/lxc"

# For token authentication  
curl -k -H "Authorization: PVEAPIToken=username@realm!token_name=token_value" \
  "https://your-proxmox-host:8006/api2/json/nodes/your-node/lxc"
```

### 10. Still Having Issues?

If none of the above solutions work:

1. Check the Home Assistant logs for specific error messages
2. Verify the Proxmox API is working by testing in the web interface
3. Try creating a new API token with full permissions
4. Check if there are any Proxmox-specific error messages in the system logs

## Getting Help

If you're still experiencing issues:

1. Enable debug logging (see step 3 above)
2. Collect the relevant log entries
3. Include your Proxmox version and Home Assistant version
4. Share the error messages you're seeing 

## Load Data Not Showing Up

If you're not seeing system load or load average information in your Proxmox sensors, here are the steps to debug and fix the issue:

### 1. Enable Debug Logging

First, enable debug logging to see what's happening:

1. In Home Assistant, go to **Configuration** → **Settings** → **System**
2. Click on **Logs**
3. Add this to your `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.proxmox: debug
```

4. Restart Home Assistant
5. Check the logs for load data related messages

### 2. Check the Debug Script

Run the load data debug script to test API access:

1. Update `debug_load_data.py` with your Proxmox credentials
2. Run: `python3 debug_load_data.py`
3. Check the output to see what load data is available

### 3. Common Issues and Solutions

**Issue: "No load data returned for node"**
- **Cause**: API user lacks permissions to access RRD data
- **Solution**: Grant `Datastore.AllocateSpace` and `VM.Audit` permissions

**Issue: "Load average data is not in expected format"**
- **Cause**: Proxmox version differences in data format
- **Solution**: The integration now tries multiple approaches to get load data

**Issue: "Failed to fetch load data from node"**
- **Cause**: Network connectivity or API endpoint issues
- **Solution**: Check network connectivity and API endpoint availability

### 4. Manual API Testing

You can test the API manually using curl:

```bash
# Test RRD data endpoint
curl -k -u "username@realm:password" \
  "https://your-proxmox-host:8006/api2/json/nodes/your-node/rrddata?timeframe=hour"

# Test node status endpoint
curl -k -u "username@realm:password" \
  "https://your-proxmox-host:8006/api2/json/nodes/your-node/status"
```

### 5. Expected Load Data Format

The integration expects load data in this format:
```json
{
  "loadavg": [1.23, 1.45, 1.67]  // 1min, 5min, 15min averages
}
```

### 6. Alternative Load Data Sources

If RRD data is not available, the integration will try:
1. Node status endpoint for load average
2. Different RRD timeframes (hour, day, week)
3. Fallback to zero values if no data is available

### 7. Check Sensor Attributes

To verify if load data is being collected:
1. Go to **Developer Tools** → **States**
2. Search for your Proxmox node sensors
3. Check if the attributes include:
   - `loadavg_1min`
   - `loadavg_5min` 
   - `loadavg_15min`
   - `cpu_frequency_mhz`
   - `cpu_cores`
   - `cpu_model`

### 8. Still Having Issues?

If load data still isn't showing up:

1. Check the Home Assistant logs for specific error messages
2. Run the debug script and share the output
3. Verify your Proxmox version and API permissions
4. Test the API endpoints manually with curl
5. Check if load data is available in the Proxmox web interface

## Getting Help

If you're still experiencing issues:

1. Enable debug logging (see step 1 above)
2. Run the debug script and collect the output
3. Check the Home Assistant logs for load data related messages
4. Include your Proxmox version and the debug output when reporting issues 