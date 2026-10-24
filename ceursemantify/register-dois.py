#!/usr/bin/env python3
#
# Register DOIs for a volume in ceur-ws.org
#
# Load metadata from index.jsonld.
# Config file defines values for DataCite API: apiUrl, apiUsername, apiPassword, doiPrefix
#
# Call:
# python3 register-dois.py -c config-file -v -t
# -v: verbose - more output
# -t: test run - no registration, no file changes
#
# Requirements:
# pip install requests
#
# Sources:
# see https://github.com/gsu-library/datacite-bulk-doi-creator/blob/master/upload-csv.py
#

import os
import sys
import collections
import datetime
import argparse
import requests
import json
from pathlib import Path

urlprefix = "https://ceur-ws.org/"

# datacite endpoint configuration - to be loaded from config file
apiUrl = ""
apiUsername = ""
apiPassword = ""
doiPrefix = ""



######################################################################################
# Function: Process and submit DOI to DataCite.
# parameter: doi
# return: DataCite REST API return code
'''
   Possible return codes from DataCite REST API:
     200 DOI updated
     201 DOI registered
     422 This DOI has already been taken
   see https://support.datacite.org/docs/api-error-codes
'''
def submit_doi(doi):
    data = {
        'data': {
            'type': 'dois',
            'attributes': {
                'event': 'publish',
                'doi': doi['doi'],
                'creators': doi['creators'],
                'titles': [{
                    'title': doi['title']
                }],
                'publisher': doi['publisher'],
                'publicationYear': doi['year'],
                'types': {
                    'resourceTypeGeneral': 'Text',
                    'resourceType': doi['type']
                },
                'schemaVersion': 'http://datacite.org/schema/kernel-4',
                'url': doi['url']
            }
        }
    }

    if(doi.get('volumeTitle')):
        relatedItems = [ {
            "title": [ { doi['volumeTitle'] } ],
            "relationType": "IsPublishedIn",
            "relatedItemType": "ConferenceProceedings",
            "relatedItemIdentifier": {
                "relatedItemIdentifier": doi['volumeDOI'],
                "relatedItemIdentifierType": "DOI"
            }
        } ]
        # data['data'].attributes.relatedItems = relatedItems
        print(data)

    '''
"relatedItems": [
        {
          "titles": [
            {
              "title": "Physics letters B"
            }
          ],
          "volume": "776",
          "lastPage": "264",
          "firstPage": "249",
          "relationType": "IsPublishedIn",
          "publicationYear": "2018",
          "relatedItemType": "Journal",
          "relatedItemIdentifier": {
            "relatedItemIdentifier": "0370-2693",
            "relatedItemIdentifierType": "ISSN"
          }
        }
      ],
    '''

    json_data = json.dumps(data, ensure_ascii=False)
    response = requests.post(
        apiUrl,
        headers={'Content-Type': 'application/vnd.api+json'},
        data=json_data.encode('utf-8'),
        auth=(apiUsername, apiPassword)
    )
    response_text = json.loads(response.text)
    print('{0} processed, response: {1}'.format(doi['doi'], response.status_code))
    if 'errors' in response_text and 'title' in response_text['errors'][0]:
        print(response_text['errors'][0]['title'])

    if (response.status_code == 422 or response.status_code == 409): # doi has already been taken, try update
        print("doi is already taken - trying to update it")
        response = requests.put(
            apiUrl+"/"+doi['doi'],
            headers={'Content-Type': 'application/vnd.api+json'},
            data=json_data.encode('utf-8'),
            auth=(apiUsername, apiPassword)
        )
        response_text = json.loads(response.text)
        print('{0} processed, response: {1}'.format(doi['doi'], response.status_code))
        if 'errors' in response_text and 'title' in response_text['errors'][0]:
            print(response_text['errors'][0]['title'])

    return response.status_code


######################################################################################
# Function: load metadata from index.jsonld

