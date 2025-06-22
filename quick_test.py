#!/usr/bin/env python3
"""Quick test script to verify Proxmox API connection and CPU data."""

import sys
from proxmoxer import ProxmoxAPI

def quick_test(host, username, password, verify_ssl=False):
    """Quick test of Proxmox API."""
    
    try:
        print(f"Connecting to {host}...")
        proxmox = ProxmoxAPI(
            host=host,
            user=username,
            password=password,
            verify_ssl=verify_ssl
        )
        
        # Get nodes
        nodes = proxmox.nodes.get()
        print(f"✓ Connected! Found {len(nodes)} nodes")
        
        if not nodes:
            print("No nodes found!")
            return
        
        node_name = nodes[0]['node']
        print(f"\nTesting node: {node_name}")
        
        # Test hardware.cpu endpoint
        print("\n1. Testing hardware.cpu endpoint:")
        try:
            cpu_info = proxmox.nodes(node_name).hardware.cpu.get()
            print(f"   ✓ SUCCESS: {len(cpu_info)} CPU cores found")
            if cpu_info:
                first_cpu = cpu_info[0]
                print(f"   Model: {first_cpu.get('model name', 'Unknown')}")
                print(f"   Frequency: {first_cpu.get('cpu MHz', 'Unknown')} MHz")
                print(f"   Cores: {len(cpu_info)}")
        except Exception as e:
            print(f"   ✗ FAILED: {e}")
        
        # Test hardware endpoint
        print("\n2. Testing hardware endpoint:")
        try:
            hardware = proxmox.nodes(node_name).hardware.get()
            cpu_items = [item for item in hardware if item.get('type') == 'cpu']
            print(f"   ✓ SUCCESS: {len(cpu_items)} CPU items found")
            for i, cpu in enumerate(cpu_items):
                data = cpu.get('data', {})
                print(f"   CPU {i+1}: {data.get('model name', 'Unknown')}")
        except Exception as e:
            print(f"   ✗ FAILED: {e}")
        
        # Test system endpoint
        print("\n3. Testing system endpoint:")
        try:
            system = proxmox.nodes(node_name).system.get()
            print(f"   ✓ SUCCESS: Keys available: {list(system.keys())}")
            if 'cpuinfo' in system:
                cpuinfo = system['cpuinfo']
                print(f"   CPU info found: {len(cpuinfo)} items")
            if 'cpu' in system:
                print(f"   CPU data found: {system['cpu']}")
        except Exception as e:
            print(f"   ✗ FAILED: {e}")
        
        print("\n✓ Test completed!")
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python3 quick_test.py <host> <username> <password> <verify_ssl>")
        print("Example: python3 quick_test.py 192.168.1.100 root@pam mypassword false")
        sys.exit(1)
    
    host = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    verify_ssl = sys.argv[4].lower() == 'true'
    
    quick_test(host, username, password, verify_ssl) 