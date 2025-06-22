#!/usr/bin/env python3
"""Test script to find available Proxmox API endpoints."""

import os
import sys
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

def test_available_endpoints():
    """Test what Proxmox API endpoints are available."""
    
    # Load environment variables
    env_vars = load_env_file('.env.test')
    if not env_vars:
        return False
    
    # Extract credentials
    username = env_vars.get('PROXMOX_USER')
    password = env_vars.get('PROXMOX_PASSWORD')
    
    if not username or not password:
        print("Error: Missing credentials in .env.test file")
        return False
    
    # Use IP address directly
    host = "192.168.50.8:8006"
    
    print(f"Host: {host}")
    print(f"Username: {username}")
    
    # Test connection
    try:
        print(f"\nConnecting to {host}...")
        proxmox = ProxmoxAPI(
            host=host,
            user=username,
            password=password,
            verify_ssl=False
        )
        
        # Get nodes
        nodes = proxmox.nodes.get()
        print(f"✓ Connected! Found {len(nodes)} nodes")
        
        if not nodes:
            print("No nodes found!")
            return False
        
        node_name = nodes[0]['node']
        print(f"\nTesting node: {node_name}")
        
        # Test various endpoints to see what's available
        endpoints_to_test = [
            ("nodes.get", lambda: proxmox.nodes.get()),
            ("nodes.status", lambda: proxmox.nodes(node_name).status.get()),
            ("nodes.rrddata", lambda: proxmox.nodes(node_name).rrddata.get(timeframe='hour')),
            ("nodes.qemu", lambda: proxmox.nodes(node_name).qemu.get()),
            ("nodes.lxc", lambda: proxmox.nodes(node_name).lxc.get()),
            ("nodes.hardware", lambda: proxmox.nodes(node_name).hardware.get()),
            ("nodes.hardware.cpu", lambda: proxmox.nodes(node_name).hardware.cpu.get()),
            ("nodes.system", lambda: proxmox.nodes(node_name).system.get()),
            ("nodes.version", lambda: proxmox.nodes(node_name).version.get()),
            ("nodes.capabilities", lambda: proxmox.nodes(node_name).capabilities.get()),
        ]
        
        print("\nTesting available endpoints:")
        print("-" * 50)
        
        for name, func in endpoints_to_test:
            try:
                result = func()
                print(f"✓ {name}: SUCCESS")
                
                if isinstance(result, list):
                    print(f"  Returns list with {len(result)} items")
                    if result and len(result) > 0:
                        print(f"  First item keys: {list(result[0].keys())}")
                else:
                    print(f"  Returns dict with keys: {list(result.keys())}")
                    
            except Exception as e:
                error_msg = str(e)
                if "501" in error_msg:
                    print(f"✗ {name}: NOT IMPLEMENTED")
                elif "403" in error_msg:
                    print(f"✗ {name}: PERMISSION DENIED")
                elif "404" in error_msg:
                    print(f"✗ {name}: NOT FOUND")
                else:
                    print(f"✗ {name}: ERROR - {error_msg}")
        
        # Test specific CPU-related data from status endpoint
        print("\n" + "=" * 50)
        print("Testing CPU data from status endpoint:")
        try:
            status = proxmox.nodes(node_name).status.get()
            print(f"✓ Status endpoint works")
            print(f"Status keys: {list(status.keys())}")
            
            # Look for CPU-related information
            cpu_related_keys = [k for k in status.keys() if 'cpu' in k.lower()]
            if cpu_related_keys:
                print(f"CPU-related keys found: {cpu_related_keys}")
                for key in cpu_related_keys:
                    print(f"  {key}: {status[key]}")
            else:
                print("No CPU-related keys found in status")
                
            # Check for load average
            if 'loadavg' in status:
                print(f"Load average: {status['loadavg']}")
                
        except Exception as e:
            print(f"✗ Status endpoint failed: {e}")
        
        print("\n✓ Test completed!")
        return True
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_available_endpoints() 