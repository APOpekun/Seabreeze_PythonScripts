from seabreeze.spectrometers import *
import numpy as np
import time
from datetime import datetime
import threading
import sys

class SpectrometerLogger:
    def __init__(self, samples_per_second=10, duration_hours=1):
        self.spec = None
        self.wavelengths = None
        self.intensityarray = None
        self.timearray = None
        
        # Timing configurations
        self.samples_per_second = samples_per_second
        self.delay = 1.0 / samples_per_second
        self.total_samples = samples_per_second * 3600 * duration_hours
        
        # Thread sync & control flags
        self.current_index = 0
        self.is_running = False
        self.error_occurred = None

    def connect_spec(self):
        devices = list_devices()
        print(f"[Watchdog] Found devices: {devices}")
        if not devices:
            raise RuntimeError("No spectrometer detected!")
        
        self.spec = Spectrometer(devices[0])
        self.wavelengths = np.array(self.spec.wavelengths())
        
        # Pre-allocate memory arrays
        self.intensityarray = np.zeros((self.total_samples, len(self.wavelengths)))
        self.timearray = np.zeros((self.total_samples, 1), dtype='<U26')
        print(f"[Watchdog] Memory allocated for {self.total_samples} samples.")

    def set_shutter_speed(self, stops, ref=250):
        frac = ref / (2**stops)
        us = int(1000000 // frac)
        self.spec.integration_time_micros(us)
        print(f"[Watchdog] Shutter set to {us} microseconds.")

    def lamp_ctrl(self, state):
        self.spec.features["continuous_strobe"][0].set_enable(state)
        print(f"\n[Watchdog] Continuous strobe lamp turned {'ON' if state else 'OFF'}.")

    def _data_collection_worker(self):
        """Background thread target tasked solely with hardware collection."""
        print("[Data Thread] Worker thread initialized.")
        lamp_triggered = False
        lamp_trigger_index = self.total_samples // 3
        
        # Pre-calculate next wake times to minimize loop drift
        next_waketime = time.monotonic()
        
        try:
            while self.is_running and self.current_index < self.total_samples:
                # 1. Capture data immediately
                self.intensityarray[self.current_index] = self.spec.intensities()
                self.timearray[self.current_index] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                
                # 2. Watchdog lamp event evaluation
                if self.current_index >= lamp_trigger_index and not lamp_triggered:
                    self.lamp_ctrl(True)
                    lamp_triggered = True
                
                self.current_index += 1
                
                # 3. Dynamic interval timing to prevent system sleep drift
                next_waketime += self.delay
                sleep_duration = next_waketime - time.monotonic()
                if sleep_duration > 0:
                    time.sleep(sleep_duration)
                    
        except Exception as e:
            self.error_occurred = e
        finally:
            self.is_running = False
            print("[Data Thread] Worker thread safely halted.")

    def run(self):
        """Main thread loop acting as the watchdog monitor."""
        self.connect_spec()
        self.set_shutter_speed(0.321928)
        
        # Start background worker thread
        self.is_running = True
        data_thread = threading.Thread(target=self._data_collection_worker, daemon=True)
        data_thread.start()
        
        print("[Watchdog] Active monitoring system online. Press Ctrl+C to cancel.")
        
        try:
            while self.is_running:
                # Handle unexpected background worker crashes
                if self.error_occurred:
                    raise self.error_occurred
                
                # Dynamic visual terminal update (overwriting the current line)
                pct = (self.current_index / self.total_samples) * 100
                sys.stdout.write(f"\r Progress: {self.current_index}/{self.total_samples} samples ({pct:.2f}%)")
                sys.stdout.flush()
                
                time.sleep(0.5) # Watchdog wakes up twice a second to report status
                
        except KeyboardInterrupt:
            print("\n[Watchdog] Interrupted by user! Stopping logging and saving partial data...")
            self.is_running = False
            data_thread.join(timeout=2.0) # Wait for thread cleanup
            
        finally:
            # Clean up hardware and dump arrays safely
            if self.spec:
                try:
                    self.lamp_ctrl(False)
                except:
                    pass
            
            # Trim trailing zeros if the run was cut short by user abort
            final_intensity = self.intensityarray[:self.current_index]
            final_time = self.timearray[:self.current_index]
            
            np.savez("LampStability.npz",
                    wavelengths=self.wavelengths,
                    intensity=final_intensity,
                    timearray=final_time)
            print(f"\n[Watchdog] Completed. {self.current_index} samples successfully archived to LampStability.npz.")

if __name__ == "__main__":
    # Configure for a 1-hour sample run at 10Hz
    logger = SpectrometerLogger(samples_per_second=10, duration_hours=1)
    logger.run()
