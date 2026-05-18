from seabreeze.spectrometers import *
import numpy as np
import pandas as pd
import ast
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter1d
import time
import csv
import tkinter as tk
from tkinter import ttk

		

def Plotter(wavelengths,signal,xlim=[343,1043]):
	plt.figure(figsize=(10,6))
	plt.plot(wavelengths,signal,linewidth=1.2)
	plt.xlabel("Wavelength (nm)")
	plt.ylabel("Intensity (counts)")
	plt.title("Spectrum")
	plt.grid(True,alpha=0.3)
	plt.xlim(xlim)
	plt.show()
def PlotterDual(wavelengths,I0,I,xlim=[343,1043]):
	plt.figure(figsize=(10,6))
	plt.semilogy(wavelengths,I0,linewidth=1.2,label="I0 (source)")
	plt.semilogy(wavelengths,I ,linewidth=1.2,label="I (sample)")
	plt.xlabel("Wavelength (nm)")
	plt.ylabel("Intensity (counts)")
	plt.title("Spectrum")
	plt.legend()
	plt.grid(True,alpha=0.3)
	plt.xlim(xlim)
	plt.show()
def PlotIntensityStopsSteps(index_history,intensity_history,stop_history):
	plt.figure(figsize=(10,6))
	plt.semilogy(index_history,intensity_history,linewidth=1.2)
	plt.axhline(50000, color="red", linestyle = '-',label="50kcounts")
	plt.xlabel("Steps")
	plt.ylabel("Intensity (counts,log)")
	plt.title("Intensity over Steps")
	
	plt.figure(figsize=(10,6))
	plt.plot(index_history,stop_history,linewidth=1.2)
	plt.xlabel("Steps")
	plt.ylabel("Stops")
	plt.title("Stops over Steps")
def AutoDarkLightReference(spec,NumItterations,SampleWindow,warmup=30):
	#estimate_acquisition_time(n_scans=NumItterations,integration_us=SampleWindow,overhead_ms = 5)
	LampControl(spec=spec,state=False,warmup=warmup)
	input("CAPTURING dark source. REMOVE SAMPLE. Press Enter to continue...")
	wavelengths,darkCounts,time = Capture(spec=spec,NumItterations=NumItterations,us=SampleWindow)
	print("CAPTURING light source.")
	LampControl(spec=spec,state=True,warmup=warmup)
	wavelengths,lightCounts,time = Capture(spec=spec,NumItterations=NumItterations,us=SampleWindow)
	input("apply Sample or Filter then Press Enter to continue...")
	wavelengths,sampleCounts,time = Capture(spec=spec,NumItterations=NumItterations,us=SampleWindow)
	LampControl(spec=spec,state=False,warmup=warmup)
	return wavelengths,darkCounts,lightCounts,sampleCounts
	
def source_sample_calculation(darkCounts,lightCounts,transmissionCounts):
	source = np.maximum((lightCounts  - darkCounts).astype(float),1)
	sample = np.maximum((transmissionCounts - darkCounts).astype(float),1)
	return source,sample
	
#def main():
	#specs = [Spectrometer(dev) for dev in devices]
	#stops, wavelengths,Signal,intensity_history,stop_history,index_history = AutoShutter(spec,waveband = [509.9,510.1],target = CenterSpan2LowHigh(center=60000,span=100))
	#intensity_trunc = [float(f"{v:.4f}") for v in intensity_history]
	#df = pd.DataFrame({"index_history":index_history,"stop_history":stop_history,"intensity_history":intensity_history})
	#print(df)
	#Plotter(wavelengths,Signal)
	#wavelengths,darkCounts,lightCounts,sampleCounts=AutoDarkLightReference(spec,NumItterations=1000,SampleWindow=shutterspeedStops(stops))
	#source,sample = source_sample_calculation(darkCounts,lightCounts,sampleCounts)
	#PlotterDual(wavelengths,source,sample,xlim=[500,520])
	#Plotter(wavelengths,sample/source,xlim=[500,520])
	#plt.figure(figsize=(10,6))
	#plt.plot(wavelengths,Signal,linewidth=1.2,label="Signal")
	#plt.plot(wavelengths,smoothSignal,linewidth=1.2,label="SmoothSignal")
	#plt.axvline(510, color="red", linestyle = '-',label="510 nm")
	#plt.axhline(gLvl, color="red", linestyle = '-',label="510nm gausian_roi_metric")
	#plt.xlabel("Wavelength (nm)")
	#plt.ylabel("Intensity (counts)")
	#plt.title("Spectrum")
	#plt.grid(True,alpha=0.3)
	#plt.xlim([500,520])
	#plt.ylim([40000,60000])
	#plt.legend()
	#plt.show()
	

