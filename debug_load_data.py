#!/usr/bin/env python3
"""Debug script to test Proxmox load data retrieval."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'custom_components', 'proxmox'))

# Mock homeassistant.const to avoid import errors
sys.modules['homeassistant.const'] = type('MockModule', (), {'CONF_HOST': 'host', 'CONF_PASSWORD': 'password', 'CONF_USERNAME': 'username'})

from api import ProxmoxClient

def debug_load_data():
    """Debug the Proxmox load data retrieval."""
    # You'll need to update these with your actual credentials
    host = "your-proxmox-host:8006"  # Update this
    username = "your-username"  # Update this
    password = "your-password"  # Update this
    
    print("Please update the credentials in this script and run it to test load data retrieval.")
    print("This will help us understand why load data isn't showing up in Home Assistant.")
    
    # Uncomment the following lines and update credentials to test:
    """
    try:
        client = ProxmoxClient(host=host, username=username, password=password, verify_ssl=False)
        client.authenticate()
        
        print("=== Testing Load Data Retrieval ===")
        
        # Get nodes
        nodes = client.proxmox.nodes.get()
        print(f"Nodes found: {len(nodes)}")
        
        for node in nodes:
            node_name = node['node']
            print(f"\n--- Testing Node: {node_name} ---")
            
            # Test 1: Try RRD data with different timeframes
            print("1. Testing RRD data retrieval:")
            for timeframe in ["hour", "day", "week"]:
                try:
                    rrd_data = client.proxmox.nodes(node_name).rrddata.get(timeframe=timeframe)
                    print(f"   Timeframe '{timeframe}': {len(rrd_data)} data points")
                    if rrd_data:
                        latest = rrd_data[-1]
                        print(f"   Latest data: {latest}")
                        if 'loadavg' in latest:
                            print(f"   Load average: {latest['loadavg']}")
                        else:
                            print(f"   No loadavg field found. Available fields: {list(latest.keys())}")
                    else:
                        print(f"   No data returned")
                except Exception as e:
                    print(f"   Error with timeframe '{timeframe}': {e}")
            
            # Test 2: Try node status
            print("\n2. Testing node status:")
            try:
                status_data = client.proxmox.nodes(node_name).status.get()
                print(f"   Status data keys: {list(status_data.keys())}")
                if 'loadavg' in status_data:
                    print(f"   Load average from status: {status_data['loadavg']}")
                else:
                    print(f"   No loadavg in status data")
                if 'cpuinfo' in status_data:
                    print(f"   CPU info available: {list(status_data['cpuinfo'].keys())}")
                else:
                    print(f"   No cpuinfo in status data")
            except Exception as e:
                print(f"   Error getting status: {e}")
            
            # Test 3: Try different RRD data parameters
            print("\n3. Testing RRD data with different parameters:")
            try:
                # Try without timeframe parameter
                rrd_data = client.proxmox.nodes(node_name).rrddata.get()
                print(f"   RRD data without timeframe: {len(rrd_data)} data points")
                if rrd_data:
                    latest = rrd_data[-1]
                    print(f"   Latest data fields: {list(latest.keys())}")
            except Exception as e:
                print(f"   Error getting RRD data without timeframe: {e}")
                
    except Exception as e:
        print(f"Error: {e}")
    """

if __name__ == "__main__":
    debug_load_data() 