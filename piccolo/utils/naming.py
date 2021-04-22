import re

_camel_words = re.compile(r"([A-Z][a-z0-9_]+)")


def _camel_to_snake(s):
    """ Convert CamelCase to snake_case.
    """
    return "_".join(
        [
            i.lower() for i in _camel_words.split(s)[1::2]
        ]
    )
