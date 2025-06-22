#!/usr/bin/env python3
"""
Test to verify the static method implementation.
"""

import re

def test_static_method():
    """Test that async_get_options_flow is correctly implemented as a static method."""
    print("Testing static method implementation...")
    
    with open("custom_components/proxmox_ve/config_flow.py", 'r') as f:
        content = f.read()
    
    # Look for the static method pattern
    pattern = r'@staticmethod\s*\n\s*async def async_get_options_flow\s*\(\s*config_entry:\s*config_entries\.ConfigEntry\s*\)\s*->\s*OptionsFlow:'
    
    if re.search(pattern, content, re.MULTILINE):
        print("✓ Static method is correctly implemented")
        return True
    else:
        print("✗ Static method pattern not found")
        return False

def test_no_self_parameter():
    """Test that the method doesn't have a self parameter."""
    print("Testing for absence of self parameter...")
    
    with open("custom_components/proxmox_ve/config_flow.py", 'r') as f:
        content = f.read()
    
    # Look specifically for the async_get_options_flow method
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'async def async_get_options_flow' in line:
            # Check this line and the next few lines for self parameter
            method_lines = lines[i:i+5]
            method_content = '\n'.join(method_lines)
            if 'self,' in method_content:
                print("✗ Self parameter found in async_get_options_flow method")
                return False
            else:
                print("✓ No self parameter found in async_get_options_flow method")
                return True
    
    print("✗ async_get_options_flow method not found")
    return False

def main():
    """Run tests."""
    print("Testing static method fix...")
    print("=" * 40)
    
    if test_static_method() and test_no_self_parameter():
        print("\n" + "=" * 40)
        print("✓ Fix applied successfully!")
        print("The async_get_options_flow method is now correctly implemented as a static method.")
        print("Please restart Home Assistant and try the configure button again.")
    else:
        print("\n✗ Fix failed. Please check the implementation.")
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main()) 