import sounddevice as sd

def select_audio_device(kind='input'):
    """
    Interactively prompts the user to select an audio device from a list.

    Args:
        device_list (list): A list of device dictionaries from sounddevice.query_devices().
        direction (str): The direction of the device ('input' or 'output'), used for prompts.

    Returns:
        The device name (str) or index (int) of the selected device, or None if no selection is made.
    """
    kind = kind.lower()
    if kind not in ("output", "input"):
        raise ValueError("kind must be 'output' or 'input'")
    devices = sd.query_devices()
    filtered = [
        d for d in devices
        if (d["max_output_channels"] > 0 if kind == "output" else d["max_input_channels"] > 0)
    ]
    print(f"Available {kind} devices:")
    for d in filtered:
        print(
            f"  [{d['index']}] {d['name']} (host: {sd.query_hostapis()[d['hostapi']]['name']}), "
            f"inputs: {d['max_input_channels']} outputs: {d['max_output_channels']}"
        )
    while True:
        try:
            sel = input(f"Enter {kind} device index (or press Enter for default): ").strip()
            if not sel:
                default = sd.default.device[1 if kind == 'output' else 0]
                print(f"Using default device index {default}")
                return sd.query_devices(default)
            sel = int(sel)
            dev = [d for d in filtered if d["index"] == sel]
            if dev:
                return dev[0]
            print("Invalid index.")
        except Exception as e:
            print(f"Error: {e}")
