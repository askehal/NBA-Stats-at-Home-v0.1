# -*- coding: utf-8 -*-
"""nbasql_functions.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1qPdI3Fr8IKJgYJvtkNOUtPpwgjAnjJwO
"""

import pandas as pd
from bs4 import BeautifulSoup
import requests
import json
import re
import psycopg2
from sqlalchemy import create_engine
from datetime import datetime, timedelta
import numpy as np

def char_to_alphabet_concatenated_int(s):
    # Convert each character to its alphabet index
    alphabet_indices = [ord(char) - 64 for char in s.upper() if 'A' <= char <= 'Z']

    # Concatenate the indices as strings and then convert to an integer
    concatenated_int = int(''.join(map(str, alphabet_indices)))

    return concatenated_int

def getTeamPerGame(team, season_end_year, playoffs = 'FALSE'):
  if playoffs == 'FALSE':
    selector = 'per_game'
  elif playoffs == 'TRUE':
    selector = 'playoffs_per_game'
  r = requests.get(f'https://www.basketball-reference.com/teams/{team}/{season_end_year}.html#{selector}')
  df = None
  print(r.status_code)
  if r.status_code == 200:
    soup = BeautifulSoup(r.content, 'html.parser')
    mydivs = soup.find_all("table", class_ = 'stats_table sortable', id = selector)
    df = pd.read_html(str(mydivs))[0]
    df = df.drop('Rk', axis = 1)
    return df

def getSeasonTotal(season_end_year):
  url = f"https://www.basketball-reference.com/leagues/NBA_{season_end_year}_totals.html"

  r = requests.get(url)
  df = None

  if r.status_code == 200:
    soup = BeautifulSoup(r.content, 'html.parser')
    mydivs = soup.find_all("table", class_ = 'sortable stats_table', id = 'totals_stats')
    df = pd.read_html(str(mydivs))[0]
    df = df.drop('Rk', axis = 1)
    df = df[df['Tm'] != 'TOT']
    # Remove non-player rows from table
    remove = ['Age']
    df = df.loc[~df['Age'].isin(remove)]
    return df

# Returns an array of links to the box score webpages for all games on the given day (mm/dd/yyyy)
def getLinks(date):
  # Pull month, day, and year from the inputted date and use to create url of webpage that has all scores on that date
  date = str(date)
  month = date[0:2]
  day = date[3:5]
  year = date[6:10]
  url = f'https://www.basketball-reference.com/boxscores/?month={month}&day={day}&year={year}'
  r = requests.get(url)

  if r.status_code == 200:
    soup = BeautifulSoup(r.content, 'html.parser')

    # Pulls all of the url suffixes that link to individual games
    teams = soup.find_all('td', class_='right gamelink')

    # Edit url suffixes to convert them to full, usable urls and add to returned list
    links = []
    for a in teams:
      a = str(a)
      a = "".join(['https://www.basketball-reference.com', a[a.index('/b'):a.index('l"')+1]])
      links.append(a)

    return links

