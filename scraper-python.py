import requests
from bs4 import BeautifulSoup

def scrape():
    print('Enter your Letterboxd username. Case sensitive:')
    username = input()
    url = f'https://letterboxd.com/{username}/films/by/entry-rating/'

    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    num_of_pages = soup.find_all('li', class_="paginate-page")
    x = 1

    for i in num_of_pages:
        url = f'https://letterboxd.com/{username}/films/by/entry-rating/page/{x}/'
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        films = soup.find_all('li', class_='poster-container')
        for film in films:
            img = film.find('img')
            if img and img.has_attr('alt'):
                print(img['alt'])
            rating = film.find('p')
            print(rating.text)
        x = x+1

if __name__ == '__main__':
    scrape()