#!/usr/bin/env python3
"""
Test script to debug why entities aren't being notified by the coordinator.
"""

import asyncio
import logging
from datetime import timedelta

# Set up logging
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

# Mock Home Assistant DataUpdateCoordinator
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
        """Request a refresh of the data."""
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

# Mock CoordinatorEntity base class
class MockCoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.update_count = 0
        # Register with coordinator
        coordinator.add_listener(self._handle_coordinator_update)
        _LOGGER.debug("Created coordinator entity")
    
    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        self.update_count += 1
        _LOGGER.debug("=== ENTITY UPDATE TRIGGERED (count: %s) ===", self.update_count)
        
        if not self.coordinator.data:
            _LOGGER.debug("No coordinator data available")
            return
        
        _LOGGER.debug("Entity updated with new data")
        _LOGGER.debug("Coordinator data keys: %s", list(self.coordinator.data.keys()))

class MockSensor(MockCoordinatorEntity):
    def __init__(self, coordinator, device_type, device_id, attr_name):
        super().__init__(coordinator)
        self._device_type = device_type
        self._device_id = device_id
        self._raw_attr_name = attr_name
        self._attr_native_value = 0
        self._attr_name = f"Test {device_type} {attr_name}"
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
    
    def _update_node_value(self, node_data):
        """Update sensor value from node data."""
        if self._raw_attr_name == "cpu_usage_percent":
            self._attr_native_value = float(node_data.get("cpu", 0)) * 100
    
    @property
    def native_value(self):
        _LOGGER.debug("Getting native_value for %s: %s", self._attr_name, self._attr_native_value)
        return self._attr_native_value

async def mock_update_data():
    """Mock update data function."""
    _LOGGER.debug("Mock update data called")
    return {
        "nodes": [
            {
                "node": "pve-0001",
                "cpu": 0.25,  # 25% CPU usage
                "mem": 1024 * 1024 * 1024,  # 1GB used
                "maxmem": 4 * 1024 * 1024 * 1024,  # 4GB total
            }
        ]
    }

async def test_entity_notification_debug():
    """Test entity notification debugging."""
    
    _LOGGER.info("=== STARTING ENTITY NOTIFICATION DEBUG TEST ===")
    
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
    
    # Create entities
    cpu_entity = MockSensor(coordinator, "Node", "pve-0001", "cpu_usage_percent")
    memory_entity = MockSensor(coordinator, "Node", "pve-0001", "memory_usage_percent")
    
    print(f"\nInitial state:")
    print(f"  Coordinator listeners: {len(coordinator._listeners)}")
    print(f"  CPU entity value: {cpu_entity.native_value}%")
    print(f"  Memory entity value: {memory_entity.native_value}%")
    print(f"  CPU entity updates: {cpu_entity.update_count}")
    print(f"  Memory entity updates: {memory_entity.update_count}")
    
    # Test coordinator refresh
    print("\nTesting coordinator refresh...")
    await coordinator.async_request_refresh()
    
    print(f"\nAfter coordinator refresh:")
    print(f"  Coordinator updates: {coordinator.update_count}")
    print(f"  CPU entity value: {cpu_entity.native_value}%")
    print(f"  Memory entity value: {memory_entity.native_value}%")
    print(f"  CPU entity updates: {cpu_entity.update_count}")
    print(f"  Memory entity updates: {memory_entity.update_count}")
    
    # Test second refresh with different data
    print("\nTesting second refresh with different data...")
    coordinator.data["nodes"][0]["cpu"] = 0.5  # 50% CPU usage
    
    # Trigger another refresh
    await coordinator.async_request_refresh()
    
    print(f"\nAfter second refresh:")
    print(f"  Coordinator updates: {coordinator.update_count}")
    print(f"  CPU entity value: {cpu_entity.native_value}%")
    print(f"  Memory entity value: {memory_entity.native_value}%")
    print(f"  CPU entity updates: {cpu_entity.update_count}")
    print(f"  Memory entity updates: {memory_entity.update_count}")
    
    _LOGGER.info("=== ENTITY NOTIFICATION DEBUG TEST COMPLETED ===")

if __name__ == "__main__":
    asyncio.run(test_entity_notification_debug()) 