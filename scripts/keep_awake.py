# scripts/keep_awake.py
# !/usr/bin/env python3
"""
Advanced script to keep Streamlit Cloud app awake
and simulate user interactions
"""

import requests
import time
import random
import json
import sys
from datetime import datetime
from typing import Optional


class StreamlitAppKeeper:
    def __init__(self, app_url: str):
        self.app_url = app_url
        self.session = requests.Session()
        self.languages = ["en", "ru"]
        self.setup_session()

    def setup_session(self):
        """Initialize session with realistic browser headers"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        })

    def visit_page(self, params: Optional[dict] = None) -> int:
        """Visit the app page"""
        try:
            response = self.session.get(
                self.app_url,
                params=params,
                timeout=30,
                allow_redirects=True
            )
            return response.status_code
        except requests.exceptions.RequestException as e:
            print(f"Error visiting page: {e}")
            return 0

    def simulate_language_change(self):
        """Simulate changing language by sending requests with different Accept-Language"""
        selected_language = random.choice(self.languages)
        print(f"[{datetime.now()}] Simulating language change to: {selected_language}")

        # Update headers to simulate language preference
        self.session.headers.update({
            'Accept-Language': f'{selected_language},en;q=0.5'
        })

        return self.visit_page()

    def simulate_cache_clear(self):
        """Simulate cache clearing with multiple requests"""
        print(f"[{datetime.now()}] Simulating cache clearing...")

        for i in range(3):
            # Add unique cache-busting parameters
            params = {
                'cache_clear': int(time.time() * 1000),
                'request_id': i,
                'nocache': random.randint(10000, 99999)
            }

            status = self.visit_page(params)
            time.sleep(1)

            if status != 200:
                return False

        return True

    def check_health(self) -> bool:
        """Verify app is responsive"""
        try:
            response = self.session.get(self.app_url, timeout=10)
            if response.status_code == 200:
                # Check if response contains expected content
                if 'Streamlit' in response.text or response.text.strip():
                    return True
            return False
        except:
            return False

    def run_keep_alive_cycle(self):
        """Execute full keep-alive cycle"""
        print(f"[{datetime.now()}] Starting keep-alive cycle...")

        # Step 1: Wake up the app
        print(f"[{datetime.now()}] Step 1: Initial wake-up...")
        status = self.visit_page()
        if status != 200:
            print(f"⚠️ Wake-up returned status {status}, retrying...")
            time.sleep(5)
            status = self.visit_page()

        time.sleep(2)

        # Step 2: Simulate language selection
        print(f"[{datetime.now()}] Step 2: Language interaction...")
        self.simulate_language_change()
        time.sleep(2)

        # Step 3: Simulate clicking around
        print(f"[{datetime.now()}] Step 3: Simulating additional interactions...")
        # Add random query parameters to simulate state changes
        self.visit_page({'tab': 'input_params'})
        time.sleep(1)
        self.visit_page({'tab': 'processing_results'})
        time.sleep(1)

        # Step 4: Clear cache
        print(f"[{datetime.now()}] Step 4: Clearing cache...")
        self.simulate_cache_clear()
        time.sleep(2)

        # Step 5: Final health check
        print(f"[{datetime.now()}] Step 5: Health check...")
        if self.check_health():
            print(f"[{datetime.now()}] ✅ App is healthy and responsive")
            return True
        else:
            print(f"[{datetime.now()}] ⚠️ App health check failed")
            return False


def main():
    # Replace with your actual Streamlit Cloud URL
    APP_URL = "https://agroet.streamlit.app"

    if len(sys.argv) > 1:
        APP_URL = sys.argv[1]

    keeper = StreamlitAppKeeper(APP_URL)

    # Run keep-alive cycle
    success = keeper.run_keep_alive_cycle()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()