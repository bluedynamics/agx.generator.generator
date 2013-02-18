# -*- coding: utf-8 -*-
import os
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
from node.ext.directory import (
    File,
    Directory,
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
    Decorator,
    Attribute,
)
from node.ext.python.utils import Imports
from agx.generator.pyegg.utils import (
    egg_source,
    implicit_dotted_path,
)
from agx.generator.zca.utils import (
    set_zcml_directive,
    get_zcml,
)
from node.ext.zcml import SimpleDirective
from agx.generator.pyegg.utils import (
    class_base_name,
    implicit_dotted_path,
)
import agx.generator.generator


@handler('generatescopeclass', 'uml2fs', 'connectorgenerator', 'classscope',
         order=9)
def generatescopeclass(self, source, target):
    """Generates scope classes.
    """
    targetclass = read_target_node(source, target.target)
    module = targetclass.parent

    module = targetclass.parent
    methods = [m for m in targetclass.functions()]
    methnames = [m.functionname for m in methods]
    methname = '__call__'
    tgv = TaggedValues(source)
    stereotypes = tgv.direct('stereotypes', 'generator:class_scope', None) or \
        tgv.direct('stereotypes', 'generator:simple_scope', None) or []
    transform = tgv.direct('transform', 'generator:class_scope', None) or \
        tgv.direct('transform', 'generator:simple_scope', None) or \
        'uml2fs'

    if stereotypes:
        for st in stereotypes:
            if ':' not in st:
                msg = 'you have to specify the stereotype in the form ' + \
                      '"namespace:stereotype", but forgot the namespace ' + \
                      '(scope %s, stereotype %s)' % (source.name, st)
                raise ValueError(msg)

    #if not stereotypes:
    #    msg = 'scope %s must have a stereotype attribute!!' % source.name
    #    raise ValueError(msg)

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
    if source.stereotype('pyegg:stub'):
        return

    targetclass = read_target_node(source, target.target)
    module = targetclass.parent
    blocks = module.blocks()

    tgv = TaggedValues(source)

    transform = tgv.direct('transform', 'generator:class_scope', None) or \
        tgv.direct('transform', 'generator:simple_scope', None) or \
        'uml2fs'

    interfaces = tgv.direct('interfaces', 'generator:class_scope', None) or \
        tgv.direct('interfaces', 'generator:simple_scope', None)

    scopename = tgv.direct('scopename', 'generator:class_scope', None) or \
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
        ['Scope', None],
        ['registerScope', None],
        ['token', None],
    ])

    # make the register statement
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

    # look if the reg stmt already exists
    regsearch = "registerScope('%s'" % scopename
    blockfound = None
    for b in blocks:
        for i in range(len(b.lines)):
            lcode = b.lines[i].strip().replace(' ', '')
            if lcode.startswith(regsearch):
                # replace the line
                b.lines[i] = reg
                return

    # else make a new block after the class declaration    
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
    """Remove the classes that should not be generated, should run quite in
    the end.

    XXX: this one sould belong to pyegg in a final generator, but there
    needs to be done some work on sorting generators first
    """
    klass = read_target_node(source, target.target)
    if not klass:
        return
    module = klass.parent

    try:
        tok = token(str(source.uuid), False, dont_generate=False)
    # no tok with flag found, so ignore
    except ComponentLookupError:
        return
    if tok.dont_generate:
        module.detach(klass.__name__)

        # remove the imports
        init = module.parent['__init__.py']
        imps = init.imports()
        impname = [klass.classname, None]
        for imp in imps:
            if impname in imp.names:
                if len(imp.names) > 1:
                    # if more names are in the imp delete the name
                    imp.names = [n for n in imp.names if n != impname]
                else:
                    # delete the whole import
                    init.detach(imp.__name__)


@handler('collect_dependencies', 'uml2fs', 'hierarchygenerator',
         'generatordependency', order=15)
