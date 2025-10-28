#!/usr/bin/env python3
"""
Custom logger configuration for LDES Consumer.
Provides structured logging with appropriate levels and formatting.
"""
import logging
import sys
from typing import Optional


def setup_logger(name: str = "ldes-consumer", level: Optional[str] = None) -> logging.Logger:
    """
    Set up and configure a logger for the LDES consumer service.
    
    Args:
        name: Name of the logger
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               If None, defaults to INFO
    
    Returns:
        Configured logger instance
    """
    # Determine log level
    if level is None:
        level = "INFO"
    
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Add formatter to handler
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    return logger
