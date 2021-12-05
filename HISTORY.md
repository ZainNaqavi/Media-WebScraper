Version History
===============

v1.3.0
------

**Improvements**
- Uses requests Session instead of requests.get (a new session is created for each thread since it is not considered thread safe according to requests documentation).
- Uses a single session to visit each season page when scraping for episode information for a given media.
- Minor API improvement; tells user if no results found at all or just missing poster/ episode data in summary.

**Bugfixes**
- Added retry parameters to requests Session to limit reconnect attempts to servers.
- Added timeout parameter to each request to prevent possibility of long hang time when waiting for a response.
- Detects default blank image for poster (when there is no image in database) and sets it to "Unknown" rather than attempting to download it.

**Documentation**
- Updated help text file.

v1.2.1
------

**Bugfixes**
- Solved issue of being unable to save scraped data if user input media names contain invalid characters by removing the invalid characters when generating media list.
- Added error handling for writing scraped data to file.

v1.2.0
------

**Features**
- Added support for running the program from a frozen exe file rather than python (added freeze support for multiprocessed functions and correct detection of exe location for save folder creation).

**Improvements**
- Added functionality to also include files within a specified directory when generating a media list and remove any file extensions or parentheses from names.

v1.1.0
------

**Features**
- Added functionality to scrape all episode information for media (will ask user if they want to scrape episode information if TV search tag specified).

**Documentation**
- Added help text file which can be accessed at the start of the program.

v1.0.0
------

**Features**
- Added user option to specify search tags (movies, TV, anime) for more accurate scrapes.
- Added function to test internet connection before scraping data which allows user to fix connection before continuing.
- Added user option to retry scrape for any unsuccessful scrapes where media list is updated to only contain unsuccessful scrapes.

**Improvements**
- Added hash tables to store status of scraped data for each media which is used to update media list to only contain unsuccessful scrapes upon retry.
- API improvement; added summary output for scraped data (time taken, number of successful scrapes, location of saved data and any unsuccessful scrapes)
- Fully abstracted functions which scrape data from database which will maintain compatibility with rest of code if they are overloaded for a different database in the future.

v0.2.1
------

**Bugfixes**
- Solved issue of deadlock due to download function waiting for poster cache when no information found (set poster cache to None).
- Added error handling for requests.

v0.2.0
------

**Features**
- Can generate media list from folder names in specified directory or user input.
- Can choose a different file location to save scraped data.

**Improvements**
- Multithreaded the functions which save media information and images rather than iterating through a list.
- Abstracted functions which check user input.
- Checks if relevant file already present before scraping data.
- Handles missing data from search database by saving value as "Unknown".
- Can read text file to find image link rather than rescraping information before scraping image.

v0.1.0
------

- Iterates through a media list and scrapes media information and poster image to save folder.
- Saves scraped information to txt file and poster to jpg file for each media.
