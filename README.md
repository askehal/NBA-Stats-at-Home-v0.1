# NBA Stats at Home

This project allows you to build a relational PostgreSQL database, scrape basketball statistics from Basketball-Reference.com, and push this data to the database. From there, you're free to connect this data to any number of statistical analysis or visualization programs. 

## Requirements

- Python 3.x
- PostgreSQL (not compatible with PostgreSQL 16)
- Required Python Libraries: `requests`, `BeautifulSoup`, `pandas`, `psycopg2`, `sqlalchemy`

## Usage - Database Setup

1. Setup database host (if using included push functions to populate DB).
2. Connect to host via a DB Management tool of your choice (I like DBeaver).
3. In your DBM, run the script from `Table Setup PostgreSQL.txt` as a SQL script. This will setup the tables of the DB.

## Usage - Web Scraper

1. Depending on your preference for Python environments (Notebook vs local), run the applicable `nbasql_functions` file.
2. If using DB push functions, you’ll need to enter your DB host’s address information into the functions to connect to your host.

## ER Diagram
![NBA DB ER Diagram](https://github.com/askehal/NBA-Stats-at-Home-v0.01/assets/122184111/598223d1-d411-42a0-bc25-4819c89b8498)


## Functions

### `char_to_alphabet_concatenated_int`

- Helper function
- **Input**: String
- **Output**: Concatenated integer representing the alphabet indices of characters in the string.

### `dateRangetoList`

- Helper function
- **Input**: Start date and end date (mm/dd/yyyy)
- **Output**: List of all dates between the start and end dates.

### `getLinks`

- Helper function
- **Input**: Date (mm/dd/yyyy)
- **Output**: List of URLs linking to box score webpages for all games on the given date.

### `getTeamPerGame`

- Extra scraping function, not used for DB
- **Input**: Team abbreviation, season end year, playoffs flag (optional)
- **Output**: DataFrame containing team per game stats for the specified season/postseason.

### `getSeasonTotal`

- **Input**: Season end year
- **Output**: DataFrame containing season totals for all NBA teams in the specified season.

### `getBoxScore`

- **Input**: URL of a box score webpage
- **Output**: DataFrames containing box score and game details.

### `dayScores`

- **Input**: Date (mm/dd/yyyy) or list of dates
- **Output**: Concatenated DataFrames of box score and game details for all games on the given date(s).

### `pushSeasonTotal`

- **Input**: Season end year
- **Output**: Pushes formatted season total stats to the `season_totals` table in the database.

### `pushBigBoxScore`

- **Input**: DataFrame containing box score details
- **Output**: Pushes box score data to the `game_logs` table in the database.

### `pushBasicBoxScore`

- **Input**: DataFrame containing basic game details
- **Output**: Pushes basic game details to the `games` table in the database.

### `pushDayScores`

- **Input**: Date (mm/dd/yyyy) or list of dates
- **Output**: For the given date(s), uses `pushBigBoxScore` and `pushBasicBoxScore` to push box score and basic game details to the database.

## Notes

- Occasionally the Scraper will fail as it is performing too many requests to Basketball-Reference.com. You can confirm this by checking if the last Status Codes in the output window before failure were Status Code 429.
- The script assumes a PostgreSQL database setup with specific table structures. Modify the database interactions as needed to fit your database schema.
