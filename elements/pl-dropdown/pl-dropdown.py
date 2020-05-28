import prairielearn as pl
import lxml.html
import json
import chevron
import os

WEIGHT_DEFAULT = 1

def prepare(element_html, data):
    element = lxml.html.fragment_fromstring(element_html)
    pl.check_attribs(element, required_attribs=['options', 'answer', 'answer-key'], optional_attribs=['weight'])
    name = pl.get_string_attrib(element, 'answer-key')

    correct_answer = pl.get_float_attrib(element, 'correct-answer', None)
    if correct_answer is not None:
        if name in data['correct_answers']:
            raise Exception('duplicate correct_answers variable name: %s' % name)
        data['correct_answers'][name] = correct_answer

def render(element_html, data):
    element = lxml.html.fragment_fromstring(element_html)
    dropdown_options = json.loads(pl.get_string_attrib(element, 'options'))
    answer_key = pl.get_string_attrib(element, 'answer-key')

    html_params = {
        'uuid': pl.get_uuid(),
        'options': dropdown_options,
        'answer-key': answer_key
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

    if data['correct_answers'][name] == None:
        raise Exception('Correct answer not defined for %s' % name)
    
    if data['correct_answers'][name] == answer:
        data['partial_scores'][name] = {'score': 1, 'weight': weight}
    else:
        data['partial_scores'][name] = {'score': 0, 'weight': weight}

    answer = pl.get_string_attrib(element, 'answer')
    data['submitted_answers'][name] = answer


def generate(element_html, data):
    element = lxml.html.fragment_fromstring(element_html)
    answer_key = pl.get_string_attrib(element, 'answer-key')
    data['correct_answers']['species'] = pl.get_string_attrib(element, 'answer')
