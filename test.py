import json

def print_json_keys(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            data = json.load(file)

            if isinstance(data, dict):
                print("Top-level keys in JSON:", list(data.keys()))
            elif isinstance(data, list):
                print("JSON root is a list, not a dictionary.")
            else:
                print("Unexpected JSON format.")

    except FileNotFoundError:
        print("Error: The file 'test.json' was not found.")
    except json.JSONDecodeError:
        print("Error: Failed to decode 'test.json'. Ensure it is valid JSON.")
    except Exception as e:
        print(f"Unexpected error: {e}")

print_json_keys('../test.json')