# Returns df of box score from given game, appended
def getBoxScore(url):

  r = requests.get(url)
  print(f'Status code: {r.status_code}')
  if r.status_code == 200:
    soup = BeautifulSoup(r.content, 'html.parser')
    # Find all links
    links = soup.find_all('a')

    # Check if links have appropriate substrings that signify tags used for Game links, add compliant links to list
    teams = []
    for a in links:
      a = str(a)
      if '<a href="/teams/' in a:
        if 'Schedule</u>' in a:
          teams.append(a)

    # Pull and isolate the json lines containing date info. Clean and convert these lines to date type
    datepull = soup.find_all(class_ = "index")
    datecol = str(datepull[0])
    start = datecol.index('<u>')
    end = datecol.index('NBA')
    datecol = datecol[(start+3):(end-1)]
    datecol = datetime.strptime(datecol, "%b %d, %Y").date()

    # Prepare variables for iteration and create empty 2D dataframe
    i = 0
    r = 0
    rows = 2
    c = 0
    cols = 4
    finalTeams = [["" for i in range(cols)] for j in range(rows)]

    for b in teams:
      if i < 2:
        c = 0
        # Create 3 letter abbreviated team name substring from team link
        b = b[16:19]
        finalTeams[r][c] = b
        c+=1
        # In next column, use abbreviated team name to create tag used to find team's box score in game webpage
        b = f"box-{b}-game-basic"
        finalTeams[r][c] = b
        r+=1
      i += 1


    # Use finalTeams table created above to assign team names, winner and loser, home and away, etc.
    # As webpage is setup to have the away team's table first, we can assign home and away teams just by seeing which team is first in the finalTeams DataFrame
    box = soup.find_all('table', id = finalTeams[0][1])
    box2 = soup.find_all('table', id = finalTeams[1][1])
    df = pd.read_html(str(box))[0]
    df2 = pd.read_html(str(box2))[0]

    # Add abbreviated team name column to box score dataframes
    df['Team'] = finalTeams[0][0]
    df2['Team'] = finalTeams[1][0]

    # Establish Home and Away teams and their final scores
    basic_home = finalTeams[1][0]
    basic_home_score = df2.iloc[-1,-3]
    basic_away = finalTeams[0][0]
    basic_away_score = df.iloc[-1,-3]

    # Establish Winner and Loser using final scores
    if df.iloc[-1,-3] > df2.iloc[-1,-3]:
      df['wl'] = 'W'
      df2['wl'] = 'L'
      basic_winner = finalTeams[0][0]
      basic_loser = finalTeams[1][0]
    else:
      df['wl'] = 'L'
      df2['wl'] = 'W'
      basic_winner = finalTeams[1][0]
      basic_loser = finalTeams[0][0]

    # Find title of page to check if game is Playoff, Regular Season, or In-Season Tournament Final
    yoffs = soup.find_all(class_ = "breadcrumbs")
    if 'Conference' in str(yoffs[0]):
      df['Game Type'] = 'Playoff'
      df2['Game Type'] = 'Playoff'
      basic_game_type = 'Playoff'

    elif 'In-Season Tournament Final' in str(yoffs[0]):
      df['Game Type'] = 'IST Final'
      df2['Game Type'] = 'IST Final'
      basic_game_type = 'IST Final'

    elif 'Play-In' in str(yoffs[0]):
      df['Game Type'] = 'Play-In Tournament'
      df2['Game Type'] = 'Play-In Tournament'
      basic_game_type = 'Play-In Tournament'

    else:
      df['Game Type'] = 'Regular Season'
      df2['Game Type'] = 'Regular Season'
      basic_game_type = 'Regular Season'

    # Concat dataframes together (SQL Union) and establish column names
    boxScore = pd.concat([df, df2])
    boxScore = boxScore.reset_index(drop=True)
    boxScore['Date'] = datecol
    basic_date = datecol
    print(basic_date)
    basic_season_id = 0
    basic_year = datecol.year
    basic_month = int(datecol.month)
    basic_day = int(datecol.day)
    basic_id = f"{basic_month:02d}" + f"{basic_day:02d}" + str(basic_year) + str(char_to_alphabet_concatenated_int(finalTeams[1][0]))
    print(basic_id)

    # Create DataFrame for game_basic SQL table
    basic_row = {'game_id':basic_id, 'team_id_home':basic_home, 'team_id_away':basic_away, 'home_score':basic_home_score, 'away_score':basic_away_score, 'team_id_winner':basic_winner, 'team_id_loser':basic_loser, 'season_id':basic_season_id, 'game_date':basic_date, 'game_type':basic_game_type}
    game_basic = pd.DataFrame([basic_row])

    cols = ['Players', 'MP', 'FGM', 'FGA', 'FG%', '3PM', '3PA', '3P%', 'FTM', 'FTA', 'FT%', 'ORB', 'DRB', 'TRB', 'AST', 'STL', 'BLK', 'TO', 'PF', 'PTS', '+/-', 'wl','Team', 'Game Type', 'Date']
    boxScore.columns = cols

    # Remove non-player rows from table
    remove = ['Reserves', 'Team Totals']
    boxScore = boxScore.loc[~boxScore['Players'].isin(remove)]


    # Replace NA and non-numeric cells with 0
    j = 2
    while j < 21:
      boxScore[cols[j]] = boxScore[cols[j]].fillna(0)
      boxScore[cols[j]] = pd.to_numeric(boxScore[cols[j]], errors='coerce').fillna(0)
      j+=1

    # Reset index before iterating over df
    boxScore = boxScore.reset_index(drop=True)

    # Cast columns as time, int, or float depending on column index
    j = 1
    while j <= 20:
      match j:
          case 1:
            # For MP, first must convert non-numeric values to 0 using specific parameters (to_numeric would flag all MP as non-numeric), then cast as datetime --> time
            q = 0
            while q < len(boxScore):
              boxScore[cols[j]] = boxScore[cols[j]].replace('Did Not Play', '00:00')
              boxScore[cols[j]] = boxScore[cols[j]].replace('Did Not Dress', '00:00')
              boxScore[cols[j]] = boxScore[cols[j]].replace('DNP', '00:00')
              boxScore[cols[j]] = boxScore[cols[j]].replace('Not With Team', '00:00')
              boxScore[cols[j]] = boxScore[cols[j]].replace('Player Suspended', '00:00')
              boxScore.loc[q, 'MP'] = datetime.strptime(boxScore.loc[q, 'MP'], '%M:%S').time()
              q+=1
          case 2 | 3 | 5 | 6 | 8 | 9 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20:
            boxScore[cols[j]] = boxScore[cols[j]].astype(int)
          case 4 | 7 | 10:
            boxScore[cols[j]] = boxScore[cols[j]].astype(float)
      j+=1

    # Calculate and assign Double Double and Triple Double booleans to final dataframe
    boxScore['dd'] = 0
    boxScore['td'] = 0
    stri = ""
    i = 0
    boxScore['player_game_id'] = ""
    for i in range(boxScore.shape[0]):
      count = 0
      boxScore.iloc[i,-1] = f"{basic_month:02d}" + f"{basic_day:02d}" + str(basic_year) + str(char_to_alphabet_concatenated_int(boxScore.iloc[i,0]))
      if int(boxScore.iloc[i,-9]) >= 10:
        count+=1
      if int(boxScore.iloc[i,-12]) >= 10:
        count+=1
      if int(boxScore.iloc[i,-13]) >= 10:
        count+=1
      if int(boxScore.iloc[i,-14]) >= 10:
        count+=1
      if int(boxScore.iloc[i,-15]) >= 10:
        count+=1
      if count >= 2:
        boxScore.iloc[i, -3] = 1
      if count >= 3:
        boxScore.iloc[i, -2] = 1
      i+=1

    # Update columns to align with SQL server's naming conventions
    cols = ['player_name', 'min', 'fgm', 'fga', 'fg_pct', 'fg3m', 'fg3a', 'fg3_pct', 'ftm', 'fta', 'ft_pct', 'oreb', 'dreb', 'reb', 'ast', 'stl', 'blk', 'tov', 'pf', 'pts', 'plus_minus', 'team_id','wl', 'game_type', 'game_date', 'dd2', 'td3', 'player_game_id']
    boxScore.columns = cols

    # Add season id and game id
    linkos = soup.find_all('a')
    seas = []
    for a in linkos:
      a = str(a)
      if '<a href="/leagues/NBA_' in a:
        if '_games.html">' in a:
          seas.append(a)
    season_id = (seas[0])[22:26]
    boxScore['season_id'] = season_id
    game_basic['season_id'] = season_id
    boxScore['game_id'] = basic_id


    return boxScore, game_basic

  else:
    print(requests.Response())

    requests.Response().raise_for_status


