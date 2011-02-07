"""
Author: John Earls
Created: 11-01-10
Copyright 2011 Institute for Genomic Biology

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import json#this comes by default with python -V >= 2.6
import urllib2
class Client:
    """
    This program is a python version of the Babel client software.
    You can see the original PERL version at 
    http://search.cpan.org/~phonybone/Data-Babel-Client-0.01/
    It's purpose is to contact a Babel server 
    (default: http://babel.gdxbase.org/cgi-bin/translate.cgi)
    and request a mapping from one gene array platform to another 
    (or set of others.)
    """
    def __init__(self, base_url="http://babel.gdxbase.org/cgi-bin/translate.cgi"):
        self.base_url = base_url
        self._idtypes = {}

    def getIDTypes(self):
        """
        Returns the available idtypes as a dictionary {idtype:idtype desc.}
        """
        if len(self._idtypes) == 0:#only hit the server if we have not before
            args = {'request_type':'idtypes', 'output_format':'json'}
            for id in self._fetch(**args):
                self._idtypes[id[0]] = id[1] 
        return self._idtypes

    def translate(self, **kwargs):
        """
        Get matching ids from one input_type to another output_type
        Required args:
            input_type(string): a valid idtype(platform) for the input_ids
            input_ids(list): the ids to be cross-referenced
            output_types(list): valid idtypes(platforms) to be crossreferenced
        Returns:
            A list of lists containing the crossreferenced information
            of the form
            [[input_id1, Xref val for outtype1, Xref val for outype2 ...],
            ...,
             [input_idn, Xref val for outtype1, Xref val for outype2 ...]]
            Note that when an idtype Xrefs with multiple values for an outtype
            there will be multiple rows for input_idx.
        Throws: TypeError on missing args or HTTPError on server errors.
        """
        #override any given reqtype or outformat 
        kwargs['request_type'] = 'translate'
        kwargs['output_format'] = 'json'
        #check all required args are there or Error
        req_args = 'request_type input_ids input_type output_types output_format'.split(' ')
        missing_args = [arg for arg in req_args if arg not in kwargs]
        if len(missing_args) > 0:
            raise TypeError('missing args: ' + ' ,'.join(missing_args))
        return self._fetch(**kwargs)
    
    def translateAll(self, **kwargs):
        """
        Get all matching ids from one input_type to another output_type
        Required args:
            input_type(string): a valid idtype(platform) for the input_ids
            output_types(list): valid idtypes(platforms) to be crossreferenced
        Returns:
            A list of lists containing the crossreferenced information
            of the form
            [[input_type_id1, Xref val for outtype1, Xref val for outype2 ...],
            ...,
             [input_type_idn, Xref val for outtype1, Xref val for outype2 ...]]
            Note that when an idtype Xrefs with multiple values for an outtype
            there will be multiple rows for input_idx.
        Throws: TypeError on missing args or HTTPError on server errors.
         Returns a complete mapping from an input type to a set of output_types.
        """
        kwargs['request_type'] = 'translate'
        kwargs['output_format'] = 'json'
        kwargs['input_ids_all'] = 1 

        req_args = 'request_type input_ids_all input_type output_types output_format'.split(' ')
        missing_args = [arg for arg in req_args if arg not in kwargs]
        if len(missing_args) > 0:
            raise TypeError('missing args: ' + ' ,'.join(missing_args))
        return self._fetch(**kwargs)
 
    def _fetch(self, **kwargs):
        """
        Returns the results of a post request to base_url with args
        being a dictionary containing the key, value pairs to be submitted.
        Returns
        Throws: HTTPError or URLError
        """
        req = urllib2.Request(self.base_url, self._buildQString(**kwargs))     
        res =  json.loads(urllib2.urlopen(req).read())
        if 'error' in res:
            raise urllib2.HTTPError(req.get_full_url(),400,res['error'], None,None)
        return res

    def _buildQString(self, **kwargs):
        """
        Turns the dict into a key=value query string.
        Lists are broken up into separate pairs
        """
        reqstr = []

        for key, val in kwargs.iteritems():
            if isinstance(val, list):
                for item in val:
                    reqstr.append(key + "=" + str(item))
            else:
                reqstr.append(key + "=" + str(val))
        return '&'.join(reqstr)

def prettyPrint(table):
    """
    Little helper function that takes a table and returns a print friendly
    string.
    """ 
    return '\n'.join(['\t'.join([str(val) for val in row]) for row in table])

if __name__ == "__main__":
    c = Client()
    for x in c.getIDTypes().keys():
        print x
    t =  c.translate(input_type='gene_entrez',
          input_ids=[2983,1829,589,20383,293883],
          output_types='protein_ensembl peptide_pepatlas reaction_ec function_go gene_symbol_synonym'.split(' ')
        )
    print prettyPrint(t)
