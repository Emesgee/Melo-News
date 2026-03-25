import json
import time
import pytest

# Integration test: requires a running Kafka broker at localhost:9092
pytestmark = pytest.mark.integration


@pytest.mark.integration
def test_kafka_topic_has_messages():
    """Connect to the eyesonpalestine Kafka topic and verify messages exist.

    Requires a running Kafka broker at localhost:9092.
    Excluded from the default test run (marked 'integration').
    """
    confluent_kafka = pytest.importorskip(
        "confluent_kafka", reason="confluent_kafka not installed"
    )
    Consumer = confluent_kafka.Consumer
    KafkaError = confluent_kafka.KafkaError

    print("=" * 60)
    print("KAFKA TOPIC DEBUG TEST")
    print("=" * 60)

    consumer = Consumer({
        'bootstrap.servers': 'localhost:9092',
        'group.id': 'test-debug-' + str(int(time.time())),
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False,
    })

    consumer.subscribe(['eyesonpalestine'])
    print("[TEST] Subscribed to topic: eyesonpalestine")
    print("[TEST] Waiting for messages (10 second timeout)...\n")

    message_count = 0
    timeout_counter = 0

    try:
        while timeout_counter < 10:
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

            message_count += 1
            try:
                data = json.loads(msg.value().decode('utf-8'))
                print(f"\nMESSAGE #{message_count} FOUND!")
                print(f"   City: {data.get('matched_city')}")
                print(f"   Text: {data.get('message', '')[:80]}...")
                print(f"   Views: {data.get('total_views')}")
                print(f"   Lat/Lon: ({data.get('lat')}, {data.get('lon')})\n")
            except Exception as e:
                print(f"Error parsing message: {e}")

    finally:
        consumer.close()
        print("\n" + "=" * 60)
        if message_count > 0:
            print(f"SUCCESS! Found {message_count} message(s) in Kafka")
            print("   Producer is working correctly")
        else:
            print("NO MESSAGES FOUND")
            print("   Producer hasn't sent any messages yet")
            print("   Run: python kafkaProducer.py")
        print("=" * 60)
