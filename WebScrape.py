########################
### Media WebScraper ###
########################

# benchmarking
import time

# multi-threading
import concurrent.futures
from multiprocessing import freeze_support

# file handling
import sys
import os
import csv

# regular expressions
import re

# scraping
import requests
from bs4 import BeautifulSoup


# user agent for browser visit (Source: useragentstring.com)
user_agent = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0'
    }

# Database to scrape from
IMDB = {
    "Name": "IMDb",                                     # name of database
    
    "Search": "https://www.imdb.com/search/title/?",    # root of search url
    "Query": "title=",                                  # root of search query
    "Movie": "title_type=feature,tv_movie,video",       # tag for movie search
    "TV": "title_type=tv_series,tv_miniseries,video",   # tag for tv search
    "Anime": "genres=animation&countries=jp",           # tag for anime search
    
    "TV Root": "https://www.imdb.com/title/",           # root of media page url
    "TV Episodes": "/episodes?season=",                 # root of media episodes query
    }

# Default Search database
DEFAULT_DATABASE = IMDB

# Default Save directory
SAVE_FOLDER_NAME = "ScrapedData"

if getattr(sys, 'frozen', False):
    # program location if running code from frozen exe
    DEFAULT_PATH = os.path.dirname(sys.executable)
    freeze_support()    # also include support for multiprocessing when running frozen exe
else:
    # program location if running code from script file
    DEFAULT_PATH = os.path.dirname(os.path.abspath(__file__))

# Initialise hash tables for media
idList = {}           # stores cache of database ID (value) for each media (key)
posterList = {}       # stores cache of poster urls (value) for each media (key)
infoScraped = {}      # stores True, False, None (value) to indicate status of info scrape for each media (key)
imagesScraped = {}    # stores True, False, None (value) to indicate status of image scrape for each media (key)
episodesScraped = {}  # stores True, False, None (value) to indicate status of episodes scrape for each media (key)

####################################################################################################

def main():

    # setup
    mediaList = generateMediaList()
    if len(mediaList) > 0:
        createSaveFolder()
    else:
        print("Empty media list.")

    # main while loop
    while len(mediaList) > 0:

        # reset lists storing status of scraped data
        infoScraped.clear()
        imagesScraped.clear()
        episodesScraped.clear()

        # set base search url
        setSearchDatabase()

        # test internet connection
        internetConnection = testInternetConnection()
        if internetConnection is False:
            break
        
        # save media information
        print(f"\n\n{'-'*20} Retrieving media information . . . {'-'*20}")
        saveStartTime = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(save_info, mediaList)  # multithread save_info()
        saveEndTime = time.perf_counter()
        
        # download images and save episode information
        if scrapeTV: print(f"\n\n{'-'*20} Retrieving media episodes and images . . . {'-'*12}")
        else: print(f"\n\n{'-'*20} Retrieving media images . . . {'-'*25}")
        downloadStartTime = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            if scrapeTV: executor.map(save_info_episodes, mediaList)    # multithread save_info_episodes()
            executor.map(download_images, mediaList)    # multithread download_images()
        downloadEndTime = time.perf_counter()

        # initialise lists to hold all media with unsuccessful scrapes or missing data
        unscrapedMedia = []
        missingMedia = []
        
        missingInfo = []        # list to hold media with all missing information
        missingImages = []      # list to hold media with partial missing data (poster image)
        missingEpisodes = []    # list to hold media with partial missing data (episode data)

        # check unsuccessful scrapes or missing data for media info
        for media, info in infoScraped.items():
            if info is False and media not in unscrapedMedia:
                unscrapedMedia.append(media)
            elif info is None:
                if media not in missingMedia:   missingMedia.append(media)
                if media not in missingInfo:    missingInfo.append(media)

        # check unsuccessful scrapes or missing data for media images
        for media, images in imagesScraped.items():
            if images is False and media not in unscrapedMedia:
                unscrapedMedia.append(media)
            elif images is None:
                if media not in missingMedia:   missingMedia.append(media)
                if media not in missingInfo:    missingImages.append(media)

        # check unsuccessful scrapes or missing data for media episodes
        if scrapeTV:
            for media, episodes in episodesScraped.items():
                if episodes is False and media not in unscrapedMedia:
                    unscrapedMedia.append(media)
                elif episodes is None:
                    if media not in missingMedia:   missingMedia.append(media)
                    if media not in missingInfo:    missingEpisodes.append(media)

        # summary
        print(f"""\n\n{'-'*76}
Finished scraping in {(downloadEndTime - saveStartTime):.2f} seconds
    Retrieved media information in {(saveEndTime - saveStartTime):.2f} seconds
    Retrieved media images and episode data (if specified) in {(downloadEndTime - downloadStartTime):.2f} seconds
\nScraped {len(mediaList) - len(unscrapedMedia) - len(missingMedia)} out of {len(mediaList)} media:
    {len(unscrapedMedia)} unsuccessful scrapes (error encountered when retrieving url)
    {len(missingMedia)} missing data (search yielded no results)
\nScraped data saved to {SAVE_FOLDER}
{'-'*76}""")

        # output media with unsuccessful or incomplete scrapes
        if len(unscrapedMedia) > 0:
            print(f"\nThere were errors when scraping for:\n{unscrapedMedia}\n")
            print("Scraping again could result in successful scrapes.\n")
        if len(missingMedia) > 0:
            if len(missingInfo) > 0:
                print(f"\nThere were no results when scraping for:\n{missingInfo}\n")
                print("Scraping again using different search tags could result in successful scrapes.\n")
            if len(missingImages) > 0:
                print(f"\nThere were no images found when scraping for:\n{missingImages}\n")
            if len(missingEpisodes) > 0:
                print(f"\nThere were no episodes found when scraping for:\n{missingEpisodes}\n")

        # ask user to retry for unscraped media
        if len(unscrapedMedia) > 0 or len(missingMedia) > 0:
            retryQuestion = "Retry Scrape?"
            retry = askUserBool(retryQuestion)
        else:
            retry = False

        if retry is True:
            # reset media list to only contain failed scrapes for next iteration of loop
            mediaList.clear()
            mediaList.extend(unscrapedMedia)
            mediaList.extend(missingMedia)
        else:
            break

    print("\n\nDone.")
        
