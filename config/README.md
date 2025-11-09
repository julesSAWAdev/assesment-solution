# Configuration Directory

This directory contains configuration files for the data pipeline.

## Files

- `pipeline_config.yaml` - Main pipeline configuration settings

## Purpose

Configuration files allow you to:
- Adjust API rate limits and timeouts
- Configure data storage formats
- Set transformation parameters
- Tune database connection settings

## Usage

Configuration values are used as defaults. Environment variables in `.env` take precedence over these settings.
