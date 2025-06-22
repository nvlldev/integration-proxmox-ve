#!/usr/bin/env python3
"""Debug script to check Proxmox VE API response structure."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'custom_components', 'proxmox_ve'))

# Mock homeassistant.const to avoid import errors
class MockConstants:
    CONF_HOST = "host"
    CONF_PASSWORD = "password" 
    CONF_USERNAME = "username"

sys.modules['homeassistant.const'] = type('MockModule', (), {'CONF_HOST': 'host', 'CONF_PASSWORD': 'password', 'CONF_USERNAME': 'username'})

from api import ProxmoxClient

def debug_proxmox_api():
    """Debug the Proxmox VE API response structure."""
    # Update these with your actual credentials
    host = "your-proxmox-host:8006"  # Update this
    username = "root"  # Update this
    password = "your-password"  # Update this
    
    # For token authentication, uncomment and use these instead:
    # token_name = "hass"
    # token_value = "your-token-value"
    
    print(f"Debugging Proxmox VE API for host: {host}")
    print(f"Username: {username}")
    
    try:
        # Create client with password authentication
        client = ProxmoxClient(host=host, username=username, password=password, verify_ssl=False)
        
        # For token authentication, use this instead:
        # client = ProxmoxClient(host=host, username=username, token_name=token_name, token_value=token_value, verify_ssl=False)
        
        # Test authentication
        client.authenticate()
        print("✓ Authentication successful!")
        
        # Get nodes
        print("\n=== NODES ===")
        nodes = client.proxmox.nodes.get()
        print(f"Found {len(nodes)} nodes:")
        for node in nodes:
            print(f"  - {node}")
        
        # Get containers from first node
        if nodes:
            node_name = nodes[0]["node"]
            print(f"\n=== CONTAINERS ON NODE {node_name} ===")
            try:
                containers = client.proxmox.nodes(node_name).lxc.get()
                print(f"Found {len(containers)} containers:")
                for container in containers:
                    print(f"  - {container}")
            except Exception as e:
                print(f"Error getting containers: {e}")
        
        print("\n✓ Debug completed successfully!")
        
    except Exception as e:
        print(f"✗ Debug failed: {e}")
        print(f"Error type: {type(e).__name__}")


if __name__ == "__main__":
    print("Proxmox VE API Debug Script")
    print("=" * 40)
    print("Before running this script:")
    print("1. Update the credentials in the script")
    print("2. Run: python3 debug_proxmox.py")
    print()
    
    # Uncomment the line below to run the debug
    # debug_proxmox_api() 