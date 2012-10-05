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
from node.ext.uml.utils import TaggedValues
from node.ext.python import (
    Function,
    Block,
)
from agx.core import (
    handler,
    Scope,
    registerScope,
    token
)

@handler('generatescopeclass', 'uml2fs', 'connectorgenerator',
         'classscope', order=9)
def generatescopeclass(self, source, target):
    '''preparation for joined table inheritance base class
    '''
    targetclass = read_target_node(source, target.target)
    
    module = targetclass.parent
    methods = [m for m in targetclass.functions()]
    methnames=[m.functionname for m in methods]
    methname='__call__'
    tgv=TaggedValues(source)
    stereotype=tgv.direct('stereotype','generator:class_scope',None) or\
        tgv.direct('stereotype','generator:simple_scope',None)
    transform=tgv.direct('transform','generator:class_scope',None) or\
        tgv.direct('transform','generator:simple_scope',None) or \
        'uml2fs'
        
    if not stereotype:
        raise ValueError,'scope %s must have a stereotype attribute!!' % source.name
        
    if 'Scope' not in targetclass.bases:
        targetclass.bases.append('Scope')
        
    if methname not in methnames:
        f=Function()
        f.functionname=methname
        f.args=['self','scope']
        f.__name__=str(f.uuid)
        targetclass.insertfirst(f)
        
        bl=Block()
        bl.__name__=str(bl.uuid)
        bl.lines.append("return node.stereotype('%s') is not None" % stereotype)
        
        f.insertfirst(bl)
        import pdb;pdb.set_trace()