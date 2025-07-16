#!/usr/bin/env python3
"""
Performance test for validation system to ensure 422 error fixes don't impact performance
"""

import requests
import json
import time
import statistics

def generate_test_data(size):
    """Generate test data of varying sizes"""
    colors = []
    color_codes = [
        "RAL7048", "RAL5017", "69115038", "RAL1019", "160024", "20889000",
        "RAL9023", "RAL9006", "RAL9007", "RAL9001", "160058", "160000",
        "RAL7024", "RAL7015", "RAL7011", "RAL8019", "RAL3020", "RAL9003"
    ]
    color_types = ["E", "K", "R", "RE", "F"]
    orders = ["corto", "lungo"]
    
    for i in range(size):
        colors.append({
            "code": f"{color_codes[i % len(color_codes)]}-{i}",
            "type": color_types[i % len(color_types)],
            "CH": round(1.0 + (i % 5) * 0.5, 1),
            "lunghezza_ordine": orders[i % len(orders)]
        })
    
    return {
        "colors_today": colors,
        "prioritized_reintegrations": [colors[0]["code"], colors[1]["code"]] if size > 1 else []
    }

def test_api_performance(endpoint, data, test_name):
    """Test API performance with given data"""
    times = []
    
    print(f"\n=== {test_name} ===")
    print(f"Testing with {len(data['colors_today'])} colors")
    
    # Warmup request
    try:
        requests.post(endpoint, json=data, timeout=30)
    except:
        pass
    
    # Performance tests
    for i in range(5):
        start_time = time.time()
        try:
            response = requests.post(endpoint, json=data, timeout=30)
            end_time = time.time()
            
            if response.status_code == 200:
                request_time = end_time - start_time
                times.append(request_time)
                print(f"  Request {i+1}: {request_time:.3f}s ✅")
            else:
                print(f"  Request {i+1}: FAILED (Status: {response.status_code})")
        except Exception as e:
            end_time = time.time()
            print(f"  Request {i+1}: ERROR - {e}")
    
    if times:
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        print(f"  Average: {avg_time:.3f}s | Min: {min_time:.3f}s | Max: {max_time:.3f}s")
        return avg_time
    else:
        print("  No successful requests")
        return None

def test_validation_performance():
    """Test validation doesn't significantly impact performance"""
    print("Validation Performance Test")
    print("=" * 50)
    
    frontend_endpoint = "http://localhost:5001/api/optimize"
    backend_endpoint = "http://localhost:8001/optimize"
    
    # Test different data sizes
    test_sizes = [5, 10, 20]
    frontend_times = []
    backend_times = []
    
    for size in test_sizes:
        data = generate_test_data(size)
        
        # Test frontend
        frontend_time = test_api_performance(frontend_endpoint, data, f"Frontend - {size} colors")
        if frontend_time:
            frontend_times.append(frontend_time)
        
        # Test backend
        backend_time = test_api_performance(backend_endpoint, data, f"Backend - {size} colors")
        if backend_time:
            backend_times.append(backend_time)
    
    # Test malformed data handling performance
    print(f"\n=== Validation Error Handling Performance ===")
    
    malformed_data_tests = [
        ({"colors_today": []}, "Empty array"),
        ({"colors_today": [{"code": "RAL9005"}]}, "Missing type"),
        ({"colors_today": [{"type": "R"}]}, "Missing code"),
        ({"colors_today": "not_an_array"}, "Invalid array")
    ]
    
    validation_times = []
    for malformed_data, test_desc in malformed_data_tests:
        start_time = time.time()
        try:
            response = requests.post(frontend_endpoint, json=malformed_data, timeout=10)
            end_time = time.time()
            request_time = end_time - start_time
            validation_times.append(request_time)
            print(f"  {test_desc}: {request_time:.3f}s (Status: {response.status_code})")
        except Exception as e:
            end_time = time.time()
            print(f"  {test_desc}: ERROR - {e}")
    
    # Summary
    print(f"\n" + "=" * 50)
    print("PERFORMANCE SUMMARY:")
    if frontend_times:
        print(f"✅ Frontend avg response time: {statistics.mean(frontend_times):.3f}s")
    if backend_times:
        print(f"✅ Backend avg response time: {statistics.mean(backend_times):.3f}s")
    if validation_times:
        print(f"✅ Validation error handling: {statistics.mean(validation_times):.3f}s")
    
    # Performance thresholds
    max_acceptable_time = 5.0  # 5 seconds max
    if frontend_times and statistics.mean(frontend_times) < max_acceptable_time:
        print(f"✅ Frontend performance: GOOD (< {max_acceptable_time}s)")
    if backend_times and statistics.mean(backend_times) < max_acceptable_time:
        print(f"✅ Backend performance: GOOD (< {max_acceptable_time}s)")
    if validation_times and statistics.mean(validation_times) < 1.0:
        print(f"✅ Validation performance: EXCELLENT (< 1s)")

if __name__ == "__main__":
    test_validation_performance()
