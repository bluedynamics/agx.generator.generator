# -*- coding: utf-8 -*-
from zope.interface import implementer
from agx.core.interfaces import IProfileLocation
import agx.generator.generator


@implementer(IProfileLocation)
class ProfileLocation(object):
    name = u'generator.profile.uml'
    package = agx.generator.generator
