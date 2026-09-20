from bs4 import BeautifulSoup
import re
import json
from collections import Counter
from flask import Flask, render_template, request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from curl_cffi.requests import Session  # 🔥 Replaces cloudscraper and requests
import time

app = Flask(__name__)

# -----------------------------------------------------------
# Multithreaded Film Scraper Function 
# -----------------------------------------------------------
def process_film(film, session):
    dictMovie = {}
    try:
        # --- BASIC FILM DATA ---
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

        # --- FILM PAGE REQUEST ---
        filmLinkDiv = film.find('div', class_='react-component')
        if not filmLinkDiv:
            return None
            
        url = 'https://letterboxd.com' + str(filmLinkDiv.get('data-item-link'))
        
        # 🔥 RETRY LOGIC ADDED HERE
        max_retries = 3
        soup = None
        
        for attempt in range(max_retries):
            try:
                # Increased timeout to 30 seconds
                resp = session.get(url, timeout=30)
                
                # If we get a 429 (Too Many Requests), wait and try again
                if resp.status_code == 429:
                    time.sleep(2)
                    continue
                    
                soup = BeautifulSoup(resp.text, 'html.parser')
                break # Successfully got the page, exit the retry loop
                
            except Exception as req_error:
                if attempt == max_retries - 1:
                    print(f"Failed {dictMovie['Name']} after {max_retries} attempts: {req_error}")
                    return None
                time.sleep(1) # Wait 1 second before retrying

        if not soup:
            return None # Failsafe if loop finishes without soup

        # YEAR
        metaData = soup.find('meta', property='og:title')
        if metaData and metaData.get('content'):
            releaseYear = metaData['content']
            dictMovie["Year"] = releaseYear[-5:-1]
        else:
            dictMovie["Year"] = "0000"

        # DIRECTOR
        directorPara = soup.find('p', class_='credits')
        if directorPara:
            directorNamed = directorPara.text[13:-2]
            if ',' in directorNamed:
                indexOf = directorNamed.find(',')
                dictMovie["Director"] = directorNamed[:indexOf]
            else:
                dictMovie["Director"] = directorNamed
        else:
            dictMovie["Director"] = "Unknown"

        # GENRE
        dictMovie["Genre"] = "Unknown"
        scripts = soup.find_all('script')
        for script in scripts:
            if script.text and 'window.ramp.custom_tags' in script.text:
                script_content = script.string
                lines = script_content.splitlines()
                for line in lines:
                    if "'," in line:
                        dictMovie["Genre"] = line.strip()[1:-2]
                        break
                        
    except Exception as e:
        print(f"Error processing {dictMovie.get('Name', 'a film')}: {e}")
        return None

    return dictMovie

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
        
        # 🔥 Create ONE curl_cffi session impersonating Chrome 110
        session = Session(
            impersonate="chrome120", 
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://letterboxd.com/",
                "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Upgrade-Insecure-Requests": "1"
            }
        )
        
        response = session.get(url)
        print(f"Main Page Status Code: {response.status_code}") # 200 = Success, 403 = Blocked
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Debug: Check if Cloudflare hit us with a CAPTCHA page
        if soup.title and "Just a moment" in soup.title.string:
            print("❌ Cloudflare blocked the request!")
            
        num_of_pages = soup.find_all('li', class_="paginate-page")
        all_film_elements = []

        if num_of_pages:
            total_pages = int(num_of_pages[-1].text)
            for x in range(1, total_pages + 1):
                print(f"Fetching page {x} of {total_pages}")
                page_url = f'https://letterboxd.com/{username}/films/by/entry-rating/page/{x}/'
                
                response = session.get(page_url)
                soup = BeautifulSoup(response.text, 'html.parser')
                page_films = soup.find_all('li', class_='poster-container') # Check for both classes
                if not page_films:
                    page_films = soup.find_all('li', class_='griditem')
                    
                all_film_elements.extend(page_films)
                time.sleep(0.5) 
        else:
            # Single page fallback
            page_films = soup.find_all('li', class_='poster-container')
            if not page_films:
                page_films = soup.find_all('li', class_='griditem')
            all_film_elements = page_films

        print(f"Total films found to process: {len(all_film_elements)}")

        filmList, directorList, ratingList, genreList, yearList, decadeList = [], [], [], [], [], []

        # Process with threads (Max 8 to avoid rate limits)
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(process_film, film, session) for film in all_film_elements]

            for future in as_completed(futures):
                data = future.result()
                if data is not None: 
                    filmList.append(data)
                    ratingList.append(data["Rating"])
                    directorList.append(data["Director"])
                    yearList.append(data["Year"])
                    if data["Genre"] != "Unknown":
                        genreList.append(data["Genre"])

        print(f"Successfully processed {len(filmList)} films.")

        # Analytics calculations
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
    app.run(debug=True)