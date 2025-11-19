import requests  # type: ignore
from bs4 import BeautifulSoup  # type: ignore
import re
import json
from collections import Counter
from flask import Flask, render_template, request, redirect, url_for
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)


# -----------------------------------------------------------
# 🔥 Multithreaded Film Scraper Function (NEW)
# -----------------------------------------------------------
def process_film(film):
    dictMovie = {}

    # --- BASIC FILM DATA ---
    nameFinder = film.find('div')
    dictMovie["Name"] = nameFinder['data-item-name']

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

    # --- FILM PAGE REQUEST ---
    filmLinkDiv = film.find('div', class_='react-component')
    url = 'https://letterboxd.com' + str(filmLinkDiv.get('data-item-link'))
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:108.0) Gecko/20100101 Firefox/108.0"
    }

    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, 'html.parser')

    # YEAR
    metaData = soup.find('meta', property='og:title')
    releaseYear = metaData['content']
    dictMovie["Year"] = releaseYear[-5:-1]

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
        if 'window.ramp.custom_tags' in script.text:
            script_content = script.string
            lines = script_content.splitlines()
            for line in lines:
                if "'," in line:
                    dictMovie["Genre"] = line.strip()[1:-2]
                    break

    return dictMovie


# -----------------------------------------------------------
# FLASK ROUTE
# -----------------------------------------------------------
@app.route('/', methods=['GET', 'POST'])
def scrape():
    if request.method == 'POST':
        username = request.form.get('userInput')

        url = f'https://letterboxd.com/{username}/films/by/entry-rating/'
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        num_of_pages = soup.find_all('li', class_="paginate-page")

        x = 1
        totalCount = 0
        directorList = []
        ratingList = []
        genreList = []
        yearList = []
        filmList = []
        decadeList = []

        # -----------------------------------------------------------
        # MULTITHREADED PAGE SCRAPING
        # -----------------------------------------------------------
        if num_of_pages:
            for i in range(int(num_of_pages[-1].text)):
                page_url = f'https://letterboxd.com/{username}/films/by/entry-rating/page/{x}/'
                response = requests.get(page_url)
                soup = BeautifulSoup(response.text, 'html.parser')
                films = soup.find_all('li', class_='griditem')

                # ---- THREADPOOL HERE ----
                with ThreadPoolExecutor(max_workers=20) as executor:
                    futures = [executor.submit(process_film, film) for film in films]

                    for future in as_completed(futures):
                        data = future.result()
                        filmList.append(data)
                        ratingList.append(data["Rating"])
                        directorList.append(data["Director"])
                        yearList.append(data["Year"])
                        genreList.append(data["Genre"])

                x += 1

        else:
            # Single page fallback
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            films = soup.find_all('li', class_='griditem')

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(process_film, film) for film in films]

                for future in as_completed(futures):
                    data = future.result()
                    filmList.append(data)
                    ratingList.append(data["Rating"])
                    directorList.append(data["Director"])
                    yearList.append(data["Year"])
                    genreList.append(data["Genre"])

        # -----------------------------------------------------------
        # ORIGINAL ANALYTICS LOGIC (unchanged)
        # -----------------------------------------------------------

        def top_5_most_common(input_list):
            if not input_list:
                return []
            item_counts = Counter(input_list)
            return item_counts.most_common(5)

        def top_10_most_common(input_list):
            if not input_list:
                return []
            item_counts = Counter(input_list)
            return item_counts.most_common(10)

        def most_common_genre(input_list):
            if not input_list:
                return []
            return Counter(input_list).most_common()

        def most_common_year(input_list):
            if not input_list:
                return []
            return Counter(input_list).most_common()

        def top_decade(input_list):
            if not input_list:
                return []
            return Counter(input_list).most_common()

        top_items = top_5_most_common(directorList)
        commonRating = top_10_most_common(ratingList)
        commonGenre = most_common_genre(genreList)

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

        totalRatingOne = totalRatingTwo = totalRatingThre = totalRatingFour = totalRatingFive = 0
        ratedCountOne = ratedCountTwo = ratedCountThree = ratedCountFour = ratedCountFive = 0

        for film in filmList:
            rating = int(film["Rating"])

            if film["Director"] == topDirector:
                if rating > 0:
                    totalRatingOne += rating
                    ratedCountOne += 1
            elif film["Director"] == stopDirector:
                if rating > 0:
                    totalRatingTwo += rating
                    ratedCountTwo += 1
            elif film["Director"] == ttopDirector:
                if rating > 0:
                    totalRatingThre += rating
                    ratedCountThree += 1
            elif film["Director"] == ftopDirector:
                if rating > 0:
                    totalRatingFour += rating
                    ratedCountFour += 1
            elif film["Director"] == fitopDirector:
                if rating > 0:
                    totalRatingFive += rating
                    ratedCountFive += 1

        for film in yearList:
            year = int(film)
            if 2020 <= year < 2030: decadeList.append("2020s")
            if 2010 <= year < 2020: decadeList.append("2010s")
            if 2000 <= year < 2010: decadeList.append("2000s")
            if 1990 <= year < 2000: decadeList.append("1990s")
            if 1980 <= year < 1990: decadeList.append("1980s")
            if 1970 <= year < 1980: decadeList.append("1970s")
            if 1960 <= year < 1970: decadeList.append("1960s")
            if 1950 <= year < 1960: decadeList.append("1950s")
            if 1940 <= year < 1950: decadeList.append("1940s")
            if 1930 <= year < 1940: decadeList.append("1930s")
            if 1920 <= year < 1930: decadeList.append("1920s")
            if 1910 <= year < 1920: decadeList.append("1910s")
            if 1900 <= year < 1910: decadeList.append("1900s")
            if 1890 <= year < 1900: decadeList.append("1890s")
            if 1880 <= year < 1890: decadeList.append("1880s")
            if 1870 <= year < 1880: decadeList.append("1870s")

        topDecade = top_decade(decadeList)

        avgRatingOne = round(totalRatingOne / ratedCountOne, 2) if ratedCountOne else 0
        avgRatingTwo = round(totalRatingTwo / ratedCountTwo, 2) if ratedCountTwo else 0
        avgRatingThre = round(totalRatingThre / ratedCountThree, 2) if ratedCountThree else 0
        avgRatingFour = round(totalRatingFour / ratedCountFour, 2) if ratedCountFour else 0
        avgRatingFive = round(totalRatingFive / ratedCountFive, 2) if ratedCountFive else 0

        decadeOne = topDecade[0][0]
        decadeOneCount = topDecade[0][1]
        decadeTwo = topDecade[1][0]
        decadeTwoCount = topDecade[1][1]
        decadeThree = topDecade[2][0]
        decadeThreeCount = topDecade[2][1]

        ratingOne = commonRating[0][0]
        ratingOneCount = commonRating[0][1]
        ratingTwo = commonRating[1][0]
        ratingTwoCount = commonRating[1][1]
        ratingThree = commonRating[2][0]
        ratingThreeCount = commonRating[2][1]
        ratingFour = commonRating[3][0]
        ratingFourCount = commonRating[3][1]
        ratingFive = commonRating[4][0]
        ratingFiveCount = commonRating[4][1]

        genreOne = str(commonGenre[0][0]).capitalize()
        genreOneCount = commonGenre[0][1]
        genreTwo = str(commonGenre[1][0]).capitalize()
        genreTwoCount = commonGenre[1][1]
        genreThree = str(commonGenre[2][0]).capitalize()
        genreThreeCount = commonGenre[2][1]
        genreFour = str(commonGenre[3][0]).capitalize()
        genreFourCount = commonGenre[3][1]
        genreFive = str(commonGenre[4][0]).capitalize()
        genreFiveCount = commonGenre[4][1]
        remainderPer = len(filmList) - (
            genreOneCount + genreTwoCount + genreThreeCount + genreFourCount + genreFiveCount
        )

        return render_template(
            'answer.html',
            user=username,
            directorOne=topDirector,
            directorOneCount=topDirectorCount,
            directorTwo=stopDirector,
            directorTwoCount=stopDirectorCount,
            directorThree=ttopDirector,
            directorThreeCount=ttopDirectorCount,
            directorFour=ftopDirector,
            directorFourCount=ftopDirectorCount,
            directorFive=fitopDirector,
            directorFiveCount=fitopDirectorCount,
            avgOne=avgRatingOne,
            avgTwo=avgRatingTwo,
            avgThre=avgRatingThre,
            avgFour=avgRatingFour,
            avgFive=avgRatingFive,
            decOne=decadeOne,
            decOneCount=decadeOneCount,
            decTwo=decadeTwo,
            decTwoCount=decadeTwoCount,
            decThree=decadeThree,
            decThreeCount=decadeThreeCount,
            rateOne=ratingOne,
            rateOneCount=ratingOneCount,
            rateTwo=ratingTwo,
            rateTwoCount=ratingTwoCount,
            rateThree=ratingThree,
            rateThreeCount=ratingThreeCount,
            rateFour=ratingFour,
            rateFourCount=ratingFourCount,
            rateFive=ratingFive,
            rateFiveCount=ratingFiveCount,
            genreOne=genreOne,
            genreOneCount=genreOneCount,
            genreTwo=genreTwo,
            genreTwoCount=genreTwoCount,
            genreThree=genreThree,
            genreThreeCount=genreThreeCount,
            genreFour=genreFour,
            genreFourCount=genreFourCount,
            genreFive=genreFive,
            genreFiveCount=genreFiveCount,
            remainderPer=remainderPer,
        )

    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