# --- Placeholder Functions for Your Code Logic ---

class DataManager:
	def __init__(self):
		#Raw data
		self.raw_dark = None
		self.raw_light  = None
		self.raw_ref = None
		self.raw_sample = None
		#dark corrected data
		self.light  = None
		self.ref = None
		self.sample = None
		#metadata
		self.spec= None
		self.wavelength = None
		self.integration_time_us = None
		self.stops = None
	def set(self, name, arr):
		if hasattr(self,name):
			setattr(self,name,arr)
		else:
			raise AttributeError(f"Unknown field: {name}")
	def get(self,name):
		return getattr(self,name,None)
		
	def have(self,*names):
		return all(getattr(self,n)is not None for n  in names)
	def clear(self,*names):
		for n in names:
			setattr(self, n, None)
	def clear_all(self):
		for name in self.__dict__.keys():
			setattr(self,name,None)
			
class Timer:
	def tic():
		return time.perf_counter()
	def tok(start):
		end = time.perf_counter()
		diff = end - start
		#print(f"Elapsed: {diff:.6f} s")
		return diff
def GetSpec():
	# List all connected devices
	devices = list_devices()
	print("Devices:", devices,flush=True)
	# Open first device
	spec = Spectrometer(devices[0])
	
	wavelengths = np.array(spec.wavelengths())
	return spec,wavelengths
def LampControl(spec,state,warmup):
	if state==True:
		print(f"Lamp ON,warm up for {warmup}",flush=True)
	else:
		print(f"Lamp OFF,warm up for {warmup}",flush=True)
	spec.features["continuous_strobe"][0].set_enable(state)
	time.sleep(warmup)

def shutterspeedStops(stops,ref=250):
	#negative means a faster shutter (stop down) Whole stops
	#positice means a slower shutter (stop open) Whole stops 
	frac = ref/(2**stops)
	return 1000000//frac
def Capture(spec,NumItterations):
	accumulator = np.zeros(spec.pixels)
	# Read wavelengths and intensities
	wavelengths = np.array(spec.wavelengths())
	Start = Timer.tic()
	for n in range(NumItterations):
		accumulator += spec.intensities()
		#print(f"{n}")
	print(f"spectrum captured",flush=True)
	signal= np.array(accumulator / NumItterations)
	capturetime = Timer.tok(Start)
	return [wavelengths,signal,capturetime]

def gausian_roi_metric(wavelengths,signal,target,sigma=1):
	w = np.exp(-0.5 * ((wavelengths - target) / sigma)**2)
	return np.sum(signal * w) / np.sum(w)
	
def autogain_loop(spec,wavelengths,gain_mode,threshold,target):
	itterations = 20
	Stops = 0
	Step = 2
	Index = 0
	Direction = [1,1]
	Signal = np.zeros(spec.pixels)
	intensity_history=[]
	stop_history=[]
	index_history=[]
	
	if gain_mode=="Target" and (target > max(wavelengths) or target < min(wavelengths)) :
		print(f"gain_mode = {gain_mode}",flush=True)
		print(f"target = {target}nm",flush=True)
		print(f"max(wavelengths) = {max(wavelengths)}nm",flush=True)
		print(f"min(wavelengths) = {min(wavelengths)}nm",flush=True)
		raise ValueError("Target wavelength out of bounds of wavelengths")
		#return Stops,Signal,intensity_history,stop_history,index_history
	#DARK CAPTURE
	print(f"100 Dark itterations at 6 stops",flush=True)
	Stops = 6
	us = shutterspeedStops(Stops)			#Set shutter Speed
	spec.integration_time_micros(us)
	print(f"{Stops}stops = {us}us",flush=True)
	LampControl(spec=spec,state=False,warmup=3)		#Light OFF
	print("Trash 5 itter:", end=" ",flush=True)
	_,trash,_ = Capture(spec=spec,NumItterations=5) 	#Capture throwaway
	print("Dark 100 itter:", end=" ",flush=True)
	_,Dark,_ = Capture(spec=spec,NumItterations=100) 	#Capture Darks 
	
	Stops=2
	LampControl(spec=spec,state=True,warmup=30)		#Light ON
	while True:
		us = shutterspeedStops(Stops)			#Set shutter Speed
		spec.integration_time_micros(us)
		print(f"{Stops}stops = {us}us",flush=True)
		print("Trash 5 itter:", end=" ",flush=True)
		_,trash,_ = Capture(spec=spec,NumItterations=5) 	#Capture throwaway
		print(f"Light {itterations} itter:", end=" ",flush=True)
		_,Light,_ = Capture(spec=spec,NumItterations=itterations)	#Capture Lights
		
		Signal = Light-Dark					#Correction
		if gain_mode=="Target":
			I = gausian_roi_metric(wavelengths,Signal,target)#smoothII
		else:
			I = max(gaussian_filter1d(Signal,sigma=2)) #Sigma in pixels  #SmoothI
		
		print(f"{I} counts @{Stops}stops,{us}us",flush=True)
		intensity_history.append(I)
		stop_history.append(Stops)
		index_history.append(Index)
		Index += 1
		if I < threshold[0]:					#if too low
			print("Too Low",flush=True)
			Direction[1] = 1
		elif I > threshold[1]:					#if too high
			print("Too High",flush=True)					
			Direction[1] = 0
		else:
			LampControl(spec=spec,state=False,warmup=0)		#Light OFF
			return Stops,Signal,intensity_history,stop_history,index_history	
		if Direction[0] != Direction[1]:
			Step /= 2
			Direction[0] = Direction[1]
		if Direction[0] == 1:
			Stops += Step					#increment
		else:
			Stops -= Step					#decrement	
