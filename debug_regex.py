import re

text = """...Abu Sinan - ابو سنان",33.0300
35.1500,Abu Sinan,أبو سنان..."""

normalized = text.replace("\r\n", " ").replace("\n", " ")
print(f"Normalized: '{normalized}'")

pattern = re.compile(r'(-?\d+\.\d+)[,\s]+(-?\d+\.\d+)[,\s]+')

matches = list(pattern.finditer(normalized))
print(f"Matches: {len(matches)}")
for m in matches:
    print(f"Match: {m.group(0)} -> Lat: {m.group(1)}, Lon: {m.group(2)}")