####################################################################################################
### Functions to setup variables ###

def generateMediaList():
    '''Generates a media list from an existing folder or from user input'''
    mediaList = []

    # Determine how media list will be generated (from folder or user input)
    existingMediaQuestion = "Create media list from an existing folder?"
    existingMedia = askUserBool(existingMediaQuestion)
    
    # Generate media list from an existing folder
    if existingMedia:
        # input source folder to generate media list
        sourceFolderRequest = "Enter the folder path to generate media list"
        SOURCE_FOLDER = askUserPath(sourceFolderRequest)

        # create media list from subfolder names
        folderMedia = os.listdir(SOURCE_FOLDER)
        for i, media in enumerate(folderMedia):
            folderMedia[i] = os.path.splitext(media)[0]                             # remove any file extensions
            folderMedia[i] = re.sub("[\(\[].*?[\)\]]", "", folderMedia[i]).strip()  # remove any parentheses
        mediaList.extend(folderMedia)

    # Generate media list from user input
    else:
        # input a single media name to add to media list
        newMedia = str(input("\nEnter a Movie or TV show: "))
        while len(newMedia.strip()) > 0:
            newMedia = newMedia.replace(':', ' -')                   # replace invalid ':' common in titles
            newMedia = re.sub(r'[\/:*?"<>|]', ' ', newMedia).strip() # remove any invalid characters
            if newMedia:
                # add to media list if not an empty string after removing invalid characters
                mediaList.append(newMedia)
            newMedia = str(input("Enter another Movie or TV show (enter nothing to stop): "))

    print("Generated media list\n")
    return mediaList

def createSaveFolder():
    '''Creates a save folder to store scraped data'''
    global SAVE_FOLDER

    # Determine if non default save folder path
    changeSaveQuestion = "Store saved scraped data to default location?"
    changeSave = not askUserBool(changeSaveQuestion)

    # Non default save path
    if changeSave:
        # input new save path
        saveFolderRequest = "Enter a file path to store saved data"
        SAVE_FOLDER_ROOT = askUserPath(saveFolderRequest)
        SAVE_FOLDER = os.path.join(SAVE_FOLDER_ROOT, SAVE_FOLDER_NAME)
        
    # Default save path
    else:
        SAVE_FOLDER = os.path.join(DEFAULT_PATH, SAVE_FOLDER_NAME)

    # Check if save folder already exits before creating
    if not os.path.exists(SAVE_FOLDER):
        os.mkdir(SAVE_FOLDER)
        print("Created save folder '" + SAVE_FOLDER_NAME + "' located at '" + SAVE_FOLDER + "'\n")
    else:
        print("Using existing save folder '" + SAVE_FOLDER_NAME + "' located at '" + SAVE_FOLDER + "'\n")

