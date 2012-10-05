# -*- coding: utf-8 -*-
from agx.core import (
    handler,
    Scope,
    registerScope,
    token
)
from node.ext.uml.interfaces import (
    IOperation,
    IClass,
    IPackage,
    IInterface,
    IInterfaceRealization,
    IDependency,
    IProperty,
    IAssociation,
)

class ScopeClassScope(Scope):

    def __call__(self, node):
        return node.stereotype('generator:scope_class') is not None

registerScope('scopeclass', 'uml2fs', [IClass] , ScopeClassScope)

class SimpleScopeScope(Scope):

    def __call__(self, node):
        return node.stereotype('generator:simple_scope') is not None

registerScope('simplescope', 'uml2fs', [IClass] , SimpleScopeScope)

class GeneratorScope(object):
    pass