def collect_dependencies(self, source, target):
    handlerscope = getUtility(IScope, 'uml2fs.handler')
    scopescope = getUtility(IScope, 'uml2fs.scope')
    generatorscope = getUtility(IScope, 'uml2fs.generator')
    transformscope = getUtility(IScope, 'uml2fs.transform')

    deps = token(str(source.uuid), True, genDeps=odict())
    if handlerscope(source.client):
        if scopescope(source.supplier):
            token(str(source.client.uuid),
                  True, scopes=[]).scopes.append(source.supplier)
        elif handlerscope(source.supplier):
            token(str(source.client.uuid),
                  True, depends_on=[]).depends_on.append(source.supplier)
        elif generatorscope(source.supplier):
            token(str(source.client.uuid),
                  True, generators=[]).generators.append(source.supplier)
    if generatorscope(source.client):
        if generatorscope(source.supplier):
            token(str(source.client.uuid),
                  True, depends_on=[]).depends_on.append(source.supplier)
        elif transformscope(source.supplier):
            token(str(source.client.uuid),
                  True, transforms=[]).transforms.append(source.supplier)


@handler('mark_handler_as_function', 'uml2fs', 'hierarchygenerator', 'handler',
         order=8)
def mark_handler_as_function(self, source, target):
    token(str(source.uuid), True, is_function=True)
    egg = egg_source(source)
    tok=token(str(egg.uuid),True,is_generator_egg=True)
    tok.is_generator_egg=True


@handler('finalize_handler', 'uml2fs', 'gen_connectorgenerator', 'handler',
         order=15)
def finalize_handler(self, source, target):
    func = read_target_node(source, target.target)
    tok = token(str(source.uuid), True, scopes=[], generators=[])
    tgv = TaggedValues(source)
    order = tgv.direct('order', 'generator:handler', None)
    func.args = ['self', 'source', 'target']

    # ...or by dependency on a generator
    if tok.generators:
        generatornames = [g.name for g in tok.generators]
    else:
        # the generator can be defined by tgv
        generatornames = [tgv.direct('generator', 'generator:handler', None)]

    for scope in tok.scopes:
        stgv = TaggedValues(scope)

        scopename = stgv.direct('scopename', 'generator:class_scope', None) or \
           stgv.direct('scopename', 'generator:simple_scope', None) or \
           scope.name.lower()

        transform = stgv.direct('transform', 'generator:class_scope', None) or \
           stgv.direct('transform', 'generator:class_scope', None) or \
           'uml2fs'

        transformarg = "'%s'" % transform
        scopenamearg = "'%s'" % scopename
        decfound = None

        for generatorname in generatornames:
            generatornamearg = "'%s'" % generatorname
            # find the dec
            for dec in func.decorators():
                if dec.args[1] == transformarg \
                  and dec.args[2] == generatornamearg \
                  and dec.args[3] == scopenamearg:
                    decfound = dec
            if decfound:
                dec = decfound
            # if not found make it
            else:
                dec = Decorator()
                dec.decoratorname = 'handler'
                dec.__name__ = dec.uuid
                func.insertfirst(dec)
            # define the args for the generator
            dec.args = ["'%s'" % source.name, transformarg,
                        generatornamearg, scopenamearg]
            if not order is None:
                dec.kwargs['order'] = order


@handler('make_generators', 'uml2fs', 'connectorgenerator', 'generator')
def make_generators(self, source, target):
    if source.stereotype('pyegg:stub'):
        return
    egg = egg_source(source)
    eggtarget = read_target_node(egg, target.target)
    zcml = get_zcml(eggtarget, 'configure.zcml',
                    nsmap={None: 'http://namespaces.zope.org/zope', 
                           'agx': 'http://namespaces.zope.org/agx'})
    tgv = TaggedValues(source)

    # if transform isnt specified as tgv, get it from dependency relations to
    # other generators
    transform = tgv.direct('transform', 'generator:generator', None)
    if not transform:
        transforms = token(str(source.uuid), True, transforms=[]).transforms
        if len(transforms) > 1:
            msg = 'Currently only one transform per generator allowed (%s)'
            msg = msg % source.name
            raise ValueError(msg)
        elif len(transforms) == 1:
            transform = transforms[0].name

    if not transform:
        transform = 'uml2fs'

    # if depends isnt specified as tgv, get it from dependency relations to
    # transforms
    depend = tgv.direct('depends', 'generator:generator', None)
    if not depend:
        depends = token(str(source.uuid), True, depends_on=[]).depends_on
        if len(depends) > 1:
            msg = 'Currently only one depends per generator allowed (%s)'
            msg = msg % source.name
            raise ValueError(msg)
        elif len(depends) == 1:
            depend = depends[0].name

    if not depend:
        depend = 'NO'

    directives = zcml.filter(tag='agx:generator', attr='name')

    directive = None
    for d in directives:
        if d.attrs['name'] == source.name:
            directive = d
            break

    if not directive:
        directive = SimpleDirective(name='agx:generator', parent=zcml)

    directive.attrs['name'] = source.name
    directive.attrs['transform'] = transform
    directive.attrs['depends'] = depend

    set_zcml_directive(eggtarget, 'configure.zcml', 'agx:generator',
                       'name', source.name, overwrite=True)


