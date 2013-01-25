# -*- coding: utf-8 -*-
import generator
import scope


def register():
    """register this generator.
    """
    import agx.generator.generator
    from agx.core.config import register_generator
    register_generator(agx.generator.generator)
