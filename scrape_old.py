"""

=======================================================================================================
Query historical data from CoinMarketCap.com for any currency without having to use their paywalled API
=======================================================================================================

@author: Micha Eichmann

Possible error when connection time > 20s:
Protocol error Runtime.callFunctionOn: Target closed.

Issue fixed with: 
pip3 install websockets==6.0 --force-reinstall

Workaround:
Simply restart whenever you hear "error!"

"""

# TODO: implement automatic going back in weeks without providing a list of URLs


import asyncio
from pyppeteer import launch
from time import sleep
from datetime import datetime
import os
import sys


def log_to_tsv(fp, row, m='a'):
    """
    Logs a list of strings to specified file in tab-separated format.
    :param fp: full path to log file
    :param row: list of strings to be logged
    :param m: Writing Mode: a = append (default), w = start new file
    """
    # construct row in tab-separated string format
    s = '\t'.join(row)
    s = s + '\n'

    # write to log file
    with open(fp, mode=m) as lf:
        lf.write(s)


def create_new_logfile(p):
    """
    Creates a new log file
    :param p: full path to directory in which the new log file is created
    :return: full path to created log file
    """
    # define filename
    time_str_fn = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

    # create full path of log file
    fn = os.path.join(p, time_str_fn + '.tsv')

    return fn


async def get_data(url, target, max_pages):
    """
    :param url: URL to scrape data from
    :param target: Token or coin name to search for
    :param max_pages: Maximum number of additional pages to load on each site
    :return: search result or False if unsuccessful in list form for tsv logging
    """
    browser = await launch()
    page = await browser.newPage()
    await page.goto(url)

    ti = await page.querySelector('h1')
    page_title = await page.evaluate('(ti) => ti.textContent', ti)
    page_title = page_title.split(' - ')[1]
    print('')
    print(page_title)

    # search max n_pages pages
    for p in range(max_pages):
        # search table
        rows = await page.querySelectorAll('tr')
        for r in rows:
            row = await page.evaluate('(r) => r.textContent', r)
            # check if target currency is in row text
            if target in row:
                # get text from all cells in row
                cells = await r.querySelectorAll('td')
                cells_txt = '\t'.join([await page.evaluate('(c) => c.textContent', c) for c in cells])
                print(cells_txt)
                await browser.close()
                return [url, page_title, cells_txt]

        # if target is not wound on current page, load more rows
        # find "load more" button
        cmc_buttons = await page.querySelectorAll('.cmc-button')
        for cb in cmc_buttons:
            button_text = await page.evaluate('(cb) => cb.textContent', cb)
            if 'Load More' == button_text:
                print('loading more rows')
                await cb.click()
                sleep(5)  # work-around to allow loading the whole table
                break

    await browser.close()
    return [False]


def main(token, interval):
    # define search criteria
    max_n_pages = 5
    urls_file = token+'_weekly_urls.txt'

    # processed URLs log file
    processed_urls_file = token+'_weekly_urls_processed.txt'
    # in case the script has to be rerun, the processed URLs log file is kept
    if not os.path.isfile(processed_urls_file):
        with open(processed_urls_file, 'a'):
            os.utime(processed_urls_file, None)

    # results log files
    log_dir = token+'_weekly_tsv'
    log_file = create_new_logfile(log_dir)
    header = ['url', 'title', 'row', '#', 'Name', 'Symbol', 'Market Cap', 'Price', 'Circulating Supply',
              'Volume (24h)', '% 1h', '% 24h', '% 7d']
    log_to_tsv(log_file, header, m='w')

    with open(urls_file) as uf:
        with open(processed_urls_file) as puf:
            for line in uf:
                if line not in puf:
                    stripped_url_line = line.rstrip('\n')
                    try:
                        result = asyncio.get_event_loop().run_until_complete(get_data(url=stripped_url_line,
                                                                                      target=token,
                                                                                      max_pages=max_n_pages))
                        log_to_tsv(log_file, result)
                        log_to_tsv(processed_urls_file, [stripped_url_line])

                    except Exception as ex:
                        os.system('say "error!"')
                        print(ex)
                        break


main(token=str(sys.argv[1]), interval=sys.argv[2])