def loadMetadataFromIndexJSONLD():
    data_json = { }
    try:
        # try to open file
        with open("index.jsonld", "r") as file:
            jsonldcontent = file.read()
            data_json = json.loads(jsonldcontent)
            #print(data_json)
    except FileNotFoundError:
        print("ERROR - no file index.jsonld")
        sys.exit()
    return data_json


######################################################################################
# Function: save updated metadata to index.jsonld

def saveMetadataToIndexJSONLD(data_json):

    os.system("mv index.jsonld index.jsonld.bak")

    text_file = open("index.jsonld", "w")
    json.dump(data_json, text_file, ensure_ascii=False, indent=4)
    text_file.close()

    return


######################################################################################
# MAIN 
######################################################################################

# parse command line arguments
parser = argparse.ArgumentParser(
                    prog='register-dois',
                    description='Register the DOIs for a CEURWS Volume and its papers')
parser.add_argument('-v', '--verbose', action='store_true')  # on/off flag
parser.add_argument('-t', '--test', action='store_true')  # on/off flag
parser.add_argument('-c', '--config')  # config file name
args = parser.parse_args()

configFile = "register-dois.cfg"
if (args.config):
    configFile = args.config

if (args.verbose):
    print("Loading configuration from "+configFile)

# load config
with open(configFile, 'r') as f:
    config = json.load(f)

if (args.verbose):
    print(config)

apiUrl = config.get("apiUrl", "")
apiUsername = config.get("apiUsername", "")
apiPassword = config.get("apiPassword", "")
doiPrefix = config.get("doiPrefix", "")

# check config
if (not apiUsername):
    print("ERROR: no configuration for accessing DataCite")
    sys.exit()
if (not apiPassword):
    print("ERROR: no configuration for accessing DataCite")
    sys.exit()

# check files
if (not os.path.exists("index.html")):
    print("ERROR: There is no file index.html in current directory")
    sys.exit()
if (not os.path.exists("index.jsonld")):
    print("ERROR: There is no file index.jsonld in current directory")
    print("You have to create this file from index.html using the command \"ceursemantify --embed .\"")
    sys.exit()

# load data from jsonld file
if (args.verbose):
    print("Loading data from index.jsonld")
data_json = loadMetadataFromIndexJSONLD()


######################################################################################
# check if the data is complete (the metadata is defined by the DataCite Metadata Schema http://schema.datacite.org/ 
# and will include (minimum): Creator (editors, authors), Title, Publisher (ceur-ws.org), PublicationYear

everythingFine = True
tmps = data_json["title"]
if (not tmps):
    print("ERROR: no ceedings title defined")
    everythingFine = False
tmps = data_json["publisher"]
if (not tmps):
    print("ERROR: publisher not defined")
    everythingFine = False
tmps = data_json["pubYear"]
if (not tmps):
    print("ERROR: publication_year not defined")
    everythingFine = False
tmpa = data_json["editors"]
if (not tmpa):
    print("ERROR: editor list not defined")
    everythingFine = False
if (len(tmpa)<1):
    print("ERROR: editor list not defined")
    everythingFine = False

if (not everythingFine):
    sys.exit()

# TBD: Check data for papers ...


######################################################################################
# generate and store dois
# if there are alreads doi attributes defined, print a warning and continue

if (args.verbose):
    print("Generating DOIs");

volNum = data_json["volumeNumber"]
volNumFormated = "{:05d}".format(volNum)
volTitle = data_json["title"]

doiVolume = doiPrefix + "/ceurws_"+volNumFormated
urlVolume = urlprefix + "Vol-" + str(volNum)

# store volume doi in data_json
tmps = data_json.get("doi", "")
if (tmps):
    if (not tmps == doiVolume):
        print("WARN: There is already a doi defined: "+tmps)
        print("WARN: Do not overwrite this with new value: "+doiVolume)
        doiVolume = tmps
