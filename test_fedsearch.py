import asyncio

from fedsearch import SkosSearch, EndpointDetails


def test_basic():
    endpoint_details = [
        EndpointDetails("http://cgi.vocabs.ga.gov.au/sparql/", None, None),
        EndpointDetails("http://ggic.vocabs.ga.gov.au/sparql/", None, None),
    ]
    c = SkosSearch.combine_search_results(
        asyncio.run(SkosSearch.federated_search("coal", "preflabel", endpoint_details)),
        "preflabel",
    )
    assert len(c) == 8
    assert "http://resource.geosciml.org/classifier/cgi/commodity-code/coal" in str(c)
