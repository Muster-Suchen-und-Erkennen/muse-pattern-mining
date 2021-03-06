#! /usr/bin/python3

"""Python script to create mining models for muse."""

import argparse
import re
import csv
import hashlib
humanhash = None
try:
    import humanhash
except ImportError:
    pass
from os import path, remove
from pathlib import Path
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

    @property
    def level(self) -> int:
        level = re.match('.*[Ll]?([0-9]+)$', str(self))
        if not level:
            return 0
        for group in level.groups():
            return max(map(int, group))

    @property
    def shortname(self):
        name = str(self)
        return re.sub('[-_\s]*[Ll]?[0-9]+$', '', name)

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
            column = regex.sub('', column)
            to_compare = regex.sub('', to_compare)
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

    def __init__(self, filename: str, name: str=None):
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

        self._name = name

    def load(self):
        """(Re-)Load the document."""
        self.xml = ET.parse(self.filename)
        self.root = path.basename(self.filename).rstrip('_vorlage.dmm').strip('ms_')
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
        """The name of this documentnormalized to 100 characters."""
        name = ''
        if self._name:
            name = self._name
        else:
            name = '{}__{}'.format(self.root, self.part_name)
        if len(name) > 100:
            part_name = hashlib.sha256(self.part_name.encode()).hexdigest()
            if humanhash:
                part_name = humanhash.humanize(part_name, words=3)
            name = '{}__{}__{}'.format(self.root, part_name, self.output_column.shortname)[:100]
        return name

    @property
    def part_name(self) -> str:
        """Part of the name containing used mining columns."""
        name = []
        if self.input_columns:
            name.append('_'.join([col.shortname for col in self.input_columns]))
        if self.output_column:
            name.append(self.output_column.shortname)
        if not name:
            return 'null_null'
        return '__'.join(name)

    def get_columns_by_name(self, col_name):
        matches = [col for col in self.mining_columns if col.matches(col_name)]
        return matches

    def clear_selection(self):
        """Clear the selection."""
        self.input_columns = []
        self.output_column = None

    def prepare(self):
        """Prepare the document for writing."""
        uuids = self.xml.getroot().findall('.//*[@dwd:design-time-name]', Document.namespaces)
        for node in uuids:
            del node.attrib['{http://schemas.microsoft.com/DataWarehouse/Designer/1.0}design-time-name']
        self.xml.getroot().find('./default:ID', Document.namespaces).text = self.name
        self.xml.getroot().find('./default:Name', Document.namespaces).text = self.name
        # Mining models
        models = self.xml.getroot().findall('./default:MiningModels/default:MiningModel', Document.namespaces)
        for model in models:
            self._prepare_model_columns(model)
            if 'western' in model.find('./default:Name', Document.namespaces).text:
                model.find('./default:ID', Document.namespaces).text = 'western__{}'.format(self.name)[:100]
                model.find('./default:Name', Document.namespaces).text = 'western__{}'.format(self.name)[:100]
            elif 'highschool_komoedie' in model.find('./default:Name', Document.namespaces).text:
                model.find('./default:ID', Document.namespaces).text = 'highschool_komoedie__{}'.format(self.name)[:100]
                model.find('./default:Name', Document.namespaces).text = 'highschool_komoedie__{}'.format(self.name)[:100]
            elif 'maerchen' in model.find('./default:Name', Document.namespaces).text:
                model.find('./default:ID', Document.namespaces).text = 'maerchen__{}'.format(self.name)[:100]
                model.find('./default:Name', Document.namespaces).text = 'maerchen__{}'.format(self.name)[:100]

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

    def write(self):
        """Write the prepared file to disk."""
        new_model = Path(self.filename).resolve().parent / Path('{}.dmm'.format(self.name))
        if new_model.exists():
            if not confirm('Model {} already exists! Override existing Model?'.format(self.name), default=False):
                return
        self.xml.write(str(new_model), encoding='utf-8')

        # fix first line of xml not containing all namespaces:
        # pylint: disable=line-too-long
        firstline = '<MiningStructure xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:ddl2="http://schemas.microsoft.com/analysisservices/2003/engine/2" xmlns:ddl2_2="http://schemas.microsoft.com/analysisservices/2003/engine/2/2" xmlns:ddl100_100="http://schemas.microsoft.com/analysisservices/2008/engine/100/100" xmlns:ddl200="http://schemas.microsoft.com/analysisservices/2010/engine/200" xmlns:ddl200_200="http://schemas.microsoft.com/analysisservices/2010/engine/200/200" xmlns:ddl300="http://schemas.microsoft.com/analysisservices/2011/engine/300" xmlns:ddl300_300="http://schemas.microsoft.com/analysisservices/2011/engine/300/300" xmlns:ddl400="http://schemas.microsoft.com/analysisservices/2012/engine/400" xmlns:ddl400_400="http://schemas.microsoft.com/analysisservices/2012/engine/400/400" xmlns:dwd="http://schemas.microsoft.com/DataWarehouse/Designer/1.0" dwd:design-time-name="9a04bc07-3516-401d-bb79-9590a3dca94b" xmlns="http://schemas.microsoft.com/analysisservices/2003/engine">\n'
        lines = ['']
        with new_model.open() as file:
            lines = file.readlines()
        lines[0] = firstline
        with new_model.open(mode='w') as file:
            lines = file.writelines(lines)
        self.write_project_item()

    def write_project_item(self):
        """Add the mining model to the project file."""
        project_files = Path(self.filename).resolve().parent.glob('*.dwproj')
        for project in project_files:
            lines = None
            with project.open() as file:
                lines = file.readlines()
            for line in lines:
                if self.name in line:
                    # dmm already exists in project
                    return
            with project.open(mode='w') as file:
                for line in lines:
                    if '</MiningModels>' in line:
                        file.write('    <ProjectItem>\n')
                        file.write('      <Name>{}.dmm</Name>\n'.format(self.name))
                        file.write('      <FullPath>{}.dmm</FullPath>\n'.format(self.name))
                        file.write('    </ProjectItem>\n')
                    file.write(line)

    def delete(self):
        """Delete existing model from disk."""
        new_model = Path(self.filename).resolve().parent / Path('{}.dmm'.format(self.name))
        if new_model.exists():
            remove(str(new_model))
        self.remove_project_item()

    def remove_project_item(self):
        """Add the mining model to the project file."""
        project_files = Path(self.filename).resolve().parent.glob('*.dwproj')

        def project_items(lines):
            """Group project items into one string."""
            index = 0
            while index < len(lines):
                line = lines[index]
                if '<ProjectItem>' in line:
                    while '</ProjectItem>' not in line:
                        index += 1
                        line += lines[index]
                yield line
                index += 1

        for project in project_files:
            lines = None
            with project.open() as file:
                lines = file.readlines()
            lines = [line for line in project_items(lines) if self.name not in line]
            with project.open(mode='w') as file:
                file.writelines(lines)

    def export_mining_columns(self) -> str:
        columns = sorted(self.mining_columns, key=str)
        last_col = None
        filtered = []
        for col in columns:
            if last_col and col.matches(last_col):
                continue
            else:
                last_col = col
                if col.shortname.upper() != 'ID':
                    filtered.append(col.shortname)
        filtered.sort()
        output = Path(self.filename).resolve()
        output = output.parent / Path(output.stem + '.csv')
        if output.exists():
            if not confirm('CSV File for {} already exists! Override CSV File?'.format(output.stem), default=False):
                return
        with output.open(mode='w') as csv_file:
            writer = csv.writer(csv_file, delimiter=';')
            writer.writerow([''] + filtered + ['filename'])
            for row in filtered:
                writer.writerow([row] + ['']*(len(filtered) + 1))


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
    return confirm('Is everything correct?')


