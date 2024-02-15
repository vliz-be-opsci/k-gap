# this file will be used to trigger the injest processes into graphdb
# this prevents the injest.py and tryout_watch.py to be run at the same
# time with conflicting circular imports

from SPARQLWrapper import SPARQLWrapper, JSON
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, quote
import logging
from rdflib import Graph
import time
import os

# from dotenv import load_dotenv
from .helpers import resolve_path  # ,enable_logging
from pyrdfj2 import J2RDFSyntaxBuilder

log = logging.getLogger(__name__)
URN_BASE = os.getenv("URN_BASE", "urn:lwua:INGEST")


def gdb_from_config():
    base = os.getenv("GDB_BASE", "http://localhost:7200")
    repoid = os.getenv("GDB_REPO", "lwua23")

    endpoint = f"{ base }/repositories/{ repoid }"
    # update statements are handled at other endpoint
    updateEndpoint = endpoint + "/statements"

    log.debug(f"using endpoint {endpoint}")

    GDB = SPARQLWrapper(
        endpoint=endpoint,
        updateEndpoint=updateEndpoint,
        returnFormat=JSON,
        agent="lwua-python-sparql-client",
    )
    GDB.method = "POST"
    return GDB


GDB = gdb_from_config()


def get_j2rdf_builder():
    template_folder = resolve_path("./lwua/templates")
    log.info(f"template_folder == {template_folder}")
    # init J2RDFSyntaxBuilder
    j2rdf = J2RDFSyntaxBuilder(
        templates_folder=template_folder,
        extra_functions={"registry_of_lastmod_context": f"{URN_BASE}:ADMIN"},
    )
    return j2rdf


J2RDF = get_j2rdf_builder()


def update_registry_lastmod(context: str, lastmod: datetime):
    """
    Update the administration of a context.

    :param context: The context to update.
    :type context: str
    :param lastmod: The date string to update with.
    :type lastmod: str
    """
    log.info(f"update registry_of_lastmod_context on {context}")

    # check if context is IRI compliant
    assert_iri_compliance(context)

    # variables for the template
    template = "update_context_lastmod.sparql"
    vars = {
        "context": context,
        "lastmod": lastmod if lastmod is not None else None,
    }
    # get the sparql query
    query = J2RDF.build_syntax(template, **vars)
    log.debug(f"update_registry_lastmod query == {query}")
    # execute the query
    GDB.setQuery(query)
    GDB.query()


def assert_iri_compliance(context: str):
    assert context.startswith(
        URN_BASE), f"Context {context} is not IRI compliant"


def insert_graph(graph: Graph, context: str = None):
    """
    Insert data into a context.

    :param graph: The graph to insert data from.
    :type graph: Graph
    :param context: The context to insert data into.
    :type context: str
    """

    log.info(f"insert_graph into {context}")
    assert_context_exists(context)
    # Initialize the J2RDFSyntaxBuilder

    assert_iri_compliance(context) if context is not None else None

    # Variables for the template
    template = "insert_graph.sparql"
    ntstr = graph.serialize(format="nt")
    vars = {"context": context, "raw_triples": ntstr}

    # Get the SPARQL query
    query = J2RDF.build_syntax(template, **vars)
    # log.debug(f"insert_graph query == {query}")

    # Execute the query
    GDB.setQuery(query)
    GDB.query()


def assert_context_exists(context: str):
    assert context is not None, "Context cannot be None"


def delete_graph(context: str):
    """
    Delete data from a context.

    :param context: The context to delete data from.
    :type context: str
    """

    log.info(f"delete_graph on {context}")
    assert_context_exists(context)

    # Initialize the J2RDFSyntaxBuilder

    # check if context is IRI compliant
    assert_iri_compliance(context) if context is not None else None

    # Variables for the template
    template = "delete_graph.sparql"
    vars = {"context": context}

    # Get the SPARQL query
    query = J2RDF.build_syntax(template, **vars)

    # Execute the query
    GDB.setQuery(query)
    GDB.query()


def ingest_graph(
        graph: Graph,
        lastmod: datetime,
        context: str,
        replace: bool = False):
    """
    Ingest a graph into a context.

    :param fname: The filename to convert.
    :type fname: str
    :return: The context corresponding to the filename.
    :rtype: str
    """
    log.debug(f"to insert data into <{ context }>")
    assert_context_exists(context)
    # do the cleanup if possible
    if replace and context is not None:
        log.debug(f"deleting <{ context }> before insert")
        delete_graph(context)

    # insert the data
    insert_graph(graph, context)

    # convert the epoch timestamp to a date string
    update_registry_lastmod(context, lastmod)


def context_2_fname(context: str):
    """
    Convert a context to a filename path.

    :param context: The context to convert.
    :type context: str
    :return: The filename corresponding to the context.
    :rtype: str
    """
    assert context.startswith(
        URN_BASE), f"Context {context} is not IRI compliant"
    return unquote(context[len(URN_BASE) + 1:])


def fname_2_context(fname: str):
    """
    Convert a filename to a context.

    :param fname: The filename to convert.
    :type fname: str
    :return: The context corresponding to the filename.
    :rtype: str
    """
    fname = str(fname)
    return f"{URN_BASE}:{quote(fname)}"


def get_registry_of_lastmod():
    log.info(f"getting last modified graph")

    template = "lastmod_info.sparql"
    vars = {}
    query = J2RDF.build_syntax(template, **vars)
    # log.debug(f"get_admin_graph query == {query}")
    GDB.setQuery(query)
    GDB.setReturnFormat(JSON)
    results = GDB.query().convert()

    # convert {'head': {'vars': ['graph', 'lastmod']}, 'results': {'bindings': []}} to [{PosixPath('graph'): lastmod}]
    # URI must be substracted from graph context and datetime str must be
    # converted to epoch

    converted = {}
    return convert_results_registry_of_lastmod(results)


def convert_results_registry_of_lastmod(results):
    converted = {}
    for g in results["results"]["bindings"]:
        path = context_2_fname(g["graph"]["value"])
        time = datetime.fromisoformat(g["lastmod"]["value"])
        converted[path] = time
    return converted


def format_from_filepath(fpath: Path):
    suffix = fpath.suffix[1:].lower()
    if suffix in ["ttl", "turtle"]:
        return "turtle"
    if suffix in ["jsonld", "json"]:
        return "json-ld"
    # todo consider others if needed
    return None


def read_graph(fpath: Path, format: str = None):
    format = format or format_from_filepath(fpath)
    graph: Graph = Graph().parse(location=str(fpath), format=format)
    return graph
