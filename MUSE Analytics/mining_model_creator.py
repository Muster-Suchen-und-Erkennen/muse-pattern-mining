#! /usr/bin/python3

"""Python script to create mining models for muse."""

import argparse
import re
from os import path
from xml.etree import ElementTree as ET

from typing import List, Union, Set, Tuple, TypeVar

# Controls wether or not unused columns will be deleted before saving
REMOVE_UNUSED_COLUMNS = True  # type: bool

# Columns that should never be removed
DONT_REMOVE_COLUMNS = ('Genre', 'Rollenrelevanz', 'Geschlecht', 'Dominante Charaktereigenschaft')  # type: Tuple

# Output folder
OUTPUT_FOLDER = 'MUSE Analytics'


class MiningColumn():
    """Class for representing mining columns in a mining model."""

    node = None  # type: ET

    def __init__(self, node: ET):
        self.node = node

    @property
    def nested(self) -> bool:
        """If the column is a nested table."""
        col_type = self.node.attrib['{{{}}}type'.format(Document.namespaces['xsi'])]
        return col_type == 'TableMiningStructureColumn'

    @property
    def child(self) -> 'MiningColumn':
        """Return the first child column if the column is nested."""
        if not self.nested:
            return None
        else:
            node = self.node.find('./default:Columns/default:Column', Document.namespaces)
            return MiningColumn(node)

    @property
    def name(self) -> str:
        """The name of the mining column."""
        return self.node.find('./default:Name', Document.namespaces).text

    @property
    def id(self) -> str:
        """The ID of the mining column."""
        return self.node.find('./default:ID', Document.namespaces).text

    def __str__(self):
        """The name of the column (if nested the name of the child column)."""
        if not self.nested:
            return self.name
        else:
            return str(self.child)

    __repr__ = __str__

    def matches(self, column: Union[str, 'MiningColumn'], strict: bool=False) -> bool:
        """
        Check if the given column or name matches this column.

        strict -- if true: only exact match (default: False)
        """
        if isinstance(column, MiningColumn):
            column = str(column)
        to_compare = str(self)
        if column == to_compare:
            return True
        if not strict:
            regex = re.compile('.[Ll]?[0-9]+$')
            column = re.sub(regex, '', column)
            to_compare = re.sub(regex, '', to_compare)
            return to_compare == column
        return False

    def create_mining_node(self, parent: ET, usage: str=None):
        """
        Create a mining node under given parent node.

        usage: 'Key', 'Predict' or 'PredictOnly'
        """
        col = ET.SubElement(parent, 'Column')
        ET.SubElement(col, 'ID').text = self.name
        ET.SubElement(col, 'Name').text = self.name
        ET.SubElement(col, 'SourceColumnID').text = self.id
        if usage:
            ET.SubElement(col, 'Usage').text = usage
        if self.nested:
            columns = ET.SubElement(col, 'Columns')
            self.child.create_mining_node(columns, 'Key')


