#!/usr/bin/env python3
"""Debug script to examine Proxmox API response structure for CPU information."""

import json
import sys
from proxmoxer import ProxmoxAPI

def debug_proxmox_api(host, username, password, verify_ssl=False):
    """Debug Proxmox API responses to understand the data structure."""
    
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
        print("=" * 50)
        
        # Get nodes
        nodes = proxmox.nodes.get()
        print(f"Found {len(nodes)} nodes:")
        for node in nodes:
            print(f"  - {node['node']}")
        
        print("\n" + "=" * 50)
        
        # For each node, examine the API responses
        for node in nodes:
            node_name = node['node']
            print(f"\nExamining node: {node_name}")
            print("-" * 30)
            
            # 1. Get node status
            try:
                status = proxmox.nodes(node_name).status.get()
                print(f"Node status keys: {list(status.keys())}")
                print(f"Node status: {json.dumps(status, indent=2)}")
            except Exception as e:
                print(f"Error getting node status: {e}")
            
            print("\n" + "-" * 30)
            
            # 2. Try to get CPU info specifically
            try:
                # Try different endpoints that might contain CPU info
                print("Trying different CPU info endpoints:")
                
                # Try rrddata for CPU
                try:
                    rrd_cpu = proxmox.nodes(node_name).rrddata.get(timeframe='hour')
                    print(f"RRD data keys: {list(rrd_cpu[0].keys()) if rrd_cpu else 'No data'}")
                    if rrd_cpu:
                        print(f"First RRD entry: {json.dumps(rrd_cpu[0], indent=2)}")
                except Exception as e:
                    print(f"RRD data error: {e}")
                
                # Try system info
                try:
                    system = proxmox.nodes(node_name).system.get()
                    print(f"System info keys: {list(system.keys())}")
                    print(f"System info: {json.dumps(system, indent=2)}")
                except Exception as e:
                    print(f"System info error: {e}")
                
                # Try hardware info
                try:
                    hardware = proxmox.nodes(node_name).hardware.get()
                    print(f"Hardware info keys: {list(hardware.keys())}")
                    print(f"Hardware info: {json.dumps(hardware, indent=2)}")
                except Exception as e:
                    print(f"Hardware info error: {e}")
                
                # Try to get CPU info from different paths
                try:
                    cpu_info = proxmox.nodes(node_name).hardware.cpu.get()
                    print(f"CPU info: {json.dumps(cpu_info, indent=2)}")
                except Exception as e:
                    print(f"CPU info error: {e}")
                
            except Exception as e:
                print(f"Error getting CPU info: {e}")
            
            print("\n" + "=" * 50)
            
            # Only examine first node to avoid too much output
            break
            
    except Exception as e:
        print(f"Connection error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python debug_cpu_info.py <host> <username> <password> <verify_ssl>")
        print("Example: python debug_cpu_info.py 192.168.1.100 root@pam mypassword false")
        sys.exit(1)
    
    host = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    verify_ssl = sys.argv[4].lower() == 'true'
    
    debug_proxmox_api(host, username, password, verify_ssl) 