# coding: utf-8

'''
Easy way to import Encodable sub-classes in order to register and provide
them for the running client or server or whatever.
'''

# TODO [2020-11-12]: Better way to do this?
# On server, can register as part of game start up sequence...
# But client we don't have defined yet, really.

# And ideally they'd use the same code.

# Can we use importlib or anything to do this automatically-ish but
# with minimal magic?
# https://docs.python.org/3/library/importlib.html


# -----------------------------------------------------------------------------
# Search for:
# -----------------------------------------------------------------------------

# ------------------------------
# Encodable
# ------------------------------

# class.*\(.*Encodable - for direct subclasses

# ------------------------------
# Subclasses
# ------------------------------

# FlagEncode.*Mixin - for encoded enums

# class.*\(.*MonotonicId
# class.*\(.*SerializableId

# class.*\(.*Address
# class.*\(.*Envelope

# class.*\(.*Recipient
# class.*\(.*OutputEvent

# class.*\(.*MsgType

# class.*\(.*Message
# class.*\(.*Message.SpecialId
# class.*\(.*ConnectionMessage

# class.*\(.*Validity
# class.*\(.*BasePayload

# class.*\(.*LogField
# class.*\(.*LogReply
# class.*\(.*LogPayload


# class.*\(.*MathOutputEvent

# class.*\(.*NodeType
# class.*\(.*MathTree

# class.*\(.*Node
# class.*\(.*Leaf
# class.*\(.*Dice
# class.*\(.*Constant
# class.*\(.*Variable
# class.*\(.*Branch
# class.*\(.*OperatorMath
# class.*\(.*OperatorAdd
# class.*\(.*OperatorSub
# class.*\(.*OperatorMult
# class.*\(.*OperatorDiv
# class.*\(.*OperatorMod
# class.*\(.*OperatorPow

# class.*\(.*Action

# class.*\(.*Context

# class.*\(.*Subject



# Subclasses of... anything else added in here.


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

# Sort by depth & alphabetically, please.

# ------------------------------
# Base
# ------------------------------

# FlagEncodeNameMixin, FlagEncodeValueMixin
import veredi.base.enum

# MonotonicId, SerializableId
import veredi.base.identity


# ------------------------------
# Data
# ------------------------------
# ---
# Codec
# ---
# # Just for CodecInput NewType.
# import veredi.data.codec.base

# # Encodable itself - don't import.
# import veredi.data.codec.encodable

# # Just an isinstance().
# import veredi.data.codec.json.codec

# UserId - subclass of SerializableId
# UserKey - subclass of SerializableId
import veredi.data.identity




# ------------------------------
# Game
# ------------------------------
# ---
# ECS
# ---
# ComponentId - subclass of MonotonicId
# EntityId - subclass of MonotonicId
# SystemId - subclass of MonotonicId
import veredi.game.ecs.base.identity


# ------------------------------
# Interface
# ------------------------------
# InputId - subclass of SerializableId
import veredi.interface.input.identity

# MsgType - subclass of FlagEncodeValueMixin
import veredi.interface.mediator.const

# Message - subclass of Encodable
# Message.SpecialId - subclass of FlagEncodeValueMixin
# ConnectionMessage - subclass of Message, subclass of Encodable
import veredi.interface.mediator.message

# Validity - subclass of FlagEncodeValueMixin
# BasePayload - subclass of Encodable
import veredi.interface.mediator.payload.base

# LogField - subclass of FlagEncodeNameMixin
# LogReply - subclass of Encodable
# LogPayload - subclass of Encodable
import veredi.interface.mediator.payload.logging

# # Just for EncodableRegistry
# import veredi.interface.mediator.websocket.mediator

# Address - subclass of Encodable
# Envelope - subclass of Encodable
import veredi.interface.output.envelope

# Recipient - subclass of FlagEncodeValueMixin
# OutputEvent - subclass of Encodable
import veredi.interface.output.event


# ------------------------------
# Math
# ------------------------------
# MathOutputEvent - subclass of OutputEvent, subclass of Encodable
import veredi.math.event

# NodeType - subclass of FlagEncodeNameMixin
# MathTree - subclass of Encodable
import veredi.math.parser

# Node - subclass of MathTree
#   Leaf - subclass of Node
#     Dice - subclass of Leaf
#     Constant - subclass of Leaf
#     Variable - subclass of Leaf
#   Branch - subclass of Node
#     OperatorMath - subclass of Branch
#       OperatorAdd - subclass of OperatorMath
#       OperatorSub - subclass of OperatorMath
#       OperatorMult - subclass of OperatorMath
#       OperatorDiv - subclass of OperatorMath
#       OperatorMod - subclass of OperatorMath
#       OperatorPow - subclass of OperatorMath
import veredi.math.d20.tree


# ------------------------------
# Security
# ------------------------------
# Action - subclass of FlagEncodeNameMixin
import veredi.security.abac.attributes.action

# Context - subclass of FlagEncodeNameMixin
import veredi.security.abac.attributes.context

# Subject - subclass of FlagEncodeNameMixin
import veredi.security.abac.attributes.subject

# PolicyId - subclass of SerializableId
import veredi.security.abac.identity

# # make() - Type Hinting
# import veredi.security.abac.resource.name


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Code
# -----------------------------------------------------------------------------
