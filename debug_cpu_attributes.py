#!/usr/bin/env python3
"""Debug script to test CPU data collection exactly like the integration."""

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

def debug_cpu_collection():
    """Debug CPU data collection exactly like the integration."""
    
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
        
        # Simulate the exact CPU data collection from the integration
        print("\n" + "=" * 60)
        print("SIMULATING INTEGRATION CPU DATA COLLECTION")
        print("=" * 60)
        
        # Initialize variables like the integration
        cpu_frequency = 0
        cpu_cores = 0
        cpu_sockets = 0
        cpu_total = 0
        cpu_model = "Unknown"
        
        print(f"Initial CPU values: freq={cpu_frequency}, cores={cpu_cores}, sockets={cpu_sockets}, total={cpu_total}, model={cpu_model}")
        
        # Approach 1: Try to get CPU info from status endpoint
        print("\n--- Approach 1: Status endpoint ---")
        try:
            print(f"Trying status endpoint for node {node_name}")
            status_info = proxmox.nodes(node_name).status.get()
            print(f"Status info keys: {list(status_info.keys())}")
            
            if status_info and "cpuinfo" in status_info:
                cpuinfo = status_info["cpuinfo"]
                print(f"CPU info from status: {cpuinfo}")
                
                # Extract CPU information from cpuinfo (exactly like integration)
                cpu_model = cpuinfo.get("model", "Unknown")
                print(f"  cpu_model = cpuinfo.get('model', 'Unknown') = {cpu_model}")
                
                freq_raw = cpuinfo.get("mhz", 0)
                print(f"  freq_raw = cpuinfo.get('mhz', 0) = {freq_raw}")
                try:
                    cpu_frequency = int(float(freq_raw)) if freq_raw else 0
                    print(f"  cpu_frequency = int(float(freq_raw)) = {cpu_frequency}")
                except (ValueError, TypeError):
                    cpu_frequency = 0
                    print(f"  cpu_frequency = 0 (conversion failed)")
                
                cpu_cores = cpuinfo.get("cores", 0)
                print(f"  cpu_cores = cpuinfo.get('cores', 0) = {cpu_cores}")
                
                cpu_sockets = cpuinfo.get("sockets", 0)
                print(f"  cpu_sockets = cpuinfo.get('sockets', 0) = {cpu_sockets}")
                
                cpu_total = cpuinfo.get("cpus", 0)
                print(f"  cpu_total = cpuinfo.get('cpus', 0) = {cpu_total}")
                
                print(f"Parsed CPU info from status: model={cpu_model}, freq={cpu_frequency}, cores={cpu_cores}, sockets={cpu_sockets}, total={cpu_total}")
            else:
                print("No cpuinfo found in status")
                
        except Exception as e:
            print(f"Failed to get CPU info from status: {e}")
        
        # Create node_load_data like the integration
        print("\n--- Creating node_load_data ---")
        node_load_data = {}
        node_load_data[node_name] = {
            "cpu_frequency": cpu_frequency,
            "cpu_cores": cpu_cores,
            "cpu_sockets": cpu_sockets,
            "cpu_total": cpu_total,
            "cpu_model": cpu_model,
        }
        
        print(f"Final node_load_data for {node_name}: {node_load_data[node_name]}")
        
        # Simulate sensor attribute creation
        print("\n--- Simulating sensor attributes ---")
        load_data = node_load_data[node_name]
        
        attributes = {
            "cpu_frequency_mhz": load_data.get("cpu_frequency", 0),
            "cpu_cores": load_data.get("cpu_cores", 0),
            "cpu_sockets": load_data.get("cpu_sockets", 0),
            "cpu_total": load_data.get("cpu_total", 0),
            "cpu_model": load_data.get("cpu_model", "Unknown"),
        }
        
        print(f"Final sensor attributes: {attributes}")
        print(f"  cpu_frequency_mhz: {attributes['cpu_frequency_mhz']}")
        print(f"  cpu_cores: {attributes['cpu_cores']}")
        print(f"  cpu_sockets: {attributes['cpu_sockets']}")
        print(f"  cpu_total: {attributes['cpu_total']}")
        print(f"  cpu_model: {attributes['cpu_model']}")
        
        print("\n✓ Debug completed!")
        return True
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

if __name__ == "__main__":
    debug_cpu_collection() 