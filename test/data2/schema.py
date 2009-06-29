from yams.buildobjs import String
from yams.reader import context
from data.schema.schema import Affaire, Note

Affaire.permissions = {'read': (),
                       'add': (),
                       'update': (),
                       'delete': ()}

class MyNote(Note):
    text = String()

assert 'Note' in context.defined
