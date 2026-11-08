"""
Simple traffic generator for R4.
Fires repeated requests at the ALB DNS name so you can watch the
Auto Scaling Group react (or just prove the site is reachable).

Usage:
    pip install requests
    python traffic_generator.py http://your-alb-dns-name.elb.amazonaws.com
"""

import sys
import time
import threading
import requests

def hit(url, thread_id, count):
    for i in range(count):
        try:
            r = requests.get(url, timeout=5)
            print(f"[thread {thread_id}] request {i+1}: status {r.status_code}")
        except requests.RequestException as e:
            print(f"[thread {thread_id}] request {i+1}: failed - {e}")
        time.sleep(0.5)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python traffic_generator.py <alb_url>")
        sys.exit(1)

    url = sys.argv[1]
    num_threads = 5
    requests_per_thread = 20

    threads = []
    for t in range(num_threads):
        th = threading.Thread(target=hit, args=(url, t, requests_per_thread))
        threads.append(th)
        th.start()

    for th in threads:
        th.join()

    print("Traffic generation complete.")
