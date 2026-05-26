"""
NoiseAugmentation -- Add realistic background noise to caller audio.

SNR 15-25dB mixing with restaurant, street, speakerphone profiles.
Simulates real-world calling conditions for stress testing.
"""

import logging
import numpy as np
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class NoiseProfile:
    """Background noise profiles."""
    RESTAURANT = "restaurant"  # Chatter, clinking, ambient
    STREET = "street"  # Traffic, wind, sirens
    SPEAKERPHONE = "speakerphone"  # Echo, hollow, low quality


class NoiseAugmentation:
    """Add noise to audio for realistic testing."""

    def __init__(self, sample_rate: int = 8000):
        """
        Args:
            sample_rate: Audio sample rate (8000 Hz for phone quality)
        """
        self.sample_rate = sample_rate
        self.noise_profiles = {
            NoiseProfile.RESTAURANT: self._generate_restaurant_noise,
            NoiseProfile.STREET: self._generate_street_noise,
            NoiseProfile.SPEAKERPHONE: self._generate_speakerphone_noise,
        }

    def _generate_restaurant_noise(self, duration_ms: int) -> np.ndarray:
        """Generate restaurant ambient noise (chatter, clinking)."""
        num_samples = int(self.sample_rate * duration_ms / 1000)
        # Mix of low-freq hum + mid-freq chatter + occasional high peaks
        t = np.arange(num_samples) / self.sample_rate
        noise = (
            0.3 * np.sin(2 * np.pi * 60 * t) +  # 60Hz hum
            0.4 * np.random.normal(0, 0.1, num_samples) +  # Chatter
            0.2 * np.sin(2 * np.pi * 200 * t) * np.random.rand(num_samples)  # Clinking
        )
        return noise / np.max(np.abs(noise))  # Normalize

    def _generate_street_noise(self, duration_ms: int) -> np.ndarray:
        """Generate street noise (traffic, wind)."""
        num_samples = int(self.sample_rate * duration_ms / 1000)
        t = np.arange(num_samples) / self.sample_rate
        noise = (
            0.4 * np.random.normal(0, 0.15, num_samples) +  # Wind, traffic
            0.3 * np.sin(2 * np.pi * 120 * t) +  # Engine noise
            0.2 * np.sin(2 * np.pi * 500 * t) * (np.random.rand(num_samples) > 0.8)  # Sirens (sparse)
        )
        return noise / np.max(np.abs(noise))

    def _generate_speakerphone_noise(self, duration_ms: int) -> np.ndarray:
        """Generate speakerphone noise (echo, compression artifacts)."""
        num_samples = int(self.sample_rate * duration_ms / 1000)
        t = np.arange(num_samples) / self.sample_rate
        noise = (
            0.5 * np.random.normal(0, 0.08, num_samples) +  # Compression artifacts
            0.3 * np.sin(2 * np.pi * 50 * t)  # Low-freq rumble
        )
        return noise / np.max(np.abs(noise))

    def add_noise(
        self,
        audio: bytes,
        noise_profile: str,
        snr_db: float = 20.0,
    ) -> bytes:
        """
        Add background noise to audio at specified SNR.

        Args:
            audio: PCM 16-bit audio bytes
            noise_profile: e.g., "restaurant"
            snr_db: Signal-to-Noise Ratio (higher = less noise)

        Returns:
            Audio bytes with noise mixed in
        """
        # Convert bytes to numpy array (PCM 16-bit mono)
        audio_np = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0

        duration_ms = len(audio_np) / self.sample_rate * 1000
        noise_generator = self.noise_profiles.get(
            noise_profile,
            self.noise_profiles[NoiseProfile.RESTAURANT],
        )
        noise = noise_generator(int(duration_ms))

        # Adjust noise power to achieve target SNR
        signal_power = np.mean(audio_np ** 2)
        noise_power = np.mean(noise ** 2)
        snr_linear = 10 ** (snr_db / 10)
        noise_factor = np.sqrt(signal_power / (snr_linear * noise_power + 1e-8))
        noise = noise * noise_factor

        # Mix signal + noise
        mixed = audio_np + noise
        mixed = np.clip(mixed, -1.0, 1.0)  # Prevent clipping

        # Convert back to 16-bit PCM
        mixed_int16 = (mixed * 32767).astype(np.int16)
        return mixed_int16.tobytes()

    def get_random_snr(self) -> float:
        """Get random SNR value between 15-25dB."""
        import random
        return random.uniform(15.0, 25.0)
