# coding: utf-8

'''
List helper functions.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Optional, Any, Callable, List
from collections.abc import Sequence


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

def flatten(*args: Any,
            function: Optional[Callable[[Any], Any]] = None) -> List[Any]:
    '''
    Flattens the list of `args` down.

    If `function` is not None, call it with each list element after it is
    determined to be 'flat', and replace that element with the returned value.
    If the `function` returned element itself needs flattening, will continue
    with list flattening using it (so don't do anything infinite...).

    Examples:
      flatten([1, [2, 3]])
        -> [1, 2, 3]
      flatten([1, [2, 3]], my_add_one_fn)
        -> [2, 3, 4]
    '''
    # (Shallow) copy the list; we'll be flattening it as we go.
    flattening = list(args)
    # Loop over the list and flatten as we go.
    i = 0
    while i < len(flattening):
        # Loop over element if it's a sub-list.
        while _needs_flattening(flattening[i]):
            # Nothing in this sub-list? Get rid of it.
            if not flattening[i]:
                i = _pop_flatten(flattening, i)

            # Something in the sub-list: stitch it into primary list,
            # flattening one level.
            # Example:        v-----(i=2)-----v
            #    list: [1, 2, [3, [...m], ...n], ...o]
            #      ->  [1, 2, 3, [...m], ...n, ...o]
            else:
                flattening[i:i + 1] = flattening[i]

        # Dropped out of our sub-list-stitching, or this element doesn't need
        # flattening... Either way - we're (almost) done.

        # First: Check for our result filtering function first, and possibly
        # loop back into flattening the result we got...
        if function:
            # Generate element from current list index item.
            element = function(flattening[i])
            flattening[i] = element

            # Sanity checks...
            if isinstance(element, Sequence):
                # We got an empty list back; pop this index.
                if not element:
                    i = _pop_flatten(flattening, i)

                # We got a list with just one element... deal with it here to
                # remove the infinite loop.
                elif len(element) == 1:
                    # Replace it with its actual element.
                    element = element[0]
                    flattening[i] = element

            # Is the generated element something that should be flattened?
            if _needs_flattening(element):
                continue

        # Done with this element; increment so we can check next.
        i += 1

    # Done walking the list. It is flat.
    return flattening


def _pop_flatten(flattening: List[Any], index: int) -> int:
    '''
    Remove current index from the list and return the index to continue from.
    '''
    flattening.pop(index)
    return index - 1


def _needs_flattening(element: Any) -> bool:
    '''
    Returns True if element is a kind of element that (still) neeeds
    flattening.
    '''
    return (not isinstance(element, (str, bytes))
            and isinstance(element, Sequence))
