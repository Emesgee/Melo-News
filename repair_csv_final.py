import csv
import re
from pathlib import Path

def clean_csv():
    path = Path("data/palestinians_towns.csv")
    backup_path = path.with_suffix(".csv.bak")
    
    # Prefer reading from backup if it exists (source of truth)
    read_path = backup_path if backup_path.exists() else path
    
    if not read_path.exists():
        print(f"File not found: {read_path}")
        return

    print(f"Reading from {read_path}")
    # Read raw text
    text = read_path.read_text(encoding="utf-8", errors="replace")
    
    # Normalize newlines to spaces to treat as a stream
    text = text.replace("\r\n", " ").replace("\n", " ")
    
    # Regex to find "Lat,Lon," pattern match start
    # allow matches like "33.0300 35.1500," (space instead of comma between lat/long)
    pattern = re.compile(r'(-?\d+\.\d+)[,\s]+(-?\d+\.\d+)[,\s]+')
    
    def in_bounds(lat, lon):
        return 29.0 <= lat <= 34.8 and 33.0 <= lon <= 36.8

    # Find ALL matches first
    matches = list(pattern.finditer(text))
    valid_matches = []
    
    for i, m in enumerate(matches):
        try:
            lat = float(m.group(1))
            lon = float(m.group(2))
            if in_bounds(lat, lon):
                valid_matches.append(m)
        except ValueError:
            continue
    
    print(f"Valid geographic matches: {len(valid_matches)}")

    if not valid_matches:
        print("No valid records found.")
        return

    records = []
    
    # Process slices
    for i in range(len(valid_matches)):
        # Extract Lat/Lon from regex groups directly
        lat = valid_matches[i].group(1)
        lon = valid_matches[i].group(2)
        
        # The data content starts AFTER the Lat/Lon match
        start_idx = valid_matches[i].end()
        
        # End index is the start of the next match
        if i < len(valid_matches) - 1:
            end_idx = valid_matches[i+1].start()
        else:
            end_idx = len(text)
            
        chunk = text[start_idx:end_idx].strip()
        
        # Remove trailing comma if exists
        if chunk.endswith(','):
            chunk = chunk[:-1]
            
        # Parse this chunk as a CSV line (Expect: Eng, Ara, Gov, Dist, Type, Stat, Notes)
        try:
            parsed_rows = list(csv.reader([chunk]))
            if not parsed_rows:
                continue
            fields = parsed_rows[0]
            # If the regex consumed the comma, fields[0] is Eng Name.
            # If there was an empty field due to double comma, filter empty?
            # Usually fields are dense.
            fields = [f for f in fields if f] # Remove empty tokens caused by parse artifacts? 
            # No, don't remove empty, but careful.
            # Usually Eng Name is first.
        except Exception as e:
            print(f"Error parsing chunk {i}: {e}")
            continue

        # We expect at least 6 fields for Eng, Ara, Gov, Dist, Type, Stat
        if len(fields) < 6:
            continue
            
        eng_name = fields[0]
        ara_name = fields[1]
        gov = fields[2]
        dist = fields[3]
        type_ = fields[4]
        status = fields[5]
        
        notes = ""
        if len(fields) > 6:
            notes = " ".join(fields[6:]) # Join remaining fields as notes
        
        town_name = f"{eng_name} - {ara_name}"
        if len(records) < 10:
            print(f"Added: {town_name}")
        
        records.append({
            "town_name": town_name,
            "latitude": lat,
            "longitude": lon,
            "english_name": eng_name,
            "arabic_name": ara_name,
            "governorate": gov,
            "district": dist,
            "type": type_,
            "status": status,
            "notes": notes
        })

    # CLEANUP STEP
    for i in range(len(records) - 1):
        curr = records[i]
        next_rec = records[i+1]
        junk_name = next_rec["town_name"]
        
        # If the notes end with the next town's name, strip it
        if curr["notes"].endswith(junk_name):
            curr["notes"] = curr["notes"][:-len(junk_name)].strip()
            
        curr["notes"] = curr["notes"].strip().strip('"')

    header = [
        "town_name", "latitude", "longitude", "english_name", "arabic_name",
        "governorate", "district", "type", "status", "notes"
    ]

    backup_path = path.with_suffix(".csv.bak")
    if not backup_path.exists():
        path.rename(backup_path) # Backup original
        
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(records)
        
    print(f"Successfully repaired CSV. {len(records)} records saved to {path}")
    print(f"Original file backed up to {backup_path}")

if __name__ == "__main__":
    clean_csv()
