import requests # type: ignore
from bs4 import BeautifulSoup # type: ignore
import re
import json
from collections import Counter
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

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

        if num_of_pages:
            for i in range(int(num_of_pages[-1].text)):

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
                    dictMovie.update({"Name": img['alt']})
                    
                    rating = film.find('span', class_='rating')
                    if rating:
                        listOfClass = rating['class']
                        rateNum = str(listOfClass[-1:])
                        if len(str(rateNum)) == 12:
                            dictMovie.update({"Rating": int(rateNum[-4:-2])})
                        elif len(str(rateNum)) == 11:
                            dictMovie.update({"Rating": int(rateNum[-3:-2])})
                        ratingList.append(dictMovie.get('Rating'))
                    else:  
                        print("Not rated")

                    filmLinkDiv = film.find('div', class_='poster')
                    url = 'https://letterboxd.com' + filmLinkDiv.get('data-target-link')
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:108.0) Gecko/20100101     Firefox/108.0"}
                    response = requests.get(url, headers=headers)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    metaData = soup.find('meta', property='og:title')

                    releaseYear = metaData['content']
                    dictMovie.update({"Year": releaseYear[-5:-1]})
                    yearList.append(dictMovie.get('Year'))

                    directorPara = soup.find('p', class_='credits')
                    if directorPara:
                        directorNamed = directorPara.text[13:-2]
                        if ',' in directorNamed:
                            indexOf = directorNamed.find(',')
                            dictMovie.update({"Director": directorNamed[0:indexOf]})
                        else:
                            dictMovie.update({"Director": directorNamed})
                        directorList.append(dictMovie.get('Director'))
                    else:
                        print("No director")
                        
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
                                    genreList.append(dictMovie.get('Genre'))
                                    totalCount = totalCount + 1
                                    break
                    
                    toAppend = dictMovie.copy()
                    filmList.append(toAppend)
                    
                x = x+1

        else:
            dictMovie = {
                "Name": "FilmName",
                "Year": 0,
                "Rating": 0,
                "Director": "DirectorName",
                "Genre": "Genre"
                }

            url = f'https://letterboxd.com/{username}/films/by/entry-rating/'
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            films = soup.find_all('li', class_='poster-container')

            for film in films:
                img = film.find('img')
                dictMovie.update({"Name": img['alt']})
                
                rating = film.find('span', class_='rating')
                if rating:
                    listOfClass = rating['class']
                    rateNum = str(listOfClass[-1:])
                    if len(str(rateNum)) == 12:
                        dictMovie.update({"Rating": int(rateNum[-4:-2])})
                    elif len(str(rateNum)) == 11:
                        dictMovie.update({"Rating": int(rateNum[-3:-2])})
                    ratingList.append(dictMovie.get('Rating'))
                else:  
                    print("Not rated")

                filmLinkDiv = film.find('div', class_='poster')
                url = 'https://letterboxd.com' + filmLinkDiv.get('data-target-link')
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:108.0) Gecko/20100101     Firefox/108.0"}
                response = requests.get(url, headers=headers)
                soup = BeautifulSoup(response.text, 'html.parser')
                metaData = soup.find('meta', property='og:title')

                releaseYear = metaData['content']
                dictMovie.update({"Year": releaseYear[-5:-1]})
                yearList.append(dictMovie.get('Year'))

                directorPara = soup.find('p', class_='credits')
                if directorPara:
                    directorNamed = directorPara.text[13:-2]
                    if ',' in directorNamed:
                        indexOf = directorNamed.find(',')
                        dictMovie.update({"Director": directorNamed[0:indexOf]})
                    else:
                        dictMovie.update({"Director": directorNamed})
                    directorList.append(dictMovie.get('Director'))
                else:
                    print("No director")
                    
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
                                genreList.append(dictMovie.get('Genre'))
                                totalCount = totalCount + 1
                                break

                toAppend = dictMovie.copy()
                filmList.append(toAppend)


        def top_5_most_common(input_list):
                    if not input_list:
                        return []
                    
                    item_counts = Counter(input_list)
                    most_common_items = item_counts.most_common(5)
                    return most_common_items


        def top_10_most_common(input_list):
            if not input_list:
                return []
            
            item_counts = Counter(input_list)
            most_common_items = item_counts.most_common(10)
            return most_common_items
        
        def most_common_genre(input_list):
            if not input_list:
                return []
            

            item_counts = Counter(input_list)
            most_common_items = item_counts.most_common()
            return most_common_items
        
        def most_common_year(input_list):
            if not input_list:
                return []
            

            item_counts = Counter(input_list)
            most_common_items = item_counts.most_common()
            return most_common_items
            
        def top_decade(input_list):
                    if not input_list:
                        return []
                    
                    item_counts = Counter(input_list)
                    most_common_items = item_counts.most_common()
                    return most_common_items

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

        totalRatingOne = 0
        totalRatingTwo = 0
        totalRatingThre = 0
        totalRatingFour = 0
        totalRatingFive = 0

        for film in filmList:
            if film.get("Director") == topDirector:
                totalRatingOne += int(film.get('Rating'))
            elif film.get("Director") == stopDirector:
                totalRatingTwo += int(film.get('Rating'))
            elif film.get("Director") == ttopDirector:
                totalRatingThre += int(film.get('Rating'))
            elif film.get("Director") == ftopDirector:
                totalRatingFour += int(film.get('Rating'))
            elif film.get('Director') == fitopDirector:
                totalRatingFive += int(film.get('Rating'))


        for film in yearList:
            if  2020 <= int(film) < 2030:
                decadeList.append("2020s")
            if 2010 <= int(film) < 2020:
                decadeList.append("2010s")
            if 2000 <= int(film) < 2010:
                decadeList.append("2000s")
            if 1990 <= int(film) < 2000:
                decadeList.append("1990s")
            if 1980 <= int(film) < 1990:
                decadeList.append("1980s")
            if 1970 <= int(film) < 1980:
                decadeList.append("1970s")
            if 1960 <= int(film) < 1970:
                decadeList.append("1960s")
            if 1950 <= int(film) < 1960:
                decadeList.append("1950s")
            if 1940 <= int(film) < 1950:
                decadeList.append("1940s")
            if 1930 <= int(film) < 1940:
                decadeList.append("1930s")
            if 1920 <= int(film) < 1930:
                decadeList.append("1920s")
            if 1910 <= int(film) < 1920:
                decadeList.append("1910s")
            if 1900 <= int(film) < 1910:
                decadeList.append("1900s")
            if 1890 <= int(film) < 1900:
                decadeList.append("1890s")
            if 1880 <= int(film) < 1890:
                decadeList.append("1880ss")
            if 1870 <= int(film) < 1880:
                decadeList.append("1870s")

        topDecade = top_decade(decadeList)

        avgRatingOne = round(float(totalRatingOne/ topDirectorCount), 2)
        avgRatingTwo = round(float(totalRatingTwo/ stopDirectorCount), 2)
        avgRatingThre = round(float(totalRatingThre/ ttopDirectorCount), 2)
        avgRatingFour = round(float(totalRatingFour/ ftopDirectorCount), 2)
        avgRatingFive = round(float(totalRatingFive/ fitopDirectorCount), 2)

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
        remainderPer = len(filmList) - genreOneCount - genreTwoCount - genreThreeCount - genreFourCount - genreFiveCount
        
        
        

        return render_template('answer.html', user=username, directorOne = topDirector, directorOneCount =topDirectorCount, directorTwo = stopDirector, directorTwoCount = stopDirectorCount, directorThree = ttopDirector, directorThreeCount = ttopDirectorCount, directorFour = ftopDirector, directorFourCount = ftopDirectorCount, directorFive = fitopDirector, directorFiveCount = fitopDirectorCount,
                               avgOne = avgRatingOne, avgTwo = avgRatingTwo, avgThre = avgRatingThre, avgFour = avgRatingFour, avgFive = avgRatingFive,
                               decOne = decadeOne, decOneCount = decadeOneCount, decTwo = decadeTwo, decTwoCount = decadeTwoCount, decThree = decadeThree, decThreeCount = decadeThreeCount,
                               rateOne = ratingOne, rateOneCount = ratingOneCount, rateTwo = ratingTwo, rateTwoCount = ratingTwoCount, rateThree = ratingThree, rateThreeCount = ratingThreeCount, rateFour = ratingFour, rateFourCount = ratingFourCount, rateFive = ratingFive, rateFiveCount = ratingFiveCount,
                               genreOne = genreOne, genreOneCount = genreOneCount, genreTwo = genreTwo, genreTwoCount = genreTwoCount, genreThree = genreThree, genreThreeCount = genreThreeCount,
                               genreFour = genreFour, genreFourCount = genreFourCount, genreFive = genreFive, genreFiveCount = genreFiveCount,
                               remainderPer = remainderPer,
                               )
    return render_template('index.html')





if __name__ == '__main__':
    app.run(debug=True)
