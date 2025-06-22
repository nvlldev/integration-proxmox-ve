#!/usr/bin/env python3
"""Simple debug script to test Proxmox API endpoints."""

import json
import sys
from proxmoxer import ProxmoxAPI

def debug_proxmox(host, username, password, verify_ssl=False):
    """Debug Proxmox API responses."""
    
    try:
        # Connect to Proxmox
        print(f"Connecting to {host} with user {username}...")
        proxmox = ProxmoxAPI(
            host=host,
            user=username,
            password=password,
            verify_ssl=verify_ssl
        )
        
        # Get nodes
        nodes = proxmox.nodes.get()
        print(f"Found {len(nodes)} nodes: {[n['node'] for n in nodes]}")
        
        if not nodes:
            print("No nodes found!")
            return
        
        node_name = nodes[0]['node']
        print(f"\nTesting node: {node_name}")
        
        # Test each endpoint
        endpoints = [
            ("hardware.cpu", lambda: proxmox.nodes(node_name).hardware.cpu.get()),
            ("hardware", lambda: proxmox.nodes(node_name).hardware.get()),
            ("system", lambda: proxmox.nodes(node_name).system.get()),
            ("status", lambda: proxmox.nodes(node_name).status.get()),
        ]
        
        for name, func in endpoints:
            print(f"\n--- Testing {name} ---")
            try:
                result = func()
                print(f"SUCCESS: {type(result)}")
                
                if isinstance(result, list):
                    print(f"List with {len(result)} items")
                    if result:
                        print(f"First item keys: {list(result[0].keys())}")
                        if name == "hardware":
                            # Look for CPU items
                            cpu_items = [item for item in result if item.get('type') == 'cpu']
                            print(f"CPU items found: {len(cpu_items)}")
                            for i, cpu in enumerate(cpu_items):
                                print(f"CPU {i}: {cpu}")
                        elif name == "hardware.cpu":
                            print(f"CPU data: {result}")
                else:
                    print(f"Dict with keys: {list(result.keys())}")
                    # Look for CPU-related keys
                    cpu_keys = [k for k in result.keys() if 'cpu' in k.lower()]
                    if cpu_keys:
                        print(f"CPU-related keys: {cpu_keys}")
                        for key in cpu_keys:
                            print(f"  {key}: {result[key]}")
                
            except Exception as e:
                print(f"ERROR: {e}")
        
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python3 debug_simple.py <host> <username> <password> <verify_ssl>")
        print("Example: python3 debug_simple.py 192.168.1.100 root@pam mypassword false")
        sys.exit(1)
    
    host = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    verify_ssl = sys.argv[4].lower() == 'true'
    
    debug_proxmox(host, username, password, verify_ssl) 