@handler('mark_generators_as_stub', 'uml2fs', 'hierarchygenerator', 'pyclass',
         order=10)
def mark_generators_as_stub(self, source, target):
    isgenerator = getUtility(IScope, 'uml2fs.generator')
    if not isgenerator(source):
        return
    token('custom_handled_classes',
          True, classes=[]).classes.append(str(source.uuid))
    token(str(source.uuid), True, dont_generate=True).dont_generate = True


@handler('generate_profile_location', 'uml2fs', 'semanticsgenerator',
         'profile')
def generate_profile_location(self, source, target):
    targetclass = read_target_node(source, target.target)
    module = targetclass.parent

    ifspec = {
        'path': 'agx.core.interfaces.IProfileLocation',
        'name': 'IProfileLocation',
    }
    tok = token(str(targetclass.uuid), False, realizes=[])
    if ifspec not in tok.realizes:
        tok.realizes.append(ifspec)

    tgv = TaggedValues(source)
    name = tgv.direct('profile_name', 'generator:profile', None)
    if not name:
        name=source.name
        #msg = 'profile_name tagged value not defined for %s!' % source.name
        #raise ValueError(msg)

    imps = Imports(module)
    frompath = '.'.join(ifspec['path'].split('.')[:-1])
    imps.set(frompath, [[ifspec['name'], None]])

    attributenames = [att.targets[0] for att in targetclass.attributes()]
    if 'name' not in attributenames:
        att = Attribute()
        att.__name__ = att.uuid
        targetclass[att.name] = att
        att.targets = ['name']
        att.value = "'%s.profile.uml'" % name

    if 'package' not in attributenames:
        att = Attribute()
        att.__name__ = att.uuid
        targetclass[att.name] = att
        att.targets = ['package']
        att.value = dotted_path(source.parent)
        imps.set('', [[att.value, None]])
        # remove the import from this class
        init = targetclass.parent.parent['__init__.py']
        fromimp = '.'.join(implicit_dotted_path(source).split('.')[:-1])
        imps = [imp for imp in init.imports() if imp.fromimport == fromimp]
        for imp in imps:
            init.detach(str(imp.uuid))


@handler('generate_profile_location_zcml', 'uml2fs', 'semanticsgenerator',
         'profile')
def generate_profile_location_zcml(self, source, target):
    if source.stereotype('pyegg:stub'):
        return

    targetclass = read_target_node(source, target.target)
    module = targetclass.parent
    blocks = module.blocks()
    egg = egg_source(source)
    eggtarget = read_target_node(egg, target.target)

    tgv = TaggedValues(source)
    #name = tgv.direct('name', 'generator:profile', None)

    set_zcml_directive(eggtarget, 'configure.zcml', 'utility', 'name',
            implicit_dotted_path(source),
            provides="agx.core.interfaces.IProfileLocation",
            component=implicit_dotted_path(source))


@handler('prepare_zcml', 'uml2fs', 'connectorgenerator', 'pythonegg')
def prepare_zcml(self, source, target):
    """Prepares zcml for generator stuff, therefore the check.
    """
    try:
        tok = token(str(source.uuid), False, is_generator_egg=False)
        if tok.is_generator_egg:
            package = read_target_node(source,target.target)
            nsmap = {
                None: "http://namespaces.zope.org/zope",
                'agx': "http://namespaces.zope.org/agx",
            }
            zcml = get_zcml(package, 'configure.zcml', nsmap=nsmap)
            set_zcml_directive(package, 'configure.zcml', 'include',
                               'package', 'agx.generator.pyegg')
    except ComponentLookupError:
        # if we dont have a token, do nothing
        pass