else:
    if (args.verbose):
        print("DOI for volume is "+doiVolume)
    data_json["doi"] = doiVolume

# iterate through all papers and add paper dois
papers = data_json["papers"]
count = 1
for paper in papers:
    paperID = paper["id"]
    paperPDFURL = paper["pdfUrl"]

    authors = paper.get("authors")
    if (not authors):
        if (args.verbose):
            print("WARN: No authors for paper "+paperID)
        # no dois for papers without authors - these usually are preface etc.
        continue

    landingPage = urlVolume + "/" + paperID + "/"

    paperPID = "{:03d}".format(count)
    doiPaper = doiVolume+"_"+paperPID

    tmps = paper.get("doi", "")
    if (tmps):
        if (not tmps == doiPaper):
            print("WARN: There is already a paper doi defined: "+tmps)
            print("WARN: Do not overwrite this with new value: "+doiPaper)
            doiPaper = tmps   
    else:
        if (args.verbose):
            print("DOI for paper "+paperID+" is "+doiPaper)
        paper["doi"] = doiPaper
        paper["landingPage"] = landingPage

    count = count + 1

if (not args.test):
    if (args.verbose):
        print("Saving metadata to JSON-LD file");
    saveMetadataToIndexJSONLD(data_json)

######################################################################################
# register dois

if (args.verbose):
    print("Registering DOIs");

###################################
# register doi for volume

pubYear = data_json["pubYear"]

# create data structure for registering doi for volume
doi = {
    'publisher': 'CEUR-WS.org',
    'type': 'ConferenceProceeding',
}

creator_arr = []
editor_arr = data_json["editors"]
for editor in editor_arr:
    creator = { }
    creator["nameType"] = "Personal"
    creator["givenName"] = editor["firstName"]
    creator["familyName"] = editor["name"]
    creator["creatorName"] = editor["firstName"]+" "+editor["name"]
    creator_arr.append(creator)

doi["doi"] = doiVolume
doi["creators"] = creator_arr
doi["title"] = volTitle
doi["year"] = pubYear
doi["url"] = urlVolume

if (not args.test):
    submit_doi(doi)
else:
    print("WARN: test mode - no not register doi")
    print(doi)

###################################
# register dois for papers

doiPrefixPaper = doiPrefix + "/ceurws_" + str(volNum)

papers = data_json["papers"]

for paper in papers:

    paperdoi = paper.get("doi")
    if (not paperdoi):
        continue

    # create data structure for registering doi for volume
    doi = {
        'publisher': 'CEUR-WS.org',
        'type': 'ConferencePaper',
        'volumeTitle': volTitle,
        'volumeDOI': doiVolume,
    }

    contributor_arr = paper["authors"]
    creator_arr = []
    for contributor in contributor_arr:
        creator = { }
        creator["nameType"] = "Personal"
        creator["givenName"] = contributor["firstName"]
        creator["familyName"] = contributor["name"]
        creator["creatorName"] = contributor["firstName"]+" "+contributor["name"]
        '''
        orcid = contributor.get("ceur:orcid")
        if (not orcid):
            nI = {
              "nameIdentifier": orcid,
              "nameIdentifierScheme": "ORCID",
              "schemeURI": "https://orcid.org/"
            }
            creator["nameIdentifiers"] = [ nI ]
        affiliation = None
        if (not affiliation):
            a = {
              "name": affiliation,
              #"affiliationIdentifier": "https://ror.org/03efmqc40",
              #"affiliationIdentifierScheme": "ROR"
            }
            creator["affiliations"] = [ a ]
        '''
        creator_arr.append(creator)

    doi["doi"] = paper["doi"]
    doi["creators"] = creator_arr
    doi["title"] = paper["title"]
    doi["year"] = pubYear
    doi["url"] = paper["landingPage"]

    if (not args.test):
        submit_doi(doi)
    else:
        print("WARN: test mode - no not register paper doi")
        print(doi)


