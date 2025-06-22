#!/usr/bin/env python3
"""Test script that reads credentials from .env.test file."""

import os
import sys
from getpass import getpass
from proxmoxer import ProxmoxAPI

def load_env_file(file_path):
    """Load environment variables from .env file."""
    env_vars = {}
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
        return env_vars
    except FileNotFoundError:
        print(f"Error: {file_path} not found")
        return None
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

def test_proxmox_with_env():
    """Test Proxmox API using credentials from .env.test file."""
    
    # Load environment variables
    env_vars = load_env_file('.env.test')
    if not env_vars:
        return False
    
    # Extract credentials
    url = env_vars.get('PROXMOX_URL')
    username = env_vars.get('PROXMOX_USER')
    password = env_vars.get('PROXMOX_PASSWORD')
    
    if not url or not username or not password:
        print("Error: Missing PROXMOX_URL, PROXMOX_USER, or PROXMOX_PASSWORD in .env.test file")
        return False
    
    # Extract host from URL
    if url.startswith('https://'):
        host = url[8:]  # Remove 'https://'
    elif url.startswith('http://'):
        host = url[7:]  # Remove 'http://'
    else:
        host = url
    
    # Remove port if present
    if ':' in host:
        host = host.split(':')[0]
    
    print(f"Host: {host}")
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password)}")  # Show masked password
    
    # Test connection
    try:
        print(f"\nConnecting to {host}...")
        proxmox = ProxmoxAPI(
            host=host,
            user=username,
            password=password,
            verify_ssl=False  # Set to True if you have valid SSL certificates
        )
        
        # Get nodes
        nodes = proxmox.nodes.get()
        print(f"✓ Connected! Found {len(nodes)} nodes")
        
        if not nodes:
            print("No nodes found!")
            return False
        
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
                print(f"   Full CPU data: {first_cpu}")
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
                print(f"   Full CPU data: {data}")
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
                if cpuinfo:
                    print(f"   First CPU info: {cpuinfo[0]}")
            if 'cpu' in system:
                print(f"   CPU data found: {system['cpu']}")
        except Exception as e:
            print(f"   ✗ FAILED: {e}")
        
        print("\n✓ Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_proxmox_with_env() 