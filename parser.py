#!/usr/bin/env python

import os
import json
import glob
import csv
import elasticsearch
import elasticsearch.helpers
from elasticsearch import Elasticsearch

if 'ESURL' not in os.environ:
    es_url = "http://localhost:9200"
else:
    es_url = os.environ['ESURL']

es = Elasticsearch([es_url])

# Delete the index if it exists
if es.indices.exists('covid-19') is True:
    es.indices.delete(index='covid-19', ignore=[400, 404])

# We have to create it and add a mapping
fh = open('mapping.json')
mapping = json.load(fh)
es.indices.create('covid-19', body=mapping)

all_data = []

csv_data = glob.glob("data/*.csv")

for f in csv_data:
    with open(f, 'r') as csvfile:
        csvdata = csv.reader(csvfile)

        first_line = next(csvdata)


        for i in csvdata:
            # The data format looks like this:
            #
            #Province/State,Country/Region,Last Update,Confirmed,Deaths,Recovered,Latitude,Longitude
            # We want one document per line

            base = {}

            # Some of the data is strange. Since we're importing it, we'll
            # do some transforms here

            if i[1] == "Mainland China":
                i[1] = "China"

            if i[1] == "South Korea":
                i[1] = "Korea, South"

            if i[1] == "Iran (Islamic Republic of)":
                i[1] = "Iran"

            base["province"] = i[0]
            base["country"] = i[1]

            # This field is a tire fire in the data, we'll fix it later
            #base["last_update"] = i[2]


            # Empty strings exist, make them zero
            if i[3] == '': i[3] = '0'
            if i[4] == '': i[4] = '0'
            if i[5] == '': i[5] = '0'

            base["confirmed"] = int(i[3])
            base["deaths"] = int(i[4])
            base["recovered"] = int(i[5])

            # Some of the data is missing long/lat details
            if len(i) == 8:
                # Elasticsearch geopoint format
                base["location"] = {"lat": i[6], "lon": i[7]}

            # Now the dates, this is from the filename f

            [month, day, year] = f.split('/')[1].split('.')[0].split('-')

            base['day'] = "%s%s%s" % (year, month, day)

            bulk = {
                    "_op_type": "index",
                    "_index":   "covid-19",
                   }

            bulk.update(base.copy())

            all_data.append(bulk)

for ok, item in elasticsearch.helpers.streaming_bulk(es, all_data, max_retries=2):
    if not ok:
        print("ERROR:")
        print(item)
