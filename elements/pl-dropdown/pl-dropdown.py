import prairielearn as pl
import lxml.html
import json
import random
import chevron
import os
from enum import Enum

WEIGHT_DEFAULT = 1

class SortTypes(Enum): 
    RANDOM = 'random'
    ASCEND = 'ascend'
    DESCEND = 'descend'

def prepare(element_html, data):
    element = lxml.html.fragment_fromstring(element_html)
    pl.check_attribs(element, required_attribs=['options', 'answer', 'answer-key'], optional_attribs=['weight', 'sort'])
    name = pl.get_string_attrib(element, 'answer-key')
    correct_answer = pl.get_float_attrib(element, 'correct-answer', None)

    if data['correct_answers'][name] == None:
        raise Exception('Correct answer not defined for %s' % name)
    
    if correct_answer is not None:
        if name in data['correct_answers']:
            raise Exception('duplicate correct_answers variable name: %s' % name)
        data['correct_answers'][name] = correct_answer

def render(element_html, data):
    element = lxml.html.fragment_fromstring(element_html)
    dropdown_options = json.loads(pl.get_string_attrib(element, 'options'))
    sort = pl.get_string_attrib(element, 'sort', '').upper().strip()

    answer_key = pl.get_string_attrib(element, 'answer-key')
    html_params = {}
    html = ''

    if data['panel'] == 'question':
        if sort == SortTypes.DESCEND.name:
            dropdown_options.sort(reverse=True)
        elif sort == SortTypes.ASCEND.name:
            dropdown_options.sort(reverse=False)
        elif sort == SortTypes.RANDOM.name: 
            random.shuffle(dropdown_options)

        html_params = {
            'question': True,
            'uuid': pl.get_uuid(),
            'options': dropdown_options,
        }
    elif data['panel'] == 'submission':
        html_params = {
            'submission': True,
            'submitted_answer': data['submitted_answers'].get(answer_key, None),
            'answer_key': answer_key
        }
    elif data['panel'] == 'answer':
        answer_key = pl.get_string_attrib(element, 'answer-key')
        submitted_answer = data['submitted_answers'].get(answer_key, None)
        name = pl.get_string_attrib(element, 'answer-key')

        html_params = {
            'answer': True,
            'submitted_answer': submitted_answer,
            'correct_answer': data['correct_answers'][name],
            'correct': data['correct_answers'][name] == submitted_answer
        }

    with open('pl-dropdown.mustache', 'r', encoding='utf-8') as f:
        html = chevron.render(f, html_params).strip()
    return html

def parse(element_html, data):
    html_element = lxml.html.fragment_fromstring(element_html)
    answer_key = pl.get_string_attrib(html_element, 'answer-key')
    answer_options = json.loads(pl.get_string_attrib(html_element, 'options'))
    answer = data['submitted_answers'].get(answer_key, None)

    if answer is None:
        data['format_errors'][answer_key] = 'No answer was submitted.'
        return

    if answer not in answer_options:
        data['format_errors'][answer_key] = f'Invalid choice: {pl.escape_invalid_string(answer_key)}'
        return

def grade(element_html, data):
    element = lxml.html.fragment_fromstring(element_html)
    name = pl.get_string_attrib(element, 'answer-key')
    weight = pl.get_integer_attrib(element, 'weight', WEIGHT_DEFAULT)
    answer = data['submitted_answers'].get(name, None)
    
    if data['correct_answers'][name] == answer:
        data['partial_scores'][name] = {'score': 1, 'weight': weight}
    else:
        data['partial_scores'][name] = {'score': 0, 'weight': weight}

    answer = pl.get_string_attrib(element, 'answer')
    data['submitted_answers'][name] = answer
