# fedsearch - Federated SPARQL search for VocPrez

This tiny package implements a number of search methods for terms in SKOS vocabularies and allows them to be sent to
multiple VocPrez instances and other systems in parallel.

This package will be incorporated into VocPrez 3 but may also be used elsewhere, hence its independent life.

## Search Status

- **VocPrez**
  - searching across multiple VocPrezes works fine
    - not GSQ: seems to be an auth issue in Python, not present using cURL
- **RVA**
  - search results obtained but not meshed in, see TODO on test_rva
- **NVS**
  - not started
- **CSIRO Registry**
  - not started

Broader systems:

- **BARTOC**
  - not started
- **AGROVOC**
  - not started

## Version

See fedsearch SkosSearch.version