@handler('common_imports', 'uml2fs', 'semanticsgenerator', 'pymodule')
def common_imports(self, source, target):
    """does common imports for modules with handlers
    """
    handlerscope = getUtility(IScope, 'uml2fs.handler')
    module = read_target_node(source, target.target)
    has_handlers = False
    for klass in source.classes:
        if handlerscope(klass):
            has_handlers = True
            break

    if not has_handlers:
        return

    # do some common imports
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
        ['Scope', None],
        ['registerScope', None],
        ['token', None],
    ])
    imps.set('agx.core.interfaces', [
        ['IScope', None],
    ])
    imps.set('agx.core.util', [
        ['read_target_node', None],
        ['dotted_path', None],
    ])
    imps.set('agx.generator.pyegg.utils', [
        ['class_base_name', None],
        ['implicit_dotted_path', None],
    ])

def is_generator_egg(source):
    if source.stereotype('generator:handler') is not None:
        return 1
    
    for n in source.values():
        if is_generator_egg(n):
            return 1
        

@handler('setup_entry_points', 'uml2fs', 'hierarchygenerator', 'pythonegg',
         order=9)
def setup_entry_points(self, source, target):
    # hooks in the entry point as a token, so that it gets generated 
    # by pyeggs eggdocuments handler
    
    if not is_generator_egg(source):
        return

    ept = """[agx.generator]
        register = %s:register"""
    tok = token('entry_points', True, defs=[])
    tok.defs.append(ept % dotted_path(source))

        
@handler('create_register_func', 'uml2fs', 'connectorgenerator', 'pythonegg')
def create_register_func(self, source, target):
    """Creates the register function.
    """
    if not token(str(source.uuid),True,is_generator_egg=False).is_generator_egg:
        return

    init = read_target_node(source, target.target)['__init__.py']
    fname = 'register'
    path = dotted_path(source)
    if fname not in [f.functionname for f in init.functions()]:
        f = Function()
        f.functionname = fname
        f.__name__ = str(f.uuid)
        bl = Block()
        bl.__name__ = str(bl.uuid)
        bl.lines.append('"""register this generator"""')
        bl.lines.append("import %s" % path)
        bl.lines.append("from agx.core.config import register_generator")
        bl.lines.append("register_generator(%s)" % path)
        f.insertfirst(bl)
        init[f.name] = f


@handler('generate_vanilla_profile', 'uml2fs', 'hierarchygenerator',
         'profile')
def generate_vanilla_profile(self, source, target):
    egg = egg_source(source)
    if not token(str(egg.uuid),True,is_generator_egg=False).is_generator_egg:
        return

    tgv = TaggedValues(source)
    profilename = tgv.direct('name', 'generator:profile', source.name)

    basepath = os.path.dirname(agx.generator.generator.__file__)
    profilepath = os.path.join(basepath, 'resources', 'vanilla_profile')

    # read the model files
    model_di = open(os.path.join(profilepath, 'model.profile.di')).read()
    model_uml = open(os.path.join(profilepath, 'model.profile.uml')).read()
    model_notation = open(
        os.path.join(profilepath, 'model.profile.notation')).read()

    eggdir = read_target_node(egg_source(source), target.target)

    # create profiles dir
    if 'profiles' not in eggdir.keys():
        profiles = Directory()
        profiles.__name__ = 'profiles'
        eggdir['profiles'] = profiles

    profiles = eggdir['profiles']

    # add the model files with correct name and change the references
    if profilename + '.profile.di' not in profiles.keys():
        ff = File()
        ff._data = model_di.replace(
            'model.profile.notation', profilename + '.profile.notation')
        profiles[profilename + '.profile.di'] = ff

    if profilename + '.profile.uml' not in profiles.keys():
        ff = File()
        ff._data = model_uml.replace('profilename_changeme', profilename)
        profiles[profilename + '.profile.uml'] = ff
    
    if profilename + '.profile.notation' not in profiles.keys():
        ff = File()
        ff._data = model_notation.replace(
            'model.profile.uml', profilename + '.profile.uml')
        profiles[profilename + '.profile.notation'] = ff
