#!/usr/bin/python
import datetime
import json
import os
import re
import sys
import time

import requests
from requests_oauthlib import OAuth1Session
from tqdm import tqdm

#	Python script to download media and links from Twitter timeline
#	1. get timeline json starting from the latest id from previous run
#	2. download the original twitter images
#	3. look for links to download (drive/tistory/daum/kakao) and links to blogs
#	4. fingerprint images and look for dupes
#	5. run on schedule

DAUM = 'DAUM'
KAKAO = 'KAKAO'
TISTORY = 'TISTORY'
GOOGLE = 'GOOGLE'
BITLY = 'BITLY'
IMGUR = 'IMGUR'

# TODO google links are wrong somewhere, probably at bitly

# Pull media urls from timeline

def process_time_line(time_line):

    # Iter timeline looking for the image url and then add the image modifier
    # Save filename url key value pair
    # Ignore key errors for when tweets don't have media in them
    name_link = {}
    for tweet in time_line:
        # print(tweet['id'])
        try:
            if tweet['extended_entities']['media']:
                for pic in tweet['extended_entities']['media']:
                    if 'media' in pic['media_url_https']:
                        file_name = pic['media_url_https'].rsplit('/', 1)[1]
                        name_link[file_name] = pic['media_url_https'] + \
                            '?format=jpg&name=orig'
        except KeyError:
            continue
    return name_link

# Look for shortened links


def find_shortened_links(time_line):
    # TODO also ignore bitly to google form and other sites that aren't daum/kakao/drive
    bitly = re.findall(r'bit.ly/\w+', str(time_line))
    # print(bitly)
    uniques = set(bitly)

    # Expand shortened link and add original modifiers
    expanded = []
    for i in uniques:
        link = requests.head('https://' + i)
        if link.status_code != 404:
            link = link.headers['location']
            if 'image' in link:
                link = link.replace('image', 'original')
            elif 'tistory' in link:
                link = link + '?original'
            elif 'thumb' in link:
                link = re.sub(
                    'https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=', '', link)
            expanded.append(link)

    # Derive filename from link and add the extension
    # Save filename url key value pair
    # TODO combine into for loop above and retest
    name_links = {}
    for link in expanded:
        # print('link: ' + link)
        if 'daumcdn' in link:
            file_name = link.rsplit('/', 1)[1].replace('?original', '')
        elif 'kakaocdn' in link:
            file_name = link.rsplit('/', 3)[1]
        else:
            # print(link)
            file_name = link.rsplit('/', 1)[1]
        ext = get_extension(link)
        if ext:
            name_links[file_name + '.' + ext] = link
    return name_links

# TODO this doesn't look like its working


def find_google_links(time_line):
    google = re.findall(
        r'http(?:s)://drive.google.com/file/d/(?:\w|-|_)+', str(time_line))
    uniques = set(google)
    name_links = {}
    for i in uniques:
        file_name = i.rsplit('/', 1)[1]
        html = requests.get(i).content
        link = re.findall(
            r'http(?:s)://\w+.googleusercontent.com/(?:\w|-|_)+', str(html))
        if len(link) > 0:
            ext = get_extension(link[0])
            if ext:
                name_links[file_name + '.' + ext] = link[0]
    return name_links


def find_links(time_line, site, regex):
    results = re.findall(regex, str(time_line))
    uniques = set(results)
    name_links = {}
    for link in uniques:
        if site == TISTORY:
            file_name = link.rsplit('/', 1)[1]
            download = link.replace('image', 'original')
            ext = get_extension(download)
        elif site == DAUM:
            file_name = link.rsplit('/', 1)[1]
            download = link + '?original'
            ext = get_extension(download)
        elif site == KAKAO:
            file_name = link.rsplit('/', 3)[1]
            ext = link.rsplit('.', 1)[1]
            download = link
        elif site == IMGUR:
            file_name = link.rsplit('/', 1)[1]
            file_name = file_name.rsplit('.', 1)[0]
            ext = link.rsplit('.', 1)[1]
            download = link
        else:
            file_name = link
            download = link
            ext = 'jpg'
        if ext:
            name_links[file_name + '.' + ext] = download
    return name_links


