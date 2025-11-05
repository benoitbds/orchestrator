#!/usr/bin/env python3
"""Test WebSocket connection to verify connectivity."""
import asyncio
import websockets
import json
import sys

async def test_websocket():
    """Test WebSocket connection."""
    run_id = "test-connection-123"
    
    # Try local connection
    urls = [
        f"ws://localhost:8000/ws/agents/{run_id}",
        f"wss://agent4ba.baq.ovh/ws/agents/{run_id}"
    ]
    
    for url in urls:
        print(f"\n{'='*60}")
        print(f"Testing WebSocket connection to: {url}")
        print(f"{'='*60}")
        
        try:
            async with websockets.connect(url, ping_timeout=10) as websocket:
                print(f"✅ Connected successfully!")
                print(f"Protocol: {websocket.subprotocol}")
                print(f"Extensions: {websocket.extensions}")
                
                # Send a ping message
                ping_msg = {"type": "ping"}
                print(f"\n📤 Sending ping: {ping_msg}")
                await websocket.send(json.dumps(ping_msg))
                
                # Wait for pong
                print(f"⏳ Waiting for response...")
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    print(f"✅ Received: {response}")
                except asyncio.TimeoutError:
                    print(f"⚠️ No response within 5 seconds")
                
                print(f"✅ Connection test successful for {url}")
                return True
                
        except websockets.exceptions.InvalidStatusCode as e:
            print(f"❌ Invalid status code: {e.status_code}")
            print(f"Headers: {e.headers}")
        except websockets.exceptions.WebSocketException as e:
            print(f"❌ WebSocket error: {type(e).__name__}: {e}")
        except Exception as e:
            print(f"❌ Connection failed: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    return False

if __name__ == "__main__":
    print("WebSocket Connection Test")
    print("=" * 60)
    
    success = asyncio.run(test_websocket())
    
    if success:
        print("\n✅ WebSocket connection test PASSED")
        sys.exit(0)
    else:
        print("\n❌ WebSocket connection test FAILED")
        sys.exit(1)
