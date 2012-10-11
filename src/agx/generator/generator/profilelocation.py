# -*- coding: utf-8 -*-
from zope.interface import implements
from agx.core.interfaces import IProfileLocation
import agx.generator.generator

class ProfileLocation(object):

    implements(IProfileLocation)

    name = u'generator.profile.uml'
    package = agx.generator.generator