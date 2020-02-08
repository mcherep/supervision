# Copyright (c) 2020
# Manuel Cherep <manuel.cherep@epfl.ch>

"""
Scraper for the relations between supervisor and student
"""

import requests
import json
import wikitextparser as wtp
from bs4 import BeautifulSoup
import pandas as pd

URL = 'https://en.wikipedia.org/api/rest_v1/page/html/'


def main():
    people = seed()
    relations = []
    visited = {}
    while people:
        # Pop first person and remove it from the list
        p = people.pop(0)
        if not visited.get(p, False):
            # Warning: It's possible to visit a person twice if
            # Wikipedia allows different names.
            visited[p] = True
            advisors, students = get_advisors_students(title(p))
            # BFS
            people = people + advisors + students
            # Create relations
            for s in students:
                relations.append({'supervisor': p, 'student': s})
            for a in advisors:
                relations.append({'supervisor': a, 'student': p})
        if len(relations) % 100 == 0:
            print('There are already {} relations!'.format(len(relations)))
            print('There are {} people left!'.format(len(people)))

    # Save relatiosn as a csv
    relations_df = pd.DataFrame(relations)
    relations_df.to_csv('relations.csv', index=False)


def title(name):
    return name.replace(' ', '_')


def seed():
    print('Retrieving seed information...')
    # Download Nobel Laureates in Physics from the Nobel API
    physics_df = pd.read_csv(
        'http://api.nobelprize.org/v1/prize.csv?category=physics')
    physics_df['name'] = physics_df['firstname'] + ' ' + physics_df['surname']
    physics_laureates = physics_df.name.tolist()

    # Read seed people (i.e. Turing and mathematicians) from JSON
    with open('seed.json') as json_file:
        seed = json.load(json_file)

    # Download Nobel Laureates in Chemistry from the Nobel API
    chemistry_df = pd.read_csv(
        'http://api.nobelprize.org/v1/prize.csv?category=chemistry')

    # There's two specific cases where the firstname doesn't
    # match the one on Wikipedia, so we change it manually
    chemistry_df.loc[chemistry_df.firstname ==
                     'Sir Gregory P.', 'firstname'] = 'Gregory'
    chemistry_df.loc[chemistry_df.firstname ==
                     'Sir J. Fraser', 'firstname'] = 'Fraser'

    chemistry_df['name'] = chemistry_df['firstname'] + \
        ' ' + chemistry_df['surname']
    chemistry_laureates = chemistry_df.name.tolist()

    return physics_laureates + chemistry_laureates + seed


def get_advisors_students(title):
    print('Retrieving information from {}...'.format(title))
    advisors = []
    students = []

    # Request to Wikipedia API
    r = requests.get(URL + title)
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        # Find the table with the infobox
        infobox = soup.find('table', {'class': 'infobox biography vcard'})

        if infobox != None and infobox.attrs.get('data-mw') != None:
            # If there's infobox then transform to json and obtain its params
            template_params = json.loads(
                infobox.attrs['data-mw'])['parts'][0]['template']['params']

            params_advisors = ['doctoral_advisor',
                               'academic_advisors',
                               'other_academic_advisors']
            params_students = ['doctoral_students',
                               'notable_students',
                               'other_notable_students']

            for param in params_advisors:
                relations = find_relations(template_params, param)
                advisors += relations
            for param in params_students:
                relations = find_relations(template_params, param)
                students += relations

    else:
        print('Title {} is not on Wikipedia'.format(title))

    return advisors, students


def find_relations(template_params, param):
    relations = []
    if template_params.get(param) != None:
        wikitext = template_params[param]['wt']
        parsed = wtp.parse(wikitext)
        # Traverse wikilinks and get the title (i.e. names)
        for a in parsed.wikilinks:
            relations.append(a.title)
    return relations


if __name__ == "__main__":
    main()
