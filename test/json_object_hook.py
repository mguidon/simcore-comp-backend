

import json

class Simcore:
  def __init__( self, dict ):
      vars(self).update(dict)

data='{ "input1": {"type" : "csv", "url" : "test.csv", "varname" : "A"}}'

_simcore = json.loads(data, object_hook=Simcore)

print( _simcore.input1.type  )
print( _simcore.input1.url  )


print(_simcore.input1.varname)