def auto_gain():
	#init spec
	spec,wavelengths = GetSpec()
	
	#get user params
	gain_mode = gain_mode_var.get()
	low_thresh = lower_thresh.get()
	up_thresh = upper_thresh.get()
	target_wavelength_var = target_wavelength.get()
	print("AutoGain clicked",flush=True)
	print(f"AutoGain | Mode: {gain_mode}",flush=True)
	print(f"Thresholds -> Lower: {low_thresh} | Upper: {up_thresh}",flush=True)
	print(f"Custom Wavelength Center: {target_wavelength_var} nm",flush=True)
	
	
	Stops,Signal,intensity_history,stop_history,index_history = autogain_loop(spec=spec,wavelengths=wavelengths,gain_mode=gain_mode,threshold=[low_thresh,up_thresh],target=target_wavelength_var)
	# UPDATE THE GUI TEXT BOX VIA ITS VARIABLE
	current_stops.set(Stops)
	print(f"AutoGain executed. Updated Current Stops to: {Stops}",flush=True)

	
	# Get values using: current_stops.get() or itteration_spinner.get()

			

	

def dark_frame_capture():
	print(f"Dark Frame Capture clicked. Capturing...",flush=True)
	spec,wavelengths = GetSpec()
	
	itterations = itteration_spinner.get()
	Stops = current_stops.get()
	us = shutterspeedStops(Stops)
	print(f"{itterations} itterations @{Stops}stops,{us}us",flush=True)
	
	LampControl(spec=spec,state=False,warmup=5)		#Light OFF
	print("Trash 5 itter:", end=" ",flush=True)
	_,trash,_ = Capture(spec=spec,NumItterations=5) 	#Capture throwaway
	print(f"Light {itterations} itter:", end=" ",flush=True)
	_,Dark,_ = Capture(spec=spec,NumItterations=itterations) 	#Capture Darks
	signal_raw_dark_counts.set(Dark)
	print(f"RAW Dark Frame Captured. Sample size: {itterations}",flush=True)
	print(Dark,flush=True)


def light_frame_capture():
	print(f"RAW Light Frame Capture clicked. Capturing...",flush=True)
	spec,wavelengths = GetSpec()

	itterations = itteration_spinner.get()
	Stops = current_stops.get()
	us = shutterspeedStops(Stops)
	print(f"{itterations} itterations @{Stops}stops,{us}us",flush=True)
	
	LampControl(spec=spec,state=True,warmup=5)		#Light ON
	print("Trash 5 itter:", end=" ",flush=True)
	_,trash,_ = Capture(spec=spec,NumItterations=5) 	#Capture throwaway
	print(f"Light {itterations} itter:", end=" ",flush=True)
	_,Light,_ = Capture(spec=spec,NumItterations=itterations)	#Capture Lights
	signal_raw_light_counts.set(Light)
	print(f"RAW Light Frame Captured. Sample size: {itterations}",flush=True)
	print(Light,flush=True)

