import requests
from bs4 import BeautifulSoup
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

urls = [
    "https://www.palestineremembered.com/AcreTownsSnapshot.html",
    "https://www.palestineremembered.com/BaysanTownsSnapshot.html",
    "https://www.palestineremembered.com/BeershebaTownsSnapshot.html",
    "https://www.palestineremembered.com/HaifaTownsSnapshot.html",
    "https://www.palestineremembered.com/JerusalemTownsSnapshot.html",
    "https://www.palestineremembered.com/JerichoTownsSnapshot.html",
    "https://www.palestineremembered.com/NablusTownsSnapshot.html",
    "https://www.palestineremembered.com/TiberiasTownsSnapshot.html",
    "https://www.palestineremembered.com/TulKarmTownsSnapshot.html",
    "https://www.palestineremembered.com/YafaTownsSnapshot.html",
    "https://www.palestineremembered.com/JaffaTownsSnapshot.html",
    "https://www.palestineremembered.com/LyddTownsSnapshot.html",
    "https://www.palestineremembered.com/RamlehTownsSnapshot.html",
    "https://www.palestineremembered.com/BeisanTownsSnapshot.html",
    "https://www.palestineremembered.com/SalfitTownsSnapshot.html",
    "https://www.palestineremembered.com/QalqilyaTownsSnapshot.html",
    "https://www.palestineremembered.com/JeninTownsSnapshot.html",
    "https://www.palestineremembered.com/TulkarmTownsSnapshot.html",
    "https://www.palestineremembered.com/QabatiyaTownsSnapshot.html",
    "https://www.palestineremembered.com/KufrQaddumTownsSnapshot.html",
    "https://www.palestineremembered.com/BethlehemTownsSnapshot.html",
    "https://www.palestineremembered.com/HebronTownsSnapshot.html"
]

# Collect all town/village names across all districts
town_names = []

for url in urls:
    response = requests.get(url, verify=False)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", id="TownListingTable")
    if table:
        for row in table.find_all("tr"):
            for td in row.find_all("td"):
                ul = td.find("ul")
                if ul:
                    for li in ul.find_all("li"):
                        a_tag = li.find("a")
                        if a_tag:
                            town_names.append(a_tag.get_text(strip=True))

# Print all towns
for name in town_names:
    print(len(name))

# save as csv file
import pandas as pd
df = pd.DataFrame(town_names, columns=["town_name"])
df.to_csv("palestinian_towns.csv", index=False)
print("Saved to palestinian_towns.csv")


