import csv
import requests
import bs4
import argparse
import re
import math
import sys
from urllib.parse import quote_plus
from datetime import datetime, timedelta
import traceback

# Widly used regexes compiled
re_par         = re.compile(r'\(([^\)]*)\)')
re_percent     = re.compile(r'([0-9.]*)%')
re_date_f1     = re.compile(r'[A-z][a-z][a-z]-[0-3][0-9]-[0-9][0-9]')
re_date_f2     = re.compile(r'[0-3]?[0-9] [A-z][a-z][a-z] [1-2][09][0-9][0-9] at [1-2]?[0-9]:[0-5]?[0-9]:[0-5]?[0-9][ap]m')

# enter multiple phrases separated by '',
phrases = []

phrases += ['Iphone 1','iphone 3G','iphone 3G -3Gs','Iphone 4 -4s',]
phrases += ['Iphone 4s','Iphone 5 -5c -5s','iphone 5c','Iphone 5s','Iphone 6 -plus -6s',]
phrases += ['Iphone 6 plus -6s','iphone 6s -plus','iphone 6s plus','Iphone se','Iphone 7 -plus',]
phrases += ['Iphone 7 plus','Iphone 8 -plus','Iphone 8 plus','iphone x -xs -max -xr',]
phrases += ['Iphone xs -max','Iphone xs max','Iphone xr','Iphone 11 –pro -max',]
phrases += ['Iphone 11 pro -max','Iphone 11 pro max',]
phrases += ['Iphone se','Iphone 12 -pro -mini','Iphone 12 pro -mini ',]
phrases += ['Iphone 12 pro mini ','Iphone 12 mini -pro']

def get_total_pages(given_url):
  print (given_url)
  soup = get_page_soup(given_url)
  return int( soup.find_all('a' ,class_='pg')[-1].getText() )

def get_in_paranthasis(str_par):
    return re_par.search(str_par)[1]


def get_percent(str_per):
    return re_percent.search(str_per)[1]
    
def get_date_f1(str_date):
    date_data = re_date_f1.search(str_date)[0]
    return datetime.strptime(date_data, '%b-%d-%y')

def get_date_f2(str_date):
    date_data = re_date_f2.search(str_date)[0]
    return datetime.strptime(date_data, '%d %b %Y at %I:%M:%S%p')


def get_data_from_seller_page(seller_span):
    seller_page_href = seller_span.contents[1]['href']
    soup = get_page_soup(seller_page_href)

    rating = soup.find(**{'data-test-id': "user-score"}).contents[0]
    print("rating_score:", rating)

    all_votes = 0

    for i in range(3):
        all_votes += int( (soup.find(class_='overall-rating-summary').
            contents[1].contents[1].contents[i].contents[3] # table->tbody->line-i->cell-4 (count for 12 month)
        ).getText() )
    print ("overall_votes:", all_votes)

    positive_feedback = float(get_percent(str(soup.find(class_='positiveFeedbackText'))))
    print("positive_feedback: {:.2f}".format(positive_feedback))

    user_hist = str( soup.find(**{'data-test-id':"user-history"}).contents[0] )
    member_since = (get_date_f1( user_hist ))
    print ("member_since", member_since)

    member_from = user_hist.split(" in ")[1]
    print("member_from", member_from)

    return (rating, all_votes, positive_feedback, member_since, member_from)

def extract_seller_data(soup):
    seller_span = soup.find(class_='mbg-l')
    if seller_span:
        return get_data_from_seller_page(seller_span)

    seller_span = soup.find(class_='bdg-90')
    if seller_span:
        return get_data_from_seller_page(seller_span)

def get_bidding_price(soup):
    bid_price_element = soup.find(id='prcIsum_bidPrice')
    if (bid_price_element):
        return bid_price_element.getText()

    bid_price_element = soup.find(class_='vi-VR-cvipPrice')
    if (bid_price_element):
        return bid_price_element.getText()
    
    bid_price_element = soup.find(id="prcIsum")
    return bid_price_element.getText()

def get_bid_data_from_bid_page(href, opening_bid):
    soup = get_page_soup(href)

    winning_bid = None
    rows = soup.find(class_="ui-component-table_wrapper").contents[1]
    if (len(rows) > 1):
        opening_bid = rows.contents[-1].contents[1].getText()
        winning_bid = rows.contents[0].contents[1].getText()

    date_ended = get_date_f2( soup.find(class_="app-bid-info_wrapper").contents[0].contents[2].getText() )
    duration_txt = soup.find(class_="app-bid-info_wrapper").contents[0].contents[3].getText()
    duration = int( 
        duration_txt.split(':')[1].split(' ')[0]
    )
    
    date_started = date_ended - timedelta(days=duration)
    print ("date_started", date_started)
    print ("date_ended", date_ended)
    print ("duration", duration)
    return (opening_bid, winning_bid, date_started, date_ended, duration)

