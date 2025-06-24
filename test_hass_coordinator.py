#!/usr/bin/env python3
"""
Test script to check Home Assistant DataUpdateCoordinator behavior.
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
        self._unsub_refresh = None
    
    def add_listener(self, listener):
        self._listeners.append(listener)
        _LOGGER.debug("Added listener to coordinator, total listeners: %s", len(self._listeners))
    
    async def async_config_entry_first_refresh(self):
        """Refresh data for the first time."""
        _LOGGER.debug("=== FIRST REFRESH CALLED ===")
        await self.async_request_refresh()
    
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
                "cpu": 0.25,
                "mem": 1024 * 1024 * 1024,
                "maxmem": 4 * 1024 * 1024 * 1024,
            }
        ]
    }
    
    _LOGGER.debug("Returning mock data")
    return data

async def test_hass_coordinator():
    """Test the Home Assistant coordinator behavior."""
    
    _LOGGER.info("=== STARTING HASS COORDINATOR TEST ===")
    
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
    
    # Create entities
    entity1 = MockCoordinatorEntity(coordinator)
    entity2 = MockCoordinatorEntity(coordinator)
    
    print(f"\nInitial state:")
    print(f"  Coordinator listeners: {len(coordinator._listeners)}")
    print(f"  Entity1 updates: {entity1.update_count}")
    print(f"  Entity2 updates: {entity2.update_count}")
    
    # Test first refresh
    print("\nTesting first refresh...")
    await coordinator.async_config_entry_first_refresh()
    
    print(f"\nAfter first refresh:")
    print(f"  Coordinator updates: {coordinator.update_count}")
    print(f"  Entity1 updates: {entity1.update_count}")
    print(f"  Entity2 updates: {entity2.update_count}")
    
    # Test manual refresh
    print("\nTesting manual refresh...")
    await coordinator.async_request_refresh()
    
    print(f"\nAfter manual refresh:")
    print(f"  Coordinator updates: {coordinator.update_count}")
    print(f"  Entity1 updates: {entity1.update_count}")
    print(f"  Entity2 updates: {entity2.update_count}")
    
    _LOGGER.info("=== HASS COORDINATOR TEST COMPLETED ===")

if __name__ == "__main__":
    asyncio.run(test_hass_coordinator()) 