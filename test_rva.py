import asyncio

from fedsearch import SkosSearch

if __name__ == "__main__":
    r = asyncio.run(SkosSearch.rva("coal"))
    print(r)

# TODO: blend RVA search results in with others
#
# per result, find if it's a prefLabel, altLabel etc matching
# "skos_prefLabel_search_all": [
#    "HL_STARTCoalHL_END"
# ],
#
#  strip 'HL_START' & 'HL_END'
#
# note this can determin if it's a complete match, as above, or a partial match, as below.
# "skos_definition_search_all": [
#     "HL_STARTCoalHL_END (Sedimentary rock, chemical or organic)"
# ],
#
# use weighted search criteria to add up the match fields from RVA, just like from VP SPARQL
#
# mesh these results back into combined results
