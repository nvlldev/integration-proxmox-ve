#!/usr/bin/env python3
"""
Test script to debug coordinator and entity update issues.
"""

import asyncio
import logging
from datetime import timedelta

# Set up logging
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

# Mock Home Assistant components
class MockDataUpdateCoordinator:
    def __init__(self, hass, logger, name, update_method, update_interval):
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_method = update_method
        self.update_interval = update_interval
        self.data = None
        self._listeners = []
        self.update_count = 0
    
    def add_listener(self, listener):
        self._listeners.append(listener)
        _LOGGER.debug("Added listener to coordinator, total listeners: %s", len(self._listeners))
    
    async def async_request_refresh(self):
        self.update_count += 1
        _LOGGER.debug("=== COORDINATOR REFRESH REQUESTED (count: %s) ===", self.update_count)
        
        try:
            # Call the update method
            self.data = await self.update_method()
            _LOGGER.debug("Update method completed successfully")
            
            # Notify all listeners
            _LOGGER.debug("Notifying %s listeners", len(self._listeners))
            for i, listener in enumerate(self._listeners):
                try:
                    _LOGGER.debug("Notifying listener %s", i+1)
                    listener()
                    _LOGGER.debug("Successfully notified listener %s", i+1)
                except Exception as e:
                    _LOGGER.error("Error notifying listener %s: %s", i+1, e)
            
            _LOGGER.debug("=== COORDINATOR REFRESH COMPLETED ===")
        except Exception as e:
            _LOGGER.error("Error in coordinator refresh: %s", e)

class MockSensor:
    def __init__(self, coordinator, device_type, device_id, attr_name):
        self.coordinator = coordinator
        self._device_type = device_type
        self._device_id = device_id
        self._raw_attr_name = attr_name
        self._attr_native_value = 0
        self._attr_name = f"Test {device_type} {attr_name}"
        self.update_count = 0
        
        # Register with coordinator
        coordinator.add_listener(self._handle_coordinator_update)
        _LOGGER.debug("Created sensor: %s (ID: %s, Type: %s)", self._attr_name, device_id, device_type)
    
    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        self.update_count += 1
        _LOGGER.debug("=== SENSOR UPDATE TRIGGERED FOR %s (count: %s) ===", self._attr_name, self.update_count)
        
        if not self.coordinator.data:
            _LOGGER.debug("No coordinator data available for sensor %s", self._attr_name)
            return
        
        _LOGGER.debug("Updating sensor %s with new coordinator data", self._attr_name)
        _LOGGER.debug("Device type: %s, Device ID: %s", self._device_type, self._device_id)
        _LOGGER.debug("Raw attr name: %s", self._raw_attr_name)
        
        if self._device_type == "Node":
            for node in self.coordinator.data.get("nodes", []):
                if node.get("node") == self._device_id:
                    _LOGGER.debug("Found matching node: %s", node.get("node"))
                    old_value = self._attr_native_value
                    self._update_node_value(node)
                    _LOGGER.debug("Updated node sensor %s: %s -> %s", self._attr_name, old_value, self._attr_native_value)
                    break
            else:
                _LOGGER.warning("No matching node found for device ID: %s", self._device_id)
                _LOGGER.debug("Available nodes: %s", [n.get("node") for n in self.coordinator.data.get("nodes", [])])
    
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
        _LOGGER.debug("Getting native_value for %s: %s", self._attr_name, self._attr_native_value)
        return self._attr_native_value

async def mock_update_data():
    """Mock update data function."""
    _LOGGER.debug("=== MOCK UPDATE DATA FUNCTION CALLED ===")
    
    # Simulate some delay
    await asyncio.sleep(0.1)
    
    # Return mock data
    data = {
        "nodes": [
            {
                "node": "pve-0001",
                "cpu": 0.25,  # 25% CPU usage
                "mem": 1024 * 1024 * 1024,  # 1GB used
                "maxmem": 4 * 1024 * 1024 * 1024,  # 4GB total
                "disk": 10 * 1024 * 1024 * 1024,  # 10GB used
                "maxdisk": 100 * 1024 * 1024 * 1024,  # 100GB total
                "uptime": 3600,  # 1 hour uptime
            }
        ],
        "node_load_data": {
            "pve-0001": {
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
    
    _LOGGER.debug("Returning mock data: %s", data)
    return data

async def test_coordinator_debug():
    """Test the coordinator debug functionality."""
    
    _LOGGER.info("=== STARTING COORDINATOR DEBUG TEST ===")
    
    # Create mock hass
    mock_hass = type('MockHass', (), {})()
    
    # Create coordinator
    coordinator = MockDataUpdateCoordinator(
        mock_hass, 
        _LOGGER, 
        "proxmox", 
        mock_update_data, 
        timedelta(seconds=10)
    )
    
    _LOGGER.debug("Created coordinator: %s", coordinator.name)
    _LOGGER.debug("Update interval: %s seconds", coordinator.update_interval.total_seconds())
    _LOGGER.debug("Update method: %s", coordinator.update_method.__name__)
    
    # Create sensors
    cpu_sensor = MockSensor(coordinator, "Node", "pve-0001", "cpu_usage_percent")
    memory_sensor = MockSensor(coordinator, "Node", "pve-0001", "memory_usage_percent")
    load_sensor = MockSensor(coordinator, "Node", "pve-0001", "load_average_1min")
    
    print("\nInitial sensor values:")
    print(f"  CPU Usage: {cpu_sensor.native_value}%")
    print(f"  Memory Usage: {memory_sensor.native_value}%")
    print(f"  Load Average: {load_sensor.native_value}")
    
    # Test coordinator refresh
    print("\nTesting coordinator refresh...")
    await coordinator.async_request_refresh()
    
    print("\nUpdated sensor values:")
    print(f"  CPU Usage: {cpu_sensor.native_value}%")
    print(f"  Memory Usage: {memory_sensor.native_value}%")
    print(f"  Load Average: {load_sensor.native_value}")
    
    print(f"\nUpdate counts:")
    print(f"  Coordinator updates: {coordinator.update_count}")
    print(f"  CPU sensor updates: {cpu_sensor.update_count}")
    print(f"  Memory sensor updates: {memory_sensor.update_count}")
    print(f"  Load sensor updates: {load_sensor.update_count}")
    
    _LOGGER.info("=== COORDINATOR DEBUG TEST COMPLETED ===")

if __name__ == "__main__":
    asyncio.run(test_coordinator_debug()) 