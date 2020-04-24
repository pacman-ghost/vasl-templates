#!/usr/bin/env python3
""" Manage VASL build files. """

import os
import zipfile
import itertools

from lxml import etree
import click

# ---------------------------------------------------------------------

class BuildFile:
    """Wrapper around a VASL module's buildFile."""

    def __init__( self, build_file ):
        self.doc_root = etree.fromstring( build_file ) #pylint: disable=c-extension-no-member
        self.attribs = self.doc_root.attrib

    def dump( self, line_nos=False, images=False ):
        """Dump the BuildFile."""

        # dump the module header
        click.echo( "Name:         {}".format( self.attribs.get( "name" ) ) )
        click.echo( "Description:  {}".format( self.attribs.get( "description" ) ) )
        click.echo( "Version:      {}".format( self.attribs.get( "version" ) ) )
        click.echo( "VASSAL:       {}".format( self.attribs.get( "VassalVersion" ) ) )
        click.echo( "Next slot ID: {}".format( self.attribs.get( "nextPieceSlotId" ) ) )
        click.echo()

        # initialize
        opts = { "extract_images": images }

        def dump_node( node, depth=0 ):
            """Dump an XML node and its children."""

            # dump each child node
            for child in node:

                # get the attributes we want to dump
                attribs = get_attrib_vals( child, opts )

                if depth == 0:
                    # this is a top-level node, show it with a header
                    header = click.style( "===", fg="green" )
                    val = click.style( child.tag, fg="green" )
                    if line_nos:
                        val += ":{}".format( click.style( str(child.sourceline), fg="cyan" ) )
                    click.echo( "{} {} {}".format( header, val, header ) )
                    click.echo()
                    # dump any attributes
                    if attribs:
                        for key,val in attribs:
                            click.echo( "{} = {}".format( key, val ) )
                        click.echo()
                else:
                    # this a lower-level node, show it normally
                    val = click.style( child.tag, fg="yellow" )
                    tab = "  " * (depth-1)
                    click.echo( tab+val, nl=False )
                    if line_nos:
                        click.echo( ":{}".format( click.style( str(child.sourceline), fg="cyan" ) ), nl=False )
                    if attribs:
                        attribs = [ "{}={}".format( k, v ) for k,v in attribs ]
                        click.echo( ": {}".format( " ; ".join( attribs ) ) )
                    else:
                        click.echo()

                # dump child nodes
                dump_node( child, depth+1 )

            if depth == 1 and len(list(node.getchildren())) > 0: #pylint: disable=len-as-condition
                click.echo()

        # dump the XML document
        dump_node( self.doc_root )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _get_node_cdata( node, opts ): #pylint: disable=unused-argument
    """Get the CDATA for a node."""
    return "cdata", node.text

def _get_pieceslot_images( node, opts ):
    """Get any image paths in a PieceSlot."""

    # check if we need to do this
    if not opts["extract_images"]:
        return None, None

    # IMPORTANT! The data in the build file looks like a serialized object, so we use
    # a bunch of heuristics to try to identify the fields we want :-/ This means that
    # we might sometimes return the wrong results :-(

    # split the data into fields
    val = node.text.replace( "\\/", "/" )
    fields = val.split( ";" ) # fields seem to be semicolon-separated
    fields = [ f.split(",") for f in fields ] # fields can have comma-separated sub-fields
    fields = [ f.strip() for f in itertools.chain(*fields) ]
    fields = [ f for f in fields if f ]

    # identify fields that look like an image path
    valid_prefixes = ( "ru/", "ge/", "am/", "br/", "it/", "ja/", "ch/", "sh/", "fr/", "al/", "ax/", "hu/", "fi/",
        "po/", "ss/", # nb: for BFP
    )
    def is_image_path( val ):
        """Check if a value looks like an image path."""
        if val.endswith( (".gif",".png") ):
            return True
        if val.startswith( valid_prefixes ):
            return True
        return False
    fields = [ f for f in fields if is_image_path(f) ]

    # return the final results
    return "images", ";".join(fields) if fields else None

# which attributes to dump for each type of XML node in the build file
NODE_ATTRIBS_TO_DUMP = {
    "VASL.build.module.ASLMap":[ "mapName" ],
    "VASSAL.build.module.ChartWindow": [ "name" ],
    "VASSAL.build.module.Map": [ "mapName"],
    "VASSAL.build.module.PieceWindow": [ "name" ],
    "VASSAL.build.widget.TabWidget": [ "entryName?" ],
    "VASSAL.build.widget.ListWidget": [ "entryName?" ],
    "VASSAL.build.widget.Chart": [ "chartName", "fileName" ],
    "VASSAL.build.widget.PanelWidget": [ "entryName?", "nColumns" ],
    "VASSAL.build.widget.BoxWidget": [ "entryName" ],
    "VASSAL.build.widget.PieceSlot": [ "gpid", "entryName", _get_pieceslot_images ],
    "VASSAL.build.module.PrototypeDefinition": [ "name" ],
    "VASSAL.build.module.documentation.HelpFile": [ "title", "fileName" ],
    "VASSAL.build.module.documentation.AboutScreen": [ "title", "fileName" ],
    "VASSAL.build.module.documentation.BrowserHelpFile": [ "title", "fileName" ],
    "option": [ "name" ], # nb: these appear under VASSAL.build.module.GlobalOptions
    "entry": [ "name", _get_node_cdata ], # nb: these appear under VASL.build.module.map.MassRemover
}

def get_attrib_vals( node, opts ):
    """Get the attribute values we're interested in from an XML node."""

    # figure out which attributes we're interested in
    attribs = NODE_ATTRIBS_TO_DUMP.get( node.tag, [] )
    if attribs == "*":
        attribs = node.attrib.keys()

    # get the attribute values
    def get_attr_val( attr ):
        """Get the value for the specified attribute."""
        if callable( attr ):
            return attr( node , opts )
        if attr.endswith( "?" ):
            # nb: this is an optional attribute (we don't show it if not present)
            attr = attr[:-1]
            return attr, node.attrib.get( attr )
        else:
            # nb: we expect this attribute to be present, return a "missing" marker if it's not
            return attr, node.attrib.get( attr, "???" )
    vals = [ get_attr_val(a) for a in attribs ]

    # return the final results
    return [ (k,v) for k,v in vals if v is not None ]

# ---------------------------------------------------------------------

@click.command()
@click.argument( "input-file", type=click.File("rb") )
@click.option( "-l","--line-nos", is_flag=True, help="Include line numbers for each XML node." )
@click.option( "-i","--images", is_flag=True, help="Show images paths for each PieceSlot." )
def main( input_file, line_nos, images ):
    """Dump a VASL build file."""

    # check if we've been given a .vmod file
    if os.path.splitext( input_file.name )[1] == ".vmod":
        # yup - extract the build file
        zip_file = zipfile.ZipFile( input_file.name, "r" )
        build_file = zip_file.read( "buildFile" )
    else:
        # nope - read the build file from the specified file
        build_file = input_file.read()

    # load and dump the build file
    build_file = BuildFile( build_file )
    build_file.dump( line_nos=line_nos, images=images )

# ---------------------------------------------------------------------

if __name__ == "__main__":
    main() #pylint: disable=no-value-for-parameter
