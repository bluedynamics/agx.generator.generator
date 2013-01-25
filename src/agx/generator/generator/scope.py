# -*- coding: utf-8 -*-
from zope.component import getUtility
from agx.core.interfaces import IScope
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


registerScope('simplescope', 'uml2fs', None , SimpleScopeScope)


class GeneratorScope(Scope):

    def __call__(self, node):
        return node.stereotype('generator:generator') is not None


registerScope('generator', 'uml2fs', [IClass] , GeneratorScope)


class ScopeScope(Scope):

    def __call__(self, node):
        return node.stereotype('generator:class_scope') is not None or \
            node.stereotype('generator:simple_scope') is not None


registerScope('scope', 'uml2fs', [IClass] , ScopeScope)


class GeneratorDependencyScope(Scope):

    def __call__(self, node):
        if IDependency.providedBy(node):
            genscope = getUtility(IScope, 'uml2fs.generatorstuff')
            if genscope(node.client):
                return True


registerScope('generatordependency', 'uml2fs',
              [IDependency] , GeneratorDependencyScope)


class GeneratorStuffScope(Scope):

    def __call__(self, node):
        return node.stereotype('generator:transform') is not None or\
            node.stereotype('generator:generator') is not None or\
            node.stereotype('generator:simple_scope') is not None or \
            node.stereotype('generator:class_scope') is not None or \
            node.stereotype('generator:handler') is not None


registerScope('generatorstuff', 'uml2fs', [IClass] , GeneratorStuffScope)


class HandlerScope(Scope):

    def __call__(self, node):
        return node.stereotype('generator:handler') is not None


registerScope('handler', 'uml2fs', [IClass] , HandlerScope)


class TransformScope(Scope):

    def __call__(self, node):
        return node.stereotype('generator:transform') is not None


registerScope('transform', 'uml2fs', [IClass] , TransformScope)


class ProfileScope(Scope):

    def __call__(self, node):
        return node.stereotype('generator:profile') is not None


registerScope('profile', 'uml2fs', [IClass] , ProfileScope)