def setSearchDatabase():
    '''Set base search database with additional user specified tags based on type of media to be scraped'''
    global DATABASE_SEARCH
    global DATABASE
    global scrapeTV

    DATABASE = IMDB     # TODO add user option to change this once code supports more databases
    scrapeTV = False    # bool value to determine if TV episode information will be scraped
    
    # Determine if there are additional tags for media list search
    specifySearchQuestion = "Specify type of media being scraped (more accurate scrapes)?"
    specifySearch = askUserBool(specifySearchQuestion)

    # Specify search tags
    if specifySearch:
        tags = []   # initialise list to store tags added to root search url

        # add tag for movies or tv shows
        tvQuestion = "Do you want to scrape for TV shows?"
        tagTV = askUserBool(tvQuestion)
        if tagTV:
            print("Scraping for TV shows")
            tags.append(DATABASE["TV"])     # search with TV tag
            
            # determine whether to scrape episode data
            episodeQuestion = "Do you want to scrape information for each TV episode?"
            scrapeTV = askUserBool(episodeQuestion)
            if scrapeTV: print("Scraping for TV episodes")
        else:
            print("Scraping for Movies")
            tags.append(DATABASE["Movie"])  # search with movies tag

        # add tag for anime
        animeQuestion = "Do you want to scrape for anime only?"
        tagAnime = askUserBool(animeQuestion)
        if tagAnime:
            print("Scraping for Anime")
            tags.append(DATABASE["Anime"])  # search with anime tag

        # set root search url inlcuding tags specified by user  
        tags.append(DATABASE["Query"])
        DATABASE_SEARCH = DATABASE["Search"] + "&".join(tags)

    # No additional search tags
    else:
        # set root search url with no tags for a general search
        print("Scraping for general media")
        DATABASE_SEARCH = DEFAULT_DATABASE["Search"] + DEFAULT_DATABASE["Query"]

    print(f"\nSearching {DATABASE['Name']} with root url:\n{DATABASE_SEARCH}\n")

####################################################################################################
### Functions for internet connection ###
    
