#!/usr/bin/env python3
"""Test script for Proxmox VE API connection."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'custom_components', 'proxmox_ve'))

from api import ProxmoxClient

def validate_username(username: str) -> str:
    """Validate and format username for Proxmox VE."""
    # If username doesn't contain @, assume it's a local user and add @pam
    if '@' not in username:
        username = f"{username}@pam"
        print(f"Username format corrected to: {username}")
    return username

def test_proxmox_connection():
    """Test the Proxmox VE API connection."""
    # Replace these with your actual Proxmox VE credentials
    host = "your-proxmox-host"  # e.g., "192.168.1.100:8006"
    username = "root"  # or "root@pam"
    password = "your-password"
    
    # For token authentication, uncomment and use these instead:
    # token_name = "hass"  # The token name you created in Proxmox VE
    # token_value = "your-token-value"  # The token value from Proxmox VE
    
    # Validate and format username
    username = validate_username(username)
    
    print(f"Testing connection to {host} with username: {username}")
    
    try:
        # Test with password authentication
        print("\n1. Testing password authentication...")
        client = ProxmoxClient(
            host=host,
            username=username,
            password=password,
            verify_ssl=False
        )
        
        # Test with token authentication (uncomment to test)
        # print("\n2. Testing token authentication...")
        # client = ProxmoxClient(
        #     host=host,
        #     username=username,
        #     token_name=token_name,
        #     token_value=token_value,
        #     verify_ssl=False
        # )
        
        # Test authentication
        client.authenticate()
        print("✓ Authentication successful!")
        
        # Test basic API calls
        print("\n3. Testing API calls...")
        
        # Get nodes
        print("   Getting nodes...")
        nodes = client.proxmox.nodes.get()
        print(f"   ✓ Found {len(nodes)} nodes")
        
        for node in nodes:
            node_name = node["node"]
            print(f"   - Node: {node_name}")
            
            # Get VMs for this node
            try:
                node_vms = client.proxmox.nodes(node["node"]).qemu.get()
                print(f"     ✓ Found {len(node_vms)} VMs")
            except Exception as e:
                print(f"     ✗ Error getting VMs: {e}")
            
            # Get containers for this node
            try:
                node_containers = client.proxmox.nodes(node["node"]).lxc.get()
                print(f"     ✓ Found {len(node_containers)} containers")
            except Exception as e:
                print(f"     ✗ Error getting containers: {e}")
        
        print("\n✓ All tests passed!")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        print(f"Error type: {type(e).__name__}")
        
        # Provide helpful error messages
        if "Authentication" in str(e):
            print("\nTroubleshooting authentication issues:")
            print("1. Check your username and password/token")
            print("2. Ensure the user has API access enabled")
            print("3. Ensure the user has API access enabled in Proxmox VE")
        elif "Connection" in str(e):
            print("\nTroubleshooting connection issues:")
            print("1. Check your host address and port")
            print("2. Check network connectivity from this machine to Proxmox VE")
            print("3. Ensure Proxmox VE web interface is accessible")
        else:
            print("\nGeneral troubleshooting:")
            print("1. Check Proxmox VE server logs for more details")
            print("2. Verify API access is enabled in Proxmox VE")
            print("3. Try accessing the Proxmox VE web interface directly")

if __name__ == "__main__":
    print("Proxmox VE API Test Script")
    print("=" * 40)
    print("Before running this script:")
    print("1. Update the credentials at the top of the script")
    print("2. Run: python3 test_proxmox_api.py")
    print()
    
    # Uncomment the line below to run the test
    # test_proxmox_connection() 