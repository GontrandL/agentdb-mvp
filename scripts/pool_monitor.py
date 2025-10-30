#!/usr/bin/env python3
"""
Continuous Pool Monitor - Automatically generates tasks when pool runs low.

Runs in background and triggers auto_task_generator when available tasks drop below threshold.
Focus: CODE and TESTS first, validation second, documentation last.
"""

import time
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime


class PoolMonitor:
    """Continuously monitors worker pool and triggers task generation when needed."""

    def __init__(
        self,
        project_root: str = "/home/gontrand/ActiveProjects/agentdb-mvp",
        min_threshold: int = 20,
        check_interval: int = 30
    ):
        self.project_root = Path(project_root)
        self.queue_file = self.project_root / "WORKER_TASK_QUEUE.json"
        self.min_threshold = min_threshold
        self.check_interval = check_interval  # seconds between checks

    def count_available(self) -> int:
        """Count available tasks in pool."""
        try:
            with open(self.queue_file, 'r') as f:
                data = json.load(f)
            return sum(1 for t in data['tasks'] if t['status'] == 'available')
        except Exception as e:
            print(f"Error reading queue: {e}", file=sys.stderr)
            return 0

    def trigger_generation(self) -> bool:
        """Trigger auto task generator script."""
        try:
            generator_script = self.project_root / "scripts" / "auto_task_generator.py"

            print(f"[{datetime.now().isoformat()}] Triggering task generation...")

            result = subprocess.run(
                [sys.executable, str(generator_script)],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                print(result.stdout)
                return True
            else:
                print(f"Generation failed: {result.stderr}", file=sys.stderr)
                return False

        except Exception as e:
            print(f"Error triggering generation: {e}", file=sys.stderr)
            return False

    def run_continuous(self):
        """Run continuous monitoring loop."""
        print(f"🔍 Pool Monitor Started")
        print(f"   Threshold: {self.min_threshold} available tasks")
        print(f"   Check interval: {self.check_interval} seconds")
        print(f"   Queue file: {self.queue_file}")
        print()

        consecutive_failures = 0
        max_failures = 5

        while True:
            try:
                available = self.count_available()
                timestamp = datetime.now().strftime("%H:%M:%S")

                print(f"[{timestamp}] Available tasks: {available}")

                if available < self.min_threshold:
                    print(f"⚠️  Below threshold ({self.min_threshold})! Generating tasks...")

                    if self.trigger_generation():
                        consecutive_failures = 0
                        # Check new count
                        new_available = self.count_available()
                        print(f"✅ Generation complete. New count: {new_available}")
                    else:
                        consecutive_failures += 1
                        print(f"❌ Generation failed ({consecutive_failures}/{max_failures})")

                        if consecutive_failures >= max_failures:
                            print("Too many failures. Exiting.", file=sys.stderr)
                            return 1
                else:
                    print(f"✓ Pool healthy ({available} >= {self.min_threshold})")
                    consecutive_failures = 0

                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                print("\n👋 Monitor stopped by user")
                return 0
            except Exception as e:
                print(f"Error in monitor loop: {e}", file=sys.stderr)
                consecutive_failures += 1

                if consecutive_failures >= max_failures:
                    print("Too many errors. Exiting.", file=sys.stderr)
                    return 1

                time.sleep(self.check_interval)


def main():
    """Run pool monitor with configuration."""
    import argparse

    parser = argparse.ArgumentParser(description="Continuous worker pool monitor")
    parser.add_argument(
        "--threshold",
        type=int,
        default=20,
        help="Minimum available tasks before triggering generation (default: 20)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Check interval in seconds (default: 30)"
    )

    args = parser.parse_args()

    monitor = PoolMonitor(
        min_threshold=args.threshold,
        check_interval=args.interval
    )

    sys.exit(monitor.run_continuous())


if __name__ == '__main__':
    main()
