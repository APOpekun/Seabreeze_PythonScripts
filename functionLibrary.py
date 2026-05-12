from seabreeze.spectrometers import *
import numpy as np
import matplotlib.pyplot as plt
import time
import csv
class Timer:
	def tic():
		return time.perf_counter()
	def tok(start):
		end = time.perf_counter()
		diff = end - start
		#print(f"Elapsed: {diff:.6f} s")
		return diff
def LampControl(spec,state,warmup):
	spec.features["continuous_strobe"][0].set_enable(state)
	if state == True:
		time.sleep(warmup)
def Capture(spec,NumSamples,us):
	accumulator = np.zeros(spec.pixels)
	spec.integration_time_micros(us)

	# Read wavelengths and intensities
	wavelengths = np.array(spec.wavelengths())
	Start = Timer.tic()
	for n in range(NumSamples):
		accumulator += spec.intensities()
		if n % 50 == 0:
			print(f"{n} samples")
	print("spectrum captured")
	aveCounts= np.array(accumulator / NumSamples)
	capturetime = Timer.tok(Start)
	return [wavelengths,aveCounts,capturetime]
	
def Plotter(wavelengths,aveCounts):
	plt.figure(figsize=(10,6))
	plt.plot(wavelengths,aveCounts,linewidth=1.2)
	plt.xlabel("Wavelength (nm)")
	plt.ylabel("Intensity (counts)")
	plt.title("Spectrum")
	plt.grid(True,alpha=0.3)
	plt.tight_layout()
	plt.show()
	
def PlotterDual(wavelengths,I0,I,mask):
	plt.figure(figsize=(10,6))
	plt.semilogy(wavelengths[mask],I0[mask],linewidth=1.2,label="I0 (source)")
	plt.semilogy(wavelengths[mask],I[mask],linewidth=1.2,label="I (sample)")
	plt.axhline(0xFFFF,color='r',linestyle='-',alpha=0.5,label="saturation")
	plt.xlabel("Wavelength (nm)")
	plt.ylabel("Intensity (counts)")
	plt.title("Spectrum")
	plt.legend()
	plt.grid(True,alpha=0.3)
	plt.tight_layout()
	plt.show()
	
def estimate_acquisition_time(n_scans,integration_us,overhead_ms = 5):
	total_s = n_scans * (integration_us / 1E6 + overhead_ms / 1E3)
	print(f"approx. {total_s:.1f}s total for {n_scans} scans at {integration_us} us")
	confirm = input("This may take a while. Continue? [y/N]")
	if confirm.lower() != "y":
		raise SystemExit("Acquisition cancelled")

def DarkLightReference(spec,NumSamples,SampleWindow):
	#estimate_acquisition_time(n_scans=NumSamples,integration_us=SampleWindow,overhead_ms = 5)

	input("apply dark source then Press Enter to continue...")
	wavelengths,darkCounts,time = Capture(spec=spec,NumSamples=NumSamples,us=SampleWindow)
	input("apply light source then Press Enter to continue...")
	wavelengths,lightCounts,time = Capture(spec=spec,NumSamples=NumSamples,us=SampleWindow)
	input("apply Sample or Filter then Press Enter to continue...")
	wavelengths,sampleCounts,time = Capture(spec=spec,NumSamples=NumSamples,us=SampleWindow)
	return wavelengths,darkCounts,lightCounts,sampleCounts
	
def AutoDarkLightReference(spec,NumSamples,SampleWindow):
	#estimate_acquisition_time(n_scans=NumSamples,integration_us=SampleWindow,overhead_ms = 5)

	input("CAPTURING dark source. REMOVE SAMPLE. Press Enter to continue...")
	wavelengths,darkCounts,time = Capture(spec=spec,NumSamples=NumSamples,us=SampleWindow)
	print("CAPTURING light source.")
	LampControl(spec=spec,state=True,warmup=30)
	wavelengths,lightCounts,time = Capture(spec=spec,NumSamples=NumSamples,us=SampleWindow)
	input("apply Sample or Filter then Press Enter to continue...")
	wavelengths,sampleCounts,time = Capture(spec=spec,NumSamples=NumSamples,us=SampleWindow)
	LampControl(spec=spec,state=False,warmup=30)
	return wavelengths,darkCounts,lightCounts,sampleCounts
	
def source_sample_calculation(darkCounts,lightCounts,transmissionCounts):
	source = np.maximum((lightCounts  - darkCounts).astype(float),1)
	sample = np.maximum((transmissionCounts - darkCounts).astype(float),1)
	return source,sample
	
	#Plotter(wavelengths,source)
	#Plotter(wavelengths,sample)
	
	#TransmissionRatio = np.divide(sample, source, out=np.zeros_like(source), where=source!=0)
	#print(TransmissionRatio[mask])
	#OpticalDensity = -np.log10(TransmissionRatio)
	#Plotter(wavelengths[mask],OpticalDensity[mask])	
	
	
def capturingcurve():
	# List all connected devices
	devices = list_devices()
	print("Devices:", devices)
	# Open first device
	spec = Spectrometer(devices[0])
	for samples in [1,5,10,20,50,100,200,500,1000]:
	 for shutterSpeed in [100,200,500,1000,2000,5000,10000,20000,50000,100000]:
	 	a,b,capturetime = Capture(spec,NumSamples=samples,us=shutterSpeed)
	 	print(f"{samples} samples, {shutterSpeed} us shutterSpeed = {capturetime} s")
def shutterspeedStops(stops,ref=250):
	#negative means a faster shutter (stop down) Whole stops
	#positice means a slower shutter (stop open) Whole stops 
	frac = ref/(2**stops)
	return 1000000//frac
def main(NumSamples,SampleWindow):
	# List all connected devices
	devices = list_devices()
	print("Devices:", devices)
	# Open first device
	spec = Spectrometer(devices[0])
	#specs = [Spectrometer(dev) for dev in devices]
	
	wavelengths,darkCounts,lightCounts,transmissionCounts = AutoDarkLightReference(spec,NumSamples,SampleWindow)
	source,sample = source_sample_calculation(darkCounts,lightCounts,transmissionCounts)
	#stack into 2D array rows=wavelength columns = fields
	table = np.column_stack([wavelengths,darkCounts,lightCounts,transmissionCounts,source,sample])
	#save to CSV
	with open("Spectra_capture_DIWater.csv","w",newline="") as f:
		writer = csv.writer(f)
		writer.writerow(["wavelength_nm","Dark","Light","Transmission","Source","Sample"])
		writer.writerows(table)
	mask = sample >=10
	PlotterDual(wavelengths,source,sample,mask)

main(16**2,shutterspeedStops(3,ref=250))
#capturingcurve()
