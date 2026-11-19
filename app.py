import asyncio
from bs4 import BeautifulSoup
from collections import Counter
from flask import Flask, render_template, request
from datetime import datetime
from curl_cffi.requests import Session, AsyncSession
import time

app = Flask(__name__)

# 🔥 FIXED PROXY FORMATTING (Removed trailing slashes)
PROXY_URL = "http://zlturfes:h96g8uefdgmz@31.59.20.176:6754"

proxy_dict = {
    "http": PROXY_URL,
    "https": PROXY_URL
}

# -----------------------------------------------------------
# ASYNC NETWORK FETCHER
# -----------------------------------------------------------
async def fetch_all_films(urls):
    sem = asyncio.Semaphore(8)
    # Added verify=False to prevent proxy SSL certificate errors
    async with AsyncSession(impersonate="chrome120", proxies=proxy_dict, verify=False) as session:
        async def fetch(url):
            async with sem:
                for attempt in range(3):
                    try:
                        resp = await session.get(url, timeout=20)
                        if resp.status_code == 429:
                            await asyncio.sleep(2)
                            continue
                        return resp.text
                    except Exception as e:
                        print(f"Async Fetch Error on {url}: {e}")
                        await asyncio.sleep(1) 
                return None
                
        tasks = [fetch(url) for url in urls]
        return await asyncio.gather(*tasks)

# -----------------------------------------------------------
# SAFE ANALYTICS HELPER
# -----------------------------------------------------------
def get_safe_stat(stat_list, index, default_name="N/A", default_count=0):
    if len(stat_list) > index:
        return stat_list[index][0], stat_list[index][1]
    return default_name, default_count

