from bs4 import BeautifulSoup 
import requests
import pandas as pd

urls = ["https://www.ufc.com/athlete/kamaru-usman",
        "https://www.ufc.com/athlete/dricus-du-plessis",
]

data = []

''' for testing to see if request is successful

url = "https://www.ufc.com/athlete/kamaru-usman"

response = requests.get(url)

print(response.status_code)
print(response.url)
print(response.text[:500])
'''
for i, url in enumerate(urls, start=1):
    soup = BeautifulSoup(requests.get(url).content, "html.parser")
    
    name = soup.find("h1", class_="hero-profile__name").text.strip()
    record = soup.find("p", class_="hero-profile__division-body").text.strip()
    weight_class = soup.find("p", class_="hero-profile__division-title").text.strip()

    bio_rows = soup.select(".c-bio__row--3col")

    bio = {}

    row1 = bio_rows[0]

    for field in row1.select(".c-bio__field"):
        label = field.select_one(".c-bio__label").get_text(strip=True)
        value = field.select_one(".c-bio__text").get_text(strip=True)
        bio[label] = value

    row2 = bio_rows[1]

    for field in row2.select(".c-bio__field"):
        label = field.select_one(".c-bio__label").get_text(strip=True)
        value = field.select_one(".c-bio__text").get_text(strip=True)
        bio[label] = value

    data.append({
        "Name": name, 
        "Record": record,
        "Weight Class": weight_class,
        "Age": bio.get("Age"),
        "Height": bio.get("Height"),
        "Reach": bio.get("Reach"),
        "Leg reach": bio.get("Leg reach"),
    })

for fighter in data:
    print(f"Name: {fighter['Name']}")
    print(f"Record: {fighter['Record']}")
    print(f"Weight Class: {fighter['Weight Class']}")
    print(f"Age: {fighter['Age']}")
    print(f"Height: {fighter['Height']}")
    print(f"Reach: {fighter['Reach']}")
    print(f"Leg reach: {fighter['Leg reach']}")
    print()