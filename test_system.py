#!/usr/bin/env python3
"""
Simple test script to verify the Voice AI Platform is working.
Tests basic connectivity to all services.
"""

import asyncio
import json
import websockets
import requests
from datetime import datetime

async def test_websocket_connection():
    """Test WebSocket connection to the realtime gateway."""
    try:
        uri = "ws://localhost:8080"
        print(f"Testing WebSocket connection to {uri}...")
        
        async with websockets.connect(uri) as websocket:
            # Send a test message
            test_message = {
                "type": "test",
                "timestamp": datetime.now().isoformat(),
                "data": "Hello from test script"
            }
            await websocket.send(json.dumps(test_message))
            print("WebSocket connection: SUCCESS")
            return True
    except Exception as e:
        print(f"WebSocket connection: FAILED - {e}")
        return False

def test_http_services():
    """Test HTTP endpoints of various services."""
    services = {
        "Realtime Gateway": "http://localhost:8080",
        "Orchestrator": "http://localhost:50052",
        "Memory Service": "http://localhost:50055", 
        "Scheduler Service": "http://localhost:50056",
        "TTS Service": "http://localhost:50054",
        "LLM Service": "http://localhost:50053",
        "STT Service": "http://localhost:50051"
    }
    
    results = {}
    for name, url in services.items():
        try:
            print(f"Testing {name} at {url}...")
            # Try different health endpoints
            for endpoint in ["/health", "/", "/status"]:
                try:
                    response = requests.get(f"{url}{endpoint}", timeout=5)
                    if response.status_code in [200, 404]:  # 404 is ok, service is running
                        results[name] = "SUCCESS"
                        print(f"{name}: SUCCESS (status {response.status_code})")
                        break
                except:
                    continue
            else:
                results[name] = "FAILED"
                print(f"{name}: FAILED")
        except Exception as e:
            results[name] = f"FAILED - {e}"
            print(f"{name}: FAILED - {e}")
    
    return results

def test_database_connection():
    """Test database connectivity."""
    try:
        import asyncpg
        print("Testing PostgreSQL connection...")
        
        async def test_db():
            conn = await asyncpg.connect(
                host="localhost",
                port=5432,
                user="postgres",
                password="postgres",
                database="voiceai"
            )
            
            # Test a simple query
            result = await conn.fetchval("SELECT 1")
            await conn.close()
            return result == 1
        
        # Run the async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(test_db())
        loop.close()
        
        if result:
            print("PostgreSQL: SUCCESS")
            return True
    except Exception as e:
        print(f"PostgreSQL: FAILED - {e}")
        return False

def test_redis_connection():
    """Test Redis connectivity."""
    try:
        import redis
        print("Testing Redis connection...")
        
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        print("Redis: SUCCESS")
        return True
    except Exception as e:
        print(f"Redis: FAILED - {e}")
        return False

async def main():
    """Run all tests."""
    print("=" * 60)
    print("Voice AI Platform - System Test")
    print("=" * 60)
    print(f"Test started at: {datetime.now()}")
    print()
    
    # Test HTTP services
    http_results = test_http_services()
    print()
    
    # Test WebSocket
    ws_result = await test_websocket_connection()
    print()
    
    # Test databases
    db_result = test_database_connection()
    print()
    redis_result = test_redis_connection()
    print()
    
    # Summary
    print("=" * 60)
    print("Test Summary:")
    print("=" * 60)
    
    success_count = 0
    total_count = 0
    
    for service, result in http_results.items():
        total_count += 1
        if "SUCCESS" in result:
            success_count += 1
        print(f"{service}: {result}")
    
    total_count += 3  # WebSocket, PostgreSQL, Redis
    if ws_result:
        success_count += 1
    print(f"WebSocket: {'SUCCESS' if ws_result else 'FAILED'}")
    
    if db_result:
        success_count += 1
    print(f"PostgreSQL: {'SUCCESS' if db_result else 'FAILED'}")
    
    if redis_result:
        success_count += 1
    print(f"Redis: {'SUCCESS' if redis_result else 'FAILED'}")
    
    print()
    print(f"Overall: {success_count}/{total_count} services working")
    print("=" * 60)
    
    if success_count == total_count:
        print("All systems operational! Ready for testing.")
    else:
        print("Some services are not responding. Check the logs.")

if __name__ == "__main__":
    asyncio.run(main())
