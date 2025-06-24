#!/usr/bin/env python3
"""
Test script to verify update interval functionality for Proxmox VE integration.
"""

import asyncio
from datetime import timedelta

# Mock the Home Assistant components for testing
class MockCoordinator:
    def __init__(self, update_interval):
        self.update_interval = update_interval
        self.update_count = 0
    
    async def async_request_refresh(self):
        self.update_count += 1
        print(f"Coordinator updated (count: {self.update_count})")

class MockHass:
    def __init__(self):
        self.data = {"proxmox_ve": {}}

class MockEntry:
    def __init__(self, entry_id, options, data):
        self.entry_id = entry_id
        self.options = options
        self.data = data

async def test_update_interval():
    """Test the update interval functionality."""
    
    # Mock setup
    hass = MockHass()
    entry = MockEntry("test_entry", {"update_interval": 30}, {"update_interval": 60})
    
    # Create a mock coordinator
    coordinator = MockCoordinator(timedelta(seconds=60))
    hass.data["proxmox_ve"]["test_entry_coordinator"] = coordinator
    
    print(f"Initial interval: {coordinator.update_interval.total_seconds()} seconds")
    
    # Simulate options update
    entry.options = {"update_interval": 10}
    
    # Test the update function
    from custom_components.proxmox_ve import async_restart_coordinator
    
    await async_restart_coordinator(hass, entry)
    
    print(f"Updated interval: {coordinator.update_interval.total_seconds()} seconds")
    print(f"Update count: {coordinator.update_count}")
    
    # Test with different interval
    entry.options = {"update_interval": 5}
    await async_restart_coordinator(hass, entry)
    
    print(f"Final interval: {coordinator.update_interval.total_seconds()} seconds")
    print(f"Final update count: {coordinator.update_count}")

if __name__ == "__main__":
    asyncio.run(test_update_interval()) 