def startSession():
    '''Creates a requests session for browser visit'''    
    session = requests.Session()

    # set user agent for all requests from this session
    session.headers = user_agent

    # retry parameter (total): set total retries to 3
    # retry parameter (backoff_factor): set sleep parameter between retries to 1
    # retry parameter (status_forcelist): force retry on "Too Many Requests" error (429) and common server errors (500/2/3/4)
    retry = requests.packages.urllib3.util.retry.Retry(total = 3, backoff_factor = 1, status_forcelist = [429, 500, 502, 503, 504])

    # mount adapter with retry parameters for http and https
    adapter = requests.adapters.HTTPAdapter(max_retries = retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    return session
    
def testInternetConnection():
    '''Tests internet connection and returns True or False depending on connection status'''
    ip = None
    while ip is None:
        try:
            with startSession() as session:
                # check IP address (Source: ipify.org)
                ip = session.get('https://api.ipify.org', timeout = 5).text
            print(f"\nSuccessful connection to internet (IP address: {ip})")
            connectionStatus = True
            
        except requests.exceptions.RequestException as error:
            #print(error)    # for debug only
            print("\nNo connection.")

            # ask user to retry connection test
            connectQuestion = "Check internet connection and retry?"
            connect = askUserBool(connectQuestion)
            if connect is False:
                connectionStatus = False
                break
            
    return connectionStatus

####################################################################################################
### Functions to check user input ###

def askUserPath(question, error = "File path does not exist"):
    '''Asks the user to enter a file path and returns a valid path'''
    user_input = str(input(f"\n{question}:   "))
    while not os.path.exists(user_input):
        print(error)
        user_input = str(input(f"\n{question}:   "))
    path = user_input
    return path

def askUserBool(question, error = "Invalid input"):
    '''Asks the user a yes or no question and returns a boolean answer'''
    user_input = str(input(f"\n{question} (Y/n)   "))
    while checkStringInput(user_input) is None:
        print(error)
        user_input = str(input(f"\n{question} (Y/n)   "))
    answer = checkStringInput(user_input)   
    return answer

def checkStringInput(user_input):
    '''Checks whether user has chosen yes (True) or no (False) to a question'''
    if user_input.lower().replace(" ", "") in ["y", "yes"]:
        return True
    elif user_input.lower().replace(" ", "") in ["n", "no"]:
        return False
    else:
        return None

####################################################################################################
### Functions to scrape information ###

def getData(soup):
    '''Gets html source of media data from database search'''
    # check for no results
    results = soup.find('div', class_ = 'desc')
    if "No results" in results.text:
        mediaData = None
    else:
        # html source of media data
        mediaData = soup.find('div', class_ = 'lister-item mode-advanced')

    return mediaData

def getID(mediaData):
    '''Gets database ID for media'''
    mediaID = mediaData.h3.a['href']
    
    # check for no data
    if mediaID is not None:
        # format html data
        mediaID = mediaID.split("/")[2]
    else:
        mediaID = "Unknown"
        
    return mediaID

def getTitle(mediaData):
    mediaTitle = mediaData.h3.a

    # check for no data
    if mediaTitle is not None:
        # format html data
        mediaTitle = mediaTitle.text
    else:
        mediaTitle = "Unknown"
        
    return mediaTitle

def getYear(mediaData):
    mediaYear = mediaData.h3.find('span', class_ = 'lister-item-year text-muted unbold')
    
    # check for no data
    if mediaYear is not None:
        # format html data
        mediaYear = mediaYear.text.replace("(", "").replace(")", "")
    else:
        mediaYear = "Unknown"
    
    return mediaYear

def getRuntime(mediaData):
    mediaRuntime = mediaData.p.find('span', class_ = 'runtime')
    
    # check for no data
    if mediaRuntime is not None:
        # format html data
        mediaRuntime = mediaRuntime.text
    else:
        mediaRuntime = "Unknown"
    
    return mediaRuntime

def getGenre(mediaData):
    mediaGenre = mediaData.p.find('span', class_ = 'genre')

    # check for no data
    if mediaGenre is not None:
        # format html data
        mediaGenre = mediaGenre.getText("", strip = True)
    else:
        mediaGenre = "Unknown"
    
    return mediaGenre

def getSynopsis(mediaData):
    mediaSynopsis = mediaData.findAll('p', class_ = 'text-muted')[1]

    # check for no data
    if mediaSynopsis is not None:
        # format html data
        mediaSynopsis = mediaSynopsis.getText("", strip = True).replace("See full summary»", "")
    else:
        mediaSynopsis = "Unknown"
        
    return mediaSynopsis

def getCredits(mediaData):
    '''Gets media director and cast and returns as a list'''
    mediaCredits = mediaData.find('p', class_ = '')

    # check for no data
    if mediaCredits is not None:
        # format html data
        mediaCredits = mediaCredits.getText(" ", strip = True).replace(" ,", ",")

        # separate director and cast
        mediaCredits = mediaCredits.split("|")

        # check if both director and cast listed
        if len(mediaCredits) > 1:
            mediaDirector = mediaCredits[0][mediaCredits[0].index(":"):-1].replace(": ", "")
            mediaCast = mediaCredits[1][mediaCredits[1].index(":"):].replace(": ", "")    
        
        # check if one or both director and cast is missing
        else:
            if "Director" in mediaCredits[0]:
                mediaDirector = mediaCredits[0][mediaCredits[0].index(":"):].replace(": ", "")
                mediaCast = "Unknown"
            elif "Star" in mediaCredits[0]:
                mediaCast = mediaCredits[0][mediaCredits[0].index(":"):].replace(": ", "")
                mediaDirector = "Unknown"
            else:
                mediaDirector = "Unknown"
                mediaCast = "Unknown"
    else:
        mediaDirector = "Unknown"
        mediaCast = "Unknown"

    return [mediaDirector, mediaCast]

def getPoster(mediaData):
    '''Gets url source for .jpg poster image'''
    mediaPoster = mediaData.find('img')['loadlate']
    
    # check for no data
    if mediaPoster is not None:
        # check for default blank image
        if mediaPoster[-3:] == "png":   mediaPoster = "Unknown"
        
        # format html data
        else:   mediaPoster = mediaPoster.split("_V1_")[0] + "jpg"  # remove image scaling
        
    else:
        mediaPoster = "Unknown"
    
    return mediaPoster

def getSeasons(soup):
    '''Gets all seasons for media and returns a list of season numbers'''
    mediaSeasons = soup.find('div', class_ = 'episode-list-select')

    # check for no data
    if mediaSeasons is not None:
        mediaSeasons = mediaSeasons.find('select').findAll('option')
        seasonList = [ season['value'] for season in mediaSeasons ] # create list of season values
    
    return seasonList

def getEpisodeData(soup):
    '''Gets html source of episode data for a season page'''
    seasonEpisodeData = soup.findAll('div', class_ = 'info')

    return seasonEpisodeData

def getEpisodeTitle(episodeData):
    episodeTitle = episodeData.a['title']
    
    return episodeTitle

def getEpisodeNumber(episodeData):
    episodeNumber = episodeData.meta['content']
    
    # check for no episode number
    if episodeNumber == '-1' or episodeNumber is None:
        episodeNumber = ''
        
    return episodeNumber

def getEpisodeDate(episodeData):
    episodeDate = episodeData.find('div', class_ = 'airdate')

    # check for no data
    if episodeDate is not None:
        # format html data
        episodeDate = episodeDate.text.strip()
        
        # check for empty date
        if episodeDate == '': episodeDate = "Unknown"
        
    else:
        episodeDate = "Unknown"
    
    return episodeDate

def getEpisodePlot(episodeData):
    episodePlot = episodeData.find('div', class_ = 'item_description')

    # check for no data
    if episodePlot is not None:
        # format html data
        episodePlot = episodePlot.text.strip()
        
        # check for empty description
        if "Know what this is about?" in episodePlot: episodePlot = ''
        
    else:
        episodePlot = ''
    
    return episodePlot

####################################################################################################
### Functions to save scraped data ###

def save_info(media):
    '''Scrapes media information and saves it to a text file
    Sets values to posterList cache and idList cache
    '''
    infoScraped[media] = False  # initialise information scrape status

    textName = os.path.join(SAVE_FOLDER, media + ".txt")    # text file path

    # Check if text file already exists
    if os.path.exists(textName):
        print("\n'" + media + "' text file already present")
        infoScraped[media] = True   # set information scrape status to indicate successful scrape
        posterList[media] = True    # add placeholder to poster cache to indicate possible url in text file
        idList[media] = True        # add placeholder to id cache to indicate possible id in text file
        return
        
    # Search online for media using the root search url set
    print("\nSearching '" + media + "'...")
    searchURL = DATABASE_SEARCH + media
    try:
        with startSession() as session:
            response = session.get(searchURL, timeout = 5)
    except requests.exceptions.RequestException as error:
        #print(error)    # for debug only
        print("\nCould not get '" + media + "' search url")
        infoScraped[media] = False  # set information scrape status to indicate failed search request
        posterList[media] = None    # add null placeholder to poster cache
        idList[media] = None        # add null placeholder to id cache
        return

    # store url content using BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')

    # extract html source of media data from url content
    mediaData = getData(soup)
    
    # check for no results
    if mediaData is None:
        print("\nNo results found for '" + media + "'")
        infoScraped[media] = None   # set information scrape status to indicate no results
        posterList[media] = None    # add null placeholder to poster cache
        idList[media] = None        # add null placeholder to id cache
        return
    
    # Extract relevant data from media data
    mediaID = getID(mediaData)
    mediaTitle = getTitle(mediaData)
    mediaYear = getYear(mediaData)
    mediaRuntime = getRuntime(mediaData)
    mediaGenre = getGenre(mediaData)
    mediaSynopsis = getSynopsis(mediaData)
    mediaCredits = getCredits(mediaData)
    mediaDirector = mediaCredits[0]
    mediaCast = mediaCredits[1]
    mediaPoster = getPoster(mediaData)
    
    posterList[media] = mediaPoster     # add poster url for media to poster cache
    idList[media] = mediaID             # add database id for media to id cache 

    # combine information for media
    info = ["Scraped from: " + DATABASE["Name"], "Database ID: " + mediaID,
            "Title: " + mediaTitle, "Release date: " + mediaYear,
            "Runtime: " + mediaRuntime, "Genre: " + mediaGenre,
            "Director: " + mediaDirector, "Cast: " + mediaCast,
            "Plot summary: " + mediaSynopsis, "Poster link: " + mediaPoster]
    
    # Save information to text file
    try:
        with open(textName, 'w') as file:
            file.write("\n".join(info))
    except OSError as error:
        #print(error)    # for debug only
        print("Could not save information for '" + media + "'")
        return
        
    print("\nSaved '" + media + "' information to '" + textName + "'")
    infoScraped[media] = True   # set information scrape status to indicate successful scrape
    

def save_info_episodes(media):
    '''Scrapes media episode information for all episodes and saves it to a csv file
    Dependant on save_info() - will extract media ID based on idList cache
    '''
    episodesScraped[media] = False  # initialise episodes scrape status

    tableName = os.path.join(SAVE_FOLDER, media + " episodes.csv")   # csv file path
    textName = os.path.join(SAVE_FOLDER, media + ".txt")             # text file path

    # Check if csv file already exists
    if os.path.exists(tableName):
        print("\n'" + media + "' episode info already present")
        episodesScraped[media] = True     # set episodes scrape status to indicate successful scrape
        return

    print("\nProcessing '" + media + "' episodes...")
        
    # Check for empty media id list cache
    if idList[media] is None:
        print("\nNo episode info found for '" + media + "'")
        episodesScraped[media] = None     # set episodes scrape status to indicate no results
        return

    # Get media ID                
    if idList[media] is not True:
        # get media id from generated id list cache
        mediaID = idList[media]   
    else:
        # get media id from existing text file
        with open(textName) as file:
            info = file.readlines()
            mediaID = info[1].replace("Database ID: ", "").strip()
            # TODO - add function to verify this is a valid media ID (in case the text file was altered)

    # check if no media id found
    if mediaID == "Unknown":
        print("\nNo episode info found for '" + media + "'")
        episodesScraped[media] = None   # set episodes scrape status to indicate no results
        return    
    
    # Navigate to media episodes page for first season
    print("\nSearching '" + media + "' season 1...")
    searchURL = DATABASE["TV Root"] + mediaID + DATABASE["TV Episodes"] + "1"
    try:
        session = startSession()    # use session without context manager to keep it open for reuse
        response = session.get(searchURL, timeout = 5)
        response.raise_for_status() # check for non existant page (will raise HTTP errors for 4XX, 5XX errors)
    except requests.exceptions.HTTPError as error:
        #print(error)    # for debug only
        session.close() # close session
        print("\nNo episode info found for '" + media + "'")
        episodesScraped[media] = None   # set episodes scrape status to indicate no results
        return
    except requests.exceptions.RequestException as error:
        #print(error)    # for debug only
        session.close() # close failed session
        print("\nCould not get '" + media + "' episodes url")
        episodesScraped[media] = False  # set episodes scrape status to indicate failed search request
        return

    # store url content for first season page using BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')

    # extract each season value from url content
    mediaSeasons = getSeasons(soup)

    # extract html source of episode data from url content
    mediaEpisodeData = getEpisodeData(soup)

    # check for no results
    if mediaSeasons is None or mediaEpisodeData is None:
        print("\nNo episode info found for '" + media + "'")
        episodesScraped[media] = None   # set episodes scrape status to indicate no results
        return

    # initialise dictionary to hold array of episode information (value) for each episode (key)
    episodeInfo = {}

    # Extract episode data for each episode for each season page
    for seasonIndex, season in enumerate(mediaSeasons):
        for episodeIndex, episodeData in enumerate(mediaEpisodeData, start = 1):
            episodeInfo["S"+season+"E"+str(episodeIndex)] = [season,
                                                             getEpisodeNumber(episodeData),
                                                             getEpisodeTitle(episodeData),
                                                             getEpisodeDate(episodeData),
                                                             getEpisodePlot(episodeData)]
        
        # go to next season page and extract html data
        if seasonIndex + 1 < len(mediaSeasons):
            print("\nSearching '" + media + "' season " + mediaSeasons[seasonIndex+1] + "...")
            searchURL = DATABASE["TV Root"] + mediaID + DATABASE["TV Episodes"] + mediaSeasons[seasonIndex+1]
            try:
                response = session.get(searchURL, timeout = 5)
            except requests.exceptions.RequestException as error:
                #print(error)    # for debug only
                session.close() # close failed session
                print("\nCould not get '" + media + "' episodes url")
                episodesScraped[media] = False  # set episodes scrape status to indicate failed search request
                return
            
            # store url content for next season page using BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')

            # extract html source of episode data from url content for next iteration of loop
            mediaEpisodeData = getEpisodeData(soup)

        # close the session if there are no more season pages to visit
        else:
            session.close()


    # Save episode information to csv file
    try:
        with open(tableName, 'w', newline = '') as file:
            fieldnames = ["Season", "Episode", "Title", "Date", "Description"]
            csv_writer = csv.writer(file, delimiter = ',')
            csv_writer.writerow(fieldnames)
            for info in episodeInfo.values():
                csv_writer.writerow(info)
    except OSError as error:
        #print(error)    # for debug only
        print("Could not save episode information for '" + media + "'")
        return
        
    print("\nSaved '" + media + "' episode info to '" + tableName + "'")
    episodesScraped[media] = True     # set episodes scrape status to indicate successful scrape

        
def download_images(media):
    '''Downloads media images (poster) to a jpg file
    Dependant on save_info() - will extract poster URL based on posterList cache
    '''
    imagesScraped[media] = False    # initialise image scrape status
    
    imageName = os.path.join(SAVE_FOLDER, media + " poster.jpg")   # image file path
    textName = os.path.join(SAVE_FOLDER, media + ".txt")           # text file path

    # Check if image already exists
    if os.path.exists(imageName):
        print("\n'" + media + "' image already present")
        imagesScraped[media] = True     # set image scrape status to indicate successful scrape
        return
        
    print("\nProcessing '" + media + "' images...")
    
    # Check for empty poster list cache
    if posterList[media] is None:
        print("\nNo image found for '" + media + "'")
        imagesScraped[media] = None     # set image scrape status to indicate no results
        return

    # Get poster url
    if posterList[media] is not True:
        # get image url from generated poster list cache
        posterURL = posterList[media]         
    else:
        # get image url from existing text file
        with open(textName) as file:
            info = file.readlines()
            posterURL = info[-1].replace("Poster link: ", "").strip()
            # TODO - add function to verify this is a valid poster URL (in case the text file was altered)

    # check if no image url found
    if posterURL == "Unknown":
        print("\nNo image found for '" + media + "'")
        imagesScraped[media] = None     # set image scrape status to indicate no results
        return
        
    # Search online for image poster using scraped url
    print("\nSearching for '" + media + "' poster...")
    try:
        with startSession() as session:
            response = session.get(posterURL, timeout = 5)
    except requests.exceptions.RequestException as error:
        #print(error)    # for debug only
        print("\nCould not get '" + media + "' poster url")
        imagesScraped[media] = False    # set image scrape status to indicate failed search request
        return
        
    # Save image to jpg file
    print("\nDownloading '" + media + "' poster...")
    try:
        with open(imageName, 'wb') as file:
            file.write(response.content)
    except OSError as error:
        #print(error)    # for debug only
        print("Could not save image for '" + media + "'")
        return

    print("\nSaved '" + media + "' poster to '" + imageName + "'")
    imagesScraped[media] = True     # set image scrape status to indicate successful scrape
    
####################################################################################################
### Run WebScrape Program ###
            
def checkHelp():
    '''Output relevant information from help text file if user inputs "h" for help'''
    user_input = str(input("\nEnter any key to start (h for help)\t"))
    if user_input.lower().replace(" ", "") != "h":
        return

    # Open text file
    try:
        with open('WebScrape_help.txt') as file:
            help_info = file.read()
    except OSError as error:
        #print(error)    # for debug only
        print("Could not find help text file.")
        return

    # Output relevant text from file
    help_info = help_info.split("-"*75)
    print(help_info[0])
    while True:
        help_info_select = str(input("Enter [1-6] for more information (any other key to start)\t"))
        if help_info_select.replace(" ", "") == "1":
            print(help_info[1])
        elif help_info_select.replace(" ", "") == "2":
            print(help_info[2])
        elif help_info_select.replace(" ", "") == "3":
            print(help_info[3])
        elif help_info_select.replace(" ", "") == "4":
            print(help_info[4])
        elif help_info_select.replace(" ", "") == "5":
            print(help_info[5])
        elif help_info_select.replace(" ", "") == "6":
            print(help_info[6])
        else:
            break
    print(f"\n\t{'*' * 29}")


if __name__ == "__main__":
    print(f"\n\t{'*'*36}\n\t* Welcome to zman's media scraper! *\n\t{'*'*36}\n")
    checkHelp()
    main()
    input() # keep window open until user presses enter
