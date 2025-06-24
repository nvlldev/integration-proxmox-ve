#!/usr/bin/env python3
"""
Test script to test manual update functionality.
"""

import asyncio
import logging
from datetime import timedelta

# Set up logging
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

# Mock the manual update function
async def async_trigger_manual_update(hass, entry_id):
    """Manually trigger an update for all entities."""
    _LOGGER.debug("=== MANUAL UPDATE TRIGGERED FOR ENTRY %s ===", entry_id)
    
    coordinator_key = f"{entry_id}_coordinator"
    coordinator = hass.data.get("proxmox_ve", {}).get(coordinator_key)
    
    if not coordinator:
        _LOGGER.error("No coordinator found for entry %s", entry_id)
        return
    
    try:
        _LOGGER.debug("Triggering manual coordinator refresh...")
        await coordinator.async_request_refresh()
        _LOGGER.debug("Manual coordinator refresh completed")
        
        # Manually notify all entities
        if hasattr(coordinator, '_listeners') and coordinator._listeners:
            _LOGGER.debug("Manually notifying %s entities", len(coordinator._listeners))
            for i, listener in enumerate(coordinator._listeners):
                try:
                    _LOGGER.debug("Manually notifying entity %s", i+1)
                    listener()
                    _LOGGER.debug("Successfully manually notified entity %s", i+1)
                except Exception as e:
                    _LOGGER.error("Error manually notifying entity %s: %s", i+1, e)
        else:
            _LOGGER.warning("No listeners found on coordinator")
            
    except Exception as e:
        _LOGGER.error("Error during manual update: %s", e)
    
    _LOGGER.debug("=== MANUAL UPDATE COMPLETED ===")

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
            
            # Note: We're NOT automatically notifying listeners here to simulate the issue
            _LOGGER.debug("NOT automatically notifying listeners (simulating the issue)")
            
            _LOGGER.debug("=== COORDINATOR REFRESH COMPLETED ===")
        except Exception as e:
            _LOGGER.error("Error in coordinator refresh: %s", e)

class MockCoordinatorEntity:
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
        _LOGGER.debug("Created coordinator entity: %s", self._attr_name)
    
    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        self.update_count += 1
        _LOGGER.debug("=== ENTITY UPDATE TRIGGERED FOR %s (count: %s) ===", self._attr_name, self.update_count)
        
        if not self.coordinator.data:
            _LOGGER.debug("No coordinator data available for %s", self._attr_name)
            return
        
        _LOGGER.debug("Updating entity %s with new coordinator data", self._attr_name)
        
        if self._device_type == "Node":
            for node in self.coordinator.data.get("nodes", []):
                if node.get("node") == self._device_id:
                    _LOGGER.debug("Found matching node: %s", node.get("node"))
                    old_value = self._attr_native_value
                    self._update_node_value(node)
                    _LOGGER.debug("Updated node entity %s: %s -> %s", self._attr_name, old_value, self._attr_native_value)
                    break
    
    def _update_node_value(self, node_data):
        """Update entity value from node data."""
        if self._raw_attr_name == "cpu_usage_percent":
            self._attr_native_value = float(node_data.get("cpu", 0)) * 100
    
    @property
    def native_value(self):
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
            }
        ]
    }
    
    _LOGGER.debug("Returning mock data")
    return data

async def test_manual_update():
    """Test the manual update functionality."""
    
    _LOGGER.info("=== STARTING MANUAL UPDATE TEST ===")
    
    # Create mock hass
    mock_hass = type('MockHass', (), {"data": {"proxmox_ve": {}}})()
    
    # Create coordinator
    coordinator = MockDataUpdateCoordinator(
        mock_hass, 
        _LOGGER, 
        "proxmox", 
        mock_update_data, 
        timedelta(seconds=10)
    )
    
    # Store coordinator in hass data
    mock_hass.data["proxmox_ve"]["test_entry_coordinator"] = coordinator
    
    _LOGGER.debug("Created coordinator: %s", coordinator.name)
    
    # Create entities
    cpu_entity = MockCoordinatorEntity(coordinator, "Node", "pve-0001", "cpu_usage_percent")
    
    print(f"\nInitial state:")
    print(f"  Coordinator listeners: {len(coordinator._listeners)}")
    print(f"  CPU entity value: {cpu_entity.native_value}%")
    print(f"  CPU entity updates: {cpu_entity.update_count}")
    
    # Test coordinator refresh (without automatic notification)
    print("\nTesting coordinator refresh (without automatic notification)...")
    await coordinator.async_request_refresh()
    
    print(f"\nAfter coordinator refresh (without notification):")
    print(f"  Coordinator updates: {coordinator.update_count}")
    print(f"  CPU entity value: {cpu_entity.native_value}%")
    print(f"  CPU entity updates: {cpu_entity.update_count}")
    
    # Test manual update
    print("\nTesting manual update...")
    await async_trigger_manual_update(mock_hass, "test_entry")
    
    print(f"\nAfter manual update:")
    print(f"  Coordinator updates: {coordinator.update_count}")
    print(f"  CPU entity value: {cpu_entity.native_value}%")
    print(f"  CPU entity updates: {cpu_entity.update_count}")
    
    _LOGGER.info("=== MANUAL UPDATE TEST COMPLETED ===")

if __name__ == "__main__":
    asyncio.run(test_manual_update()) 