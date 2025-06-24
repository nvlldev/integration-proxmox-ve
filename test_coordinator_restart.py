#!/usr/bin/env python3
"""
Test script to verify coordinator restart functionality for Proxmox VE integration.
"""

import asyncio
from datetime import timedelta

# Mock the Home Assistant components for testing
class MockCoordinator:
    def __init__(self, update_interval):
        self.update_interval = update_interval
        self.data = None
        self._listeners = []
        self.shutdown_called = False
    
    def add_listener(self, listener):
        self._listeners.append(listener)
    
    async def async_shutdown(self):
        self.shutdown_called = True
        print(f"Coordinator shutdown called (interval was: {self.update_interval.total_seconds()}s)")
    
    async def async_request_refresh(self):
        print(f"Coordinator refresh requested (interval: {self.update_interval.total_seconds()}s)")
        # Simulate data update
        self.data = {"test": "data"}

class MockHass:
    def __init__(self):
        self.data = {"proxmox_ve": {}}
        self.platforms_unloaded = []
        self.platforms_loaded = []
    
    async def config_entries_async_unload_platforms(self, entry, platforms):
        self.platforms_unloaded.extend(platforms)
        print(f"Unloaded platforms: {platforms}")
        return True
    
    async def config_entries_async_forward_entry_setups(self, entry, platforms):
        self.platforms_loaded.extend(platforms)
        print(f"Loaded platforms: {platforms}")
        # Simulate creating a new coordinator
        new_coordinator = MockCoordinator(timedelta(seconds=entry.options.get("update_interval", 60)))
        self.data["proxmox_ve"][f"{entry.entry_id}_coordinator"] = new_coordinator
        return True

class MockEntry:
    def __init__(self, entry_id, options, data):
        self.entry_id = entry_id
        self.options = options
        self.data = data

async def mock_async_restart_coordinator(hass, entry):
    """Mock version of the coordinator restart function."""
    print("Starting coordinator restart for entry:", entry.entry_id)
    
    # Get the coordinator key
    coordinator_key = f"{entry.entry_id}_coordinator"
    
    # Check if coordinator exists
    if coordinator_key in hass.data["proxmox_ve"]:
        old_coordinator = hass.data["proxmox_ve"][coordinator_key]
        print(f"Found existing coordinator with interval: {old_coordinator.update_interval.total_seconds()} seconds")
        
        # Stop the old coordinator
        if hasattr(old_coordinator, 'async_shutdown'):
            await old_coordinator.async_shutdown()
            print("Successfully stopped old coordinator")
        else:
            print("Old coordinator does not have async_shutdown method")
        
        # Remove the old coordinator from hass data
        hass.data["proxmox_ve"].pop(coordinator_key)
        print("Removed old coordinator from hass data")
    else:
        print("No existing coordinator found")
    
    # Get the new interval
    new_interval = timedelta(seconds=entry.options.get("update_interval", 60))
    print(f"New update interval will be: {new_interval.total_seconds()} seconds")
    
    # Reload the sensor platform to create a new coordinator
    print("Unloading sensor platform...")
    await hass.config_entries_async_unload_platforms(entry, ["sensor"])
    print("Reloading sensor platform...")
    await hass.config_entries_async_forward_entry_setups(entry, ["sensor"])
    
    # Verify the new coordinator was created
    if coordinator_key in hass.data["proxmox_ve"]:
        new_coordinator = hass.data["proxmox_ve"][coordinator_key]
        print(f"Successfully created new coordinator with interval: {new_coordinator.update_interval.total_seconds()} seconds")
    else:
        print("Failed to create new coordinator")
    
    print("Coordinator restart completed")

async def test_coordinator_restart():
    """Test the coordinator restart functionality."""
    
    # Mock setup
    hass = MockHass()
    entry = MockEntry("test_entry", {"update_interval": 30}, {"update_interval": 60})
    
    # Create initial coordinator
    initial_coordinator = MockCoordinator(timedelta(seconds=60))
    hass.data["proxmox_ve"]["test_entry_coordinator"] = initial_coordinator
    
    print(f"Initial coordinator interval: {initial_coordinator.update_interval.total_seconds()} seconds")
    
    # Test the restart function
    print("\nTesting coordinator restart...")
    await mock_async_restart_coordinator(hass, entry)
    
    # Check results
    print(f"\nResults:")
    print(f"  Old coordinator shutdown called: {initial_coordinator.shutdown_called}")
    print(f"  Platforms unloaded: {hass.platforms_unloaded}")
    print(f"  Platforms loaded: {hass.platforms_loaded}")
    
    # Check if new coordinator was created
    if "test_entry_coordinator" in hass.data["proxmox_ve"]:
        new_coordinator = hass.data["proxmox_ve"]["test_entry_coordinator"]
        print(f"  New coordinator interval: {new_coordinator.update_interval.total_seconds()} seconds")
        print(f"  New coordinator is different: {new_coordinator is not initial_coordinator}")
    else:
        print("  No new coordinator found!")
    
    # Test with different interval
    print("\nTesting with different interval...")
    entry.options = {"update_interval": 10}
    await mock_async_restart_coordinator(hass, entry)
    
    # Check final results
    if "test_entry_coordinator" in hass.data["proxmox_ve"]:
        final_coordinator = hass.data["proxmox_ve"]["test_entry_coordinator"]
        print(f"  Final coordinator interval: {final_coordinator.update_interval.total_seconds()} seconds")

if __name__ == "__main__":
    asyncio.run(test_coordinator_restart()) 