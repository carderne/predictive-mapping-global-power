#!/usr/bin/env python

from bs4 import BeautifulSoup
import urllib.request

resp = urllib.request.urlopen(
    "https://ngdc.noaa.gov/eog/viirs/download_dnb_composites_iframe.html"
)
soup = BeautifulSoup(resp, "lxml", from_encoding=resp.info().get_param("charset"))

count = 0
for link in soup.find_all("a", href=True):
    href = link["href"]
    if "tgz" in href and "slcfg" not in href:
        if "//2017" in href:
            print(href)
            count += 1
