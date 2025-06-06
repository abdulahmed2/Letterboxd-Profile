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
    totalCount = 0
    directorList = []
    ratingList = []
    genreList = []
    yearList = []

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
                print(img['alt'])
                dictMovie.update({"Name": img['alt']})
                
                rating = film.find('span', class_='rating')
                if rating:
                    listOfClass = rating['class']
                    rateNum = str(listOfClass[-1:])
                    if len(str(rateNum)) == 12:
                        print('Rated ' + str(rateNum[-4:-2]) + '/10')
                        dictMovie.update({"Rating": int(rateNum[-4:-2])})
                    elif len(str(rateNum)) == 11:
                        print('Rated ' + str(rateNum[-3:-2]) + '/10')
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
            
            
            top_items = top_5_most_common(directorList)
            commonRating = top_10_most_common(ratingList)
            commonGenre = most_common_genre(genreList)

                
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
            print(img['alt'])
            dictMovie.update({"Name": img['alt']})
            
            rating = film.find('span', class_='rating')
            if rating:
                listOfClass = rating['class']
                rateNum = str(listOfClass[-1:])
                if len(str(rateNum)) == 12:
                    print('Rated ' + str(rateNum[-4:-2]) + '/10')
                    dictMovie.update({"Rating": int(rateNum[-4:-2])})
                elif len(str(rateNum)) == 11:
                    print('Rated ' + str(rateNum[-3:-2]) + '/10')
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

    print("Your top director is: " + topDirector + "; " + str(topDirectorCount) + " movies watched.")

    print("Your second top director is: " + stopDirector + "; " + str(stopDirectorCount) + " movies watched.")

    print("Your third top director is: " + ttopDirector + "; " + str(ttopDirectorCount) + " movies watched.")

    print("Your fourth top director is: " + ftopDirector + "; " + str(ftopDirectorCount) + " movies watched.")

    print("Your fifth top director is: " + fitopDirector + "; " + str(fitopDirectorCount) + " movies watched.")

    for i in range(len(commonRating)):
        print("Your " + str(i + 1) + " most common rating is: " + str(commonRating[i][0]) + " with you rating it " + str(commonRating[i][1]) + " times.") 

    for i in range(5):
        rawPercent = float(int(commonGenre[i][1])/totalCount) * 100
        roundedPercent = round(rawPercent, 2)
        print("Most " + str(i+1) +  " common genre is: " + str(commonGenre[i][0]) + " with you watching it " + str(commonGenre[i][1]) + " times, which is " + str(roundedPercent) + " percent of your total.")

                
if __name__ == '__main__':
    scrape()
