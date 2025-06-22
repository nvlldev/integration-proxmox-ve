#!/usr/bin/env python3
"""Test script to check Proxmox API endpoints for CPU information."""

import json
import sys
from proxmoxer import ProxmoxAPI

def test_cpu_endpoints(host, username, password, verify_ssl=False):
    """Test different Proxmox API endpoints for CPU information."""
    
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
            print(f"\nTesting node: {node_name}")
            print("-" * 40)
            
            # Test different endpoints
            endpoints_to_test = [
                ("hardware.cpu", lambda: proxmox.nodes(node_name).hardware.cpu.get()),
                ("system", lambda: proxmox.nodes(node_name).system.get()),
                ("hardware", lambda: proxmox.nodes(node_name).hardware.get()),
                ("status", lambda: proxmox.nodes(node_name).status.get()),
                ("rrddata (hour)", lambda: proxmox.nodes(node_name).rrddata.get(timeframe='hour')),
                ("rrddata (day)", lambda: proxmox.nodes(node_name).rrddata.get(timeframe='day')),
            ]
            
            for endpoint_name, endpoint_func in endpoints_to_test:
                try:
                    print(f"\nTesting endpoint: {endpoint_name}")
                    result = endpoint_func()
                    
                    if isinstance(result, list):
                        print(f"  Result is a list with {len(result)} items")
                        if result:
                            print(f"  First item keys: {list(result[0].keys())}")
                            # Look for CPU-related keys
                            cpu_keys = [k for k in result[0].keys() if 'cpu' in k.lower() or 'model' in k.lower() or 'mhz' in k.lower()]
                            if cpu_keys:
                                print(f"  CPU-related keys found: {cpu_keys}")
                                for key in cpu_keys:
                                    print(f"    {key}: {result[0][key]}")
                    else:
                        print(f"  Result is a dict with keys: {list(result.keys())}")
                        # Look for CPU-related keys
                        cpu_keys = [k for k in result.keys() if 'cpu' in k.lower() or 'model' in k.lower() or 'mhz' in k.lower()]
                        if cpu_keys:
                            print(f"  CPU-related keys found: {cpu_keys}")
                            for key in cpu_keys:
                                print(f"    {key}: {result[key]}")
                    
                except Exception as e:
                    print(f"  Error: {e}")
            
            # Only test first node to avoid too much output
            break
            
    except Exception as e:
        print(f"Connection error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python test_cpu_endpoints.py <host> <username> <password> <verify_ssl>")
        print("Example: python test_cpu_endpoints.py 192.168.1.100 root@pam mypassword false")
        sys.exit(1)
    
    host = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    verify_ssl = sys.argv[4].lower() == 'true'
    
    test_cpu_endpoints(host, username, password, verify_ssl) 