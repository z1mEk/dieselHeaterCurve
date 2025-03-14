import collections
import json
import os

class AdaptiveHeating:
    def __init__(self, target_temp=20, initial_k1=10, initial_k2=30, learning_rate=0.1, param_file="heating_params.json"):
        self.target_temp = target_temp  # Target internal temperature
        self.learning_rate = learning_rate  # Adjustment speed for parameters
        self.param_file = param_file  # File path for saving parameters

        # Fuel pump frequency range
        self.f_min = 1.4  # Hz (minimum power)
        self.f_max = 5.5  # Hz (maximum power)
        
        # Heating power corresponding to the frequency range
        self.p_min = 1.1e3  # W (at 1.4 Hz)
        self.p_max = 4.3e3  # W (at 5.5 Hz)
        
        # Buffer for smoothing frequency changes (FIFO)
        self.freq_history = collections.deque(maxlen=5)  # Averaging the last 5 values
        self.last_freq = self.f_min  # Previous frequency value
        self.hysteresis = 0.2  # Minimum frequency change threshold

        # Load heating curve parameters
        self.k1, self.k2 = self.load_params(initial_k1, initial_k2)

    def save_params(self):
        """Saves the current values of k1 and k2 to a JSON file."""
        with open(self.param_file, "w") as file:
            json.dump({"k1": self.k1, "k2": self.k2}, file)

    def load_params(self, default_k1, default_k2):
        """Loads saved values of k1 and k2 from a JSON file if it exists."""
        if os.path.exists(self.param_file):
            with open(self.param_file, "r") as file:
                data = json.load(file)
                return data.get("k1", default_k1), data.get("k2", default_k2)
        return default_k1, default_k2

    def update_curve(self, temp_ext, temp_int):
        """
        Adjusts heating curve parameters based on temperature difference.
        """
        error = self.target_temp - temp_int  # Deviation from target temperature

        # Adjust parameters
        self.k1 += self.learning_rate * error
        self.k2 += self.learning_rate * (error / 2)

        # Stability constraints
        self.k1 = max(0, min(self.k1, 20))
        self.k2 = max(0, min(self.k2, 50))

        # Save updated parameters
        self.save_params()

    def heating_frequency(self, temp_ext, heater_state):
        """
        Calculates fuel pump frequency based on current parameters.
        heater_state: True if the heater is in normal operation, False if in warm-up mode.
        """
        if not heater_state:
            return None  # No control over the pump in warm-up mode

        power = max(0, self.k1 * (self.target_temp - temp_ext) + self.k2)
        power = min(power, self.p_max)  # Limit power to maximum value

        # Convert power to fuel pump frequency (1.4 Hz - 5.5 Hz)
        frequency = self.f_min + ((power - self.p_min) / (self.p_max - self.p_min)) * (self.f_max - self.f_min)
        frequency = round(max(self.f_min, min(frequency, self.f_max)), 2)  # Keep within pump range

        # Add to smoothing buffer
        self.freq_history.append(frequency)
        avg_frequency = sum(self.freq_history) / len(self.freq_history)  # Average value

        # Hysteresis - apply frequency change only if deviation exceeds 0.2 Hz
        if abs(avg_frequency - self.last_freq) >= self.hysteresis:
            self.last_freq = avg_frequency  # Accept new value
        return round(self.last_freq, 2)

# Example usage:
heater = AdaptiveHeating(target_temp=22)  # Set target temperature to 22°C

# Sample temperature readings:
external_temp = -5  # °C
internal_temp = 18  # °C
heater_state = True  # Heater is in normal operation

heater.update_curve(external_temp, internal_temp)  # Adjust parameters
frequency = heater.heating_frequency(external_temp, heater_state)  # Calculate new pump frequency

if frequency is not None:
    print(f"Fuel pump frequency: {frequency} Hz")
else:
    print("Heater is in warm-up mode - no control over pump frequency.")