class Document():
    """Class representing the whole xml document."""

    namespaces = {
        'default': 'http://schemas.microsoft.com/analysisservices/2003/engine',
        'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        'dwd': 'http://schemas.microsoft.com/DataWarehouse/Designer/1.0'
    }  # type: dict
    filename = None  # type: str
    xml = None  # type: ET
    root = None  # type: str
    input_columns = None  # type: List[MiningColumn]
    output_column = None  # type: MiningColumn

    def __init__(self, filename: str):
        ET.register_namespace('', 'http://schemas.microsoft.com/analysisservices/2003/engine')
        ET.register_namespace('xsd', 'http://www.w3.org/2001/XMLSchema')
        ET.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        ET.register_namespace('ddl2', 'http://schemas.microsoft.com/analysisservices/2003/engine/2')
        ET.register_namespace('ddl2_2', 'http://schemas.microsoft.com/analysisservices/2003/engine/2/2')
        ET.register_namespace('ddl100_100', 'http://schemas.microsoft.com/analysisservices/2008/engine/100/100')
        ET.register_namespace('ddl200', 'http://schemas.microsoft.com/analysisservices/2010/engine/200')
        ET.register_namespace('ddl200_200', 'http://schemas.microsoft.com/analysisservices/2010/engine/200/200')
        ET.register_namespace('ddl300', 'http://schemas.microsoft.com/analysisservices/2011/engine/300')
        ET.register_namespace('ddl300_300', 'http://schemas.microsoft.com/analysisservices/2011/engine/300/300')
        ET.register_namespace('ddl400', 'http://schemas.microsoft.com/analysisservices/2012/engine/400')
        ET.register_namespace('ddl400_400', 'http://schemas.microsoft.com/analysisservices/2012/engine/400/400')
        ET.register_namespace('dwd', 'http://schemas.microsoft.com/DataWarehouse/Designer/1.0')

        self.filename = filename
        self.load()

    def load(self):
        """(Re-)Load the document."""
        self.xml = ET.parse(self.filename)
        self.root = path.basename(self.filename).split('_')[0]
        self.input_columns = []

    def __repr__(self):
        repr = [
            'Document',
            '========',
            '',
            'Name: {}'.format(self.name),
            'Predicting:',
            '    {}'.format(self.output_column),
            'Using:'
        ]
        for col in self.input_columns:
            repr.append('    {}'.format(col))
        return '\n'.join(repr)

    __str__ = __repr__

    @property
    def mining_columns(self) -> List[MiningColumn]:
        """A list of all possible mining columns."""
        nodes = self.xml.getroot().findall("./default:Columns/default:Column", Document.namespaces)
        columns = [MiningColumn(x) for x in nodes]
        columns.sort(key=str)
        return columns

    @property
    def used_columns(self) -> Set[str]:
        """A set of all mining used columns."""
        nodes = self.xml.getroot().findall(
            "./default:MiningModels/default:MiningModel/default:Columns//default:Column/default:SourceColumnID", Document.namespaces)
        names = set(x.text for x in nodes)
        for col in self.input_columns:
            names.add(str(col))
        names.add(str(self.output_column))
        return names

    @property
    def name(self) -> str:
        """The name of this document."""
        name = [self.root]
        if self.input_columns:
            name.append(str(self.input_columns[0]).replace(' ', '-'))
        if self.output_column:
            name.append(str(self.output_column).replace(' ', '-'))
        return '{}__{}'.format(self.root, self.part_name)

    @property
    def part_name(self) -> str:
        """Part of the name containing used mining columns."""
        name = []
        if self.input_columns:
            name.append(str(self.input_columns[0]).replace(' ', '-'))
        if self.output_column:
            name.append(str(self.output_column).replace(' ', '-'))
        if not name:
            return 'null_null'
        return '_'.join(name)

    def clear_selection(self):
        """Clear the selection."""
        self.input_columns = []
        self.output_column = None

    def prepare(self):
        """Prepare the document for writing."""
        uuids = self.xml.getroot().findall('.//*[@dwd:design-time-name]', Document.namespaces)
        for node in uuids:
            del node.attrib['{http://schemas.microsoft.com/DataWarehouse/Designer/1.0}design-time-name']
        self.xml.getroot().find('./default:ID', Document.namespaces).text = 'ms_{}'.format(self.name)
        self.xml.getroot().find('./default:Name', Document.namespaces).text = 'ms_{}'.format(self.name)
        # Mining models
        models = self.xml.getroot().findall('./default:MiningModels/default:MiningModel', Document.namespaces)
        for model in models:
            self._prepare_model_columns(model)
            if model.find('./default:Name', Document.namespaces).text.startswith('western'):
                model.find('./default:ID', Document.namespaces).text = 'ms_western__{}'.format(self.name)
                model.find('./default:Name', Document.namespaces).text = 'western__{}'.format(self.name)
            elif model.find('./default:Name', Document.namespaces).text.startswith('highschool_komoedie'):
                model.find('./default:ID', Document.namespaces).text = 'ms_highschool_komoedie__{}'.format(self.name)
                model.find('./default:Name', Document.namespaces).text = 'highschool_komoedie__{}'.format(self.name)

    def _prepare_model_columns(self, model: ET.Element):
        """Prepare the mining columns for the different models."""
        column_root = model.find('./default:Columns', Document.namespaces)  # type: ET.Element
        columns = model.findall('./default:Columns/default:Column', Document.namespaces)
        for col in columns:
            usage = col.find('./default:Usage', Document.namespaces)
            if (usage is not None) and (usage.text == 'Key'):
                continue
            column_root.remove(col)
        for col in self.input_columns:
            col.create_mining_node(column_root)
        # predict column:
        self.output_column.create_mining_node(column_root, usage='PredictOnly')

    def remove_unused(self, ignore: Tuple=DONT_REMOVE_COLUMNS):
        """Remove all unused mining colums."""
        column_root = self.xml.getroot().find("./default:Columns", Document.namespaces)
        used = self.used_columns
        for name in ignore:
            used.add(name)
        for col in self.mining_columns:
            for name in used:
                if col.matches(name):
                    break
            else:
                column_root.remove(col.node)

    def write(self, output_folder: str=OUTPUT_FOLDER):
        """Write the prepared file to disk."""
        self.xml.write(path.join(output_folder, 'ms_{}.dmm'.format(self.name)), encoding='utf-8')

        # fix first line of xml not containing all namespaces:
        # pylint: disable=line-too-long
        firstline = '<MiningStructure xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:ddl2="http://schemas.microsoft.com/analysisservices/2003/engine/2" xmlns:ddl2_2="http://schemas.microsoft.com/analysisservices/2003/engine/2/2" xmlns:ddl100_100="http://schemas.microsoft.com/analysisservices/2008/engine/100/100" xmlns:ddl200="http://schemas.microsoft.com/analysisservices/2010/engine/200" xmlns:ddl200_200="http://schemas.microsoft.com/analysisservices/2010/engine/200/200" xmlns:ddl300="http://schemas.microsoft.com/analysisservices/2011/engine/300" xmlns:ddl300_300="http://schemas.microsoft.com/analysisservices/2011/engine/300/300" xmlns:ddl400="http://schemas.microsoft.com/analysisservices/2012/engine/400" xmlns:ddl400_400="http://schemas.microsoft.com/analysisservices/2012/engine/400/400" xmlns:dwd="http://schemas.microsoft.com/DataWarehouse/Designer/1.0" dwd:design-time-name="9a04bc07-3516-401d-bb79-9590a3dca94b" xmlns="http://schemas.microsoft.com/analysisservices/2003/engine">\n'
        lines = ['']
        with open(path.join(output_folder, 'ms_{}.dmm'.format(self.name))) as file:
            lines = file.readlines()
        lines[0] = firstline
        with open(path.join(output_folder, 'ms_{}.dmm'.format(self.name)), mode='w') as file:
            lines = file.writelines(lines)
        self.write_project_item(output_folder)

    def write_project_item(self, output_folder: str=OUTPUT_FOLDER):
        """Append the project item xml code to a temp file."""
        with open(path.join(output_folder, 'project_items.txt'), mode='a') as file:
            file.write('    <ProjectItem>\n')
            file.write('      <Name>ms_{}.dmm</Name>\n'.format(self.name))
            file.write('      <FullPath>ms_{}.dmm</FullPath>\n'.format(self.name))
            file.write('    </ProjectItem>\n')


