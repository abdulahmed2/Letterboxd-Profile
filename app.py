import asyncio
import aiohttp
import urllib.parse
from bs4 import BeautifulSoup
from collections import Counter
from flask import Flask, render_template, request
from datetime import datetime
from curl_cffi.requests import Session
import time

app = Flask(__name__)

# 🔥 PUT YOUR TMDB API KEY HERE
TMDB_API_KEY = "ea50b58379bc05923fa888be629f23f9"

# -----------------------------------------------------------
# TMDB API FETCHER (With Rate Limit Protection)
# -----------------------------------------------------------
async def fetch_tmdb_data(film_data_list):
    # This semaphore acts as a traffic cop, allowing only 20 concurrent requests
    # at a time so TMDB doesn't block us for spamming their API.
    sem = asyncio.Semaphore(20) 
    
    async with aiohttp.ClientSession() as session:
        async def fetch_movie(movie):
            async with sem:
                title = movie["Name"]
                search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={urllib.parse.quote(title)}"
                
                for attempt in range(3): # Add a retry loop for safety
                    try:
                        async with session.get(search_url) as resp:
                            if resp.status == 401:
                                print(f"🚨 TMDB API Key is invalid or missing!")
                                return movie
                            if resp.status == 429: # Too many requests, wait and retry
                                await asyncio.sleep(1)
                                continue
                            if resp.status != 200: 
                                return movie
                                
                            search_data = await resp.json()
                            if not search_data.get('results'):
                                return movie
                                
                            movie_id = search_data['results'][0]['id']
                            
                            details_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&append_to_response=credits"
                            async with session.get(details_url) as details_resp:
                                if details_resp.status == 429:
                                    await asyncio.sleep(1)
                                    continue
                                if details_resp.status != 200: 
                                    return movie
                                    
                                details = await details_resp.json()
                                
                                if details.get('release_date'):
                                    movie["Year"] = details['release_date'][:4]
                                if details.get('genres'):
                                    movie["Genre"] = details['genres'][0]['name']
                                if details.get('credits') and details['credits'].get('crew'):
                                    for crew_member in details['credits']['crew']:
                                        if crew_member['job'] == 'Director':
                                            movie["Director"] = crew_member['name']
                                            break
                                return movie # Successfully got data, exit retry loop
                    except Exception as e:
                        print(f"Failed to fetch TMDB data for {title}: {e}")
                        await asyncio.sleep(1)
                
                return movie

        tasks = [fetch_movie(movie) for movie in film_data_list]
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
        
        session = Session(impersonate="safari15_5")
        response = session.get(url)
        
        if response.status_code == 404:
            return render_template('index.html', error="User not found. Check the username spelling!")
        if response.status_code == 403 or "Just a moment" in response.text:
            return render_template('index.html', error="Letterboxd is currently blocking cloud servers. Please try again later.")
            
        soup = BeautifulSoup(response.text, 'html.parser')
        num_of_pages = soup.find_all('li', class_="paginate-page")
        all_film_elements = []

        if num_of_pages:
            total_pages = int(num_of_pages[-1].text)
            # The page limit has been completely removed. It will scrape everything.
            
            for x in range(1, total_pages + 1):
                page_url = f'https://letterboxd.com/{username}/films/by/entry-rating/page/{x}/'
                page_response = session.get(page_url)
                page_soup = BeautifulSoup(page_response.text, 'html.parser')
                
                page_films = page_soup.find_all('li', class_='poster-container')
                if not page_films:
                    page_films = page_soup.find_all('li', class_='griditem')
                    
                all_film_elements.extend(page_films)
                time.sleep(0.5) 
        else:
            page_films = soup.find_all('li', class_='poster-container')
            if not page_films:
                page_films = soup.find_all('li', class_='griditem')
            all_film_elements = page_films

        # 2. EXTRACT BASIC DATA
        film_data_list = []
        for film in all_film_elements:
            dictMovie = {"Name": "Unknown", "Rating": 0, "Year": "0000", "Director": "Unknown", "Genre": "Unknown"}
            
            nameFinder = film.find('div')
            if nameFinder and nameFinder.get('data-item-name'):
                dictMovie["Name"] = nameFinder['data-item-name']
            else:
                imgFinder = film.find('img')
                if imgFinder and imgFinder.get('alt'):
                    dictMovie["Name"] = imgFinder['alt']
            
            rating = film.find('span', class_='rating')
            if rating:
                listOfClass = rating['class']
                rateNum = str(listOfClass[-1:])
                if len(rateNum) == 12:
                    dictMovie["Rating"] = int(rateNum[-4:-2])
                elif len(rateNum) == 11:
                    dictMovie["Rating"] = int(rateNum[-3:-2])

            if dictMovie["Name"] != "Unknown":
                film_data_list.append(dictMovie)

        print(f"Total films found to process via TMDB: {len(film_data_list)}")

        # 3. FETCH METADATA FROM TMDB (ASYNC)
        if film_data_list:
            filmList = asyncio.run(fetch_tmdb_data(film_data_list))
        else:
            filmList = []

        # 4. ANALYTICS CALCULATIONS
        directorList, ratingList, genreList, yearList, decadeList = [], [], [], [], []
        
        for film in filmList:
            ratingList.append(film["Rating"])
            if film["Director"] != "Unknown": directorList.append(film["Director"])
            if film["Year"] != "0000": yearList.append(film["Year"])
            if film["Genre"] != "Unknown": genreList.append(film["Genre"])

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