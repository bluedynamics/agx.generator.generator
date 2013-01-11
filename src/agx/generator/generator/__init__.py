# -*- coding: utf-8 -*-
import generator
import scope

def register():
    """Register this generator.
    """
    import agx.generator.generator
    from agx.core.config import register_generator
    register_generator(agx.generator.generator)