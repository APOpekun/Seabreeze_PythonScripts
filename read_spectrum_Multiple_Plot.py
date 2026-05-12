from seabreeze.spectrometers import *
import numpy as np
import matplotlib.pyplot as plt
NumSamples=1
# List all connected devices
devices = list_devices()
print("Devices:", devices)

# Open each device
specs = [Spectrometer(dev) for dev in devices]

#preallocate accumulator
waves =  [np.zeros(spec.pixels) for spec in specs]
accums = [np.zeros(spec.pixels) for spec in specs]
    
print("specs",specs)
for i, spec in enumerate(specs):
    
    print(f"\n--- Spectrometer {i+1} ---")
    #print("Serial:", spec.serial_number)
    #print("Pixels:",spec.pixels)
    # Set integration time (in microseconds)
    spec.integration_time_micros(100000)  # 100 ms

    # Read wavelengths and intensities
    waves[i] = spec.wavelengths()
    for n in range(NumSamples):
        accums[i] += spec.intensities()
    
    print("spectrum captured")
    # Optional: close device
    spec.close()

aves = [accum / NumSamples for accum in accums]
print(aves)
for i, spec in enumerate(specs):
    print(f"\n--- Spectrometer {i+1} ---")
    print("Serial:", spec.serial_number)
    print("First 10 wavelength/intensity pairs:")
    for w, I in zip(waves[i][:10], aves[i][:10]):
        print(f"{w:.2f} nm -> {I:.1f}")

    plt.figure(figsize=(10,6))
    plt.plot(waves[i],aves[i],linewidth=1.2)
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Intensity (counts)")
    plt.title(f"Dark Spectrum {i+1}")
    plt.grid(True,alpha=0.3)
    plt.tight_layout()
    plt.show()
    
