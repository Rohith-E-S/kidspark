from django import template

from assessments import palette

register = template.Library()


@register.filter
def cat_color(code):
    """Solid hex colour for a category code."""
    return palette.category_color(code)


@register.filter
def cat_tint(code):
    """12% tint of the category colour, for soft backgrounds."""
    return palette.category_tint(code)


@register.filter
def cat_tint_strong(code):
    """28% tint, for borders and chips."""
    return palette.category_tint(code, 0.28)


@register.filter
def cat_icon(code):
    """Lucide icon name for a category code."""
    return palette.category_icon(code)


@register.filter
def percent_of(value, total):
    """Round percentage of value against total, guarded against zero."""
    try:
        value, total = float(value), float(total)
    except (TypeError, ValueError):
        return 0
    if not total:
        return 0
    return round((value / total) * 100)
