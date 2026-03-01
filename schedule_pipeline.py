import os
import time
import subprocess
import sys


def run_pipeline_once():
    """Run the Kafka pipeline as a subprocess and wait for completion."""
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")

    print("[SCHEDULER] Launching Kafka pipeline", flush=True)
    proc = subprocess.Popen(
        [sys.executable, "run_kafka_pipeline.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=env,
    )

    # Stream output to keep logs visible
    for line in proc.stdout:
        if line:
            print(f"[PIPELINE] {line.rstrip()}", flush=True)

    returncode = proc.wait()
    print(f"[SCHEDULER] Pipeline finished with code {returncode}", flush=True)
    return returncode


def main():
    # Default: every 12 hours (43200 seconds). Override with SCHEDULER_INTERVAL_SECONDS.
    interval = int(os.getenv("SCHEDULER_INTERVAL_SECONDS", 43200))
    print(f"[SCHEDULER] Starting loop, interval={interval}s", flush=True)

    while True:
        try:
            rc = run_pipeline_once()
            if rc != 0:
                print(f"[SCHEDULER] Pipeline exited with non-zero code {rc}", flush=True)
        except Exception as e:
            print(f"[SCHEDULER] Error running pipeline: {e}", flush=True)

        print(f"[SCHEDULER] Sleeping {interval}s before next run", flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    main()