#!/usr/bin/env python3
"""
Structured logging utility for RepoIntel Suite
Provides consistent logging with timestamps and levels across all scripts.
"""
import logging
import sys
from datetime import datetime
from typing import Optional


class RepoLogger:
    """Structured logger for RepoIntel operations."""
    
    def __init__(self, name: str, level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Avoid duplicate handlers
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%H:%M:%S'
                )
            )
            self.logger.addHandler(handler)
    
    def info(self, msg: str, emoji: str = "ℹ️"):
        """Log info message with optional emoji."""
        self.logger.info(f"{emoji}  {msg}")
    
    def success(self, msg: str):
        """Log success message."""
        self.logger.info(f"✅  {msg}")
    
    def warning(self, msg: str):
        """Log warning message."""
        self.logger.warning(f"⚠️  {msg}")
    
    def error(self, msg: str):
        """Log error message."""
        self.logger.error(f"❌  {msg}")
    
    def debug(self, msg: str):
        """Log debug message."""
        self.logger.debug(f"🔍  {msg}")
    
    def progress(self, msg: str):
        """Log progress update."""
        self.logger.info(f"⏳  {msg}")
    
    def analysis_start(self, analysis_type: str):
        """Log analysis start."""
        self.logger.info(f"🚀  Iniciando análisis: {analysis_type}")
    
    def analysis_complete(self, analysis_type: str, duration: Optional[float] = None):
        """Log analysis completion."""
        msg = f"Análisis completado: {analysis_type}"
        if duration:
            msg += f" ({duration:.1f}s)"
        self.logger.info(f"✅  {msg}")
    
    def lock_acquired(self, lock_file: str):
        """Log lock acquisition."""
        self.logger.info(f"🔒  Bloqueo establecido: {lock_file}")
    
    def lock_released(self, lock_file: str):
        """Log lock release."""
        self.logger.info(f"🔓  Bloqueo liberado: {lock_file}")


def get_logger(name: str, level: str = "INFO") -> RepoLogger:
    """Get a configured logger instance."""
    return RepoLogger(name, level)
