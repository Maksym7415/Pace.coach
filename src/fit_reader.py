#!/usr/bin/env python3
"""
Utilities for reading and processing FIT files
"""
import fitparse
import pandas as pd
from datetime import datetime


class FitReader:
    """Class for reading FIT files"""
    
    @staticmethod
    def extract_records(fit_file):
        """Extract records from FIT file
        
        Args:
            fit_file: Path to FIT file
            
        Returns:
            DataFrame with workout records
        """
        fit = fitparse.FitFile(fit_file)
        
        records = []
        for record in fit.get_messages("record"):
            record_data = {
                'timestamp': record.get_value("timestamp"),
                'heart_rate': record.get_value("heart_rate"),
                'cadence': record.get_value("cadence"),
                'speed': record.get_value("speed"),
                'enhanced_speed': record.get_value("enhanced_speed"),
                'distance': record.get_value("distance"),
                'power': record.get_value("power"),
                'temperature': record.get_value("temperature"),
                'vertical_oscillation': record.get_value("vertical_oscillation"),
                'vertical_ratio': record.get_value("vertical_ratio"),
                'step_length': record.get_value("step_length"),
                'stance_time_balance': record.get_value("stance_time_balance"),
                'enhanced_altitude': record.get_value("enhanced_altitude"),
                'stance_time': record.get_value("stance_time"),
                'stance_time_percent': record.get_value("stance_time_percent"),
                'accumulated_power': record.get_value("accumulated_power"),
                'fractional_cadence': record.get_value("fractional_cadence"),
                'activity_type': record.get_value("activity_type"),
            }
            records.append(record_data)
        
        return pd.DataFrame(records)
    
    @staticmethod
    def get_workout_date(fit_file):
        """Get workout date from FIT file
        
        Args:
            fit_file: Path to FIT file
            
        Returns:
            datetime.date object or None
        """
        fit = fitparse.FitFile(fit_file)
        
        # Try to get from file_id
        for file_id in fit.get_messages("file_id"):
            if file_id.get_value("time_created"):
                return file_id.get_value("time_created").date()
        
        # Try to get from session
        for session in fit.get_messages("session"):
            if session.get_value("timestamp"):
                return session.get_value("timestamp").date()
        
        return None
    
    @staticmethod
    def get_session_data(fit_file):
        """Extract session data from FIT file
        
        Args:
            fit_file: Path to FIT file
            
        Returns:
            Dict with session data
        """
        fit = fitparse.FitFile(fit_file)
        
        for session in fit.get_messages('session'):
            return {
                'total_calories': session.get_value('total_calories'),
                'total_ascent': session.get_value('total_ascent'),
                'total_descent': session.get_value('total_descent'),
                'total_training_effect': session.get_value('total_training_effect'),
                'normalized_power': session.get_value('normalized_power'),
                'total_work': session.get_value('total_work'),
            }
        
        return {}
    
    @staticmethod
    def fit_to_csv(fit_file, csv_file):
        """Convert FIT file to CSV
        
        Args:
            fit_file: Path to FIT file
            csv_file: Path to output CSV file
        """
        df = FitReader.extract_records(fit_file)
        
        # Convert vertical oscillation from mm to cm
        if 'vertical_oscillation' in df.columns:
            df['vertical_oscillation_cm'] = df['vertical_oscillation'] / 10.0
        
        df.to_csv(csv_file, index=False)
        print(f"✅ Converted {fit_file} -> {csv_file}")
