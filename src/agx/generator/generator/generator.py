# -*- coding: utf-8 -*-
from zope.component.interfaces import ComponentLookupError
from zope.component import getUtility
from odict import odict
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
from agx.core.interfaces import IScope
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
    Decorator,
)
from node.ext.python.utils import Imports
from agx.core import (
    handler,
    Scope,
    registerScope,
    token
)

@handler('generatescopeclass', 'uml2fs', 'connectorgenerator', 'classscope',
         order=9)
def generatescopeclass(self, source, target):
    '''generates scope classes
    '''
    targetclass = read_target_node(source, target.target)
    module = targetclass.parent
    
    module = targetclass.parent
    methods = [m for m in targetclass.functions()]
    methnames = [m.functionname for m in methods]
    methname = '__call__'
    tgv = TaggedValues(source)
    stereotypes = tgv.direct('stereotypes', 'generator:class_scope', None) or\
        tgv.direct('stereotypes', 'generator:simple_scope', None) or []
    transform = tgv.direct('transform', 'generator:class_scope', None) or\
        tgv.direct('transform', 'generator:simple_scope', None) or \
        'uml2fs'
    
    #if not stereotypes:
    #    raise ValueError,'scope %s must have a stereotype attribute!!' % source.name
    
    if 'Scope' not in targetclass.bases:
        targetclass.bases.append('Scope')
    
    if methname not in methnames:
        f = Function()
        f.functionname = methname
        f.args = ['self', 'node']
        f.__name__ = str(f.uuid)
        targetclass.insertfirst(f)
    
        bl = Block()
        bl.__name__ = str(bl.uuid)
        conds = ["node.stereotype('%s') is not None" % st for st in stereotypes]
        cond = ' or '.join(conds)
        bl.lines.append("return %s" % cond)
    
        f.insertfirst(bl)

@handler('generatescopereg', 'uml2fs', 'semanticsgenerator', 'scope', order=15)
def generatescopereg(self, source, target):
    targetclass = read_target_node(source, target.target)
    module = targetclass.parent
    blocks = module.blocks()
    
    tgv = TaggedValues(source)
    
    transform = tgv.direct('transform', 'generator:class_scope', None) or\
        tgv.direct('transform', 'generator:simple_scope', None) or \
        'uml2fs'
    
    interfaces = tgv.direct('interfaces', 'generator:class_scope', None) or\
        tgv.direct('interfaces', 'generator:simple_scope', None)
    
    scopename = tgv.direct('scopename', 'generator:class_scope', None) or\
        tgv.direct('scopename', 'generator:simple_scope', None) or \
        source.name.lower()
    
    #do some common imports
    imps = Imports(module)
    imps.set('node.ext.uml.interfaces', [
        ['IOperation', None],
        ['IClass', None],
        ['IPackage', None],
        ['IInterface', None],
        ['IInterfaceRealization', None],
        ['IDependency', None],
        ['IProperty', None],
        ['IAssociation', None],
    ])
    
    imps.set('agx.core', [
        ['handler', None],
        ['scope', None],
        ['registerScope', None],
        ['token', None],
    ])
    
    
    #make the register statement
    if interfaces:
        ifstring = "[%s]" % ','.join(interfaces)
    else:
        ifstring = None
    
    if source.stereotype('generator:class_scope'):
        classname = source.name
    else:
        classname = 'Scope'
    
    reg = "registerScope('%s', '%s', %s , %s)" % \
        (scopename, transform, ifstring, classname)
    
    #look if the reg stmt already exists
    regsearch = "registerScope('%s'" % scopename
    blockfound = None
    for b in blocks:
        for i in range(len(b.lines)):
            lcode = b.lines[i].strip().replace(' ', '')
            if lcode.startswith(regsearch):
                #replace the line
                b.lines[i] = reg
                return
    
    #else make a new block after the class declaration    
    bl = Block()
    bl.__name__ = str(bl.uuid)
    bl.lines.append(reg)
    classes = [c for c in module.classes() if c.classname == source.name]
    if classes:
        klass = classes[0]
        module.insertafter(bl, klass)
    else:
        module.insertlast(bl)

@handler('block_simple_scopes', 'uml2fs', 'hierarchygenerator', 'simplescope',
         order=25)
def block_simple_scopes(self, source, target):
    """prevent simple_scopes from being generated as class.
    """
    if source.stereotype('generator:simple_scope'):
        token(str(source.uuid), True, dont_generate=True).dont_generate = True

