import requests
from bs4 import BeautifulSoup
import re
import json

def scrape():
    print('Enter your Letterboxd username:')
    username = input()
    url = f'https://letterboxd.com/{username}/films/by/entry-rating/'

    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    num_of_pages = soup.find_all('li', class_="paginate-page")
    x = 1
    for i in num_of_pages:
        dictMovie = {
        "Name": "FilmName",
        "Year": 0,
        "Rating": 0,
        "Director": "DirectorName",
        "Genre": "Genre",
        "Theme1": "Theme1",
        "Theme2": "Theme2"
        }
        url = f'https://letterboxd.com/{username}/films/by/entry-rating/page/{x}/'
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        films = soup.find_all('li', class_='poster-container')
        for film in films:
            img = film.find('img')
            if img and img.has_attr('alt'):
                print(img['alt'])
            dictMovie.update({"Name": img['alt']})
            rating = film.find('span', class_='rating')
            listOfClass = rating['class']
            rateNum = str(listOfClass[-1:])
            if len(str(rateNum)) == 12:
                print('Rated ' + str(rateNum[-4:-2]) + '/10')
                dictMovie.update({"Rating": int(rateNum[-4:-2])})
            elif len(str(rateNum)) == 11:
                print('Rated ' + str(rateNum[-3:-2]) + '/10')
                dictMovie.update({"Rating": int(rateNum[-3:-2])})
            filmLinkDiv = film.find('div', class_='poster')
            url = 'https://letterboxd.com' + filmLinkDiv.get('data-target-link')
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:108.0) Gecko/20100101     Firefox/108.0"}
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            metaData = soup.find('meta', property='og:title')
            releaseYear = metaData['content']
            dictMovie.update({"Year": releaseYear[-5:-1]})
            directorPara = soup.find('p', class_='credits')
            directorNamed = directorPara.text[13:-2]
            dictMovie.update({"Director": directorNamed})
            scripts = soup.find_all('script')
            for script in scripts:
                if 'window.ramp.custom_tags' in script.text:
                    match = re.search(r'window\.ramp\.custom_tags\s*=\s*(\[[^\]]*\])', script.text)
                    if match:
                        tag_list_str = match.group(1)
                        try:
                            tag_list = json.loads(tag_list_str)
                            if 'drama' in tag_list:
                                print('Drama genre found!')
                                print('Tags:', tag_list)
                        except json.JSONDecodeError:
                            print("Could not decode the tag list.")
        x = x+1

if __name__ == '__main__':
    scrape()