# Returns a single, concatenated dataframe of all games on a given date/list of dates
def dayScores(date):
 box = pd.DataFrame()
 basicbox = pd.DataFrame()
# Check if input is a single date or list of dates

 if type(date) == str:
  # Convert inputted date to datetime object that we can pass to getLinks in order to get all game links from that day
  gameday = datetime.strptime(date, '%m/%d/%Y')
  links = getLinks(date)

  # For each game link, get the box score and concat to a master dataframe that we will return
  for a in links:
    holder, basic = getBoxScore(a)
    box = pd.concat([box, holder])
    basicbox = pd.concat([basicbox, basic])

  # Reset index as currently, each game resets index
  box = box.reset_index(drop=True)
  basicbox = basicbox.reset_index(drop=True)
  print(date)
  return box, basicbox

 # If inputted data is a list of dates, we can recursively call this function for each individual date in the list and concat them all to a master dataframe
 elif type(date) == list:
  bigBox = pd.DataFrame()
  bigBasic=pd.DataFrame()

  for v in date:
    holder, basic = dayScores(str(v))
    bigBox = pd.concat([bigBox, holder])
    bigBasic = pd.concat([bigBasic, basic])

  bigBox = bigBox.reset_index(drop=True)
  bigbasic = bigBasic.reset_index(drop=True)
  return bigBox, bigBasic