T = TypeVar('T')


def print_selection(description: str, list: List[T], select: int=None) -> T:
    """Print a selection menu."""
    print('\n\n\n')
    print(description)
    print('\n')
    for i, name in enumerate(list):
        print('{: 3} {}'.format(i, str(name)))
    print('')
    if not select:
        select = int(input('Your selection: '), base=10)
    print('You chose: {}'.format(list[select]))
    return list[select]


def add_input_column(doc: Document, default: int=None):
    """Ask the user to add an input column."""
    col = print_selection('Choose a INPUT column:', doc.mining_columns, default)
    doc.input_columns.append(col)


def add_output_column(doc: Document, default: int=None):
    """Ask the user to add an output column."""
    col = print_selection('Choose a OUTPUT column:', doc.mining_columns, default)
    doc.output_column = col


def final_check(doc: Document) -> bool:
    """Ask user before writing to disc."""
    print('\n\n')
    print('Please check your inputs: \n')
    print(doc)
    print('\n')
    result = input('Is everything correct? ([y]es, [n]o) [default: y]: ')
    if result in ('yes', 'y', 'YES', 'Yes', 'Y', 'j', 'J', 'ja', 'JA', 'Ja', ''):
        return True
    return False


def main():
    """Main input loop."""
    parser = argparse.ArgumentParser(description='Create a new mining model from the template.')
    parser.add_argument('file')
    args = parser.parse_args()
    doc = Document(args.file)

    while True:
        add_input_column(doc)
        add_output_column(doc)
        if final_check(doc):
            break
        doc.clear_selection()
    else:
        doc.clear_selection()
        print('exiting program')
        return

    doc.prepare()
    if REMOVE_UNUSED_COLUMNS:
        doc.remove_unused()
    doc.write()

if __name__ == '__main__':
    main()
