# Media-WebScraper
This program scrapes information and images for movies and TV shows.

## Summary
For more information on the program, read the *WebScrape_help* text file (this can also be accessed while running the program).

For a given list of media, the program will scrape and save **general information**, **images** and any **episode information** for each media.

### General Information (default):
**Saved as a .txt file**

This will scrape general information:
- Title
- Release date
- Runtime
- Genre
- Director
- Cast
- Plot description

Additional information saved:
- Source database used for scrape
- ID for media in source database
- Poster image link

### Images (default):
**Saved as a .jpg file**

This will scrape the poster.

### Episode Information (if specified):
**Saved as a .csv file**

This will scrape information for each episode for a TV show:
- Season number
- Episode number
- Episode title
- Episode air date
- Episode description

## Features:
- **Multithreaded** scraping for media in list to greatly improve the time taken when scraping for large media lists.
- Can **generate a media list** from **folders and files in a specified directory** or from **user input**.
- Can **specify save location** for scraped data.
- Can **specify search tags** for media list for a more accurate scrape.
- Can choose to **scrape all episode information** for a TV show.
- Can **detect if data is already scraped** which allows for scraping new media from an already scraped list of media very efficient.
- Can **recover missing scraped files** if one or more are missing without rescraping all data.
- Can **retry the scrape** before exiting the program if there were any incomplete scrapes (successfully scraped files will not be altered or rescraped).
- Currently only supports scraping data from **IMDb**.

## Usage:
For more information on the program, read the *WebScrape_help* text file (this can also be accessed while running the program).

Currently a terminal-based program.

### Running the program using python:
- **Requirements:** Python 3.2+ (additional libraries: requests, beautifulsoup4)

### Running the program from bundled executable file (created using pyinstaller):
- **Requirements:** Windows 10
- Creates a 'temp' folder containing extracted libraries and support files in the same location as the program while running.
  - The temporary files will delete automatically but if the program is closed abruptly, the files will remain.
  - The 'temp' folder can be manually deleted after closing the program.
  - (As of pyinstaller v4.7, a one-file bundled executable will leave any temp '_MEIxxxxxx' folders if the program is force closed)

## Updates:
For information on version history, read the *HISTORY* markdown file.
