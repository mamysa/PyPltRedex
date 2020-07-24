import src.model.pattern as pattern
import src.model.rpython as rpy
class TermMethodTable:
    Kind = 'kind'
    Value = 'value'
    Length = 'length'
    Get = 'get'
    ReplaceWith = 'replacewith'
    CopyToRoot  = 'copy'

class TermHelperFuncs:
    CopyPathAndReplaceLast = 'copy_path_and_replace_last'
    AssertTermListsEqual = 'asserttermlistsequal'
    AreTermsEqualPairwise = 'aretermsequalpairwise'

    TermIsNumber  = 'term_is_number'
    TermIsInteger = 'term_is_integer'
    TermIsNatural = 'term_is_natural_number'
    TermIsDecimal = 'term_is_decimal'
    TermIsHole    = 'term_is_hole'

    ConsumeInteger = 'consume_literal_integer'
    ConsumeDecimal = 'consume_literal_decimal'
    ConsumeVariable = 'consume_variable'

class MatchHelperFuncs:
    CombineMatches = 'combine_matches'

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
