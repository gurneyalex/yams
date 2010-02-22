from yams.buildobjs import (EntityType, SubjectRelation, ObjectRelation,
                            String, Int, Float, Date, Boolean,
                            RelationDefinition, RelationType)

class Affaire(EntityType):
    sujet = String(maxsize=128)
    ref = String(maxsize=12)

    concerne = SubjectRelation('Societe')
    obj_wildcard = SubjectRelation('*')
    sym_rel = SubjectRelation('Person', symmetric=True)
    inline_rel = SubjectRelation('Person', inlined=True, cardinality='?*')
    subj_wildcard = ObjectRelation('*')


class Person(EntityType):
    nom    = String(maxsize=64, fulltextindexed=True, required=True)
    prenom = String(maxsize=64, fulltextindexed=True)
    sexe   = String(maxsize=1, default='M')
    promo  = String(vocabulary=('bon','pasbon'))
    titre  = String(maxsize=128, fulltextindexed=True)
    adel   = String(maxsize=128)
    ass    = String(maxsize=128)
    web    = String(maxsize=128)
    tel    = Int(__permissions__={'read': (),
                                  'update': ('managers',)})
    fax    = Int()
    datenaiss = Date()
    test   = Boolean()
    salary = Float()

    travaille = SubjectRelation('Societe',
                                __permissions__={'read': (),
                                                 'add': (),
                                                 'delete': ('managers',),
                                                 })
    evaluee = SubjectRelation('Note')


class Societe(EntityType):
    meta = False # test bw compat
    nom  = String(maxsize=64, fulltextindexed=True)
    web = String(maxsize=128)
    tel  = Int()
    fax  = Int()
    rncs = String(maxsize=32)
    ad1  = String(maxsize=128)
    ad2  = String(maxsize=128)
    ad3  = String(maxsize=128)
    cp   = String(maxsize=12)
    ville = String(maxsize=32)

    evaluee = SubjectRelation('Note')


class Note(EntityType):
    date = String(maxsize=10)
    type = String(maxsize=1)
    para = String(maxsize=512)


class pkginfo(EntityType):
    modname = String(maxsize=30, required=True)
    version = String(maxsize=10, required=True, default='0.1')
    copyright = String(required=True)
    license = String(vocabulary=('GPL', 'ZPL'))
    short_desc = String(maxsize=80, required=True)
    long_desc = String(required=True, fulltextindexed=True)
    author = String(maxsize=100, required=True)
    author_email = String(maxsize=100, required=True)
    mailinglist = String(maxsize=100)
    debian_handler = String(vocabulary=('machin', 'bidule'))


class evaluee(RelationType):
    __permissions__ = {
        'read': ('managers',),
        'add': ('managers',),
        'delete': ('managers',),
        }

class concerne(RelationDefinition):
    subject = 'Person'
    object = 'Affaire'
    __permissions__ = {
        'read': ('managers',),
        'add': ('managers',),
        'delete': ('managers',),
        }