# Format Season Total stats and push to season_total table; can run weekly to update season stats for current season
def pushSeasonTotal(year):

   # Format DataFrame to remove unneeded columns and convert column names to align with SQL database's naming convention
   df = getSeasonTotal(year)
   drops = [1, 5, 13, 14, 15, 16]
   df = df.drop(df.columns[drops], axis = 1)
   cols = ['player_name', 'age', 'team_id', 'gp', 'min', 'fgm', 'fga', 'fg_pct', 'fg3m', 'fg3a', 'fg3_pct', 'ftm', 'fta', 'ft_pct', 'oreb', 'dreb', 'reb', 'ast', 'stl', 'blk', 'tov', 'pf','pts']
   df.columns = cols

   df['age'] = df['age'].astype(int)
   df['season_id'] = year

   # Establish connection url for create engine to_sql and create psycopg2 connection for executing SQL queries
   # Enter your DB information below
   url = ""
   conn = psycopg2.connect(
    dbname = '',
    user = '',
    password = '',
    host = '',
    port =5432
   )
   conn.autocommit = True
   cur = conn.cursor()

   # Check if each player is already in the database. If so, assign the applicable player_id to the player in the stats table. If not, create a new player_id and push the player to the players table before adding to the stats table
   df['player_id'] = 0
   for i in range(df.shape[0]):
     player_name = df.iloc[i,0]

     cur.execute("SELECT player_id FROM players WHERE player_name = %s", (player_name,))
     existing_player = cur.fetchone()
     if existing_player:  # If the player exists
       player_id = existing_player[0]
     else:
       # If the player doesn't exist, insert the player into the players table
       cur.execute("SELECT * from players")
       player_id = len(cur.fetchall())

       player_id+=1
       cur.execute("INSERT INTO players (player_id, player_name) VALUES (%s, %s) RETURNING player_id", (player_id, player_name))
       print("New player inserted with player_id:", player_id)

     df.iloc[i, -1] = player_id

   # Checks if we are pulling season total stats for the current year, in which case we delete the values currently there before updating with the more recent totals
   if year == datetime.now().year:
    cur.execute("DELETE FROM season_totals WHERE season_id = %s", (year,))
    print(f"Updated season_totals for {year}")

   # Convert NULL values for % fields to 0
   # List of column names containing 'pct'
   cols_with_pct = [a for a in df.columns if 'pct' in a]

   # Replace NULL values with 0 for columns containing 'pct' in their name
   df[cols_with_pct] = df[cols_with_pct].fillna(0)

   # Push formatted DataFrame to season_totals table in SQL database
   engconn = create_engine(url, pool_pre_ping= True)
   engconn.autocommit = True
   df.to_sql('season_totals', con=engconn, index=False, if_exists='append')


# Convert a start date and end date into a list of all dates between them, inclusive
def dateRangetoList(start_date_str, end_date_str):
  # Parse start and end dates into datetime objects
  start_date = datetime.strptime(start_date_str, "%m/%d/%Y").date()
  end_date = datetime.strptime(end_date_str, "%m/%d/%Y").date()

  # Generate a range of dates
  date_range = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]

  # Format dates back into strings
  date_range_str = [date.strftime("%m/%d/%Y") for date in date_range]

  return date_range_str

