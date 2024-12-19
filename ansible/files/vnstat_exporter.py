#!/usr/bin/env python3
"""
VNStat Prometheus Exporter
-------------------------

This exporter collects network traffic statistics from vnstat and exports them in Prometheus format.

Usage:
    python3 vnstat_exporter.py [--port PORT] [--interval INTERVAL]

Options:
    --port      Port to expose metrics on (default: 9469)
    --interval  Update interval in seconds (default: 60)

Useful Commands:
    # Start the exporter
    python3 vnstat_exporter.py

    # Start with custom port and interval
    python3 vnstat_exporter.py --port 8080 --interval 30

    # Check metrics endpoint
    curl http://localhost:9469/metrics

    # Monitor service logs
    journalctl -u vnstat_exporter -f
    
    # Follow logs with timestamps
    journalctl -u vnstat_exporter -f -n 100 --output=short-precise

    # Check service status
    systemctl status vnstat_exporter

    # View last hour of logs
    journalctl -u vnstat_exporter --since "1 hour ago"

    # Search for error messages
    journalctl -u vnstat_exporter | grep ERROR

Metrics Exported:
    vnstat_traffic_5min    - Traffic in the last 5 minutes
    vnstat_traffic_hourly  - Hourly network traffic
    vnstat_traffic_daily   - Daily network traffic
    vnstat_traffic_monthly - Monthly network traffic
    vnstat_traffic_yearly  - Yearly network traffic
    vnstat_traffic_total   - Total network traffic

Labels:
    interface - Network interface name (e.g., eth0)
    direction - Traffic direction (rx for received, tx for transmitted)
"""

import subprocess
import json
from prometheus_client import start_http_server, Gauge
import time
import argparse
import logging
import logging.handlers
import sys

# Set up logging
logger = logging.getLogger('vnstat_exporter')
logger.setLevel(logging.INFO)

# Add syslog handler
syslog_handler = logging.handlers.SysLogHandler(address='/dev/log')
syslog_formatter = logging.Formatter('%(name)s: %(message)s')
syslog_handler.setFormatter(syslog_formatter)

# Add journal handler (stdout/stderr)
stream_handler = logging.StreamHandler(sys.stdout)
stream_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
stream_handler.setFormatter(stream_formatter)

# Add handlers to logger
logger.addHandler(syslog_handler)
logger.addHandler(stream_handler)

# Define all Prometheus metrics
TRAFFIC_5MIN = Gauge('vnstat_traffic_5min', 'Traffic in the last 5 minutes', ['interface', 'direction'])
TRAFFIC_HOURLY = Gauge('vnstat_traffic_hourly', 'Hourly network traffic', ['interface', 'direction'])
TRAFFIC_DAILY = Gauge('vnstat_traffic_daily', 'Daily network traffic', ['interface', 'direction'])
TRAFFIC_MONTHLY = Gauge('vnstat_traffic_monthly', 'Monthly network traffic', ['interface', 'direction'])
TRAFFIC_YEARLY = Gauge('vnstat_traffic_yearly', 'Yearly network traffic', ['interface', 'direction'])
TRAFFIC_TOTAL = Gauge('vnstat_traffic_total', 'Total network traffic', ['interface', 'direction'])

def get_vnstat_data(interface=None):
    """Get network traffic data from vnstat in JSON format"""
    cmd = ['vnstat', '--json']
    if interface:
        cmd.extend(['-i', interface])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running vnstat: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing vnstat output: {e}")
        return None

def update_metrics():
    """Update Prometheus metrics with current vnstat data"""
    data = get_vnstat_data()
    if not data:
        return

    for interface in data.get('interfaces', []):
        iface_name = interface.get('name')
        traffic = interface.get('traffic', {})

        # Process 5 minute data - get the latest entry
        fiveminute = traffic.get('fiveminute', [])
        if fiveminute:
            latest_5min = fiveminute[-1]  # Get the most recent entry
            TRAFFIC_5MIN.labels(
                interface=iface_name,
                direction='rx'
            ).set(latest_5min.get('rx', 0))
            TRAFFIC_5MIN.labels(
                interface=iface_name,
                direction='tx'
            ).set(latest_5min.get('tx', 0))

        # Process hour data - get the latest entry
        hours = traffic.get('hour', [])
        if hours:
            latest_hour = hours[-1]
            TRAFFIC_HOURLY.labels(
                interface=iface_name,
                direction='rx'
            ).set(latest_hour.get('rx', 0))
            TRAFFIC_HOURLY.labels(
                interface=iface_name,
                direction='tx'
            ).set(latest_hour.get('tx', 0))

        # Process daily data - get the latest entry
        days = traffic.get('day', [])
        if days:
            latest_day = days[-1]
            TRAFFIC_DAILY.labels(
                interface=iface_name,
                direction='rx'
            ).set(latest_day.get('rx', 0))
            TRAFFIC_DAILY.labels(
                interface=iface_name,
                direction='tx'
            ).set(latest_day.get('tx', 0))

        # Process monthly data
        months = traffic.get('month', [])
        if months:
            latest_month = months[-1]
            TRAFFIC_MONTHLY.labels(
                interface=iface_name,
                direction='rx'
            ).set(latest_month.get('rx', 0))
            TRAFFIC_MONTHLY.labels(
                interface=iface_name,
                direction='tx'
            ).set(latest_month.get('tx', 0))

        # Process yearly data
        years = traffic.get('year', [])
        if years:
            latest_year = years[-1]
            TRAFFIC_YEARLY.labels(
                interface=iface_name,
                direction='rx'
            ).set(latest_year.get('rx', 0))
            TRAFFIC_YEARLY.labels(
                interface=iface_name,
                direction='tx'
            ).set(latest_year.get('tx', 0))

        # Process total data
        total = traffic.get('total', {})
        TRAFFIC_TOTAL.labels(
            interface=iface_name,
            direction='rx'
        ).set(total.get('rx', 0))
        TRAFFIC_TOTAL.labels(
            interface=iface_name,
            direction='tx'
        ).set(total.get('tx', 0))

def main():
    parser = argparse.ArgumentParser(description='VNStat Prometheus Exporter')
    parser.add_argument('--port', type=int, default=9469,
                      help='Port to expose metrics on (default: 9469)')
    parser.add_argument('--interval', type=int, default=60,
                      help='Metrics update interval in seconds (default: 60)')
    args = parser.parse_args()

    logger.info(f"Starting VNStat exporter on port {args.port}")
    logger.info(f"Update interval: {args.interval} seconds")
    
    # Test vnstat access
    logger.info("Testing vnstat access...")
    if get_vnstat_data():
        logger.info("Successfully called vnstat")
    else:
        logger.error("Failed to call vnstat")
        sys.exit(1)

    # Start up the server to expose the metrics
    try:
        start_http_server(args.port)
        logger.info(f"Metrics server started on port {args.port}")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")
        sys.exit(1)

    # Update metrics periodically
    while True:
        try:
            logger.info("Processing vnstat data...")
            update_metrics()
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")
        time.sleep(args.interval)

if __name__ == '__main__':
    main()
