#!/usr/bin/env python3
"""
Test script for Dual Grid API endpoints.
Tests H3 and Polygon grid endpoints with sample data.
"""

import sys
import json
import time
import requests
from datetime import datetime
from typing import Optional

# Configuration
API_BASE_URL = "http://localhost:8001"
TIMEOUT = 10

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_header(text: str):
    """Print section header"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{text:^70}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{GREEN}✓ {text}{RESET}")


def print_error(text: str):
    """Print error message"""
    print(f"{RED}✗ {text}{RESET}")


def print_info(text: str):
    """Print info message"""
    print(f"{YELLOW}ℹ {text}{RESET}")


def test_health_check():
    """Test /health endpoint"""
    print_header("Testing Health Check Endpoint")

    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            print_success("Health check passed")
            print(f"  Service: {data.get('service')}")
            print(f"  Version: {data.get('version')}")
            print(f"  Status: {data.get('status')}")
            return True
        else:
            print_error(f"Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Could not connect to API: {e}")
        print_info("Make sure the API server is running:")
        print_info("  python -m uvicorn app.main:app --reload")
        return False


def get_basins() -> Optional[str]:
    """Get list of basins and return Kansas Rift ID"""
    print_header("Fetching Available Basins")

    try:
        response = requests.get(f"{API_BASE_URL}/api/basins", timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            basins = data.get('basins', [])
            print_success(f"Found {len(basins)} basin(s)")

            kansas_rift_id = None
            for basin in basins:
                basin_name = basin.get('name', 'Unknown')
                basin_id = basin.get('id')
                print(f"  - {basin_name}: {basin_id}")
                if basin_name == "Kansas Rift":
                    kansas_rift_id = basin_id

            if kansas_rift_id:
                print_success(f"Kansas Rift basin ID: {kansas_rift_id}")
                return kansas_rift_id
            else:
                print_error("Kansas Rift basin not found")
                return None
        else:
            print_error(f"Failed to fetch basins: {response.status_code}")
            return None
    except Exception as e:
        print_error(f"Error fetching basins: {e}")
        return None


def test_polygon_grid(basin_id: str) -> bool:
    """Test /api/grids/polygon endpoint"""
    print_header("Testing Polygon Grid Endpoint")
    print_info(f"Basin ID: {basin_id}")

    try:
        url = f"{API_BASE_URL}/api/grids/polygon/{basin_id}"
        print(f"Fetching: {url}")

        response = requests.get(url, timeout=TIMEOUT)

        if response.status_code == 200:
            data = response.json()
            features = data.get('features', [])
            grid_type = data.get('grid_type')

            print_success(f"Polygon grid retrieved ({len(features)} cells)")
            print(f"  Grid type: {grid_type}")
            print(f"  Features: {len(features)}")

            if features:
                sample = features[0]
                props = sample.get('properties', {})
                print(f"  Sample cell:")
                print(f"    - Position: ({props.get('grid_x')}, {props.get('grid_y')})")
                print(f"    - Score: {props.get('score', 'N/A')}")
                print(f"    - Color: {props.get('color', 'N/A')}")

                # Check for prospects
                if 'prospects' in data:
                    prospects = data['prospects'].get('features', [])
                    print(f"  Hydrogen prospects: {len(prospects)}")

            return True
        else:
            print_error(f"Failed to get polygon grid: {response.status_code}")
            print_info(f"Response: {response.text[:200]}")
            return False
    except Exception as e:
        print_error(f"Error fetching polygon grid: {e}")
        return False


def test_h3_grid(basin_id: str, resolution: int = 5) -> bool:
    """Test /api/grids/h3 endpoint"""
    print_header("Testing H3 Grid Endpoint")
    print_info(f"Basin ID: {basin_id}, Resolution: {resolution}")

    try:
        url = f"{API_BASE_URL}/api/grids/h3/{basin_id}?resolution={resolution}"
        print(f"Fetching: {url}")

        response = requests.get(url, timeout=TIMEOUT)

        if response.status_code == 200:
            data = response.json()
            features = data.get('features', [])
            grid_type = data.get('grid_type')
            res = data.get('resolution')

            print_success(f"H3 grid retrieved ({len(features)} cells)")
            print(f"  Grid type: {grid_type}")
            print(f"  Resolution: {res}")
            print(f"  Features: {len(features)}")

            if features:
                sample = features[0]
                props = sample.get('properties', {})
                print(f"  Sample cell:")
                print(f"    - H3 ID: {props.get('h3_id', 'N/A')[:16]}...")
                print(f"    - Score: {props.get('score', 'N/A')}")
                print(f"    - Quintile: {props.get('quintile', 'N/A')}/5")
                print(f"    - Color: {props.get('color', 'N/A')}")

                # Check geometry
                geom = sample.get('geometry', {})
                geom_type = geom.get('type')
                print(f"    - Geometry: {geom_type}")

                # Check for prospects
                if 'prospects' in data:
                    prospects = data['prospects'].get('features', [])
                    print(f"  Hydrogen prospects: {len(prospects)}")

            return True
        else:
            print_error(f"Failed to get H3 grid: {response.status_code}")
            print_info(f"Response: {response.text[:200]}")
            return False
    except Exception as e:
        print_error(f"Error fetching H3 grid: {e}")
        return False


def test_prospects(basin_id: str) -> bool:
    """Test /api/prospects endpoint"""
    print_header("Testing Hydrogen Prospects Endpoint")
    print_info(f"Basin ID: {basin_id}")

    try:
        # Test H3 prospects
        url = f"{API_BASE_URL}/api/prospects/{basin_id}?grid_type=h3"
        print(f"Fetching H3 prospects: {url}")

        response = requests.get(url, timeout=TIMEOUT)

        if response.status_code == 200:
            data = response.json()
            features = data.get('features', [])
            count = data.get('count', 0)

            print_success(f"Prospects retrieved ({count} total)")
            print(f"  Features: {len(features)}")

            if features:
                sample = features[0]
                props = sample.get('properties', {})
                geom = sample.get('geometry', {})
                coords = geom.get('coordinates', [0, 0])

                print(f"  Sample prospect:")
                print(f"    - Type: {props.get('prospect_type', 'N/A')}")
                print(f"    - Significance: {props.get('significance_score', 'N/A')}")
                print(f"    - Location: ({coords[0]:.4f}, {coords[1]:.4f})")
                print(f"    - H3 ID: {props.get('h3_id', 'N/A')[:16]}..." if props.get('h3_id') else "    - H3 ID: N/A")

            return True
        else:
            print_error(f"Failed to get prospects: {response.status_code}")
            print_info(f"Response: {response.text[:200]}")
            return False
    except Exception as e:
        print_error(f"Error fetching prospects: {e}")
        return False


def test_grid_types(basin_id: str) -> bool:
    """Test /api/grids/grid-types endpoint"""
    print_header("Testing Grid Types Endpoint")
    print_info(f"Basin ID: {basin_id}")

    try:
        url = f"{API_BASE_URL}/api/grids/grid-types/{basin_id}"
        print(f"Fetching: {url}")

        response = requests.get(url, timeout=TIMEOUT)

        if response.status_code == 200:
            data = response.json()
            grids = data.get('available_grids', [])

            print_success(f"Grid configurations retrieved ({len(grids)} types)")

            for grid in grids:
                grid_type = grid.get('grid_type')
                params = grid.get('grid_params', {})
                cells = grid.get('cell_count', 0)
                prospects = grid.get('prospect_count', 0)

                print(f"  - {grid_type.upper()}")
                print(f"    - Parameters: {params}")
                print(f"    - Cells: {cells}")
                print(f"    - Prospects: {prospects}")

            return True
        else:
            print_error(f"Failed to get grid types: {response.status_code}")
            print_info(f"Response: {response.text[:200]}")
            return False
    except Exception as e:
        print_error(f"Error fetching grid types: {e}")
        return False


def run_performance_test(basin_id: str) -> None:
    """Run performance benchmarks"""
    print_header("Performance Benchmarks")

    endpoints = [
        ("Polygon Grid", f"{API_BASE_URL}/api/grids/polygon/{basin_id}"),
        ("H3 Grid (Res 5)", f"{API_BASE_URL}/api/grids/h3/{basin_id}?resolution=5"),
        ("H3 Grid (Res 7)", f"{API_BASE_URL}/api/grids/h3/{basin_id}?resolution=7"),
        ("Prospects", f"{API_BASE_URL}/api/prospects/{basin_id}?grid_type=h3"),
        ("Grid Types", f"{API_BASE_URL}/api/grids/grid-types/{basin_id}"),
    ]

    print("Running performance tests...\n")

    for name, url in endpoints:
        times = []
        for _ in range(3):  # 3 runs
            try:
                start = time.time()
                response = requests.get(url, timeout=TIMEOUT)
                elapsed = (time.time() - start) * 1000  # Convert to ms

                if response.status_code == 200:
                    times.append(elapsed)
                else:
                    elapsed = -1
            except:
                elapsed = -1

        if times:
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)

            color = GREEN if avg_time < 500 else YELLOW if avg_time < 1000 else RED
            print(f"{color}{name:20} {avg_time:6.1f}ms (min: {min_time:5.1f}, max: {max_time:5.1f}){RESET}")
        else:
            print(f"{RED}{name:20} FAILED{RESET}")


def main():
    """Main test execution"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{'Dual Grid System - API Test Suite':^70}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")

    # Step 1: Health check
    if not test_health_check():
        print_error("API server is not running. Exiting.")
        sys.exit(1)

    time.sleep(1)

    # Step 2: Get basin ID
    basin_id = get_basins()
    if not basin_id:
        print_error("Could not find Kansas Rift basin")
        sys.exit(1)

    time.sleep(1)

    # Step 3: Test endpoints
    results = {
        "Polygon Grid": test_polygon_grid(basin_id),
        "H3 Grid": test_h3_grid(basin_id),
        "Prospects": test_prospects(basin_id),
        "Grid Types": test_grid_types(basin_id),
    }

    time.sleep(1)

    # Step 4: Performance tests
    run_performance_test(basin_id)

    # Summary
    print_header("Test Results Summary")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"  {name:20} {status}")

    print(f"\n{BLUE}Total: {passed}/{total} tests passed{RESET}\n")

    if passed == total:
        print_success("All tests passed! ✓")
        sys.exit(0)
    else:
        print_error(f"{total - passed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
