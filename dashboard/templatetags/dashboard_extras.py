from django import template


register = template.Library()


@register.filter
def field_by_name(form, name):
    """Return a bound form field by its name."""

    return form[name]

