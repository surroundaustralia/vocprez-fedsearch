import asyncio
import itertools
from typing import Union, List, Tuple

from httpx import AsyncClient, Response
from prettytable import PrettyTable


class EndpointDetails:
    endpoint: str
    username: str
    password: str

    def __init__(self, endpoint, username, password):
        self.endpoint = endpoint
        self.username = username
        self.password = password


class SkosSearch(object):
    version = "0.0.1"

    @staticmethod
    def get_search_methods() -> List[str]:
        return ["weighted", "preflabel"]

    @staticmethod
    async def sparql_query(
            query: str,
            sparql_endpoint: str,
            sparql_username: Union[str, None] = None,
            sparql_password: Union[str, None] = None,
    ) -> Tuple[bool, int, Union[None, str]]:
        """Sends a SPARQL query to a given Endpoint that may, or may not, use basic authentication"""
        async with AsyncClient() as client:
            if sparql_username is not None and sparql_password is not None:
                response: Response = await client.get(
                    sparql_endpoint,
                    params={"query": query},
                    headers={"Accept": "application/sparql-results+json"},
                    auth=(sparql_username, sparql_password),
                    timeout=1000,
                )
            else:
                response: Response = await client.get(
                    sparql_endpoint,
                    params={"query": query},
                    headers={"Accept": "application/sparql-results+json"},
                    timeout=1000,
                )
        if 200 <= response.status_code < 300:
            return True, response.status_code, response.json()["results"]["bindings"]
        else:
            return False, response.status_code, response.text

    @staticmethod
    async def weighted(
            term: str,
            sparql_endpoint: str,
            sparql_username: Union[str, None] = None,
            sparql_password: Union[str, None] = None,
    ) -> str:
        """Searches a given SPARQL Endpoint for the given term in Concept prefLabels, altLabels, hiddenLabels, and
        definitions, weighted to preference matches in that order."""
        q = """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    
            SELECT DISTINCT ?sys ?g ?uri ?pl (SUM(?w) AS ?weight)
            WHERE {
                GRAPH ?g {
                    {  # exact match on a prefLabel always wins
                        ?uri a skos:Concept ;
                             skos:prefLabel ?pl .
                        BIND (50 AS ?w)
                        FILTER REGEX(?pl, "^{term}$", "i")
                    }
                    UNION    
                    {
                        ?uri a skos:Concept ;
                             skos:prefLabel ?pl .
                        BIND (10 AS ?w)
                        FILTER REGEX(?pl, "{term}", "i")
                    }
                    UNION
                    {
                        ?uri a skos:Concept ;
                             skos:altLabel ?al ;
                             skos:prefLabel ?pl .
                        BIND (5 AS ?w)
                        FILTER REGEX(?al, "{term}", "i")
                    }
                    UNION
                    {
                        ?uri a skos:Concept ;
                             skos:hiddenLabel ?hl ;
                             skos:prefLabel ?pl .
                        BIND (5 AS ?w)
                        FILTER REGEX(?hl, "{term}", "i")
                    }
                    UNION
                    {
                        ?uri a skos:Concept ;
                             skos:definition ?d ;
                             skos:prefLabel ?pl .
                        BIND (1 AS ?w)
                        FILTER REGEX(?d, "{term}", "i")
                    }
                }
    
                BIND (<{sys}> AS ?sys)
            }
            GROUP BY ?g ?uri ?pl ?sys
            """.replace(
            "{sys}", sparql_endpoint
        ).replace(
            "{term}", term
        )
        r = await SkosSearch.sparql_query(
            q, sparql_endpoint, sparql_username, sparql_password
        )
        if r[0]:
            return r[2]
        else:
            raise Exception(f"SPARQL query error code {r[1]}: {r[2]}")

    @staticmethod
    async def rva(term: str):
        async with AsyncClient() as client:
            response: Response = await client.post(
                "https://vocabs.ardc.edu.au/registry/api/services/search/resources",
                data=f'filtersJson={{"q": "{term}"}}',
                headers={
                    # "Accept": "application/json"
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                timeout=1000,
            )
        if 200 <= response.status_code < 300:
            return True, response.status_code, response.json()["highlighting"]
        else:
            return False, response.status_code, response.text

    @staticmethod
    async def preflabel(
            term: str,
            sparql_endpoint: str,
            sparql_username: Union[str, None] = None,
            sparql_password: Union[str, None] = None,
    ) -> str:
        """Searches a given SPARQL Endpoint for the given term in Concept prefLabels only."""
        q = """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    
            SELECT DISTINCT ?sys ?cs ?uri ?pl (SUM(?w) AS ?weight)
            WHERE {
                {  # exact match on a prefLabel always wins
                    ?uri a skos:Concept ;
                        skos:prefLabel ?pl ;
                        skos:inScheme|skos:topConceptOf|^skos:hasTopConcept ?cs .
                    BIND (50 AS ?w)
                    FILTER REGEX(?pl, "^{term}$", "i")
                }
                UNION    
                {
                    ?uri a skos:Concept ;
                        skos:prefLabel ?pl ;
                        skos:inScheme|skos:topConceptOf|^skos:hasTopConcept ?cs .
                    BIND (10 AS ?w)
                    FILTER REGEX(?pl, "{term}", "i")
                }
    
                BIND (<{sys}> AS ?sys)
            }
            GROUP BY ?cs ?uri ?pl ?sys
            """.replace(
            "{sys}", sparql_endpoint
        ).replace(
            "{term}", term
        )
        r = await SkosSearch.sparql_query(
            q, sparql_endpoint, sparql_username, sparql_password
        )
        if r[0]:
            return r[2]
        else:
            raise Exception(f"HTTP Error\nStatus Code: {r[1]}\nMessage: {r[2]}")

    @staticmethod
    def combine_search_results(search_results: List[str], search_method: str):
        """Combines, while ordering, the (JSON) results from a number of search methods"""
        if search_method not in SkosSearch.get_search_methods():
            raise Exception(
                f"search_method must be one of: {', '.join(SkosSearch.get_search_methods())}"
            )

        aggregation = list(itertools.chain.from_iterable(search_results))

        return sorted(aggregation, key=lambda d: d["weight"]["value"], reverse=True)

    @staticmethod
    async def federated_search(
            term: str, search_method: str, sparql_details: List[EndpointDetails]
    ):
        """Searches all given SPARQL Endpoints for the given term, using the given method"""

        if search_method not in SkosSearch.get_search_methods():
            raise Exception(
                f"search_method must be one of: {', '.join(SkosSearch.get_search_methods())}"
            )

        results = await asyncio.gather(
            *[
                getattr(SkosSearch, search_method)(
                    term,
                    sparql_endpoint.endpoint,
                    sparql_endpoint.username,
                    sparql_endpoint.password,
                )
                for sparql_endpoint in sparql_details
            ]
        )
        return results


def command_line_present(search_results: list):
    t = PrettyTable()
    t.field_names = ["No.", "Label", "Concept", "System"]
    t.align = "l"
    for i, c in enumerate(search_results):
        t.add_row([i + 1, c["pl"]["value"], c["uri"]["value"], c["sys"]["value"]])

    return t


if __name__ == "__main__":
    endpoint_details = [
        EndpointDetails("http://cgi.vocabs.ga.gov.au/sparql/", None, None),
        # SparqlDetails("https://vocabs.gsq.digital/sparql/", None, None),
        EndpointDetails("http://ggic.vocabs.ga.gov.au/sparql/", None, None),
        # SparqlDetails("http://icsm.surroundaustralia.com/sparql/", None, None),
    ]
    c = SkosSearch.combine_search_results(
        asyncio.run(SkosSearch.federated_search("coal", "preflabel", endpoint_details)),
        "preflabel",
    )
    print(command_line_present(c))
