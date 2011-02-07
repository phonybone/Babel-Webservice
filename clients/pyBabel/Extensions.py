import cPickle
from Client import Client
import re
import os.path
class ext:
    """
    These are some helper extensions pretty specific to 
    what I have been working on.
    May be useful to someone else? Maybe not.
    """
    def __init__(self, cache_dir='data', base_url="http://babel.gdxbase.org/cgi-bin/translate.cgi"):
        
        self.client = Client(base_url)
        self.cache_dir = cache_dir

    def mergeProbes(self, idLists):
        """
        Returns a list of 2-tuples (i,j) where i is the index in ids1 that matches ids2 
        """
        #figure out what type of data
        idtypes =[self.discoverID(idList, self._getProbeTypes())  for idList in idLists]
        for i, idtype in enumerate(idtypes):
            if idtype == None:
                raise pyBabelError("id " + str(i) + " undefined.")
        #get the type map table
        typeMap = self.getMap(idtypes)
        #build dicts from idname->indx
        indxMaps = [self._buildIndexMap(idList) for idList in idLists]
        #we only want unique mappings
        merged = {}
        for row in typeMap:
            entrez = row[-1]
            if entrez != None:
                good = True
                for i, column in enumerate(row[:-1]):
                    if column not in indxMaps[i]:
                        good = False
                if good:
                    merged[tuple(row[:-1])] = 1
        return merged.keys()

    def getControls(self, ids):
        """
        returns a list of indices that are controls
        #have no gene entrez_id
        """
        pass #no idea if this is working or not.
        idtype = self.discoverID(ids, self._getProbeTypes())
        if idtype == None:
            raise pyBabelError("ids undefined")

        map = self.getAllTable(idtype, idtype)
        #print self.prettyPrint(map)
        indxMap = self._buildIndexMap(ids)
        res = []
        for i, _ , entrez in map:
             if entrez == None and i in indxMap:
                res.append(i)
        return res
        
        
        

    def discoverID(self, ids, base_idTypes, numIDs=10):
        """
        Given a subset of base_idTypes check which 
        id type a set of ids come from
        """
        for idtype in base_idTypes:
            if len(self.client.translate(input_type=idtype, input_ids=ids[:numIDs],output_types=[idtype]) ) > 0:
                return idtype
        return None

    def getAllTable(self, idtypes):
    
        input_type = idtypes[0]
        output_type = idtypes[1:]
        output_type.append('gene_entrez') #for control filtering
        return self.client.translateAll(input_type=input_type, output_types=output_type)
            
    def _getProbeTypes(self):
        """
        returns a list of valid idtypes that have the word 'probe' in them
        """
        p = re.compile('probe')
        return [x for x in self.client.getIDTypes() if p.search(x)]

    def prettyPrint(self, table):
        """
        Little helper function that takes a table and returns a print friendly
        string.
        """ 
        return '\n'.join(['\t'.join([str(val) for val in row]) for row in table])
    def getMap(self, idtypes, usePickle=True):
        """
        """
        #look for pickle
        if usePickle:
            p = self._getPickle(idtypes)
        else:
            p = None

        if p == None:#not kosher
            map = self.getAllTable(idtypes)
            self._writePickle(idtypes, map)#build map will pickle the result
        else:
            map = cPickle.load(p)
            p.close()

        return map
    def _buildIndexMap(self, ids):
        indxMap = {}
        for i, id in enumerate(ids):
            indxMap[id] = i
        return indxMap

    def _getPickle(self,idtypes):
        fName = os.path.join(self.cache_dir, self._getPKLName(idtypes))
        if os.path.isfile(fName):
            return open(fName, 'rb')
        else:
            return None

    def _writePickle(self, idtypes, map):
        fName = os.path.join(self.cache_dir, self._getPKLName(idtypes))
        pFile = open(fName, 'wb')
        cPickle.dump(map, pFile)
        pFile.close()

    def _getPKLName(self, idTypes):
        return '-'.join(idTypes) + ".pkl"

class pyBabelError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
