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

class ClassScopeScope(Scope):

    def __call__(self, node):
        return node.stereotype('generator:class_scope') is not None

registerScope('classscope', 'uml2fs', [IClass] , ClassScopeScope)

class SimpleScopeScope(Scope):

    def __call__(self, node):
        return node.stereotype('generator:simple_scope') is not None

registerScope('simplescope', 'uml2fs', [IClass] , SimpleScopeScope)

class GeneratorScope(Scope):

    def __call__(self, scope):
        return node.stereotype('generator:generator') is not None

class ScopeScope(Scope):

    def __call__(self, scope):
        return node.stereotype('generator:class_scope') is not None or \
            node.stereotype('generator:simple_scope') is not None