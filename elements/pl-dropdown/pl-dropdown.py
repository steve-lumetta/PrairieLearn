import prairielearn as pl
import lxml.html
import random
import chevron
from enum import Enum

WEIGHT_DEFAULT = 1
BLANK_ANSWER = ' '
BLANK_DEFAULT = True
SORT_DEFAULT = 'fixed'


class SortTypes(Enum):
    RANDOM = 'random'
    ASCEND = 'ascend'
    DESCEND = 'descend'
    FIXED = 'fixed'


def get_options(element, data, correct_answer):
    options = []
    for child in element:
        if child.tag in ['pl-answer']:
            pl.check_attribs(child, required_attribs=[], optional_attribs=['correct'])
            child_html = pl.inner_html(child).strip()
            options.append(child_html)
    return options


def get_solution(element, data, correct_answer):
    solution = []
    for child in element:
        if child.tag in ['pl-answer']:
            pl.check_attribs(child, required_attribs=[], optional_attribs=['correct'])
            is_correct = pl.get_boolean_attrib(child, 'correct', False)
            child_html = pl.inner_html(child).strip()
            if is_correct:
                solution = child_html
    return solution


def prepare(element_html, data):
    element = lxml.html.fragment_fromstring(element_html)
    pl.check_attribs(element, required_attribs=['answers-name'], optional_attribs=['blank', 'weight', 'sort'])
    answers_name = pl.get_string_attrib(element, 'answers-name')

    # Get answer from pl-answer if implemented
    data['correct_answers'][answers_name] = get_solution(element, data, answers_name)

    # Get answer from server.py if pl-answer not implemented
    if answers_name is None:
        data['correct_answers'][answers_name] = answers_name

    if data['correct_answers'][answers_name] is None:
        raise Exception('Correct answer not defined for answers-name: %s' % answers_name)


def render(element_html, data):
    element = lxml.html.fragment_fromstring(element_html)
    answers_name = pl.get_string_attrib(element, 'answers-name')
    dropdown_options = get_options(element, data, answers_name)

    sort_type = pl.get_string_attrib(element, 'sort', SORT_DEFAULT).upper().strip()
    blank_start = pl.get_boolean_attrib(element, 'blank', BLANK_DEFAULT)

    html_params = {}
    html = ''
    no_answer_selected = False

    if data['panel'] == 'question':
        if sort_type == SortTypes.FIXED.name:
            pass
        elif sort_type == SortTypes.DESCEND.name:
            dropdown_options.sort(reverse=True)
        elif sort_type == SortTypes.ASCEND.name:
            dropdown_options.sort(reverse=False)
        elif sort_type == SortTypes.RANDOM.name:
            random.shuffle(dropdown_options)

        if blank_start:
            dropdown_options.insert(0, BLANK_ANSWER)

        html_params = {
            'question': True,
            'uuid': pl.get_uuid(),
            'options': dropdown_options,
            'answers-name': answers_name
        }
    elif data['panel'] == 'submission':
        submitted_answer = data['submitted_answers'].get(answers_name, None)
        if submitted_answer == BLANK_ANSWER:
            no_answer_selected = True

        html_params = {
            'submission': True,
            'no-answer-selected': no_answer_selected,
            'submitted-answer': submitted_answer,
            'answers-name': answers_name
        }
    elif data['panel'] == 'answer':
        answers_name = pl.get_string_attrib(element, 'answers-name')
        submitted_answer = data['submitted_answers'].get(answers_name, None)
        if submitted_answer == BLANK_ANSWER:
            no_answer_selected = True

        html_params = {
            'answer': True,
            'submitted-answer': submitted_answer,
            'no-answer-selected': no_answer_selected,
            'correct-answer': data['correct_answers'][answers_name],
            'correct': data['correct_answers'][answers_name] == submitted_answer
        }

    with open('pl-dropdown.mustache', 'r', encoding='utf-8') as f:
        html = chevron.render(f, html_params).strip()
    return html


def parse(element_html, data):
    element = lxml.html.fragment_fromstring(element_html)
    answers_name = pl.get_string_attrib(element, 'answers-name')
    answer = data['submitted_answers'].get(answers_name, None)

    # We want a space to be a valid option in case 'blank' start is desired
    valid_options = [' ']

    for child in element:
        if child.tag in ['pl-answer']:
            pl.check_attribs(child, required_attribs=[], optional_attribs=['correct'])
            child_html = pl.inner_html(child).strip()
            valid_options.append(child_html)

    if answer is None:
        data['format_errors'][answers_name] = 'No answer was submitted.'

    if answer not in valid_options:
        data['format_errors'][answers_name] = 'Invalid answer submitted.'


def grade(element_html, data):
    element = lxml.html.fragment_fromstring(element_html)
    answers_name = pl.get_string_attrib(element, 'answers-name')
    weight = pl.get_integer_attrib(element, 'weight', WEIGHT_DEFAULT)
    submitted_answer = data['submitted_answers'].get(answers_name, None)

    if data['correct_answers'][answers_name] == submitted_answer:
        data['partial_scores'][answers_name] = {'score': 1, 'weight': weight}
    else:
        data['partial_scores'][answers_name] = {'score': 0, 'weight': weight}


def test(element_html, data):
    element = lxml.html.fragment_fromstring(element_html)
    answers_name = pl.get_string_attrib(element, 'answers-name')
    weight = pl.get_integer_attrib(element, 'weight', WEIGHT_DEFAULT)

    # solution is what the answer should be
    solution = get_solution(element, data, answers_name)

    # incorrect and correct answer test cases
    if data['test_type'] == 'correct':
        data['raw_submitted_answers'][answers_name] = solution
        data['partial_scores'][answers_name] = {'score': 1, 'weight': weight}
    elif data['test_type'] == 'incorrect':
        dropdown_options = get_options(element, data, answers_name)
        incorrect_ans = ''

        for option in dropdown_options:
            if option != solution:
                incorrect_ans = option

        data['raw_submitted_answers'][answers_name] = incorrect_ans
        data['partial_scores'][answers_name] = {'score': 0, 'weight': weight}
    elif data['test_type'] == 'invalid':
        # Test for invalid drop-down options in case injection on front-end
        data['raw_submitted_answers'][answers_name] = 'INVALID STRING'
        data['format_errors'][answers_name] = 'format error message'
    else:
        raise Exception('invalid result: %s' % data['test_type'])
