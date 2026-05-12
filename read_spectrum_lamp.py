from seabreeze.spectrometers import *
# List all connected devices
devices = list_devices()
print("Devices:", devices)


# Open each device
specs = [Spectrometer(dev) for dev in devices]
print(specs)
for i, spec in enumerate(specs):
    print(f"\n--- Spectrometer {i+1} ---")
    print("Serial:", spec.serial_number)
    print("spec:",dir(spec))
    #print(help(spec.f))
    print("")
    print(spec.features)
    print("")
    #print(help(spec.model))
    lamp = spec.features["continuous_strobe"][0]
    print(lamp)
    lamp.set_enable(True)
    
    # Set integration time (in microseconds)
    spec.integration_time_micros(10000)  # 10 ms
    lamp.set_enable(False)
    # Read wavelengths and intensities
    wavelengths = spec.wavelengths()
    intensities = spec.intensities()

    print("First 10 wavelength/intensity pairs:")
    for w, I in zip(wavelengths[:10], intensities[:10]):
        print(f"{w:.2f} nm -> {I:.1f}")

    # Optional: close device
    spec.close()

