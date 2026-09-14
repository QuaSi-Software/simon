"""Various utility functions for the webapp."""

from __future__ import annotations
from urllib.parse import quote, unquote
import xml.etree.ElementTree as ET

RESULT_FILES = [
    {
        "filename": "logfile_general.log",
        "tab_name": "genlog-tab",
        "tab_name_full": "General log",
        "element": "p"
    },
    {
        "filename": "logfile_balanceWarn.log",
        "tab_name": "ballog-tab",
        "tab_name_full": "Balance log",
        "element": "p"
    },
    {
        "filename": "auxiliary_info.md",
        "tab_name": "aux-tab",
        "tab_name_full": "Aux. info",
        "element": "p"
    },
    {
        "filename": "output_plot.html",
        "tab_name": "plot-tab",
        "tab_name_full": "Line plot",
        "element": "html"
    },
    {
        "filename": "output_sankey.html",
        "tab_name": "sankey-tab",
        "tab_name_full": "Sankey plot",
        "element": "html"
    },
    {
        "filename": "out.csv",
        "tab_name": "csv-tab",
        "tab_name_full": "CSV",
        "element": "table"
    },
    {
        "filename": "economic_results_cashflows.html",
        "tab_name": "ecorescash-tab",
        "tab_name_full": "Cashflows",
        "element": "html"
    },
    {
        "filename": "economic_results_present_values.html",
        "tab_name": "ecorespreval-tab",
        "tab_name_full": "Present values",
        "element": "html"
    },
    {
        "filename": "economic_results.csv",
        "tab_name": "ecores-tab",
        "tab_name_full": "Economics",
        "element": "table"
    },
    {
        "filename": "emissions_result.html",
        "tab_name": "emsres-tab",
        "tab_name_full": "Emissions",
        "element": "html"
    },
    {
        "filename": "emissions_results.csv",
        "tab_name": "emsrescsv-tab",
        "tab_name_full": "Emissions CSV",
        "element": "table"
    },
    {
        "filename": "price_and_emissions_profiles.html",
        "tab_name": "priceemsprof-tab",
        "tab_name_full": "Price/emissions profiles",
        "element": "html"
    },
    {
        "filename": "parameter_study_all_results.csv",
        "tab_name": "ps-all-tab",
        "tab_name_full": "PS All",
        "element": "table"
    },
    {
        "filename": "parameter_study_global_sensitivity.csv",
        "tab_name": "ps-glob-sens-csv-tab",
        "tab_name_full": "Glob. Sens. CSV",
        "element": "table"
    },
    {
        "filename": "parameter_study_local_sensitivity.csv",
        "tab_name": "ps-loc-sens-csv-tab",
        "tab_name_full": "Local Sens. CSV",
        "element": "table"
    },
    {
        "filename": "parameter_study_plots_convergence.html",
        "tab_name": "ps-conv-tab",
        "tab_name_full": "PS Convergence",
        "element": "html"
    },
    {
        "filename": "parameter_study_plots_global_sensitivity.html",
        "tab_name": "ps-glob-sens-plot-tab",
        "tab_name_full": "Glob. Sens. Plot",
        "element": "html"
    },
    {
        "filename": "parameter_study_plots_interactive_3d.html",
        "tab_name": "ps-inter-3d-tab",
        "tab_name_full": "PS Interactive 3D",
        "element": "html"
    },
    {
        "filename": "parameter_study_plots_local_sensitivity_response_overview.html",
        "tab_name": "ps-loc-sens-overview-tab",
        "tab_name_full": "Local Sens. Overv.",
        "element": "html"
    },
    {
        "filename": "parameter_study_plots_local_sensitivity_response_trends.html",
        "tab_name": "ps-loc-sens-trends-tab",
        "tab_name_full": "Local Sens. Trends",
        "element": "html"
    },
    {
        "filename": "parameter_study_plots_matrix_plot.html",
        "tab_name": "ps-matrix-tab",
        "tab_name_full": "PS Matrix Plot",
        "element": "html"
    },
    {
        "filename": "parameter_study_plots_objective_parameter_explorer.html",
        "tab_name": "ps-param-explorer-tab",
        "tab_name_full": "PS Param. Explorer",
        "element": "html"
    },
    {
        "filename": "parameter_study_plots_parallel_coordinates.html",
        "tab_name": "ps-parallel-coords-tab",
        "tab_name_full": "PS Para. Coord.",
        "element": "html"
    }
]

def name_from_href(href: str, username: str) -> str:
    """Extracts the file/directory name from the given response href.

    Args:
    -`href:str`: The href attribute to parse
    -`username:str`: The username of the WebDAV index, used for splitting the filename
        from the whole URN.
    Returns:
    -`str`: The extracted name of the file/directory
    """
    splitted = str(href).split(username)
    if len(splitted) < 2:
        # the username does not appear in the href, something must be wrong
        return href
    return splitted[1]

def parse_webdav_files_response(content: str, username: str) -> tuple[bool,list]:
    """Parses the XML response from a WebDAV PROPFIND request and extracts file and directory
    information.

    Args:
    -`content:str`: The XML content of the WebDAV PROPFIND response.
    -`username:str`: The username of the WebDAV index, used for extracting file/directory names.
    Returns:
    -`list`: A list of dictionaries, each containing information about a file or directory.
    """
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return False, []

    namespaces = {
        "d": "DAV:",
        "s": "http://sabredav.org/ns",
        "oc": "http://owncloud.org/ns",
        "nc": "http://nextcloud.org/ns"
    }

    files = []
    for response_tag in root.findall("d:response", namespaces):
        href = response_tag.findtext("d:href", "", namespaces)
        content_type = ""
        resource_type = ""
        is_dir = False

        for propstat in response_tag.findall("d:propstat", namespaces):
            status = propstat.findtext("d:status", "", namespaces)
            if status == "HTTP/1.1 404 Not Found":
                continue

            prop = propstat.find("d:prop", namespaces)
            if prop is None:
                continue
            content_type = prop.findtext("d:getcontenttype", "", namespaces)
            resource_type = prop.find("d:resourcetype", namespaces)
            if (
                resource_type is not None and resource_type != ""
                and len(resource_type.findall("d:collection", namespaces)) > 0
            ):
                is_dir = True

        files.append({
            "name": name_from_href(href, username),
            "is_dir": is_dir,
            "content_type": content_type
        })

    return True, files

def filename_from_nc_path(file_path: str) -> str:
    """Extracts a file's name from its full NC-like path.

    Args:
    -`file_path:str`: The full NC-like path
    Returns:
    -`str`: The extracted filename
    """
    splitted = str(file_path).split("/")
    return splitted[len(splitted)-1]

def encode_nc_path(path: str) -> str:
    """Encodes the given NC-like path and removes leading and trailing slashes.

    Args:
    -`path:str`: The NC-like path
    Returns:
    -`str`: The encoded NC-like path with stripped slashes
    """
    parts = unquote(path).split("/")
    parts = [quote(p) for p in parts if p != ""]
    return "/".join(parts)
