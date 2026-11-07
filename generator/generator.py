"""Sensor emulator: sends temperature measurements to the application API.

History mode (default) sends --count values with past timestamps spaced by --interval seconds,
the last one at the current time. Live mode (--live) sends a current value every --interval seconds.
"""

import argparse
import json
import math
import os
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone


def parse_args():
    parser = argparse.ArgumentParser(description="Sensor emulator for the ZAI 26Z measurement API.")
    parser.add_argument("--api", default=os.environ.get("ZAI_API_URL"),
                        help="API base address, e.g. https://example.com (or ZAI_API_URL env variable)")
    parser.add_argument("--key", default=os.environ.get("ZAI_API_KEY"),
                        help="sensor API key (or ZAI_API_KEY env variable)")
    parser.add_argument("--count", type=int, default=24,
                        help="number of values to send (in live mode: 0 = until stopped), default 24")
    parser.add_argument("--interval", type=float, default=3600,
                        help="seconds between values, default 3600")
    parser.add_argument("--mode", choices=["random", "sine"], default="sine",
                        help="value generation: uniform random or sine wave, default sine")
    parser.add_argument("--min", type=float, default=15.0, help="lowest generated value, default 15")
    parser.add_argument("--max", type=float, default=25.0, help="highest generated value, default 25")
    parser.add_argument("--period", type=int, default=24,
                        help="number of values per full sine cycle, default 24")
    parser.add_argument("--live", action="store_true",
                        help="send current values every --interval seconds instead of past ones")
    args = parser.parse_args()

    if not args.api:
        parser.error("API address is required (--api or ZAI_API_URL)")
    if not args.key:
        parser.error("sensor API key is required (--key or ZAI_API_KEY)")
    if args.min > args.max:
        parser.error("--min must not be greater than --max")
    return args


def generate_value(args, index):
    if args.mode == "random":
        value = random.uniform(args.min, args.max)
    else:
        middle = (args.min + args.max) / 2
        amplitude = (args.max - args.min) / 2
        value = middle + amplitude * math.sin(2 * math.pi * index / args.period)
    return round(value, 2)


def send(args, value, timestamp=None):
    body = {"value": value}
    if timestamp is not None:
        body["timestamp"] = timestamp.isoformat().replace("+00:00", "Z")

    request = urllib.request.Request(
        args.api.rstrip("/") + "/api/measurements",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json", "X-API-Key": args.key},
        method="POST",
    )
    label = f"value={value}" + (f" timestamp={body['timestamp']}" if timestamp else "")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            print(f"OK       {label} (HTTP {response.status})")
            return True
    except urllib.error.HTTPError as error:
        try:
            detail = json.loads(error.read()).get("detail", "")
        except ValueError:
            detail = ""
        print(f"REJECTED {label} (HTTP {error.code}) {detail}")
    except urllib.error.URLError as error:
        print(f"ERROR    {label}: cannot connect to API ({error.reason})")
    return False


def send_history(args):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    sent = 0
    for i in range(args.count):
        timestamp = now - timedelta(seconds=args.interval * (args.count - 1 - i))
        sent += send(args, generate_value(args, i), timestamp)
    return sent


def send_live(args):
    sent = 0
    i = 0
    try:
        while args.count == 0 or i < args.count:
            sent += send(args, generate_value(args, i))
            i += 1
            if args.count == 0 or i < args.count:
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print("Stopped.")
    return sent


def main():
    args = parse_args()
    sent = send_live(args) if args.live else send_history(args)
    print(f"Accepted {sent} measurement(s).")
    return 0 if sent > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
