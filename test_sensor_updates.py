#!/usr/bin/env python3
"""
Test script to verify sensor update functionality for Proxmox VE integration.
"""

import asyncio
from datetime import timedelta

# Mock the Home Assistant components for testing
class MockCoordinator:
    def __init__(self, update_interval):
        self.update_interval = update_interval
        self.data = None
        self._listeners = []
    
    def add_listener(self, listener):
        self._listeners.append(listener)
    
    async def async_request_refresh(self):
        # Simulate data update
        self.data = {
            "nodes": [
                {
                    "node": "testnode",
                    "cpu": 0.25,  # 25% CPU usage
                    "mem": 1024 * 1024 * 1024,  # 1GB used
                    "maxmem": 4 * 1024 * 1024 * 1024,  # 4GB total
                    "disk": 10 * 1024 * 1024 * 1024,  # 10GB used
                    "maxdisk": 100 * 1024 * 1024 * 1024,  # 100GB total
                    "uptime": 3600,  # 1 hour uptime
                }
            ],
            "node_load_data": {
                "testnode": {
                    "loadavg_1min": 1.5,
                    "loadavg_5min": 1.2,
                    "loadavg_15min": 1.0,
                    "cpu_frequency": 2400,
                    "cpu_cores": 4,
                    "cpu_sockets": 1,
                    "cpu_total": 4,
                    "cpu_model": "Intel Core i5"
                }
            }
        }
        
        # Notify listeners
        for listener in self._listeners:
            listener()

class MockSensor:
    def __init__(self, coordinator, device_type, device_id, attr_name):
        self.coordinator = coordinator
        self._device_type = device_type
        self._device_id = device_id
        self._raw_attr_name = attr_name
        self._attr_native_value = 0
        self._attr_name = f"Test {device_type} {attr_name}"
        
        # Register with coordinator
        coordinator.add_listener(self._handle_coordinator_update)
    
    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        if not self.coordinator.data:
            return
        
        print(f"Updating sensor {self._attr_name}")
        
        if self._device_type == "Node":
            for node in self.coordinator.data.get("nodes", []):
                if node.get("node") == self._device_id:
                    self._update_node_value(node)
                    break
    
    def _update_node_value(self, node_data):
        """Update sensor value from node data."""
        if self._raw_attr_name == "cpu_usage_percent":
            self._attr_native_value = float(node_data.get("cpu", 0)) * 100
        elif self._raw_attr_name == "memory_used_bytes":
            self._attr_native_value = node_data.get("mem", 0)
        elif self._raw_attr_name == "memory_usage_percent":
            mem = float(node_data.get("mem", 0))
            maxmem = float(node_data.get("maxmem", 1))
            self._attr_native_value = (mem / maxmem * 100) if maxmem > 0 else 0.0
        elif self._raw_attr_name == "load_average_1min":
            node_load_data = self.coordinator.data.get("node_load_data", {}).get(self._device_id, {})
            self._attr_native_value = float(node_load_data.get("loadavg_1min", 0))
    
    @property
    def native_value(self):
        return self._attr_native_value

async def test_sensor_updates():
    """Test the sensor update functionality."""
    
    # Create coordinator
    coordinator = MockCoordinator(timedelta(seconds=10))
    
    # Create sensors
    cpu_sensor = MockSensor(coordinator, "Node", "testnode", "cpu_usage_percent")
    memory_sensor = MockSensor(coordinator, "Node", "testnode", "memory_usage_percent")
    load_sensor = MockSensor(coordinator, "Node", "testnode", "load_average_1min")
    
    print("Initial sensor values:")
    print(f"  CPU Usage: {cpu_sensor.native_value}%")
    print(f"  Memory Usage: {memory_sensor.native_value}%")
    print(f"  Load Average: {load_sensor.native_value}")
    
    # Simulate coordinator update
    print("\nTriggering coordinator update...")
    await coordinator.async_request_refresh()
    
    print("\nUpdated sensor values:")
    print(f"  CPU Usage: {cpu_sensor.native_value}%")
    print(f"  Memory Usage: {memory_sensor.native_value}%")
    print(f"  Load Average: {load_sensor.native_value}")
    
    # Simulate another update with different data
    print("\nSimulating second update with different data...")
    coordinator.data["nodes"][0]["cpu"] = 0.5  # 50% CPU usage
    coordinator.data["nodes"][0]["mem"] = 2 * 1024 * 1024 * 1024  # 2GB used
    coordinator.data["node_load_data"]["testnode"]["loadavg_1min"] = 2.5
    
    # Trigger update
    for listener in coordinator._listeners:
        listener()
    
    print("\nSecond update sensor values:")
    print(f"  CPU Usage: {cpu_sensor.native_value}%")
    print(f"  Memory Usage: {memory_sensor.native_value}%")
    print(f"  Load Average: {load_sensor.native_value}")

if __name__ == "__main__":
    asyncio.run(test_sensor_updates()) 