def confirm(message: str, default: bool=True) -> bool:
    default = 'y' if default else 'n'
    result = input('{message} ([y]es, [n]o) [default: {default}]: '.format(message=message, default=default))
    while True:
        if result.isspace() or result == '':
            return default
        elif result in ('yes', 'y', 'YES', 'Yes', 'Y', 'j', 'J', 'ja', 'JA', 'Ja'):
            return True
        elif result in ('no', 'n', 'NO', 'No', 'N', 'nein', 'Nein', 'NEIN'):
            return False
        else:
            result = input('Please answer with [y]es or [n]o. [default: {default}]: '.format(default=default))


def find_model_by_name(name: str) -> Path:
    if not name.endswith('.dmm'):
        name += '.dmm'
    models = Path().rglob('*.dmm')
    for model in models:
        if model.name == name:
            return model


def find_csv_by_name(name: str) -> Path:
    if not name.endswith('.csv'):
        name += '.csv'
    models = Path().rglob('*.csv')
    for model in models:
        if model.name == name:
            return model


def initialize_argument_parser():
    parser = argparse.ArgumentParser(description='Create a new mining model from the template.\n'
                                     'Use "extract" to extract possible mining columns into a csv.\n'
                                     'Use "create" to create all specified mining models from a csv.\n'
                                     'For more help please look in the readme.md.')
    parser.add_argument('operation', type=str, choices=('extract', 'create', 'delete'), metavar='operation', help='"create" to create new mining models, "extract" to extract mining columns from a mining model or "delete" to delete created mining models.')
    parser.add_argument('--multiple-input-columns', '-m', dest='multiple', action='store_true',
                        help='If creating mining models "--multiple-input-columns" allows multiple input columns for a single model.')
    parser.add_argument('--model', type=str, help='The Mining Model used as base Model for creating new Models. Only used if operation is "create" or "delete".')
    parser.add_argument('filename', type=str, help='Either the name of the model (if "extract") or the name of the csv file (if "create" or "delete").')
    return parser


