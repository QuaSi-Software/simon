"""Various utility functions for the webapp."""

from __future__ import annotations
import xml.etree.ElementTree as ET

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
