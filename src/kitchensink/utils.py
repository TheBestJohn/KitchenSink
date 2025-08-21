import sounddevice as sd

def select_audio_device(direction='input'):
    """
    Interactively prompts the user to select an audio device from a list.

    Args:
        device_list (list): A list of device dictionaries from sounddevice.query_devices().
        direction (str): The direction of the device ('input' or 'output'), used for prompts.

    Returns:
        The device name (str) or index (int) of the selected device, or None if no selection is made.
    """
    if direction == "output":
        try:
            devices = sd.query_devices()
            device_list = [d for d in devices if d.get('max_output_channels', 0) > 0]
        except Exception as e:
            print(f"Could not query audio devices: {e}")
            device_list = []    
    else:
        try:
            devices = sd.query_devices()
            # Filter for devices with at least one input channel
            device_list = [device for device in devices if device.get('max_input_channels', 0) > 0]
        except Exception as e:
            print(f"Could not query audio devices: {e}")
            device_list = []    
        
    print(f"\n--- Select an audio {direction} device ---")
    if not device_list:
        print(f"No {direction} devices found.")
        return None

    for i, device in enumerate(device_list):
        # Format the device name and info for clear presentation
        device_name = device.get('name', 'Unknown Device')
        host_api = device.get('hostapi', 'N/A')
        channels = device.get(f'max_{direction}_channels', 'N/A')
        print(f"  [{i}] {device_name} ({channels} {direction} channels, Host API: {host_api})")
    
    # Add an option for the default device
    print("  [Enter] Use system default device")

    while True:
        try:
            choice_str = input(f"Enter your choice [0-{len(device_list) - 1}]: ").strip()
            if not choice_str:
                print("Using system default device.")
                return None # Return None to signify using the default
            
            choice = int(choice_str)
            if 0 <= choice < len(device_list):
                selected_device_name = device_list[choice]['name']
                print(f"Selected device: {selected_device_name}")
                return device_list[choice]                
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number or press Enter.")
        except (KeyboardInterrupt, EOFError):
            print("\nSelection cancelled. Using system default.")
            return None
