"""Baseline volume calculation with outlier removal."""
import numpy as np
from typing import List, Tuple
import logging

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class BaselineCalculator:
    """Calculate baseline volume with outlier removal."""
    
    @staticmethod
    def calculate_baseline(
        volume_history: List[Tuple[int, float]],
        method: str = "median"
    ) -> float:
        """
        Calculate baseline volume from history.
        
        Args:
            volume_history: List of (timestamp, volume) tuples
            method: 'median' or 'mean' (median is more robust to outliers)
        
        Returns:
            Baseline volume
        """
        if not volume_history:
            return 0.0
        
        # Extract volumes
        volumes = [vol for _, vol in volume_history]
        
        if len(volumes) < 3:
            # Not enough data, use mean
            return np.mean(volumes) if volumes else 0.0
        
        # Remove outliers using IQR method
        volumes_clean = BaselineCalculator._remove_outliers(volumes)
        
        if not volumes_clean:
            # If all were outliers, use original
            volumes_clean = volumes
        
        # Calculate baseline
        if method == "median":
            baseline = np.median(volumes_clean)
        else:
            baseline = np.mean(volumes_clean)
        
        return float(baseline)
    
    @staticmethod
    def _remove_outliers(volumes: List[float], factor: float = 1.5) -> List[float]:
        """
        Remove outliers using Interquartile Range (IQR) method.
        
        Args:
            volumes: List of volume values
            factor: IQR multiplier (1.5 is standard)
        
        Returns:
            List of volumes with outliers removed
        """
        if len(volumes) < 4:
            return volumes
        
        volumes_array = np.array(volumes)
        q1 = np.percentile(volumes_array, 25)
        q3 = np.percentile(volumes_array, 75)
        iqr = q3 - q1
        
        if iqr == 0:
            # No variation, return all
            return volumes
        
        lower_bound = q1 - factor * iqr
        upper_bound = q3 + factor * iqr
        
        # Filter outliers
        filtered = [
            vol for vol in volumes
            if lower_bound <= vol <= upper_bound
        ]
        
        # Keep at least 50% of data
        min_keep = max(1, len(volumes) // 2)
        if len(filtered) < min_keep:
            # Too many outliers, use less aggressive filtering
            std = np.std(volumes_array)
            mean = np.mean(volumes_array)
            filtered = [
                vol for vol in volumes
                if mean - 2 * std <= vol <= mean + 2 * std
            ]
        
        return filtered if filtered else volumes
