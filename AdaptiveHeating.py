import collections
import json
import os

class AdaptiveHeating:
    def __init__(self, target_temp=20, initial_k1=10, initial_k2=30, learning_rate=0.1, param_file="heating_params.json"):
        self.target_temp = target_temp  # Docelowa temperatura wewnętrzna
        self.learning_rate = learning_rate  # Jak szybko dostosowujemy parametry
        self.param_file = param_file  # Ścieżka do pliku zapisu parametrów

        # Zakres częstotliwości pompki
        self.f_min = 1.4  # Hz (najniższa moc)
        self.f_max = 5.5  # Hz (maksymalna moc)
        
        # Moc cieplna odpowiadająca zakresowi częstotliwości
        self.p_min = 1.1e3  # W (przy 1.4 Hz)
        self.p_max = 4.3e3  # W (przy 5.5 Hz)
        
        # Bufor do wygładzania częstotliwości (FIFO)
        self.freq_history = collections.deque(maxlen=5)  # Uśredniamy 5 ostatnich wartości
        self.last_freq = self.f_min  # Poprzednia wartość częstotliwości
        self.hysteresis = 0.2  # Minimalna zmiana częstotliwości, żeby zaakceptować nową wartość

        # Wczytanie parametrów krzywej grzewczej
        self.k1, self.k2 = self.load_params(initial_k1, initial_k2)

    def save_params(self):
        """Zapisuje aktualne wartości k1 i k2 do pliku JSON."""
        with open(self.param_file, "w") as file:
            json.dump({"k1": self.k1, "k2": self.k2}, file)

    def load_params(self, default_k1, default_k2):
        """Wczytuje zapisane wartości k1 i k2 z pliku JSON, jeśli istnieje."""
        if os.path.exists(self.param_file):
            with open(self.param_file, "r") as file:
                data = json.load(file)
                return data.get("k1", default_k1), data.get("k2", default_k2)
        return default_k1, default_k2

    def update_curve(self, temp_ext, temp_int):
        """
        Dopasowuje parametry krzywej grzewczej na podstawie różnicy temperatur.
        """
        error = self.target_temp - temp_int  # Jak bardzo odbiegamy od celu

        # Korekta parametrów
        self.k1 += self.learning_rate * error
        self.k2 += self.learning_rate * (error / 2)

        # Ograniczenia dla stabilności
        self.k1 = max(0, min(self.k1, 20))
        self.k2 = max(0, min(self.k2, 50))

        # Zapisujemy nowe parametry
        self.save_params()

    def heating_frequency(self, temp_ext, heater_state):
        """
        Oblicza częstotliwość pompki na podstawie aktualnych parametrów.
        heater_state: True jeśli piec działa normalnie, False jeśli w trybie rozgrzewania
        """
        if not heater_state:
            return None  # Nie sterujemy pompą w trybie rozgrzewania

        power = max(0, self.k1 * (self.target_temp - temp_ext) + self.k2)
        power = min(power, self.p_max)  # Ograniczamy moc do maksymalnej wartości

        # Przekształcamy moc na częstotliwość pompki (1.4 Hz - 5.5 Hz)
        frequency = self.f_min + ((power - self.p_min) / (self.p_max - self.p_min)) * (self.f_max - self.f_min)
        frequency = round(max(self.f_min, min(frequency, self.f_max)), 2)  # Ograniczamy do zakresu pompki

        # Dodanie do bufora wygładzania
        self.freq_history.append(frequency)
        avg_frequency = sum(self.freq_history) / len(self.freq_history)  # Średnia wartość

        # Histereza - zmieniamy częstotliwość tylko, jeśli różnica przekracza 0.2 Hz
        if abs(avg_frequency - self.last_freq) >= self.hysteresis:
            self.last_freq = avg_frequency  # Akceptujemy nową wartość
        return round(self.last_freq, 2)

# Przykład użycia:
heater = AdaptiveHeating(target_temp=22)  # Ustawienie docelowej temperatury na 22°C

# Przykładowe odczyty temperatur:
external_temp = -5  # °C
internal_temp = 18  # °C
heater_state = True  # Piec pracuje normalnie

heater.update_curve(external_temp, internal_temp)  # Korekta parametrów
frequency = heater.heating_frequency(external_temp, heater_state)  # Nowa częstotliwość pompki

if frequency is not None:
    print(f"Częstotliwość pompki: {frequency} Hz")
else:
    print("Piec w trybie rozgrzewania - brak ingerencji w częstotliwość pompki.")
