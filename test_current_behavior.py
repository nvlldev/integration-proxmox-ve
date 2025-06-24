#!/usr/bin/env python3
"""
Test script to understand the current behavior of entity updates.
"""

import asyncio
import logging
from datetime import timedelta

# Set up logging
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

# Simulate the current issue
class MockHomeAssistantCoordinator:
    def __init__(self, update_interval):
        self.update_interval = update_interval
        self.data = None
        self._listeners = []
        self.update_count = 0
    
    def add_listener(self, listener):
        self._listeners.append(listener)
        _LOGGER.debug("Added listener, total listeners: %s", len(self._listeners))
    
    async def async_request_refresh(self):
        """Simulate Home Assistant coordinator behavior."""
        self.update_count += 1
        _LOGGER.debug("=== COORDINATOR REFRESH REQUESTED (count: %s) ===", self.update_count)
        
        # Simulate data update
        self.data = {
            "nodes": [
                {
                    "node": "pve-0001",
                    "cpu": 0.25,  # 25% CPU usage
                    "mem": 1024 * 1024 * 1024,  # 1GB used
                    "maxmem": 4 * 1024 * 1024 * 1024,  # 4GB total
                }
            ]
        }
        
        _LOGGER.debug("Data updated, but NOT notifying listeners (simulating the issue)")
        _LOGGER.debug("=== COORDINATOR REFRESH COMPLETED ===")

class MockCoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.update_count = 0
        self._attr_name = "Test Entity"
        self._attr_native_value = 0
        
        # Register with coordinator
        coordinator.add_listener(self.async_handle_coordinator_update)
        _LOGGER.debug("Created coordinator entity")
    
    async def async_handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        self.update_count += 1
        _LOGGER.debug("=== ENTITY UPDATE TRIGGERED (count: %s) ===", self.update_count)
        
        if not self.coordinator.data:
            _LOGGER.debug("No coordinator data available")
            return
        
        _LOGGER.debug("Entity updated with new data")
        # Update the value
        if self.coordinator.data.get("nodes"):
            node = self.coordinator.data["nodes"][0]
            self._attr_native_value = float(node.get("cpu", 0)) * 100
            _LOGGER.debug("Updated value to: %s", self._attr_native_value)
    
    @property
    def native_value(self):
        _LOGGER.debug("Getting native_value: %s", self._attr_native_value)
        return self._attr_native_value

async def test_current_behavior():
    """Test the current behavior."""
    
    _LOGGER.info("=== STARTING CURRENT BEHAVIOR TEST ===")
    
    # Create coordinator
    coordinator = MockHomeAssistantCoordinator(timedelta(seconds=10))
    
    # Create entity
    entity = MockCoordinatorEntity(coordinator)
    
    print(f"\nInitial state:")
    print(f"  Coordinator listeners: {len(coordinator._listeners)}")
    print(f"  Entity value: {entity.native_value}")
    print(f"  Entity updates: {entity.update_count}")
    
    # Test coordinator refresh (without notification)
    print("\nTesting coordinator refresh (without notification)...")
    await coordinator.async_request_refresh()
    
    print(f"\nAfter coordinator refresh (without notification):")
    print(f"  Coordinator updates: {coordinator.update_count}")
    print(f"  Entity value: {entity.native_value}")
    print(f"  Entity updates: {entity.update_count}")
    
    # Test manual notification
    print("\nTesting manual notification...")
    for listener in coordinator._listeners:
        try:
            await listener()
            _LOGGER.debug("Successfully called listener")
        except Exception as e:
            _LOGGER.error("Error calling listener: %s", e)
    
    print(f"\nAfter manual notification:")
    print(f"  Coordinator updates: {coordinator.update_count}")
    print(f"  Entity value: {entity.native_value}")
    print(f"  Entity updates: {entity.update_count}")
    
    _LOGGER.info("=== CURRENT BEHAVIOR TEST COMPLETED ===")

if __name__ == "__main__":
    asyncio.run(test_current_behavior()) 