# -----------------------------------------------------------
# FLASK ROUTE
# -----------------------------------------------------------
@app.route('/', methods=['GET', 'POST'])
def scrape():
    if request.method == 'POST':
        username = request.form.get('userInput')
        url = f'https://letterboxd.com/{username}/films/by/entry-rating/'
        print(f"Scraping started for {username} at {datetime.now()}")
        
        # 1. SYNCHRONOUSLY GET PAGINATION LISTS
        # Added verify=False here as well
        session = Session(impersonate="safari15_5", proxies=proxy_dict, verify=False)      
          
        response = None
        # Retry loop just for the main page in case the first proxy IP is dead
        for attempt in range(3):
            try:
                print(f"Connecting to main page (Attempt {attempt + 1})...")
                response = session.get(url, timeout=30)
                print(f"Main Page Status Code: {response.status_code}")
                break # Success! Break out of the retry loop.
            except Exception as e:
                print(f"PROXY OR CONNECTION ERROR: {e}")
                time.sleep(2)
        
        # If all 3 attempts failed, show the error
        if not response:
            return render_template('index.html', error="Failed to connect to proxy. Please check your terminal for the exact error.")
        
        # Check for 404 or active CF blocks
        if response.status_code == 404:
            return render_template('index.html', error="User not found. Check the username spelling!")
        if response.status_code == 403 or "Just a moment" in response.text:
            return render_template('index.html', error="Letterboxd blocked the request. Try rotating your proxy.")

        soup = BeautifulSoup(response.text, 'html.parser')
        num_of_pages = soup.find_all('li', class_="paginate-page")
        all_film_elements = []

        if num_of_pages:
            total_pages = int(num_of_pages[-1].text)
            for x in range(1, total_pages + 1):
                print(f"Fetching page {x} of {total_pages}")
                page_url = f'https://letterboxd.com/{username}/films/by/entry-rating/page/{x}/'
                
                try:
                    page_response = session.get(page_url, timeout=20)
                    page_soup = BeautifulSoup(page_response.text, 'html.parser')
                    
                    page_films = page_soup.find_all('li', class_='poster-container')
                    if not page_films:
                        page_films = page_soup.find_all('li', class_='griditem')
                        
                    all_film_elements.extend(page_films)
                except Exception as e:
                    print(f"Failed to fetch page {x}: {e}")
                
                time.sleep(0.5) 
        else:
            page_films = soup.find_all('li', class_='poster-container')
            if not page_films:
                page_films = soup.find_all('li', class_='griditem')
            all_film_elements = page_films

        print(f"Total films found to process: {len(all_film_elements)}")

        # 2. EXTRACT URLS AND BASIC DATA FOR ASYNC FETCHING
        film_data_list = []
        urls_to_fetch = []

        for film in all_film_elements:
            dictMovie = {}
            nameFinder = film.find('div')
            dictMovie["Name"] = nameFinder['data-item-name'] if nameFinder else "Unknown"
            
            rating = film.find('span', class_='rating')
            if rating:
                listOfClass = rating['class']
                rateNum = str(listOfClass[-1:])
                if len(rateNum) == 12:
                    dictMovie["Rating"] = int(rateNum[-4:-2])
                elif len(rateNum) == 11:
                    dictMovie["Rating"] = int(rateNum[-3:-2])
                else:
                    dictMovie["Rating"] = 0
            else:
                dictMovie["Rating"] = 0
                
            filmLinkDiv = film.find('div', class_='react-component')
            if filmLinkDiv:
                film_url = 'https://letterboxd.com' + str(filmLinkDiv.get('data-item-link'))
                urls_to_fetch.append(film_url)
                film_data_list.append(dictMovie)

        # 3. ASYNCHRONOUSLY FETCH ALL FILM PAGES
        print(f"Fetching {len(urls_to_fetch)} film pages concurrently...")
        html_pages = asyncio.run(fetch_all_films(urls_to_fetch))

        # 4. SYNCHRONOUSLY PARSE IN MEMORY
        filmList, directorList, ratingList, genreList, yearList, decadeList = [], [], [], [], [], []

        for dictMovie, html in zip(film_data_list, html_pages):
            if not html:
                continue 
                
            film_soup = BeautifulSoup(html, 'html.parser')
            
            # YEAR
            metaData = film_soup.find('meta', property='og:title')
            dictMovie["Year"] = metaData['content'][-5:-1] if metaData and metaData.get('content') else "0000"
            
            # DIRECTOR 
            directorPara = film_soup.find('p', class_='credits')
            if directorPara:
                director_link = directorPara.find('a')
                if director_link:
                    dictMovie["Director"] = director_link.text.strip()
                else:
                    directorNamed = directorPara.text.replace('Directed by', '').strip()
                    dictMovie["Director"] = directorNamed[:directorNamed.find(',')] if ',' in directorNamed else directorNamed
            else:
                dictMovie["Director"] = "Unknown"
                
            # GENRE
            dictMovie["Genre"] = "Unknown"
            scripts = film_soup.find_all('script')
            for script in scripts:
                if script.text and 'window.ramp.custom_tags' in script.text:
                    for line in script.string.splitlines():
                        if "'," in line:
                            dictMovie["Genre"] = line.strip()[1:-2]
                            break
                            
            filmList.append(dictMovie)
            ratingList.append(dictMovie["Rating"])
            directorList.append(dictMovie["Director"])
            yearList.append(dictMovie["Year"])
            if dictMovie["Genre"] != "Unknown":
                genreList.append(dictMovie["Genre"])

        print(f"Successfully processed {len(filmList)} films.")

        # 5. ANALYTICS CALCULATIONS
        def most_common(input_list, top_n):
            if not input_list: return []
            return Counter(input_list).most_common(top_n)

        top_directors = most_common(directorList, 5)
        top_ratings = most_common(ratingList, 5)
        top_genres = most_common(genreList, 5)

        topDir1, topDir1Count = get_safe_stat(top_directors, 0)
        topDir2, topDir2Count = get_safe_stat(top_directors, 1)
        topDir3, topDir3Count = get_safe_stat(top_directors, 2)
        topDir4, topDir4Count = get_safe_stat(top_directors, 3)
        topDir5, topDir5Count = get_safe_stat(top_directors, 4)

        dir_totals = {topDir1: [0,0], topDir2: [0,0], topDir3: [0,0], topDir4: [0,0], topDir5: [0,0]}
        
        for film in filmList:
            rating = int(film["Rating"])
            director = film["Director"]
            if rating > 0 and director in dir_totals:
                dir_totals[director][0] += rating
                dir_totals[director][1] += 1

        def calc_avg(director):
            return round(dir_totals[director][0] / dir_totals[director][1], 2) if dir_totals[director][1] > 0 else 0

        avgRatingOne = calc_avg(topDir1)
        avgRatingTwo = calc_avg(topDir2)
        avgRatingThre = calc_avg(topDir3)
        avgRatingFour = calc_avg(topDir4)
        avgRatingFive = calc_avg(topDir5)

        for year in yearList:
            try:
                y = int(year)
                decade = f"{(y // 10) * 10}s"
                if 1870 <= y <= 2030:
                    decadeList.append(decade)
            except ValueError:
                pass

        top_decades = most_common(decadeList, 3)
        decOne, decOneCount = get_safe_stat(top_decades, 0)
        decTwo, decTwoCount = get_safe_stat(top_decades, 1)
        decThree, decThreeCount = get_safe_stat(top_decades, 2)

        rateOne, rateOneCount = get_safe_stat(top_ratings, 0)
        rateTwo, rateTwoCount = get_safe_stat(top_ratings, 1)
        rateThree, rateThreeCount = get_safe_stat(top_ratings, 2)
        rateFour, rateFourCount = get_safe_stat(top_ratings, 3)
        rateFive, rateFiveCount = get_safe_stat(top_ratings, 4)

        genreOne, genreOneCount = get_safe_stat(top_genres, 0)
        genreTwo, genreTwoCount = get_safe_stat(top_genres, 1)
        genreThree, genreThreeCount = get_safe_stat(top_genres, 2)
        genreFour, genreFourCount = get_safe_stat(top_genres, 3)
        genreFive, genreFiveCount = get_safe_stat(top_genres, 4)
        
        genreOne = genreOne.capitalize() if isinstance(genreOne, str) else genreOne
        genreTwo = genreTwo.capitalize() if isinstance(genreTwo, str) else genreTwo
        genreThree = genreThree.capitalize() if isinstance(genreThree, str) else genreThree
        genreFour = genreFour.capitalize() if isinstance(genreFour, str) else genreFour
        genreFive = genreFive.capitalize() if isinstance(genreFive, str) else genreFive

        remainderPer = len(filmList) - (genreOneCount + genreTwoCount + genreThreeCount + genreFourCount + genreFiveCount)
        
        return render_template(
            'answer.html',
            user=username,
            directorOne=topDir1, directorOneCount=topDir1Count,
            directorTwo=topDir2, directorTwoCount=topDir2Count,
            directorThree=topDir3, directorThreeCount=topDir3Count,
            directorFour=topDir4, directorFourCount=topDir4Count,
            directorFive=topDir5, directorFiveCount=topDir5Count,
            avgOne=avgRatingOne, avgTwo=avgRatingTwo, avgThre=avgRatingThre,
            avgFour=avgRatingFour, avgFive=avgRatingFive,
            decOne=decOne, decOneCount=decOneCount,
            decTwo=decTwo, decTwoCount=decTwoCount,
            decThree=decThree, decThreeCount=decThreeCount,
            rateOne=rateOne, rateOneCount=rateOneCount,
            rateTwo=rateTwo, rateTwoCount=rateTwoCount,
            rateThree=rateThree, rateThreeCount=rateThreeCount,
            rateFour=rateFour, rateFourCount=rateFourCount,
            rateFive=rateFive, rateFiveCount=rateFiveCount,
            genreOne=genreOne, genreOneCount=genreOneCount,
            genreTwo=genreTwo, genreTwoCount=genreTwoCount,
            genreThree=genreThree, genreThreeCount=genreThreeCount,
            genreFour=genreFour, genreFourCount=genreFourCount,
            genreFive=genreFive, genreFiveCount=genreFiveCount,
            remainderPer=remainderPer,
        )

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=False)