@handler('purgeclasses', 'uml2fs', 'zzcleanupgenerator', 'pyclass', order=255)
def purgeclasses(self, source, target):
    '''remove the classes that should not be generated, should run quite in the end
    XXX this one sould belong to pyegg in a final generator, but there
    needs to be done some work on sorting generators first
    '''
    klass = read_target_node(source, target.target)
    if not klass:
        return
    module = klass.parent
    
    try:
        tok = token(str(source.uuid), False, dont_generate=False)
    except ComponentLookupError: #no tok with flag found, so ignore
        return
    if tok.dont_generate:
        module.detach(klass.__name__)
    
        #remove the imports
        init = module.parent['__init__.py']
        imps = init.imports()
        impname = [klass.classname, None]
        for imp in imps:
            if impname in imp.names:
                if len(imp.names) > 1:
                    #if more names are in the imp delete the name
                    imp.names = [n for n in imp.names if n != impname]
                else:
                    #delete the whole import
                    init.detach(imp.__name__)

@handler('collect_dependencies', 'uml2fs', 'hierarchygenerator',
         'generatordependency', order=15)
def collect_dependencies(self, source, target):
    handlerscope = getUtility(IScope, 'uml2fs.handler')
    scopescope = getUtility(IScope, 'uml2fs.scope')
    generatorscope = getUtility(IScope, 'uml2fs.generator')
    
    deps = token(str(source.uuid), True, genDeps=odict())
    if handlerscope(source.client):
        if scopescope(source.supplier):
            token(str(source.client.uuid), True, scopes=[]).scopes.append(source.supplier)
        if handlerscope(source.supplier):
            token(str(source.client.uuid), True, depends_on=[]).depends_on.append(source.supplier)
        if generatorscope(source.supplier):
            token(str(source.client.uuid), True, generators=[]).generators.append(source.supplier)

@handler('mark_handler_as_function', 'uml2fs', 'hierarchygenerator', 'handler',
         order=15)
def mark_handler_as_function(self, source, target):
    token(str(source.uuid), True, is_function=True)

@handler('finalize_handler', 'uml2fs', 'gen_connectorgenerator', 'handler',
         order=15)
def finalize_handler(self, source, target):
    func = read_target_node(source, target.target)
    tok = token(str(source.uuid), True, scopes=[], generators=[])
    tgv = TaggedValues(source)
    order = tgv.direct('order', 'generator:handler', None)
    func.args = ['self', 'source', 'target']
    
    
    #...or by dependency on a generator
    if tok.generators:
        generatornames = [g.name for g in tok.generators]
    else:
        #the generator can be defined by tgv
        generatornames = [tgv.direct('generator', 'generator:handler', None)]
    
    
    for scope in tok.scopes:
        stgv = TaggedValues(scope)
    
        scopename = stgv.direct('scopename', 'generator:class_scope') or \
           stgv.direct('scopename', 'generator:class_scope') or \
           scope.name
    
        transform = stgv.direct('transform', 'generator:class_scope', None) or \
           stgv.direct('transform', 'generator:class_scope', None) or \
           'uml2fs'
    
        transformarg = "'%s'" % transform
        scopenamearg = "'%s'" % scopename
        decfound = None
    
        for generatorname in generatornames:
            generatornamearg = "'%s'" % generatorname
            #find the dec
            for dec in func.decorators():
                if dec.args[1] == transformarg and dec.args[2] == generatornamearg\
                 and dec.args[3] == scopenamearg:
                    decfound = dec
            if decfound:
                dec = decfound
            else:# if not found make it
                dec = Decorator()
                dec.decoratorname = 'handler'
                dec.__name__ = dec.uuid
                func.insertfirst(dec)
    
            #define the args for the generator
            dec.args = ["'%s'" % source.name, transformarg, generatornamearg, scopenamearg]
            if not order is None:
                dec.kwargs['order'] = order

@handler('make_generators', 'uml2fs', 'connectorgenerator', 'generator')
def make_generators(self, source, target):
    pass

@handler('mark_generators_as_stub', 'uml2fs', 'hierarchygenerator', 'pyclass',
         order=10)
def mark_generators_as_stub(self, source, target):
    isgenerator=getUtility(IScope,'uml2fs.generator')
    if not isgenerator(source):
        return
    token('custom_handled_classes',True,classes=[]).classes.append(source)