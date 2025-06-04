import requests
from bs4 import BeautifulSoup
import re
import json
from collections import Counter

def scrape():
    print('Enter your Letterboxd username:')
    username = input()

    url = f'https://letterboxd.com/{username}/films/by/entry-rating/'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    num_of_pages = soup.find_all('li', class_="paginate-page")
    x = 1

    directorList = []

    for i in num_of_pages:

        dictMovie = {
        "Name": "FilmName",
        "Year": 0,
        "Rating": 0,
        "Director": "DirectorName",
        "Genre": "Genre"
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
            if ',' in directorNamed:
                indexOf = directorNamed.find(',')
                dictMovie.update({"Director": directorNamed[0:indexOf]})
            else:
                dictMovie.update({"Director": directorNamed})
                
            scripts = soup.find_all('script')
            for script in scripts:
                if 'window.ramp.custom_tags' in script.text:
                    script_content = script.string
                    lines = script_content.splitlines()
                    target_line = None
                    for line in lines:
                        if "'," in line:
                            target_line = line.strip()[1:-2]
                            dictMovie.update({"Genre": target_line})
                            break
            
            directorList.append(dictMovie.get('Director'))

            def top_5_most_common(input_list):
                if not input_list:
                    return []
                
                item_counts = Counter(input_list)
                most_common_items = item_counts.most_common(5)
                return most_common_items

            top_items = top_5_most_common(directorList)
            print(dictMovie)
            
        x = x+1

    topDirector = top_items[0][0]
    topDirectorCount = top_items[0][1]

    stopDirector = top_items[1][0]
    stopDirectorCount = top_items[1][1]

    ttopDirector = top_items[2][0]
    ttopDirectorCount = top_items[2][1]

    ftopDirector = top_items[3][0]
    ftopDirectorCount = top_items[3][1]

    fitopDirector = top_items[4][0]
    fitopDirectorCount = top_items[4][1]

    print("Your top director is: " + topDirector + "; " + str(topDirectorCount) + " movies watched.")

    print("Your second top director is: " + stopDirector + "; " + str(stopDirectorCount) + " movies watched.")

    print("Your third top director is: " + ttopDirector + "; " + str(ttopDirectorCount) + " movies watched.")

    print("Your fourth top director is: " + ftopDirector + "; " + str(ftopDirectorCount) + " movies watched.")

    print("Your fifth top director is: " + fitopDirector + "; " + str(fitopDirectorCount) + " movies watched.")

if __name__ == '__main__':
    scrape()
