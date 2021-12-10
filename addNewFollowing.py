import json
import os
import re
import sys
import time
import datetime

import requests
from tqdm import tqdm
from requests_oauthlib import OAuth1Session

'''
Add new following accounts to list. Make sure to do this whenever a new account is followed immediately to not miss a tweet.
'''

# Get credentials and set up oauth

with open('TwitterTokens.json') as jsonFile:
	tokens = json.load(jsonFile)
	consumerKey = tokens['APIkey']
	consumerSecret = tokens['APIsecretKey']
	accessToken = tokens['AccessToken']
	tokenSecret = tokens['AccessTokenSecret']

oauth = OAuth1Session(consumerKey, client_secret=consumerSecret, resource_owner_key=accessToken, resource_owner_secret=tokenSecret)

# Get currently following accounts
cursor = -1
accounts = []

while (cursor != 0):
	url = 'https://api.twitter.com/1.1/friends/list.json?screen_name=&count=200&include_user_entities=false&skip_status=t'
	response = oauth.get(url + '&cursor=' + str(cursor))
	for account in response.json()['users']:
		accounts.append(account)
	cursor = response.json()['next_cursor']

# Check current list of following accounts and add the account that's not there
currentAccounts = []
with open('latestUsers.json', 'r') as readFile:
	currentAccounts = json.load(readFile)

newAccounts = []
for account in accounts:
	if account['screen_name'] not in str(currentAccounts):
		print(account['screen_name'], 'not found...adding')
		url = 'https://api.twitter.com/1.1/statuses/user_timeline.json?screen_name='+account['screen_name']+'&include_rts=false&exclude_replies=true&trim_user=true'
		response = oauth.get(url)
		if len(response.json()) != 0:
			try:
				newAccount = {}
				newAccount['screen_name'] = account['screen_name']
				newAccount['since_id'] = response.json()[0]['id']
				newAccount['latest_date'] = response.json()[0]['created_at']
				newAccounts.append(newAccount)
			except KeyError:
				print(response.json(), account['screen_name'])

if len(newAccounts) != 0:
	newList = newAccounts + currentAccounts

	with open('latestUsers.json', 'w') as writeFile:
		writeFile.write(json.dumps(newList, indent=4))
else:
	print('No accounts to add')