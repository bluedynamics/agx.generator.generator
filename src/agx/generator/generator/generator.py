# -*- coding: utf-8 -*-
from agx.core import (
    handler,
    Scope,
    registerScope,
    token
)
from agx.core.util import (
    read_target_node,
    dotted_path,
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
from agx.core import (
    handler,
    Scope,
    registerScope,
    token
)

@handler('generatescopeclass', 'uml2fs', 'connectorgenerator',
         'scopeclass', order=9)
def generatescopeclass(self, source, target):
    '''preparation for joined table inheritance base class
    '''
    targetclass = read_target_node(source, target.target)
    
    module = targetclass.parent
    methods = [att for att in targetclass.filtereditems(IOperation)]
    import pdb;pdb.set_trace()