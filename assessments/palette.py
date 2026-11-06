"""Single source of truth for the 8 dimension colours and icons.

The palette doubles as the data palette: the same colour marks a category in
the radar chart, the dimension cards and the quiz badge, so a child (and a
parent) can follow one dimension from start to report. Icons are Lucide icon
names and are rendered by ``lucide.createIcons()`` in the browser.
"""

CATEGORY_COLORS = {
    'LOGICAL': '#4F5BD5',   # indigo
    'VERBAL': '#E8567C',    # rose
    'SPATIAL': '#1FA8A0',   # teal
    'CRITICAL': '#F0A03C',  # amber
    'STEM': '#2E9E5B',      # green
    'ARTS': '#C05BD8',      # orchid
    'NATURE': '#7BA82A',    # olive
    'SOCIAL': '#F0764C',    # coral
}

CATEGORY_ICONS = {
    'LOGICAL': 'puzzle',
    'VERBAL': 'book-open',
    'SPATIAL': 'shapes',
    'CRITICAL': 'lightbulb',
    'STEM': 'flask-conical',
    'ARTS': 'palette',
    'NATURE': 'leaf',
    'SOCIAL': 'users',
}

DEFAULT_COLOR = '#5B4BE8'
DEFAULT_ICON = 'sparkles'

# The eight dimensions in ring order, used by the landing page's spark dial.
# Order matters: it reads left-to-right, top-to-bottom around the ring.
DIMENSIONS = [
    ('LOGICAL', 'Logical', 'APTITUDE'),
    ('VERBAL', 'Verbal', 'APTITUDE'),
    ('SPATIAL', 'Spatial', 'APTITUDE'),
    ('CRITICAL', 'Critical', 'APTITUDE'),
    ('STEM', 'STEM', 'INTEREST'),
    ('ARTS', 'Arts', 'INTEREST'),
    ('NATURE', 'Nature', 'INTEREST'),
    ('SOCIAL', 'Social', 'INTEREST'),
]


def category_color(code):
    return CATEGORY_COLORS.get(code, DEFAULT_COLOR)


def category_tint(code, alpha=0.12):
    color = category_color(code).lstrip('#')
    r, g, b = (int(color[i:i + 2], 16) for i in (0, 2, 4))
    return f'rgba({r}, {g}, {b}, {alpha})'


def category_icon(code):
    return CATEGORY_ICONS.get(code, DEFAULT_ICON)


# Interest bars use the same colours as the dimension cards.
INTEREST_COLORS = [CATEGORY_COLORS[c] for c in ['STEM', 'ARTS', 'NATURE', 'SOCIAL']]
APTITUDE_COLORS = [CATEGORY_COLORS[c] for c in ['LOGICAL', 'VERBAL', 'SPATIAL', 'CRITICAL']]
