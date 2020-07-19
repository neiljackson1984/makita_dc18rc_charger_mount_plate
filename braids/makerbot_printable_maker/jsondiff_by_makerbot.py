import json

"""
Represents a difference between two JSON objects, with helpers for easy printing
and analysis.
"""

class JSONDiff:
    
    class Missing:
        
        def __eq__(self, other):
            if isinstance(other, JSONDiff.Missing):
                return True
            return False
        
        def __hash__(self):
            return 0
        
    """There are a number of different kinds of diffs:
       - Empty (values are similar)
       - Value is missing (list/dict)
       - Value is added
       - Non-numeric types do not match
       - Numeric types do not match
       - Values do not match
         - Numeric values do not match
       - List of diffs
       - Dict of diffs 
    """

    def __init__(self, json_a, json_b):
        
        self.json_a = json_a
        self.json_b = json_b
        
        self.type_diff = None
        self.numeric_type_diff = None
        self.value_diff = None
        self.dict_diff = {}

        if isinstance(json_a, bool):
            self.init_bool(json_a, json_b)
        elif isinstance(json_a, (int, float)):
            self.init_number(json_a, json_b)
        elif isinstance(json_a, str):
            self.init_str(json_a, json_b)
        elif isinstance(json_a, (list, tuple)):
            self.init_list(json_a, json_b)
        elif isinstance(json_a, dict):
            self.init_dict(json_a, json_b)
        elif isinstance(json_a, JSONDiff.Missing):
            self.init_missing(json_a, json_b)
        elif isinstance(json_a, type(None)):
            self.init_null(json_a, json_b)
        else:
            self.init_unknown(json_a, json_b)

    def init_bool(self, bool_a, json_b):
        
        if not isinstance(json_b, bool):
            self.type_diff = (bool, type(json_b))
        elif bool_a != json_b:
            self.value_diff = (bool_a, json_b)
    
    def init_number(self, num_a, json_b):

        if not isinstance(json_b, (int, float)):
            self.type_diff = (type(num_a), type(json_b))
        else:
            if num_a != json_b:
                self.value_diff = (num_a, json_b)
            elif not isinstance(json_b, type(num_a)):
                self.numeric_type_diff = (type(num_a), type(json_b))

    def init_str(self, str_a, json_b):

        if not isinstance(json_b, str):
            self.type_diff = (str, type(json_b))
        elif str_a != json_b:
            self.value_diff = (str_a, json_b)

    def init_dict(self, dict_a, json_b):
        if not isinstance(json_b, dict):
            self.type_diff = (dict, type(json_b))
        else:
            for key, value_a in dict_a.items():
                if key in json_b:
                    value_b = json_b[key]
                    next_diff = JSONDiff(value_a, value_b)
                    if not next_diff.is_similar_value():
                        self.dict_diff[key] = next_diff
                else:
                    self.dict_diff[key] = JSONDiff(value_a, JSONDiff.Missing())
            for key, value_b in json_b.items():
                if key not in dict_a:
                    self.dict_diff[key] = JSONDiff(JSONDiff.Missing(), value_b)
    
    def init_missing(self, missing_a, json_b):
        if not isinstance(json_b, JSONDiff.Missing):
            self.type_diff = (JSONDiff.Missing, type(json_b))

    def init_null(self, null_a, json_b):
        if not isinstance(json_b, type(None)):
            self.type_diff = (type(None), type(json_b))

    def init_list(self, list_a, json_b):

        if not isinstance(json_b, (list, tuple)):
            self.type_diff = (type(list_a), type(json_b))
        else:
            for i, value_a in enumerate(list_a):
                if i < len(json_b):
                    value_b = json_b[i]
                    next_diff = JSONDiff(value_a, value_b)
                    if not next_diff.is_similar_value():
                        self.dict_diff[i] = next_diff
                else:
                    self.dict_diff[i] = JSONDiff(value_a, JSONDiff.Missing())

            if len(json_b) > len(list_a):
                for i, value_b in enumerate(json_b, len(list_a)):
                    self.dict_diff[i] = JSONDiff(JSONDiff.Missing(), value_b)
    
    def init_unknown(self, json_a, json_b):
        if not isinstance(json_b, type(json_a)):
            self.type_diff = (type(json_a), type(json_b))
        elif json_a != json_b:
            self.value_diff = (json_a, json_b)
    
    def __eq__(self, other):

        if self.is_type_diff():
            if self.type_diff != other.type_diff:
                return False
            return (self.json_a, self.json_b) == (other.json_a, other.json_b)
        
        elif self.is_numeric_type_diff():
            if self.numeric_type_diff != other.numeric_type_diff:
                return False
            return self.json_a == other.json_b
        
        elif self.is_value_diff():
            return self.value_diff == other.value_diff
        
        else:
            
            if len(self.dict_diff) != len(other.dict_diff):
                return False
            
            for key, value in self.dict_diff.items():
                if key not in other.dict_diff:
                    return False
                if not self.dict_diff[key].__eq__(other.dict_diff[key]):
                    return False
                
            return True
                
    def __hash__(self):
        
        return (self.type_diff, 
                self.numeric_type_diff,
                self.value_diff,
                hash(frozenset(list(self.dict_diff.items())))).__hash__()

    def is_similar_value(self):
        return (not self.type_diff) and (not self.numeric_type_diff) and \
               (not self.value_diff) and (not self.dict_diff)

    def is_added_value(self):
        return self.type_diff and isinstance(self.json_a, JSONDiff.Missing)

    def is_removed_value(self):
        return self.type_diff and isinstance(self.json_b, JSONDiff.Missing)
    
    def is_type_diff(self):
        return self.type_diff

    def is_numeric_type_diff(self):
        return self.numeric_type_diff
    
    def is_value_diff(self):
        return self.value_diff

    def is_numeric_value_diff(self):
        return self.value_diff and isinstance(self.json_a, (int, float))
    
    def is_list_diff(self):
        return self.dict_diff and isinstance(self.json_a, (list, tuple))
    
    def is_dict_diff(self):
        return self.dict_diff and not self.is_list_diff()

    def flatten(self):

        flat_dict_diff = {}
        for key, value in self.dict_diff.items():
            
            value.flatten()
            
            if not value.dict_diff:
                flat_dict_diff[key] = value
            
            if isinstance(key, int):
                key = "[%s]" % key

            for child_key, child_value in value.dict_diff.items():
    
                if isinstance(child_key, int):
                    flat_key = "%s[%s]" % (key, child_key)
                else:
                    flat_key = "%s.%s" % (key, child_key)
                
                flat_dict_diff[flat_key] = child_value
                               
        self.dict_diff = flat_dict_diff
    
    def ignore_numeric_type_diff(self):
        
        if self.numeric_type_diff:
            self.numeric_type_diff = None
        
        elif self.dict_diff:

            keys_to_remove = []
            for key, diff in self.dict_diff.items():
                
                diff.ignore_numeric_type_diff()   
                if diff.is_similar_value():
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.dict_diff[key]
    
    def ignore_numeric_value_diff(self, tolerance):

        if self.is_numeric_value_diff() and \
           abs(self.json_a - self.json_b) <= tolerance:
            self.value_diff = None
        
        elif self.dict_diff:

            keys_to_remove = []
            for key, diff in self.dict_diff.items():
                
                diff.ignore_numeric_value_diff(tolerance)   
                if diff.is_similar_value():
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.dict_diff[key]

    def pretty_str(self, indent_size=2, trim_size=12,
                   root=True):
        
        """
        A pretty-formatted, indented report of diffs.
        """

        def small_str(value, size):

            if not isinstance(value, str): 
                value_str = json.dumps(value)
            else:
                value_str = str(value)

            if len(value_str) > (size + len('...')):
                value_str = value_str[:size] + '...'
            
            if isinstance(value, str):
                value_str = '"' + value_str + '"'
            return value_str
        
        def indent_str(value_str, size):
            indent = " " * size
            return indent + value_str.replace("\n", "\n" + indent)

        if self.is_added_value():
            return "+++ %s was added" % small_str(self.json_b, trim_size)

        elif self.is_removed_value():
            return "--- %s was removed" % small_str(self.json_a, trim_size)

        elif self.type_diff:
            return "*** %s and %s have different types (%s vs %s)" % \
                    (small_str(self.json_a, trim_size), small_str(self.json_b, trim_size),
                     self.type_diff[0].__name__, self.type_diff[1].__name__)

        elif self.numeric_type_diff:
            return "### %s and %s have different numeric types (%s vs %s)" % \
                    (small_str(self.json_a, trim_size), small_str(self.json_b, trim_size),
                     self.numeric_type_diff[0].__name__, self.numeric_type_diff[1].__name__)

        elif self.is_numeric_value_diff():
            # TODO: Report close values differently?
            return "::: %s and %s do not match" % (self.json_a, self.json_b)

        elif self.value_diff:
            return "::: %s and %s do not match" % \
                    (small_str(self.json_a, trim_size), small_str(self.json_b, trim_size))

        elif self.dict_diff:
            keys = list(self.dict_diff.keys())
            keys.sort()
            pretty = ""
            for key in keys:
                
                if key != keys[0]:
                    pretty = pretty + "\n"

                next_diff = self.dict_diff[key]
                if next_diff.is_similar_value():
                    continue
                
                if isinstance(key, int):
                    key = "[%s]" % key
                elif not root:
                    key = ".%s" % key

                pretty = pretty + "%s:\n%s" % (key, 
                    indent_str(next_diff.pretty_str(indent_size=indent_size,
                                                    trim_size=trim_size,
                                                    root=False),
                               indent_size))

            return pretty

        else:
            return "(empty)"