def reference_capture():
	print(f"RAW Reference Frame Capture clicked. Capturing...",flush=True)
	spec,wavelengths = GetSpec()

	itterations = itteration_spinner.get()
	Stops = current_stops.get()
	us = shutterspeedStops(Stops)
	print(f"{itterations} itterations @{Stops}stops,{us}us",flush=True)
	
	LampControl(spec=spec,state=True,warmup=5)		#Light ON
	print("Trash 5 itter:", end=" ",flush=True)
	_,trash,_ = Capture(spec=spec,NumItterations=5) 	#Capture throwaway
	print(f"Ref {itterations} itter:", end=" ",flush=True)
	_,Ref,_ = Capture(spec=spec,NumItterations=itterations)	#Capture Lights
	signal_raw_ref_counts.set(Ref)
	print(f"RAW Reference Frame Captured. Sample size: {itterations}",flush=True)
	print(Ref,flush=True)

def sample_capture():
	print(f"RAW Sample Frame Capture clicked. Capturing...",flush=True)
	spec,wavelengths = GetSpec()
	
	itterations = itteration_spinner.get()
	Stops = current_stops.get()
	us = shutterspeedStops(Stops)
	print(f"{itterations} itterations @{Stops}stops,{us}us",flush=True)
	
	LampControl(spec=spec,state=True,warmup=5)		#Light ON
	print("Trash 5 itter:", end=" ",flush=True)
	_,trash,_ = Capture(spec=spec,NumItterations=5) 	#Capture throwaway
	print(f"Light {itterations} itter:", end=" ",flush=True)
	_,Sample,_ = Capture(spec=spec,NumItterations=itterations)	#Capture Lights
	signal_raw_samp_counts.set(Sample)
	print(f"RAW Sample Frame Captured. Itteration size: {itterations}",flush=True)
	print(Sample,flush=True)
	
def dark_frame_correct():
	Dark = text_to_array(signal_raw_dark_counts.get())
	Light = text_to_array(signal_raw_light_counts.get())
	Ref = text_to_array(signal_raw_ref_counts.get())
	Sample =text_to_array(signal_raw_samp_counts.get())
	
	signal_light_counts.set(diff_arr(Light,Dark))
	signal_ref_counts.set(diff_arr(Ref,Dark))
	signal_samp_counts.set(diff_arr(Sample,Dark))
	
def text_to_array(text):
	text = text.strip()
	#empty field -> return none
	if text.lower() == "empty":
		return None
	
	#remove brackets
	cleaned = text.strip("[]")
	
	#convert to array
	array = np.fromstring(cleaned,sep=" ")
	if array.size == 0:
		return None
	return array	
	
def diff_arr(light,dark):
	if light is None or dark is None:
		return "Missing Data for Dark Correction"
	else:
		return light-dark
		
def comparison():
	print(f"Comparison: {comparison_var.get()}",flush=True)

def lamp_off():
	spec,_ = GetSpec()
	LampControl(spec=spec,state=False,warmup=0)#LightOFF
	
def lamp_on():
	spec,_ = GetSpec()
	LampControl(spec=spec,state=True,warmup=0)#Light ON
# --- GUI Setup ---
root = tk.Tk()
root.title("Advanced Capture Control Interface")
root.geometry("750x650")
root.resizable(False, False)

padding_opts = {"padx": 10, "pady": 6}

RowIDX = 0
# =====================================================================
# SECTION 1: AUTOGAIN CONTROLS
# =====================================================================
#btn_connect = ttk.Button(root, text="Connect to Spectrometer",command = connectSpec)
#btn_auto_gain.grid(row=RowIDX, column=0, **padding_opts, sticky="ew")
#RowIDX+=1
sep = ttk.Separator(root, orient="horizontal")
sep.grid(row=RowIDX, column=0, columnspan=4, padx=10, pady=12, sticky="ew")
RowIDX+=1
btn_auto_gain = ttk.Button(root, text="AutoGain", command=auto_gain)
btn_auto_gain.grid(row=RowIDX, column=0, **padding_opts, sticky="ew")

lbl_stops = ttk.Label(root, text="Current Stops:")
lbl_stops.grid(row=RowIDX, column=1, padx=(10, 2), pady=6, sticky="e")

