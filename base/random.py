# coding: utf-8

'''
A random interface that can be un-randomed for unit testing.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Python
import random as _random
import os as _os

# Framework

# Our Stuff


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------

class Random(_random.Random):
    '''Default Actually Random Randomness'''
    ...


class NotRandom(Random):
    '''Not-Random-at-All Randomness'''

    def __init__(self, num_gen=None, seeding=None):
        super().__init__(seeding)
        self.generator = (num_gen
                          if num_gen else
                          self.int_gen)

    def randint(self, a, b):
        return self.generator()

    def int_gen(self):
        index = 0
        ints = [1, 2, 3, 4, 5, 6]
        length = len(ints)
        while True:
            yield ints[index % length]
            index += 1


# -----------------------------------------------------------------------------
# Singleton Setup
# -----------------------------------------------------------------------------

# These will share state, but that's how Python's random module works.

_inst = Random()
seed = _inst.seed
random = _inst.random
uniform = _inst.uniform
triangular = _inst.triangular
randint = _inst.randint
choice = _inst.choice
randrange = _inst.randrange
sample = _inst.sample
shuffle = _inst.shuffle
choices = _inst.choices
normalvariate = _inst.normalvariate
lognormvariate = _inst.lognormvariate
expovariate = _inst.expovariate
vonmisesvariate = _inst.vonmisesvariate
gammavariate = _inst.gammavariate
gauss = _inst.gauss
betavariate = _inst.betavariate
paretovariate = _inst.paretovariate
weibullvariate = _inst.weibullvariate
getstate = _inst.getstate
setstate = _inst.setstate
getrandbits = _inst.getrandbits


# Have forks get their own seeds.
if hasattr(_os, "fork"):
    _os.register_at_fork(after_in_child=_inst.seed)


def singleton(instance):
    global seed, random, uniform, triangular, randint, choice, randrange
    global sample, shuffle, choices, normalvariate, lognormvariate
    global expovariate, vonmisesvariate, gammavariate, gauss, betavariate
    global paretovariate, weibullvariate, getstate, setstate, getrandbits

    _inst = instance
    seed = _inst.seed
    random = _inst.random
    uniform = _inst.uniform
    triangular = _inst.triangular
    randint = _inst.randint
    choice = _inst.choice
    randrange = _inst.randrange
    sample = _inst.sample
    shuffle = _inst.shuffle
    choices = _inst.choices
    normalvariate = _inst.normalvariate
    lognormvariate = _inst.lognormvariate
    expovariate = _inst.expovariate
    vonmisesvariate = _inst.vonmisesvariate
    gammavariate = _inst.gammavariate
    gauss = _inst.gauss
    betavariate = _inst.betavariate
    paretovariate = _inst.paretovariate
    weibullvariate = _inst.weibullvariate
    getstate = _inst.getstate
    setstate = _inst.setstate
    getrandbits = _inst.getrandbits
