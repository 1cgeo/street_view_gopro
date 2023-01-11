import os
import json

class StorageConfig:

    def hasFile(self):
        return os.path.exists(self.getFilePath())

    def getFilePath(self):
        return os.path.join(
                os.path.abspath(os.path.dirname(__file__)),
                '..',
                'setup.json'
            )
     
    def getValue(self, key):
        if not self.hasFile():
            return None
        with open(self.getFilePath(), 'r') as f:
            data = json.loads(f.read())
            return data[key] if key in data else None

    def setValue(self, key, value):
        data = self.getAllValues()
        data[key] = value
        with open(self.getFilePath(), 'w') as f:
            f.write(json.dumps(data))

    def getAllValues(self):
        if not self.hasFile():
            return {}
        with open(self.getFilePath(), 'r') as f:
            data = json.loads(f.read())
            return data