# Current Stops variable initialized to 0.0
current_stops = tk.DoubleVar(value=0.0)
entry_stops = ttk.Entry(root, textvariable=current_stops, width=10)
entry_stops.grid(row=RowIDX, column=2, **padding_opts, sticky="w")

RowIDX+=1

lbl_lower = ttk.Label(root, text="Lower Threshold Counts:")
lbl_lower.grid(row=RowIDX, column=0, **padding_opts, sticky="e")

lower_thresh = tk.IntVar(value=50000)
spin_lower = ttk.Spinbox(root, from_=0, to=0xFFFF, increment=1, textvariable=lower_thresh, width=8)
spin_lower.grid(row=RowIDX, column=1, **padding_opts, sticky="w")

lbl_upper = ttk.Label(root, text="Upper Threshold Counts:")
lbl_upper.grid(row=RowIDX, column=2, **padding_opts, sticky="e")

upper_thresh = tk.IntVar(value=50100)
spin_upper = ttk.Spinbox(root, from_=0, to=0xFFFF, increment=1, textvariable=upper_thresh, width=8)
spin_upper.grid(row=RowIDX, column=3, **padding_opts, sticky="w")

RowIDX+=1

lbl_gain_mode = ttk.Label(root, text="Auto Gain Mode:")
lbl_gain_mode.grid(row=RowIDX, column=0, **padding_opts, sticky="e")

gain_mode_var = tk.StringVar(value="Target")

rad_full = ttk.Radiobutton(root, text="Full Spectrum", variable=gain_mode_var, value="Full")
rad_full.grid(row=RowIDX, column=1, **padding_opts, sticky="w")

rad_target = ttk.Radiobutton(root, text="Target Wavelength (nm)", variable=gain_mode_var, value="Target")
rad_target.grid(row=RowIDX, column=2, columnspan=2, **padding_opts, sticky="w")

target_wavelength = tk.IntVar(value=510)
spin_wavelength_center = ttk.Spinbox(root, from_=200, to=1100, increment=1, textvariable=target_wavelength, width=8)
spin_wavelength_center.grid(row=RowIDX, column=3, **padding_opts, sticky="w")

RowIDX+=1
sep = ttk.Separator(root, orient="horizontal")
sep.grid(row=RowIDX, column=0, columnspan=4, padx=10, pady=12, sticky="ew")


# --- Row 2: Sample Spinner ---
RowIDX+=1
lbl_spinner = ttk.Label(root, text="Command Sample:")
lbl_spinner.grid(row=RowIDX, column=0, **padding_opts, sticky="e")

# Spinner variable (Integer for Buttons 2, 3, 4, 5)
itteration_spinner = tk.IntVar(value=256)
spin_box = ttk.Spinbox(root, from_=1, to=10000, increment=1, textvariable=itteration_spinner, width=8)
spin_box.grid(row=RowIDX, column=1, **padding_opts, sticky="w")

btn_lamp_off = ttk.Button(root, text="LAMP OFF", command=lamp_off)
btn_lamp_off.grid(row=RowIDX, column=2, **padding_opts, sticky="ew")

btn_lamp_on = ttk.Button(root, text="LAMP ON", command=lamp_on)
btn_lamp_on.grid(row=RowIDX, column=3, **padding_opts, sticky="ew")



# --- Row 3 & 4: Capture Action Buttons ---
RowIDX+=1
btn_dark = ttk.Button(root, text="Dark Frame Capture", command=dark_frame_capture)
btn_dark.grid(row=RowIDX, column=0, **padding_opts, sticky="ew")

btn_light = ttk.Button(root, text="Light Frame Capture", command=light_frame_capture)
btn_light.grid(row=RowIDX, column=1, **padding_opts, sticky="ew")

btn_ref = ttk.Button(root, text="Reference Capture", command=reference_capture)
btn_ref.grid(row=RowIDX, column=2, **padding_opts, sticky="ew")

btn_sample = ttk.Button(root, text="Sample Capture", command=sample_capture)
btn_sample.grid(row=RowIDX, column=3, **padding_opts, sticky="ew")

# Row 5 Data Storage
# --- RAW Spectra
RowIDX+=1
#Dark

lbl_raw_dark = ttk.Label(root, text="Raw Dark Signal:")
lbl_raw_dark.grid(row=RowIDX, column=0, padx=(10, 2), pady=6, sticky="e")

signal_raw_dark_counts = tk.StringVar(value="empty")
label_raw_dark_counts = ttk.Label(root, textvariable=signal_raw_dark_counts, width=10)
label_raw_dark_counts.grid(row=RowIDX+1, column=0, **padding_opts, sticky="e")