def extract_bid_data(soup):
    sold = 1
    bids_link = soup.find(id='vi-VR-bid-lnk')
    number_of_bids = bids_link.contents[0].contents[0]
    if number_of_bids == '0':
        sold = 0

    starting_bid_price = get_bidding_price(soup)
    winning_bid_price = None
    starting_bid_price, winning_bid_price, date_started, date_ended, duration = get_bid_data_from_bid_page(bids_link['href'], starting_bid_price)

    print ("starting_bid_price", starting_bid_price)
    print ("winning_bid_price", winning_bid_price)
    if starting_bid_price.startswith ('$'):
        starting_bid_price = starting_bid_price.replace('$', 'US ')

    if starting_bid_price.startswith ('US $'):
        starting_bid_price = starting_bid_price.replace('US $', 'US ')
    
    starting_bid_price_currancy, starting_bid_price_value = starting_bid_price.split(' ')
    winning_bid_price_currancy, winning_bid_price_value = (None, None)

    if winning_bid_price:
        if winning_bid_price.startswith ('$'):
            winning_bid_price = winning_bid_price.replace('$', 'US ')

        if winning_bid_price.startswith ('US $'):
            winning_bid_price = winning_bid_price.replace('US $', 'US ')
    
        winning_bid_price_currancy, winning_bid_price_value = winning_bid_price.split(' ')
    print ("starting_bid", starting_bid_price_currancy, starting_bid_price_value)
    print ("winning_bid", winning_bid_price_currancy, winning_bid_price_value)
    print ("Did the listing sell? ", sold)
    
    return (sold, date_started, date_ended, duration,
        starting_bid_price_currancy, starting_bid_price_value, 
        winning_bid_price_currancy, winning_bid_price_value, )

def get_original_link_soup(href):
    soup = get_page_soup(href)

    original_link = soup.find(class_='nodestar-item-card-details__view-link')
    if original_link:
        print ("Link changed 1")
        return get_page_soup(original_link['href'])

    original_link = soup.find(class_='vi-inl-lnk vi-original-listing')
    if original_link:
        print ("Link changed 2:")
        return get_page_soup(original_link.contents[0]['href'])
    
    return soup

def get_shipping_details(soup):
    item_shipping = (soup.find(id='fshippingCost'))
    if (item_shipping):
        return item_shipping.getText().strip()

    item_shipping = soup.find(class_="vi-cvip-dspl")
    if (item_shipping):
        return item_shipping.getText().strip()
    
    return (soup.find(class_="shp-sub-text").contents[1].getText().strip())

def explore_product_page(href):    
    soup = get_original_link_soup(href)

    item_location = soup.find(itemprop="availableAtOrFrom").getText().split(', ')[-1]
    print ("item_location", item_location)

    item_condition = soup.find(id="vi-itm-cond").getText()
    print ("item_condition", item_condition)

    item_shipping = get_shipping_details(soup)
    print ("item_shipping", item_shipping)

    item_returns = soup.find(id='vi-ret-accrd-txt').getText()
    print ("item_returns", item_returns)

    seller_name = soup.find(class_='mbg-nw').getText()
    # print ("seller_name", seller_name)

    (sold, date_started, date_ended, duration,
        starting_bid_price_currancy, starting_bid_price_value, 
        winning_bid_price_currancy, winning_bid_price_value, ) = extract_bid_data(soup)
    (seller_rating, all_votes, positive_feedback, member_since, member_from) = extract_seller_data(soup)


    return (sold, date_started, date_ended, duration, seller_name,
        item_location, item_condition, item_shipping, item_returns,
        starting_bid_price_currancy, starting_bid_price_value, 
        winning_bid_price_currancy, winning_bid_price_value,
        seller_rating, all_votes, positive_feedback, member_since, member_from
    )

def get_page_soup(url):
    print ("Url:" , url)
    res = requests.get(url, proxies=None)
    res.raise_for_status()
    return bs4.BeautifulSoup(res.text, "html.parser")

def process_phrase(phrase, writer):
    print ("Phrase", phrase)
    url = ('https://www.ebay.com/sch/i.html?_from=R40&_sacat=0&_udlo=' +
            '&_udhi=&LH_Auction=1&_samilow=&_samihi=&_sadis=15&_stpos=90278-4805' +
            '&_fosrp=1&LH_Complete=1&_nkw={}' +
            '&_pppn=r1&scp=ce0').format(quote_plus(phrase))

    pages = get_total_pages(url)
    
    for page in range(1, min(20, pages + 1)): # max 10 pages
        cur_page = f'{url}&_pgn={page}'

        soup = get_page_soup(cur_page)

        # grab all the links and store its href destinations in a list
        link_listing = soup.find_all(class_="vip")

        for l in link_listing:
            href = l['href']
            title = l.getText()
            try:
                data = explore_product_page(href)
            except SystemExit:
                print ("Sys exit at ", href)
                raise
            except Exception:
                print(traceback.format_exc())
                print("Skipping", href)
                # raise
            else:
                data = (phrase,title) + data
                writer.writerow(data)

explore_link = None
if __name__ == '__main__':
  if explore_link:
    explore_product_page(explore_link)
  else:
    re_space_replace = re.compile(r'[ .,+]')
    re_cleanup = re.compile(r'[^A-Za-z0-9-_]')
    for phrase in phrases:
        phrase_filename = phrase
        phrase_filename = re_space_replace.sub('_', phrase_filename)
        phrase_filename = re_cleanup.sub('_', phrase_filename)
        phrase_filename = phrase_filename.lower()

        with open(f'products/{phrase_filename}.csv', 'w') as f:
            writer = csv.writer(f)
            writer.writerow(['phrase', 'title', 'sold', 'date_started', 'date_ended', 
                    'duration', 'seller_name', 'item_location', 'item_condition', 
                    'item_shipping', 'item_returns',
                    'starting_bid_price_currancy', 'starting_bid_price_value',
                    'winning_bid_price_currancy', 'winning_bid_price_value',
                    'seller_rating', 'all_votes', 'positive_feedback', 'member_since', 'member_from'])
        
            process_phrase(phrase, writer)
