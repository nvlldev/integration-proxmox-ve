#!/usr/bin/env python3
"""
Test script to verify that the custom coordinator fix works correctly.
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
        """Simulate Home Assistant coordinator behavior (doesn't notify entities)."""
        self.update_count += 1
        _LOGGER.debug("Mock coordinator: Updating data (count: %s)", self.update_count)
        
        # Update data
        self.data = {"test": f"value_{self.update_count}"}
        _LOGGER.debug("Mock coordinator: Data updated to %s", self.data)
        
        # Note: This is the problem - Home Assistant coordinator doesn't notify entities!
        _LOGGER.debug("Mock coordinator: NOT notifying entities (this is the problem)")

# Custom coordinator that fixes the issue
class ProxmoxDataUpdateCoordinator(MockDataUpdateCoordinator):
    """Custom coordinator that properly notifies entities."""
    
    async def async_request_refresh(self) -> None:
        """Request a refresh of the data and notify all entities."""
        _LOGGER.debug("ProxmoxDataUpdateCoordinator: Requesting refresh")
        
        # Call the parent method to update data
        await super().async_request_refresh()
        
        # Manually notify all entities after data update
        if hasattr(self, '_listeners') and self._listeners:
            _LOGGER.debug("ProxmoxDataUpdateCoordinator: Notifying %s entities", len(self._listeners))
            for listener in self._listeners:
                try:
                    # Check if this is a bound method (entity update method)
                    if hasattr(listener, '__self__') and hasattr(listener.__self__, 'async_handle_coordinator_update'):
                        await listener.__self__.async_handle_coordinator_update()
                        _LOGGER.debug("ProxmoxDataUpdateCoordinator: Successfully notified entity")
                    else:
                        _LOGGER.debug("ProxmoxDataUpdateCoordinator: Skipping non-entity listener")
                except Exception as e:
                    _LOGGER.error("ProxmoxDataUpdateCoordinator: Error notifying entity: %s", e)
        else:
            _LOGGER.debug("ProxmoxDataUpdateCoordinator: No listeners to notify")

# Mock entity
class MockEntity:
    def __init__(self, name, coordinator):
        self.name = name
        self.coordinator = coordinator
        self.value = "initial"
        self.update_count = 0
        
        # Register with coordinator
        coordinator.add_listener(self.async_handle_coordinator_update)
        _LOGGER.debug("Entity %s: Registered with coordinator", name)
    
    async def async_handle_coordinator_update(self):
        """Handle coordinator update."""
        self.update_count += 1
        old_value = self.value
        
        # Update value from coordinator data
        if self.coordinator.data:
            self.value = self.coordinator.data.get("test", "unknown")
        
        _LOGGER.debug("Entity %s: Updated %s -> %s (update count: %s)", 
                     self.name, old_value, self.value, self.update_count)

async def test_coordinator():
    """Test the coordinator behavior."""
    _LOGGER.info("=== TESTING COORDINATOR BEHAVIOR ===")
    
    # Test 1: Standard coordinator (problematic)
    _LOGGER.info("--- Test 1: Standard Coordinator (Problematic) ---")
    standard_coordinator = MockDataUpdateCoordinator(
        None, _LOGGER, "standard", None, timedelta(seconds=30)
    )
    
    entity1 = MockEntity("Entity1", standard_coordinator)
    entity2 = MockEntity("Entity2", standard_coordinator)
    
    _LOGGER.info("Initial values: Entity1=%s, Entity2=%s", entity1.value, entity2.value)
    
    # Trigger refresh
    await standard_coordinator.async_request_refresh()
    
    _LOGGER.info("After refresh: Entity1=%s (updates: %s), Entity2=%s (updates: %s)", 
                 entity1.value, entity1.update_count, entity2.value, entity2.update_count)
    
    # Test 2: Custom coordinator (fixed)
    _LOGGER.info("--- Test 2: Custom Coordinator (Fixed) ---")
    custom_coordinator = ProxmoxDataUpdateCoordinator(
        None, _LOGGER, "custom", None, timedelta(seconds=30)
    )
    
    entity3 = MockEntity("Entity3", custom_coordinator)
    entity4 = MockEntity("Entity4", custom_coordinator)
    
    _LOGGER.info("Initial values: Entity3=%s, Entity4=%s", entity3.value, entity4.value)
    
    # Trigger refresh
    await custom_coordinator.async_request_refresh()
    
    _LOGGER.info("After refresh: Entity3=%s (updates: %s), Entity4=%s (updates: %s)", 
                 entity3.value, entity3.update_count, entity4.value, entity4.update_count)
    
    # Test 3: Multiple refreshes
    _LOGGER.info("--- Test 3: Multiple Refreshes ---")
    await custom_coordinator.async_request_refresh()
    await custom_coordinator.async_request_refresh()
    
    _LOGGER.info("After multiple refreshes: Entity3=%s (updates: %s), Entity4=%s (updates: %s)", 
                 entity3.value, entity3.update_count, entity4.value, entity4.update_count)
    
    _LOGGER.info("=== TEST COMPLETED ===")

if __name__ == "__main__":
    asyncio.run(test_coordinator()) 