def update_multiple_models(input_columns, output_column, model, output_name: str, create: bool=True):
    """Create/Delete multiple mining models."""
    print(input_columns, '->', output_column)
    doc = Document(str(model), output_name)
    doc.output_column = max(doc.get_columns_by_name(output_column),
                            key=lambda x: x.level)
    for col in input_columns:
        col = max(doc.get_columns_by_name(col), key=lambda x: x.level)
        doc.input_columns.append(col)
    print(doc.name)
    if create:
        doc.prepare()
        if REMOVE_UNUSED_COLUMNS:
            doc.remove_unused()
        doc.write()
    else:
        doc.delete()


def update_single_model(input_rows, output_column, model, create: bool=True):
    """Create/Delete single mining model."""
    for input_columns in input_rows:
        print(input_columns, '->', output_column)
        doc = Document(str(model))
        doc.output_column = max(doc.get_columns_by_name(output_column),
                                key=lambda x: x.level)
        doc.input_columns.append(max(doc.get_columns_by_name(input_columns),
                                     key=lambda x: x.level))
        if create:
            doc.prepare()
            if REMOVE_UNUSED_COLUMNS:
                doc.remove_unused()
            doc.write()
        else:
            doc.delete()


def main():
    """Main input loop."""
    parser = initialize_argument_parser()
    args = parser.parse_args()

    if args.operation == 'extract':
        model = find_model_by_name(args.filename)
        if not model:
            print("Model could not be found!")
            return
        doc = Document(str(model))
        doc.export_mining_columns()

    elif args.operation in ('create', 'delete'):
        csv_file = find_csv_by_name(args.filename)
        if not csv_file:
            print("CSV File could not be found!")
            return
        model = None
        if args.model:
            model = find_model_by_name(args.model)
        else:
            model = find_model_by_name(csv_file.stem)
        if not model:
            print("Model for CSV File could not be found!")
            return
        with csv_file.open() as csv_file:
            reader = csv.DictReader(csv_file, delimiter=';')
            for row in reader:
                output_column = row.pop('', None)
                output_name = row.pop('filename', None)
                input_columns = [key for key in row if row[key]]
                if output_column is not None and input_columns:
                    if args.multiple:
                        update_multiple_models(input_columns, output_column, model, output_name, args.operation == 'create')
                    else:
                        update_single_model(input_columns, output_column, model, args.operation == 'create')


if __name__ == '__main__':
    main()
