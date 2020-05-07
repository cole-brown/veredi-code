# coding: utf-8

'''
Dictionary/Thesaurus for D20 terms.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Python
import enum

# Framework

# Our Stuff


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# TODO: Move into some yaml file that gets parsed into these enum objects?
# TODO: with their charts and values?
#   - e.g. for size: https://www.d20pfsrd.com/gamemastering/combat/space-reach-threatened-area-templates/

class ability(enum.Enum):
    # ability.strength.value -> "strength"
    strength     = "strength"
    dexterity    = "dexterity"
    constitution = "constitution"
    intelligence = "intelligence"
    wisdom       = "wisdom"
    charisma     = "charisma"
    # short-hand
    str          = strength
    dex          = dexterity
    con          = constitution
    int          = intelligence
    wis          = wisdom
    cha          = charisma

    def __str__(self):
        return f"{self.__class__.__name__}.{self.value}"

class size(enum.Enum):
    fine            = "Fine"
    diminutive      = "Diminutive"
    tiny            = "Tiny"
    small           = "Small"
    medium          = "Medium"
    large_tall      = "Large (tall)"
    large_long      = "Large (long)"
    huge_tall       = "Huge (tall)"
    huge_long       = "Huge (long)"
    gargantuan_tall = "Gargantuan (tall)"
    gargantuan_long = "Gargantuan (long)"
    colossal_tall   = "Colossal (tall)"
    colossal_long   = "Colossal (long)"

@enum.unique
class speed(enum.Enum):
    land  = "land"
    run   = "run"
    swim  = "swim"
    climb = "climb"
    fly   = "fly"

@enum.unique
class hitpoints(enum.Enum):
    total  = "total"
    damage = "damage"

@enum.unique
class damage(enum.Enum):
    lethal    = "lethal"
    nonlethal = "nonlethal"

class defense(enum.Enum):
    armor_class       = "Armor Class"
    ac                = armor_class
    saves             = "saves"
    combat_maneuver   = "combat-maneuver"
    cmd               = combat_maneuver
    damage_reduction  = "damage-reduction"
    dr                = damage_reduction
    energy_resistance = "energy-resistance"
    er                = energy_resistance
    resistance        = energy_resistance
    spell_resistance  = "spell-resistance"
    sr                = spell_resistance
    immunity          = "immunity"
    weakness          = "weakness"

class armor_class(enum.Enum):
    base        = "base"
    touch       = "touch"
    normal      = "normal"
    flat_footed = "flat-footed"

class saves(enum.Enum):
    fortitude = "fortitude"
    reflex    = "reflex"
    will      = "will"

class combat_maneuver(enum.Enum):
    base        = "base"
    normal      = "normal"
    flat_footed = "flat-footed"

class damage_reduction(enum.Enum):
      physical = "physical"
      energy   = "energy"

class energy(enum.Enum):
    all  = "all"
    fire = "fire"
    acid = "acid"
    # etc...

class attack(enum.Enum):
    base            = "base"
    bab             = base
    melee           = "melee"
    ranged          = "ranged"
    combat_maneuver = "combat-maneuver"
    cmb             = combat_maneuver
    initiative      = "initiative"
    init            = initiative

@enum.unique
class skill(enum.Enum):
    acrobatics       = "acrobatics"
    appraise         = "appraise"
    bluff            = "bluff"
    climb            = "climb"
    craft            = "craft"
    diplomacy        = "diplomacy"
    disable_device   = "disable-device"
    disguise         = "disguise"
    escape_artist    = "escape-artist"
    fly              = "fly"
    handle_animal    = "handle-animal"
    heal             = "heal"
    intimidate       = "intimidate"
    knowledge        = "knowledge"
    linguistics      = "linguistics"
    perception       = "perception"
    perform          = "perform"
    profession       = "profession"
    ride             = "ride"
    sense_motive     = "sense-motive"
    sleight_of_hand  = "sleight-of-hand"
    spellcraft       = "spellcraft"
    stealth          = "stealth"
    survival         = "survival"
    swim             = "swim"
    use_magic_device = "use-magic-device"


priority = [
    ability,
    hitpoints,
    saves,
    skill,

    armor_class,
    attack,
    defense,
    damage_reduction,
    combat_maneuver,
    damage,
    energy,
    speed,
    size,
]


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------