#Light
lbl_raw_light = ttk.Label(root, text="Raw Light Signal:")
lbl_raw_light.grid(row=RowIDX, column=1, padx=(10, 2), pady=6, sticky="e")

signal_raw_light_counts = tk.StringVar(value="empty")
label_raw_light_counts = ttk.Label(root, textvariable=signal_raw_light_counts, width=10)
label_raw_light_counts.grid(row=RowIDX+1, column=1, **padding_opts, sticky="e")

#Reference
lbl_raw_ref = ttk.Label(root, text="Raw Ref Signal:")
lbl_raw_ref.grid(row=RowIDX, column=2, padx=(10, 2), pady=6, sticky="e")

signal_raw_ref_counts = tk.StringVar(value="empty")
label_raw_ref_counts = ttk.Label(root, textvariable=signal_raw_ref_counts, width=10)
label_raw_ref_counts.grid(row=RowIDX+1, column=2, **padding_opts, sticky="e")

#Sample
lbl_raw_samp = ttk.Label(root, text="Raw Sample Signal:")
lbl_raw_samp.grid(row=RowIDX, column=3, padx=(10, 2), pady=6, sticky="e")

signal_raw_samp_counts = tk.StringVar(value="empty")
label_raw_samp_counts = ttk.Label(root, textvariable=signal_raw_samp_counts, width=10)
label_raw_samp_counts.grid(row=RowIDX+1, column=3, **padding_opts, sticky="e")


# --- Dark Corrected ---
RowIDX+=2
# --- Row 5: Dark Correct Buttons ---
btn_dark = ttk.Button(root, text="Dark Correct", command=dark_frame_correct)
btn_dark.grid(row=RowIDX, column=0, rowspan=2, **padding_opts, sticky="nsew")

#Light
lbl_light = ttk.Label(root, text="Corrected Light Signal:")
lbl_light.grid(row=RowIDX, column=1, padx=(10, 2), pady=6, sticky="e")

signal_light_counts = tk.StringVar(value="empty")
label_light_counts = ttk.Label(root, textvariable=signal_light_counts, width=10)
label_light_counts.grid(row=RowIDX+1, column=1, **padding_opts, sticky="w")

#Reference
lbl_ref = ttk.Label(root, text="Corrected Ref Signal:")
lbl_ref.grid(row=RowIDX, column=2, padx=(10, 2), pady=6, sticky="e")

signal_ref_counts = tk.StringVar(value="empty")
label_ref_counts = ttk.Label(root, textvariable=signal_ref_counts, width=10)
label_ref_counts.grid(row=RowIDX+1, column=2, **padding_opts, sticky="w")

#Sample
lbl_samp = ttk.Label(root, text="Corrected Sample Signal:")
lbl_samp.grid(row=RowIDX, column=3, padx=(10, 2), pady=6, sticky="e")

signal_samp_counts = tk.StringVar(value="empty")
label_samp_counts = ttk.Label(root, textvariable=signal_samp_counts, width=10)
label_samp_counts.grid(row=RowIDX+1, column=3, **padding_opts, sticky="w")


# --- Row 6: Comparison Radio Buttons ---
RowIDX+=2
lbl_radio_group = ttk.Label(root, text="Comparison Mode:")
lbl_radio_group.grid(row=RowIDX, column=0, **padding_opts, sticky="w")

# Radio variable to track selection
RowIDX+=1
comparison_var = tk.StringVar(value="sample_vs_ref")

rad_light_ref = ttk.Radiobutton(root, text="Reference / Light", variable=comparison_var, value="ref_vs_light")
rad_light_ref.grid(row=RowIDX, column=0, **padding_opts, sticky="w")

rad_light_sample = ttk.Radiobutton(root,text="Sample / Light",variable=comparison_var,value="sample_vs_light")
rad_light_sample.grid(row=RowIDX, column=1, **padding_opts, sticky="w")

rad_sample_ref = ttk.Radiobutton(root, text="Sample vs Reference", variable=comparison_var, value="sample_vs_ref")
rad_sample_ref.grid(row=RowIDX, column=2, **padding_opts, sticky="w")

RowIDX+=1
btn_compare = ttk.Button(root, text="Compare", command=comparison)
btn_compare.grid(row=RowIDX, column=1, **padding_opts, sticky="ew")






# Start application loop
root.mainloop()