# Push boxScore DataFrame to the game_logs SQL table
def pushBigBoxScore(boxScore):
  # Enter your DB information below
  url = ""
  conn = create_engine(url, pool_pre_ping=True)
  conn.autocommit = True

  # Enter your DB information below
  connpg = psycopg2.connect(
    dbname = '',
    user = '',
    password = '',
    host = '',
    port =5432
  )
  connpg.autocommit = True
  cur = connpg.cursor()
  checkcur = connpg.cursor()

  # Check if each player is already in the database. If so, assign the applicable player_id to the player in the stats table. If not, create a new player_id and push the player to the players table before adding to the stats table
  boxScore['player_id'] = 0

  # Check that player_game_id isn't already present in game_logs SQL table before pushing
  checkcur.execute("SELECT DISTINCT player_game_id from game_logs")
  ids = checkcur.fetchall()
  cleaned_ids = [str(item).replace('(', '').replace(')', '').replace(',', '').replace('Decimal','').replace('\'', '').replace('"', '') for item in ids]



  for i in range(boxScore.shape[0]):
    player_name = boxScore.iloc[i,0]

    cur.execute("SELECT player_id FROM players WHERE player_name = %s", (player_name,))
    existing_player = cur.fetchone()
    if existing_player:  # If the player exists
      player_id = existing_player[0]
    else:
      # If the player doesn't exist, insert the player into the players table
      cur.execute("SELECT count(player_id) from players")
      player_id = cur.fetchone()[0]
      player_id+=1
      cur.execute("INSERT INTO players (player_id, player_name) VALUES (%s, %s) RETURNING player_id", (player_id, player_name))
      print("New player inserted with player_id:", player_id)

    boxScore.iloc[i, -1] = player_id

  # Check if DataFrame is empty before pushing to SQL table
  if boxScore.empty:
    print(f'DataFrame is empty. Check if there were any games on this day. Skipping database operation.')
    return
  else:
    # Convert NULL values for % fields to 0
    # List of column names containing 'pct'
    cols_with_pct = [a for a in boxScore.columns if 'pct' in a]

    # Replace NULL values with 0 for columns containing 'pct' in their name
    boxScore[cols_with_pct] = boxScore[cols_with_pct].fillna(0)
    len1 = len(boxScore)
    boxScore = boxScore.loc[~boxScore['player_game_id'].isin(cleaned_ids)]
    len2 = len(boxScore)
    if len1 > len2:
      print(f"Removed {(len1-len2)} duplicate game lines out of {len1} original lines before pushing to game_logs table")

    boxScore.to_sql('game_logs', con=conn, index=False, if_exists='append')




# Push game_basic DataFrame to the games SQL table
def pushBasicBoxScore(basic):
  # Enter your DB information below
  url = ""
  conn = create_engine(url, pool_pre_ping=True)
  conn.autocommit = True

  # Enter your DB information below
  connpg = psycopg2.connect(
    dbname = '',
    user = '',
    password = '',
    host = '',
    port = 5432
  )
  cur = connpg.cursor()

  # Check that game_id isn't already present in games SQL table before pushing
  cur.execute('SELECT DISTINCT game_id from games')
  ids = cur.fetchall()
  cleaned_ids = [int(str(item).replace('(', '').replace(')', '').replace(',', '')) for item in ids]


  # Check that DataFrame is not empty before pushing to SQL table
  if basic.empty:
    print(f'DataFrame is empty. Check if there were any games on this day. Skipping database operation.')
    return
  else:
   len1 = len(basic)
   basic['game_id'] = basic['game_id'].astype(int)
   basic = basic.loc[~basic['game_id'].isin(cleaned_ids)]
   len2 = len(basic)
   if len1 > len2:
     print(f"Removed {(len1-len2)} duplicate game lines out of {len1} original lines before pushing to games table")
   basic.to_sql('games', con=conn, index=False, if_exists='append')

def pushDayScores(date):
  if type(date) == str:
    big, basic = dayScores(date)
    pushBasicBoxScore(basic)
    pushBigBoxScore(big)

  # If inputted data is a list of dates, we can recursively call this function for each individual date in the list
  elif type(date) == list:
    for v in date:
      pushDayScores(v)