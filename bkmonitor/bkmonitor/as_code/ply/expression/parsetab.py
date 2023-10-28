# parsetab.py
# This file is automatically generated. Do not edit.
# pylint: disable=W,C,R
_tabversion = '3.10'

_lr_method = 'LALR'

_lr_signature = 'FLOAT LEFT_PARENTHESES NAME OPERATOR RIGHT_PARENTHESES\n    expression : expression OPERATOR expression\n               | LEFT_PARENTHESES expression RIGHT_PARENTHESES\n               | FLOAT\n               | NAME\n    '

_lr_action_items = {
    'LEFT_PARENTHESES': (
        [
            0,
            2,
            5,
        ],
        [
            2,
            2,
            2,
        ],
    ),
    'FLOAT': (
        [
            0,
            2,
            5,
        ],
        [
            3,
            3,
            3,
        ],
    ),
    'NAME': (
        [
            0,
            2,
            5,
        ],
        [
            4,
            4,
            4,
        ],
    ),
    '$end': (
        [
            1,
            3,
            4,
            7,
            8,
        ],
        [
            0,
            -3,
            -4,
            -1,
            -2,
        ],
    ),
    'OPERATOR': (
        [
            1,
            3,
            4,
            6,
            7,
            8,
        ],
        [
            5,
            -3,
            -4,
            5,
            5,
            -2,
        ],
    ),
    'RIGHT_PARENTHESES': (
        [
            3,
            4,
            6,
            7,
            8,
        ],
        [
            -3,
            -4,
            8,
            -1,
            -2,
        ],
    ),
}

_lr_action = {}
for _k, _v in _lr_action_items.items():
    for _x, _y in zip(_v[0], _v[1]):
        if not _x in _lr_action:
            _lr_action[_x] = {}
        _lr_action[_x][_k] = _y
del _lr_action_items

_lr_goto_items = {
    'expression': (
        [
            0,
            2,
            5,
        ],
        [
            1,
            6,
            7,
        ],
    ),
}

_lr_goto = {}
for _k, _v in _lr_goto_items.items():
    for _x, _y in zip(_v[0], _v[1]):
        if not _x in _lr_goto:
            _lr_goto[_x] = {}
        _lr_goto[_x][_k] = _y
del _lr_goto_items
_lr_productions = [
    ("S' -> expression", "S'", 1, None, None, None),
    ('expression -> expression OPERATOR expression', 'expression', 3, 'p_expression', '__init__.py', 35),
    ('expression -> LEFT_PARENTHESES expression RIGHT_PARENTHESES', 'expression', 3, 'p_expression', '__init__.py', 36),
    ('expression -> FLOAT', 'expression', 1, 'p_expression', '__init__.py', 37),
    ('expression -> NAME', 'expression', 1, 'p_expression', '__init__.py', 38),
]