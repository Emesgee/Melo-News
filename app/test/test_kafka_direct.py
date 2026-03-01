import json
import pytest
import sys

# Skip Kafka tests on Windows (only run in Docker)
pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason="Kafka tests only run in Docker environment"
)

from confluent_kafka import Consumer, KafkaError

print("=" * 60)
print("🔍 KAFKA TOPIC DEBUG TEST")
print("=" * 60)

# Create consumer
consumer = Consumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'test-debug-' + str(int(__import__('time').time())),
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': False
})

consumer.subscribe(['eyesonpalestine'])

print("[TEST] Subscribed to topic: eyesonpalestine")
print("[TEST] Waiting for messages (10 second timeout)...\n")

message_count = 0
timeout_counter = 0

try:
    while timeout_counter < 10:  # Try 10 times with 1 second timeout each = 10 seconds total
        msg = consumer.poll(timeout=1.0)
        timeout_counter += 1
        
        if msg is None:
            print(f"[POLL {timeout_counter}/10] No message yet...")
            continue
        
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                print("[INFO] End of partition reached")
            else:
                print(f"[ERROR] {msg.error()}")
            continue
        
        # Message found!
        message_count += 1
        try:
            data = json.loads(msg.value().decode('utf-8'))
            print(f"\n✅ MESSAGE #{message_count} FOUND!")
            print(f"   City: {data.get('matched_city')}")
            print(f"   Text: {data.get('message', '')[:80]}...")
            print(f"   Views: {data.get('total_views')}")
            print(f"   Lat/Lon: ({data.get('lat')}, {data.get('lon')})\n")
        except Exception as e:
            print(f"❌ Error parsing message: {e}")

except KeyboardInterrupt:
    print("\n[INFO] Test interrupted by user")

finally:
    consumer.close()
    print("\n" + "=" * 60)
    if message_count > 0:
        print(f"✅ SUCCESS! Found {message_count} message(s) in Kafka")
        print("   Producer is working correctly")
    else:
        print("❌ NO MESSAGES FOUND")
        print("   Producer hasn't sent any messages yet")
        print("   Run: python kafkaProducer.py")
    print("=" * 60)