def get_extension(link):
    try:
        request = requests.head(link, timeout=5)
        # print('request: ' + request)
        if 'Content-Type' in request.headers:
            ext = request.headers['Content-Type'].rsplit('/', 1)[1]
            if ext == 'jpeg':
                return 'jpg'
            else:
                return ext
        else:
            return None
    except Exception:
        return None


# Check if file exists and download if not
def download_images(downloads):
    for file_name in downloads:
        # print(fileName)
        if not os.path.exists('images/' + file_name):
            response = requests.head(downloads[file_name])
            print('URL ' + downloads[file_name])
            if response.status_code == 200:
                print('DOWNLOADING:', file_name)
                try:
                    response = requests.get(downloads[file_name], stream=True)
                    with open('images/' + file_name, 'ab') as picFile:
                        picFile.write(response.content)
                except Exception:
                    print('Failed to GET:', downloads[file_name])


def download_and_log(user_timeline, account):

    twitter_images = process_time_line(user_timeline)
    download_images(twitter_images)

    links = find_shortened_links(user_timeline)
    download_images(links)

    links = find_google_links(user_timeline)
    download_images(links)

    # Look for daum links
    links = find_links(user_timeline, DAUM,
                       r'http(?:s)*://t1.daumcdn.net/cfile/tistory/\w{18}')
    download_images(links)

    # Look for tistory links
    links = find_links(user_timeline, TISTORY,
                       r'http(?:s)*://\w*.uf.tistory.com/(?:image|original)/\w{22}')
    download_images(links)

    # Look for kakao links
    links = find_links(user_timeline, KAKAO,
                       r'http(?:s)*://k.kakaocdn.net/dn/\w+/\w+/\w+/img.\w{3}')
    download_images(links)

    # Look for imgur links
    links = find_links(user_timeline, IMGUR,
                       r'http(?:s)*://i.imgur.com/\w+.(?:jpg|png|gif)')
    download_images(links)


if __name__ == "__main__":
    print('--------', str(datetime.datetime.now(tz=None)), '--------')

    accounts = []

    with open('latestUsers.json', 'r') as readFile:
        accounts = json.load(readFile)

    with open('TwitterTokens.json') as jsonFile:
        tokens = json.load(jsonFile)
        consumerKey = tokens['APIkey']
        consumerSecret = tokens['APIsecretKey']
        accessToken = tokens['AccessToken']
        tokenSecret = tokens['AccessTokenSecret']

    oauth = OAuth1Session(consumerKey, client_secret=consumerSecret, resource_owner_key=accessToken, resource_owner_secret=tokenSecret)

    downloads = 0

    # Others have explained that you should not remove elements from an array you are iterating over; however, if you traverse the array backwards, there is no problem.
    for account in reversed(accounts):
        print('--------', account['screen_name'], '--------')
        url = 'https://api.twitter.com/1.1/statuses/user_timeline.json?screen_name='+account['screen_name'] + \
            '&count=200&include_rts=true&exclude_replies=false&trim_user=true&tweet_mode=extended&since_id=' + \
            str(account['since_id'])
        response = oauth.get(url)

        # 404, account deleted
        # 401, account deleted or protected tweets
        if response.status_code == 404:
            print('######## ', account['screen_name'], ' got deleted ########')
            accounts.remove(account)
        elif response.status_code == 401:
            print('######## ', account['screen_name'],
                  ' tweets are protected or deleted ########')
            accounts.remove(account)
        else:
            # 429 is rate limit
            while response.status_code == 429:
                print(response.status_code, response.json(), url)
                for i in tqdm(range(900)):
                    time.sleep(1)
                response = oauth.get(url)

            # Check if tweet is newer
            if len(response.json()) > 0:
                downloads += 1
                account['since_id'] = response.json()[0]['id']
                account['latest_date'] = response.json()[0]['created_at']
                download_and_log(response.json(), account['screen_name'])

    if downloads == 0:
        print("NO NEW TWEETS")
    with open('latestUsers.json', 'w') as writeFile:
        writeFile.write(json.dumps(accounts, indent=4))
