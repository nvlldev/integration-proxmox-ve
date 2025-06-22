#!/usr/bin/env python3
"""Test script to check Proxmox API permissions for different endpoints."""

import json
import sys
from proxmoxer import ProxmoxAPI

def test_permissions(host, username, password, verify_ssl=False):
    """Test different Proxmox API endpoints to check permissions."""
    
    try:
        # Connect to Proxmox
        proxmox = ProxmoxAPI(
            host=host,
            user=username,
            password=password,
            verify_ssl=verify_ssl
        )
        
        print(f"Connected to Proxmox host: {host}")
        print(f"Username: {username}")
        print("=" * 60)
        
        # Get nodes
        nodes = proxmox.nodes.get()
        print(f"Found {len(nodes)} nodes:")
        for node in nodes:
            print(f"  - {node['node']}")
        
        print("\n" + "=" * 60)
        
        # Test each node
        for node in nodes:
            node_name = node['node']
            print(f"\nTesting permissions for node: {node_name}")
            print("-" * 40)
            
            # Test different endpoints and their permissions
            endpoints_to_test = [
                ("nodes.get", lambda: proxmox.nodes.get()),
                ("nodes.status", lambda: proxmox.nodes(node_name).status.get()),
                ("nodes.rrddata", lambda: proxmox.nodes(node_name).rrddata.get(timeframe='hour')),
                ("nodes.qemu", lambda: proxmox.nodes(node_name).qemu.get()),
                ("nodes.lxc", lambda: proxmox.nodes(node_name).lxc.get()),
                ("nodes.hardware.cpu", lambda: proxmox.nodes(node_name).hardware.cpu.get()),
                ("nodes.system", lambda: proxmox.nodes(node_name).system.get()),
                ("nodes.hardware", lambda: proxmox.nodes(node_name).hardware.get()),
            ]
            
            for endpoint_name, endpoint_func in endpoints_to_test:
                try:
                    print(f"\nTesting: {endpoint_name}")
                    result = endpoint_func()
                    
                    if isinstance(result, list):
                        print(f"  ✓ SUCCESS: List with {len(result)} items")
                        if result and len(result) > 0:
                            print(f"    First item keys: {list(result[0].keys())}")
                    else:
                        print(f"  ✓ SUCCESS: Dict with keys: {list(result.keys())}")
                    
                except Exception as e:
                    error_msg = str(e)
                    if "403" in error_msg or "Forbidden" in error_msg:
                        print(f"  ✗ PERMISSION DENIED: {error_msg}")
                    elif "404" in error_msg or "Not Found" in error_msg:
                        print(f"  ✗ NOT FOUND: {error_msg}")
                    else:
                        print(f"  ✗ ERROR: {error_msg}")
            
            # Only test first node to avoid too much output
            break
            
    except Exception as e:
        print(f"Connection error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python test_permissions.py <host> <username> <password> <verify_ssl>")
        print("Example: python test_permissions.py 192.168.1.100 root@pam mypassword false")
        sys.exit(1)
    
    host = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    verify_ssl = sys.argv[4].lower() == 'true'
    
    test_permissions(host, username, password, verify_ssl) 