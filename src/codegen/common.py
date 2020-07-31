import src.model.pattern as pattern
import src.model.rpython as rpy
class TermMethodTable:
    Kind = 'kind'
    Value = 'value'
    Length = 'length'
    Get = 'get'
    ReplaceWith = 'replacewith'
    CopyToRoot  = 'copy'
    ToString = 'tostring'

class TermHelperFuncs:
    CopyPathAndReplaceLast = 'copy_path_and_replace_last'
    AssertTermListsEqual = 'asserttermlistsequal'
    AreTermsEqualPairwise = 'aretermsequalpairwise'

    TermIsNumber  = 'term_is_number'
    TermIsInteger = 'term_is_integer'
    TermIsNatural = 'term_is_natural_number'
    TermIsFloat   = 'term_is_float'
    TermIsHole    = 'term_is_hole'
    TermIsString  = 'term_is_string'
    TermIsBoolean = 'term_is_boolean'

    ConsumeInteger = 'consume_literal_integer'
    ConsumeFloat = 'consume_literal_float'
    ConsumeBoolean = 'consume_literal_boolean'
    ConsumeVariable = 'consume_variable'
    ConsumeString = 'consume_literal_string'

    PrintTerm = 'print_term'
    PrintTermList = 'print_term_list'


class MatchHelperFuncs:
    CombineMatches = 'combine_matches'
    PrintMatchList = 'print_match_list'

class MatchMethodTable:
    AddToBinding ='addtobinding'
    AddKey = 'create_binding'
    IncreaseDepth = 'increasedepth'
    DecreaseDepth = 'decreasedepth'
    Copy = 'copy'
    CompareKeys = 'comparekeys'
    RemoveKey   = 'removebinding'
    GetBinding = 'getbinding'

# FIXME this shouldnt be here, need to reference TermKind of literal terms.
class TermKind:
    Variable = 0
    Integer  = 1
    Decimal = 2 
    Sequence = 3 
    Hole = 4
    String = 5
    Boolean = 6
