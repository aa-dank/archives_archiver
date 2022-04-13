import base64
import os
import logging
import random
import subprocess
import shutil
import sys
import threading
import time
import pandas as pd
import PySimpleGUI as sg

from thefuzz import fuzz
from collections import defaultdict
from datetime import datetime

#Version Number
__version__ = 1.13

# Typing Aliases
# pysimplegui_layout

# Environmental Variables
RECORDS_SERVER_LOCATION = r"""R:\\""" #TODO how to prevent the four backslashes
FILENAMES_TO_IGNORE = ["desktop.ini", "desktop.ini"]
DIRECTORY_CHOICES = ['A - General', 'B - Administrative Reviews and Approvals', 'C - Consultants',
                     'D - Environmental Review Process', 'E - Program and Design',
                     'F - Bid Documents and Contract Award', 'G - Construction', "H - Submittals and O&M's",
                     'A1 - Miscellaneous', 'A2 - Working File', 'A3 - Project Directory Matrix & Project Chronology',
                     "B1 - CPS and Chancellor's Approvals", 'B100 - Other', 'B11 - LEED',
                     'B12 - Outside Regulatory Agencies', 'B13 - Coastal Commission',
                     'B2 - Office of the President UC Regents', 'B3 - State Public Works Board',
                     'B4 - Department of Finance', 'B5 - Legislative Submittals', 'B6 - State Fire Marshal',
                     'B7 - Office of State Architect  (DSA)', 'B8 -  General Counsel',
                     'B8.1 - General Counsel - Confidential', 'C1 - Executive Architect', 'C1.1 - Selection',
                     'C1.2 - Correspondence', 'C1.3 - Agreement', 'C2 - Other Consultants', 'C2.1 - Selection',
                     'C2.2 - Correspondence', 'C2.3 - Agreement', 'D1 - Environmental Correspondences',
                     'D2 - EIC Forms', 'D3 - CEQA Documentation', 'D4 - Mitigation Monitoring Program', 'E1 - DPP',
                     'E2 - PPG', 'E3 - Budget Cost Estimates', 'E4 - Planning Schedules',
                     'E5 - Program and Design Correspondences', 'E5.1 - Executive Architect Correspondences',
                     'E5.2 - Special Consultants', 'E5.3 - Users. Building Committee. Campus Correspondences',
                     'E5.4 - PPC and PP', 'E5.5 - Office of the President to.from', 'E5.6 - Building Committee to.from',
                     'E5.7 - Other', 'E5.8 - Office of General Counsel', 'E6 - Reports (soils, structural, calcs)',
                     'E7 - Value Engineering', 'E7.1 - Value Engineering Correspondence',
                     'E7.2 - VE Workshop Minutes, Summaries, Final Reports', 'E8 - Program and Design Meeting Minutes',
                     'F1 - Bid and Contract Award Correspondence', 'F1.1 - Executive Architect Correspondences',
                     'F1.2 - Special Consultants Correspondences', 'F1.4 - PPC and PP',
                     'F1.5 - Office of the President Correspondences', 'F1.6 - General Counsel Correspondences',
                     'F1.7 - Pre-Qualification', 'F1.8 - Other', 'F10 - Escrow Agreement',
                     'F2 - Reviews', 'F2.1 - Constructibility, Code Reviews', 'F2.2 - In-house. PP reviews',
                     'F2.3 - Independent Cost Review', 'F2.4 - Independent Seismic Review', 'F2.5 - Other',
                     'F5 - Drawings and Spec', 'F7 - Bid Summary Forms', 'F7.1 - Bid Protest', 'F8 - Contract',
                     'F9 - Builders Risk Insurance', 'G1 - Construction Correspondence',
                     'G1.1 - Contractor Correspondences', 'G1.2 - Executive Architect Correspondences',
                     'G1.3 - Users.Building Committee.Campus Correspondences', 'G1.4 - PPC and PP. Certified Payroll',
                     'G1.5 - Geotechnical Engineer Correspondences',
                     'G1.6 - Testing and Inspection to Laboratory Correspondences',
                     'G1.7 - General Counsel Correspondences', 'G1.8 - Other',
                     'G10 - Testing and Inspection Reports.Other',
                     'G11 - Proposal Requests. Bulletins. Contractors Response', 'G12 - Request for Information RFI',
                     'G13 - Letter of Instruction LOI', 'G14 - User Request Change in Scope', 'G15 - Change Order',
                     'G16 - Field Orders', 'G17 - Warranties and Guarantees', 'G18 - Punchlist', 'G19 - NOC',
                     'G2 - Certificate of Payment', 'G20 - Warranty Deficiency', 'G21 - Construction Photos',
                     'G22 - Claims. Public Records Act', 'G22.1 - Claims Confidential', 'G23 - Commissioning',
                     'G24 - Building Permits', "G3 - Contractor's Schedule and Updates", 'G4 - Progress Meeting Notes',
                     'G5 - UCSC Inspectors Daily Reports', 'G5.1 - Hot Work Permits', 'G6 - UCSC Memoranda',
                     'G6.1 - Architects Field Reports', 'G7 - Contractors Daily Reports',
                     'G8 - Testing and Inspection Reports. Geotechnical Engineer']


class ArchiverHelpers:

    @staticmethod
    def split_path(path):
        '''splits a path into each piece that corresponds to a mount point, directory name, or file'''
        allparts = []
        while 1:
            parts = os.path.split(path)
            if parts[0] == path:  # sentinel for absolute paths
                allparts.insert(0, parts[0])
                break
            elif parts[1] == path:  # sentinel for relative paths
                allparts.insert(0, parts[1])
                break
            else:
                path = parts[0]
                allparts.insert(0, parts[1])
        return allparts

    @staticmethod
    def prefixes_from_project_number(project_no: str):
        """
        returns root directory prefix for given project number.
        eg project number 10638 returns 106xx, project number 9805A returns 98xx
        :param project_no: string project number
        :return: project directory root directory prefix for choosing correct root directory
        """
        project_no = project_no.split("-")[0]
        project_no = ''.join(i for i in project_no if i.isdigit())
        prefix = project_no[:3]
        if len(project_no) <= 4:
            prefix = project_no[:2]
        return prefix + 'xx', project_no

    @staticmethod
    def file_code_from_destination_dir(destination_dir_name):
        """

        :param destination_dir_name: full destination directory name
        :return: string filing code
        """
        file_code = ''
        dir_name_index = 0
        while destination_dir_name[dir_name_index] != '-':
            file_code += destination_dir_name[dir_name_index]
            dir_name_index += 1
        return file_code.strip().upper()

    @staticmethod
    def open_file_with_system_application(filepath):
        """
        System agnostic file opener
        :param filepath: str path to file that will be opened
        :return:
        """

        system_identifier = sys.platform
        if system_identifier.lower().startswith("linux"):
            subprocess.call(('xdg-open', filepath))
            return
        if system_identifier.lower().startswith("darwin"):
            subprocess.call(('open', filepath))
            return
        else:
            os.startfile(filepath)
            return

    @staticmethod
    def clean_path(path):
        '''Process a path string such that it can be used regardless of the os and regardless of whether its length
        surpasses the limit in windows file systems'''
        path = path.replace('/', os.sep).replace('\\', os.sep)
        if os.sep == '\\' and '\\\\?\\' not in path:
            # fix for Windows 260 char limit
            relative_levels = len([directory for directory in path.split(os.sep) if directory == '..'])
            cwd = [directory for directory in os.getcwd().split(os.sep)] if ':' not in path else []
            path = '\\\\?\\' + os.sep.join(cwd[:len(cwd) - relative_levels] \
                                           + [directory for directory in path.split(os.sep) if directory != ''][
                                             relative_levels:])
        return path




class GuiHandler:
    """
        This class is used to create and launch the various GUI windows used by the script.

        """

    def __init__(self, file_icon_path = None, folder_icon_path = None):
        self.gui_theme = random.choice(["DarkTeal6", "Green", "LightBrown11", "LightPurple", "SandyBeach", "DarkGreen4",
                                        "BluePurple", "Reddit", "DarkBrown5", "DarkBlue8", "LightGreen6", "LightBlue7",
                                        "DarkGreen2", "Kayak", "LightBrown3", "LightBrown1", "LightTeal", "Tan",
                                        "TealMono", "LightBrown4", "LightBrown3", "LightBrown2", "DarkPurple4",
                                        "DarkPurple", "DarkGreen5", "Dark Brown3", "DarkAmber", "DarkGrey6",
                                        "DarkGrey2", "DarkTeal1", "LightGrey6", "DarkBrown6"])
        self.window_close_button_event = "-WINDOW CLOSE ATTEMPTED-"
        self.file_icon = None
        self.folder_icon = None

        if file_icon_path:
            with open(file_icon_path, "rb") as image:
                self.file_icon = base64.b64encode(image.read())

        if folder_icon_path:
            with open(folder_icon_path, "rb") as image:
                self.folder_icon = base64.b64encode(image.read())


    def make_window(self, window_name: str, window_layout: list):
        sg.theme(self.gui_theme)
        # launch gui
        dist_window = sg.Window(window_name, layout= window_layout, enable_close_attempted_event= True)
        event, values = dist_window.read()
        values["Button Event"] = event
        dist_window.close()
        return defaultdict(None, values)

    def directory_treedata(self, parent_dir, dir_name) -> sg.TreeData:
        """
        Creates PysimpleGUI.TreeData ogjects from a given directory
        https://github.com/PySimpleGUI/PySimpleGUI/blob/master/DemoPrograms/Demo_Tree_Element.py
        :param parent_dir:
        :param dir_name:
        :return:
        """

        def add_files_in_folder(treedata: sg.TreeData, parent, dirname, file_icon_bytes=None, folder_icon_bytes=None):
            files = os.listdir(dirname)
            for f in files:
                fullpath = ArchiverHelpers.clean_path(os.path.join(dirname, f))
                if os.path.isdir(fullpath):  # if it's a folder, add folder and recurse
                    # add folder to tree
                    treedata.insert(parent, fullpath, f, values=[], icon= folder_icon_bytes)
                    add_files_in_folder(treedata, fullpath, fullpath, file_icon_bytes=file_icon_bytes,
                                        folder_icon_bytes=folder_icon_bytes)
                else:
                    # add file to tree
                    treedata.insert(parent, fullpath, f, values=[os.stat(fullpath).st_size / 1000], icon= file_icon_bytes)

        tree_data = sg.TreeData()
        add_files_in_folder(tree_data, parent=parent_dir, dirname=dir_name, file_icon_bytes=self.file_icon,
                            folder_icon_bytes=self.folder_icon)
        return tree_data


    def welcome_layout(self):
        welcome_gui_layout = [
            [sg.Text("Email address:"), sg.Input(key="Archivist Email")],
            [sg.Button("Ok"), sg.Button("Exit")]
        ]
        return welcome_gui_layout

    def destination_choice_layout(self, dir_choices: list[str], current_filename: str, default_project_num: str = None,
                                  research_default: bool = True):
        dir_choices.sort()
        # TODO try auto_size_text and expand_y
        listbox_width = max([len(dir_name) for dir_name in dir_choices])
        listbox_height = 18
        destination_gui_layout = [
            [sg.Text(f"Choose a location for:")],
            [sg.Input(default_text=current_filename, use_readonly_for_disable=True, disabled=True,
                      background_color='#F7F3EC', text_color="black", key='Inert Filename'), sg.Button("Open Copy")],
            [sg.Text("Default Project:"), sg.Text(default_project_num)],
            [sg.Text("Project Number (Leave Blank to use Default.):"), sg.Input(key="New Project Number")],
            [sg.Text("Destination filename"), sg.Input(key="Filename")],
            [sg.Text("Choose Directory to for file:"), sg.Listbox(values=dir_choices, key="Directory Choice",
                                                                  size=(listbox_width, listbox_height))],
            [sg.Text("Alternatively, Enter the full path to directory where the file has been archived:")],
            [sg.Input(key="Manual Path")],
            [sg.Checkbox(text="Include research with confirmation", default=research_default, key="Research")],
            [sg.Text("Notes: ")],
            [sg.Input(key="Notes")]
        ]

        destination_gui_layout.append([sg.Button("Ok"), sg.Button("Exit")])
        return destination_gui_layout

    def confirmation_layout(self, destination_path: str, similar_files: list[str] = [], dir_trees: list[sg.TreeData] = []):
        """

        :param destination_path:
        :param similar_files:
        :param dir_trees:
        :return:
        """
        treedata = sg.TreeData()

        confirmation_gui_layout = [
            [sg.Text("Confirm this is correct location for this file:"), sg.Text(destination_path)]]

        #if there is a list of similarly named files
        if similar_files:
            confirmation_gui_layout.append([sg.Text("Similar Filenames: ")])
            filepaths_text = ", \n".join(similar_files)
            confirmation_gui_layout.append([sg.Text(filepaths_text)])

        #create and append directory example structures into layout
        if dir_trees:
            confirmation_gui_layout.append([sg.Text("Examples of directories with the same filing codes: ")])
            trees = []
            for tree in dir_trees:
                #only use max of three examples
                if len(trees)  == 3:
                    break

                trees.append(sg.Tree(data= tree,
                                     headings=['Size (KB)', ],
                                     auto_size_columns=True,
                                     select_mode=sg.TABLE_SELECT_MODE_EXTENDED,
                                     num_rows=6,
                                     col0_width=40,
                                     row_height= 32,
                                     show_expanded=False,
                                     enable_events=False,
                                     expand_x=True,
                                     expand_y=True,
                                    ))

            confirmation_gui_layout.append([trees])

        confirmation_gui_layout += [
            [sg.Button("Ok"), sg.Button("Back"), sg.Button("Exit")]
        ]
        return confirmation_gui_layout

    def failed_destination_layout(self, fail_reason: str, fail_path: str):
        failed_gui_layout = [
            [sg.Text("Could not reconcile the given destination choice:")],
            [sg.Text(fail_path)],
            [sg.Text("Reason for not being able to move file to selected destination:")],
            [sg.Text(fail_reason)],
            [sg.Button("Back"), sg.Button("Exit")]
        ]
        return failed_gui_layout

    def error_message_layout(self, error_message: str):
        error_gui_layout = [
            [sg.Text("Oops, an error occured:")],
            [sg.Text(error_message)],
            [sg.Button("Back"), sg.Button("Exit")]
        ]
        return error_gui_layout


class ArchivalFile:

    def __init__(self, current_path: str, project: str = None, destination_path: str = None, new_filename: str = None,
                 notes: str = None, destination_dir: str = None):
        """

        :param current_path: path to  file
        :param project: project number string
        :param destination_path: the desired path for the file when tit is archived
        :param new_filename: optional file name for the destination file
        :param notes: for recording notes in the database
        :param destination_dir: chosen directory from the directory templates
        """
        self.current_path = current_path
        self.size = 0
        if self.current_path and os.path.exists(self.current_path):
            self.size = str(os.path.getsize(current_path))
        self.project_number = project
        self.destination_dir = destination_dir
        self.new_filename = new_filename
        self.notes = notes
        self.destination_path = destination_path
        self.datetime_archived = None
        if destination_dir:
            self.file_code = ArchiverHelpers.file_code_from_destination_dir(destination_dir)

    def assemble_destination_filename(self):
        """
        returns the resulting anticipated filename from an anticipated archival process. Handles extensions by copying
        them from current filename to desired new filename
        :return:
        """
        current_filename = ArchiverHelpers.split_path(self.current_path)[-1]
        dest_filename = current_filename
        if self.new_filename:
            dest_filename = self.new_filename

        extension = current_filename.split(".")[-1]
        split_dest_components = dest_filename.split(".")

        # if the destination filename didn't include the file extwension add it to the filename component list
        if not split_dest_components[-1] == extension:
            split_dest_components.append(extension)

        prefix_list = [self.project_number, self.file_code]
        split_dest_components = prefix_list + split_dest_components
        destination_filename = ".".join(split_dest_components)
        return destination_filename

    def nested_large_template_destination_dir(self):
        """
        eg  "E - Program and Design\E5 - Correspondence"

        :return:
        """
        # TODO handle situation when there is a destination_path but no destination_dir_name

        nested_dirs = self.destination_dir
        if nested_dirs[1].isdigit():
            # a directory from DIRECTORY_CHOICES is parent directory if it shares same first char and doesn't have a
            # digit in second char position
            is_parent_dir = lambda child_dir, dir: dir[0] == child_dir[0] and not dir[1].isdigit()
            parent_dir = [dir for dir in DIRECTORY_CHOICES if is_parent_dir(nested_dirs, dir)][0]
            nested_dirs = os.path.join(parent_dir, nested_dirs)
        return str(nested_dirs)

    def assemble_destination_path(self):
        """
        Major function that builds a plausible path string in the following steps:
        Step 1: Looks for xx directory in root (RECORDS_SERVER_LOCATION) and adds to path
        Step 2: Looks through next two levels in directory hierarchy for directories that start with the project number
            or a project number prefix and add them to the path.
        Step 3: Looks for desired directory location in nested levels and adds it to new path

        ...unless there is already a path in destination_path attribute, in which case that will be returned
        :return: string (or path object?)
        """

        def list_of_child_dirs(parent_directory_path):
            """sub-function for getting a list of just the child directories given a parent directory path"""
            return [dir for dir in os.listdir(parent_directory_path) if
                    not os.path.isfile(os.path.join(parent_directory_path, dir))]

        def path_from_project_num_dir_to_destination(path_to_project_num_dir: str, large_template_destination: str,
                                                     destination_filename: str):
            """
            Sub-routine for constructing the remainder of the destination path after building the path up to the
            directory corresponding to the archive file project number.

            :param path_to_project_num_dir: path thus constructed to the directory corresponding to the archive file
            project number
            :param large_template_destination: given by ArchivalFile.nested_large_template_destination_dir()
            :param destination_filename: given by ArchivalFile.assemble_destination_filename()
            :return: string final destination path
            """

            new_path = path_to_project_num_dir

            # if the path to the dir corresponding to the project number doesn't exist, just return the completed
            # destination filepath
            if not os.path.exists(new_path):
                new_path = os.path.join(new_path, large_template_destination)
                return os.path.join(new_path, destination_filename)

            new_path_dirs = list_of_child_dirs(new_path)
            destination_dir = ArchiverHelpers.split_path(large_template_destination)[-1]
            destination_dir_prefix = destination_dir.split(" ")[0] + " - "  # eg "F5 - ", "G12 - ", "H - ", etc
            destination_dir_parent_dir = ArchiverHelpers.split_path(large_template_destination)[0]

            # if the destination directory is a large template child director...
            if not destination_dir_parent_dir == large_template_destination:

                # need to extrapolate the parent directory prefix given the desired destination directory. eg for
                # destination "F5 - Drawings and Specifications" the parent directory prefix is "F - "
                destination_dir_parent_dir_prefix = destination_dir_parent_dir.split(" ")[0] + " - "  # eg "F - ", "G - ", etc
                parent_dirs = [dir_name for dir_name in new_path_dirs if
                               dir_name.upper().startswith(destination_dir_parent_dir_prefix.upper())]
                if len(parent_dirs) > 0:
                    # TODO cause we're lazy we'll just assume parent_dirs is only len = 1. Maybe should handle other situations?
                    new_path = os.path.join(new_path, parent_dirs[0])
                    new_path_dirs = [dir_name for dir_name in os.listdir(new_path) if
                                     not os.path.isfile(os.path.join(new_path, dir_name))]
                    existing_destination_dirs = [dir_name for dir_name in new_path_dirs if
                                                 dir_name.upper().startswith(destination_dir_prefix)]
                    if existing_destination_dirs:
                        # again, assuming only one dir matches the destination dir prefix:
                        new_path = os.path.join(new_path, existing_destination_dirs[0])

                    else:
                        new_path = os.path.join(new_path, destination_dir)

                # if there is no directory in the destination project folder that corresponds to the parent directory of
                # destination directory in a large template path...
                else:
                    # check for existing equivalents of destination directory
                    new_path_dirs = list_of_child_dirs(new_path)
                    existing_destination_dirs = [dir_name for dir_name in new_path_dirs if
                                                 dir_name.upper().startswith(destination_dir_prefix)]
                    if existing_destination_dirs:
                        new_path = os.path.join(new_path, existing_destination_dirs[0])
                    else:
                        project_num_dirs = [dir for dir in new_path_dirs if dir.lower().startswith(self.project_number)]
                        if not project_num_dirs:
                            new_path = os.path.join(new_path, large_template_destination)
                        else:
                            new_path = os.path.join(new_path, project_num_dirs[0])
                            return path_from_project_num_dir_to_destination(path_to_project_num_dir=new_path,
                                                                            large_template_destination=large_template_destination,
                                                                            destination_filename=destination_filename)

            # if the destination_dir_name doesn't have a project template dir parent...
            else:
                existing_destination_dirs = [dir_name for dir_name in new_path_dirs if
                                             dir_name.upper().startswith(destination_dir_prefix)]
                if existing_destination_dirs:
                    new_path = os.path.join(new_path, existing_destination_dirs[0])
                else:
                    file_num_dirs = [dir for dir in new_path_dirs if
                                     dir.lower().startswith(self.project_number.lower())]
                    if not file_num_dirs:
                        new_path = os.path.join(new_path, large_template_destination)
                    else:
                        return path_from_project_num_dir_to_destination(path_to_project_num_dir=new_path,
                                                                        large_template_destination=large_template_destination,
                                                                        destination_filename=destination_filename)

            return os.path.join(new_path, destination_filename)

        ############### Start of assemble_destination_path() #################
        if not self.destination_path:

            # sept
            xx_level_dir_prefix, project_num_prefix = ArchiverHelpers.prefixes_from_project_number(self.project_number)
            root_directories_list = list_of_child_dirs(RECORDS_SERVER_LOCATION)
            matching_root_dirs = [dir_name for dir_name in root_directories_list if
                                  dir_name.lower().startswith(xx_level_dir_prefix.lower())]

            # if we have more than one matching root dir we throw an error
            if len(matching_root_dirs) != 1:
                raise Exception(
                    f"{len(matching_root_dirs)} matching directories in {RECORDS_SERVER_LOCATION} for project number {self.project_number}")

            # add the directory matching the xx level prefix for this project number
            new_path = os.path.join(RECORDS_SERVER_LOCATION, matching_root_dirs[0])
            # list of contents of xx level directory which are not files (ie directories in xx level directory)
            xx_dir_dirs = list_of_child_dirs(new_path)

            # lambda functions that check whether a directory name starts with either project number or
            # prefix respectively.
            proj_num_in_dir_name = lambda dir_name: self.project_number == dir_name.split(" ")[0]
            prefix_in_dir_name = lambda dir_name: project_num_prefix == dir_name.split(" ")[0]
            dirs_matching_proj_num = [dir_name for dir_name in xx_dir_dirs if proj_num_in_dir_name(dir_name)]

            # if more than one directory starts with the same project number...
            if len(dirs_matching_proj_num) > 1:
                raise Exception(
                    f"{len(dirs_matching_proj_num)} matching directories in {new_path} for project number {self.project_number}; expected 0 or 1.")

            # if no directories match the project number...
            if len(dirs_matching_proj_num) == 0:
                dirs_matching_prefix = [dir_name for dir_name in xx_dir_dirs if prefix_in_dir_name(dir_name)]
                if len(dirs_matching_prefix) > 1:
                    raise Exception(
                        f"{len(dirs_matching_prefix)} matching directories in {new_path} for prefix for project number {self.project_number}; expected 0 or 1.")

                # if there is now project number or prefix directory at the 'xx' level, it will need to be made
                if len(dirs_matching_prefix) == 0:
                    new_path = os.path.join(new_path, project_num_prefix)
                    new_path = os.path.join(new_path, self.project_number)
                    new_path = os.path.join(new_path, self.nested_large_template_destination_dir())
                    new_path = os.path.join(new_path, self.assemble_destination_filename())
                    self.destination_path = new_path
                    return new_path

                if len(dirs_matching_prefix) == 1:
                    # if a dir exists that does begin with the prefix, we'll add it to our path and look again for
                    # directories that begin with the project number #TODO ..and prefix again too?

                    new_path = os.path.join(new_path, dirs_matching_prefix[0])
                    prefix_dir_dirs = list_of_child_dirs(new_path)
                    dirs_matching_proj_num = [dir_name for dir_name in prefix_dir_dirs if
                                              proj_num_in_dir_name(dir_name)]
                    if len(dirs_matching_proj_num) > 1:
                        logging.exception(
                            f"{len(dirs_matching_proj_num)} matching directories in {new_path} for project number {self.project_number}; expected 0 or 1.",
                            exc_info=True)
                        return ''

                # if no dirs are equivalent to the project number
                if len(dirs_matching_proj_num) == 0:
                    new_path = os.path.join(new_path, self.project_number)
                    new_path = path_from_project_num_dir_to_destination(new_path,
                                                                        self.nested_large_template_destination_dir(),
                                                                        self.assemble_destination_filename())
                    self.destination_path = new_path
                    return self.destination_path

                if len(dirs_matching_proj_num) == 1:
                    new_path = os.path.join(new_path, dirs_matching_proj_num[0])
                    new_path = path_from_project_num_dir_to_destination(new_path,
                                                                        self.nested_large_template_destination_dir(),
                                                                        self.assemble_destination_filename())
                    self.destination_path = new_path
                    return self.destination_path

            # if we do find a dir that corresponds with the project number...
            if len(dirs_matching_proj_num) == 1:
                new_path = os.path.join(new_path, dirs_matching_proj_num[0])
                #look for another project number directory in the dirs of this project number directory
                proj_num_dir_dirs = list_of_child_dirs(new_path)
                dirs_matching_proj_num = [dir_name for dir_name in proj_num_dir_dirs if proj_num_in_dir_name(dir_name)]

                # if more than one directory starts with the same project number...
                if not len(dirs_matching_proj_num) == 1:
                    raise Exception(
                        f"{len(dirs_matching_proj_num)} matching directories in {new_path} for project number {self.project_number}; expected 0 or 1.")

                if len(dirs_matching_proj_num) == 1:
                    new_path = os.path.join(new_path, dirs_matching_proj_num[0])

                new_path = path_from_project_num_dir_to_destination(path_to_project_num_dir= new_path,
                                                                    large_template_destination= self.nested_large_template_destination_dir(),
                                                                    destination_filename= self.assemble_destination_filename())
                self.destination_path = new_path
                return self.destination_path


            self.destination_path = new_path
        return self.destination_path

    def attribute_defaultdict(self):
        date_stamp = ''
        if self.datetime_archived:
            date_stamp = self.datetime_archived.strftime("%m/%d/%Y, %H:%M:%S")
        if (self.destination_path or self.current_path) and not self.size:
            if not self.destination_path:
                self.size = str(os.path.getsize(self.current_path))
            else:
                self.size = str(os.path.getsize(self.destination_path))

        attribute_dict = {"time_archived": date_stamp, "project_number": self.project_number,
                "destination_path": self.destination_path, "destination_directory": self.destination_dir,
                "file_size": self.size, "notes": self.notes}
        return defaultdict(None, attribute_dict)

    def check_permissions(self):
        """
        Returns a string describing issues with permissions that may arise when trying to archive the file.
        :return:
        """
        if not os.path.exists(self.current_path):
            return f"The file no longer exists {self.current_path}"

        issues_found = ''
        try:
            os.rename(self.current_path, self.current_path)
        except OSError as e:
            issues_found = "Access error on file using renaming test:" + '! \n' + str(e) + "\n"

        if not os.access(self.current_path, os.R_OK):
            issues_found += "No read access for the file.\n"
        if not os.access(self.current_path, os.W_OK):
            issues_found += "No write access for the file.\n"
        if not os.access(self.current_path, os.X_OK):
            issues_found += "No execution access for the file.\n"
        return issues_found



    def archive(self, destination=None):

        # if the file has already been archived return the destination path
        if self.datetime_archived:
            return self.destination_path

        # process optional parameter destination
        if destination:
            if destination in DIRECTORY_CHOICES:
                self.destination_dir = destination
            else:
                self.destination_path = destination

        if not self.destination_path:
            self.destination_path = self.assemble_destination_path()

        destination_path_list = ArchiverHelpers.split_path(self.destination_path)
        destination_dir_path = os.path.join(*destination_path_list[:-1])

        if not os.path.exists(destination_dir_path):
            os.makedirs(destination_dir_path)
        self.datetime_archived = datetime.now()
        try:
            shutil.copyfile(src=self.current_path, dst=self.destination_path)
        except Exception as e:
            return False, e
        try:
            os.remove(self.current_path)
            return True, ''
        except Exception as e:
            return False, e


class Researcher:

    def __init__(self):
        self.xx_dirs_to_ignore = ["01XX JOCs", "00xx  Consulting Agreements", "10xx   Regulatory Requirements",
                                  "110xx  Infrastructure Planning Documents and Studies",
                                  "111xx  Area Planning Documents and Studies",
                                  "112xx  Proposed Structure Planning Documents and Studies",
                                  "113xx  Environmental Planning Documents and Studies",
                                  "114xx  Long Range Development Planning (LRDP) Documents and Studies",
                                  "115xx  Student Issues Planning & Studies",
                                  "116xx  Economic Planning Documents and Studies",
                                  "117xx  Handicap ADA Planning Documents and Studies",
                                  "130xx  Campus Reference Materials", "140xx  Storm Water Management"]

    def similar_filename_paths(self, original_filename, duration=6, similarity_threshold=72, max_paths=10):
        """

        :param original_filename: (not the path)
        :param duration: length of time in seconds that this search algorithm can run
        :param similarity_threshold: how similar a filename needs to be to be included as similar
        :param max_paths: maximum number of filepaths that will be returned
        :return:
        """

        # TODO: could be made better by removing common, unhelpful tokens from original_filename
        # TODO: copuld be made better by removing very short (or comparably short) filenames from being compared to original_filename

        # start search timer
        start_time = time.time()
        current_time = start_time
        similarly_named_files = []
        dirs_to_ignore = self.xx_dirs_to_ignore.copy()

        # tests directory to see if it should be considered when searching for similar files.
        is_xx_dir_to_search = lambda dir_name: ('xx' in dir_name.lower().split(" ")[0]) and (
            not os.path.isfile(os.path.join(RECORDS_SERVER_LOCATION, dir_name))) and (
                                                       dir_name not in dirs_to_ignore)

        # While this search has not taken up the allocated time or found sufficient number of similar files...
        while (current_time - start_time) < duration and len(similarly_named_files) < max_paths:
            xx_level_dirs = [d for d in os.listdir(RECORDS_SERVER_LOCATION) if is_xx_dir_to_search(d)]
            random_index = random.randint(0, len(xx_level_dirs) - 1)
            # Path of random xx level directory where we will initialize a search.
            random_xx_start = os.path.join(RECORDS_SERVER_LOCATION, xx_level_dirs[random_index])
            dirs_to_ignore.append(xx_level_dirs[random_index])

            # choose another directory at random from which to begin search
            number_dirs = [dir for dir in os.listdir(random_xx_start) if
                           os.path.isdir(os.path.join(random_xx_start, dir))]
            random_index2 = random.randint(0, len(number_dirs) - 1)
            random_search_start = os.path.join(random_xx_start, number_dirs[random_index2])

            #  Iterate through directory structure from the random starting dir...
            for root, dirs, files in os.walk(random_search_start):
                found_similar_file = False
                for some_file in files:
                    ratio = fuzz.token_set_ratio(original_filename, some_file)

                    # if the fuzzy filename comparison calculates a similarity above our threshhold...
                    if ratio > similarity_threshold:
                        # append this searched directory so that we won't research this directory
                        similar_file_filepath = os.path.join(root, some_file)
                        similarly_named_files.append({"filepath": similar_file_filepath, "ratio": ratio})
                        found_similar_file = True
                        break
                current_time = time.time()
                if found_similar_file or (current_time - start_time) > duration:
                    break

        return similarly_named_files


    def randomized_destination_examples(self, dest_dir, num_of_examples=3,
                                        duration=4, files_in_example=3):
        """
        Starting at a random location in the directories within the xx level directories, search for examples of the
        same destination directory with at least a sufficient number of files in it to be used as examples --
        demonstrating the types of files that would be found in a given destination directory
        :param dest_dir: str name of the destination directory
        :param num_of_examples: int number of destination directory paths to be returned
        :param duration: int alotted number of seconds for this function to search for
        :param files_in_example: int minimum number of files to be in a directory for it to be considered as an example
        :return: list of path strings.
        """

        def is_good_dir_example(chosen_destination_dir, dir_example_path, desired_files_num=files_in_example):
            """
            Sub-routine for deciding if a given directory represents a good example of the chosen directory type.
            for the purposes of this application, a good directory example starts with the same filing code
            (eg C1.2, F10, H) and has the desired number of files in it.
            :param original_dir:
            :param dir_example_path:
            :param desired_files_num:
            :return:
            """
            # a directory name probably starts with a filing code (eg C1.2, F10, H) if it starts with a letter and when
            # split by spaces, the second element is a dash #TODO may need improving
            probably_has_filing_code = lambda dir: (len(dir.split(" ")) > 2) and (dir[0].isalpha()) and \
                                                   (dir.split(" ")[1] == "-")
            example_dir_name = ArchiverHelpers.split_path(dir_example_path)[-1]
            if not probably_has_filing_code(example_dir_name):
                return False

            # if the directory doesn't share a filing code with chosen destination dir, it is not a good example
            example_file_code = ArchiverHelpers.file_code_from_destination_dir(example_dir_name)
            if not ArchiverHelpers.file_code_from_destination_dir(chosen_destination_dir) == example_file_code:
                return False

            # if the example directory doesn't have enough files in it, it is a bad example
            files_in_example = [file for file in os.listdir(dir_example_path) if
                                os.path.isfile(os.path.join(dir_example_path, file))]
            if not len(files_in_example) >= desired_files_num:
                return False

            return True

        start_time = time.time()
        current_time = start_time
        example_dir_paths = []
        dirs_to_ignore = self.xx_dirs_to_ignore.copy()

        # function to test directory to see if it should be considered when searching for good destination examples.
        is_xx_dir_to_search = lambda dir_name: ('xx' in dir_name.lower().split(" ")[0]) and (
            not os.path.isfile(os.path.join(RECORDS_SERVER_LOCATION, dir_name))) and (
                                                       dir_name not in dirs_to_ignore)

        #  While the duration allotted for this function has not been used and we haven't found enough good destination
        #  examples, choose random xx level directory and a subsequent random project number directory to search for
        #  another example of the destination directory.
        while (current_time - start_time) < duration and len(example_dir_paths) < num_of_examples:
            xx_level_dirs = [d for d in os.listdir(RECORDS_SERVER_LOCATION) if is_xx_dir_to_search(d)]
            random_index = random.randint(0, len(xx_level_dirs) - 1)

            # Path of random xx level directory where we will initialize a search.
            random_xx_start = os.path.join(RECORDS_SERVER_LOCATION, xx_level_dirs[random_index])
            dirs_to_ignore.append(xx_level_dirs[random_index])

            #choose another directory at random from which to begin search
            number_dirs = [dir for dir in os.listdir(random_xx_start) if
                           os.path.isdir(os.path.join(random_xx_start, dir))]
            random_index2 = random.randint(0, len(number_dirs) - 1)
            random_search_start = os.path.join(random_xx_start, number_dirs[random_index2])

            for root, dirs, files in os.walk(random_search_start):
                good_dir_example = False
                if not is_good_dir_example(chosen_destination_dir=dest_dir, dir_example_path=root):
                    current_time = time.time()
                    if (current_time - start_time) > duration:
                        break

                    continue

                #add good example path to example path list
                example_dir_paths.append(root)
                current_time = time.time()
                break

        return example_dir_paths


class Archivist:
    """
    Class for executing main archiving procedure
    """

    def __init__(self, files_to_archive_directory: str, app_files_directory: str, records_drive_path: str,
                 gui_file_icon: str, gui_dir_icon: str, file_to_archive: ArchivalFile = None):

        ##Build necessary directory structiure###
        self.files_to_archive_directory = files_to_archive_directory
        if not os.path.exists(files_to_archive_directory):
            try:
                os.mkdir(files_to_archive_directory)
            except Exception as e:
                print(e)
                print(f"error from trying to make {files_to_archive_directory}")

        self.app_files_directory = app_files_directory
        if not os.path.exists(self.app_files_directory):
            try:
                os.mkdir(self.app_files_directory)
            except Exception as e:
                print(e)
                print(f"error from trying to make {self.app_files_directory}")

        self.opened_copies_directory = os.path.join(self.app_files_directory, 'temp')
        if not os.path.exists(self.opened_copies_directory):
            try:
                os.mkdir(self.opened_copies_directory)
            except Exception as e:
                print(e)
                print(f"error from trying to make {self.opened_copies_directory}")

        gui_file_icon_path = ''
        if gui_file_icon:
            gui_file_icon_path = os.path.join(self.app_files_directory, gui_file_icon)

        gui_dir_icon_path = ''
        if gui_dir_icon:
            gui_dir_icon_path = os.path.join(self.app_files_directory, gui_dir_icon)

        self.records_drive_path = records_drive_path
        self.gui = GuiHandler(file_icon_path=gui_file_icon_path, folder_icon_path=gui_dir_icon_path)
        self.file_to_archive = file_to_archive
        self.email = None
        self.default_project_number = None
        self.perform_research = True
        self.researcher = Researcher()

    def display_error(self, error_message) -> bool:
        """

        :param error_message: string message to display
        :return: bool whether user hit 'ok' button or not
        """
        error_layout = self.gui.error_message_layout(error_message=error_message)
        error_window_results = self.gui.make_window(window_name="ERROR", window_layout=error_layout)
        if error_window_results["Button Event"].lower() in ["exit", self.gui.window_close_button_event.lower()]:
            self.exit_app()
        return error_window_results["Button Event"].lower() == "ok"

    def retrieve_email(self):

        welcome_window_layout = self.gui.welcome_layout()
        welcome_window_results = self.gui.make_window("Welcome!", welcome_window_layout)

        # if the user clicks exit, shutdown app
        if welcome_window_results["Button Event"].lower() in ["exit", self.gui.window_close_button_event.lower()]:
            self.exit_app()
        else:
            self.email = welcome_window_results["Archivist Email"]
            return

    def open_file_copy(self, filepath: str = ''):
        """
        Creates a copy of the file in the opened_copies_directory directory and opens that copy. Will open
        self.file_to_archive if no filepath parameter is given
        :return: None
        """
        if not filepath:
            filepath = self.file_to_archive.current_path
        timestamp = str(time.time()).split(".")[0]
        filename = ArchiverHelpers.split_path(filepath)[-1]
        copies_dir = os.path.join(os.getcwd(), self.opened_copies_directory)
        copy_path = os.path.join(copies_dir, (timestamp + "_" + filename))
        shutil.copyfile(src=filepath, dst=copy_path)
        ArchiverHelpers.open_file_with_system_application(copy_path)
        return

    def files_to_archive(self, archiver_dir_path=None):
        """
        return a list of paths to files to archive in the self.files_to_archive_directory or achiver_dir_path
        :param archiver_dir_path: path to directory with files to archive
        :return: List of filepaths
        """

        if archiver_dir_path:
            self.files_to_archive_directory = archiver_dir_path

        if self.files_to_archive_directory and not archiver_dir_path:
            archiver_dir_path = self.files_to_archive_directory

        # TODO if not archiver_dir_path and not self.files_to_archive_directory (maybe not relevant)

        files = [os.path.join(archiver_dir_path, file) for file in os.listdir(archiver_dir_path) if
                 not (file in FILENAMES_TO_IGNORE or os.path.isdir(os.path.join(archiver_dir_path, file)))]
        return files

    def retrieve_file_destination_choice(self):
        """
        retrieves
        :return:
        """
        files_in_archiving_dir = self.files_to_archive()
        #
        default_proj_number = ""
        if self.default_project_number:
            default_proj_number = self.default_project_number

        current_file = ArchiverHelpers.split_path(files_in_archiving_dir[0])[-1]
        destination_window_layout = self.gui.destination_choice_layout(dir_choices=DIRECTORY_CHOICES,
                                                                       current_filename=current_file,
                                                                       default_project_num=default_proj_number,
                                                                       research_default=self.perform_research)
        destination_gui_results = self.gui.make_window(window_name="Enter file and destination info.",
                                                       window_layout=destination_window_layout)

        if (not destination_gui_results["Button Event"]) or destination_gui_results["Button Event"].lower() in ["exit", self.gui.window_close_button_event.lower()]:
            self.exit_app()

        #if the user selects the open copy window, open a copy an relaunch the window
        if destination_gui_results["Button Event"].lower() == "open copy":
            self.open_file_copy()
            return self.retrieve_file_destination_choice()


        if destination_gui_results["Button Event"].lower() == "back":
            return ""

        if destination_gui_results["Button Event"].lower() == "ok":

            # use default project number unless new project number was given
            project_num = destination_gui_results["New Project Number"]
            if not project_num:
                project_num = default_proj_number

            self.default_project_number = project_num

            #set the default research setting
            self.perform_research = destination_gui_results["Research"]

            directory_choice = ''
            if destination_gui_results["Directory Choice"]:
                directory_choice = destination_gui_results["Directory Choice"][0]

            manual_archived_path = destination_gui_results["Manual Path"]
            file_notes = destination_gui_results["Notes"]
            new_filename = destination_gui_results["Filename"]
            self.file_to_archive = ArchivalFile(current_path=files_in_archiving_dir[0],
                                                project=project_num,
                                                new_filename=new_filename,
                                                destination_dir=directory_choice,
                                                notes=file_notes)
            if manual_archived_path:
                self.file_to_archive.destination_path = os.path.join(manual_archived_path,
                                                                     self.file_to_archive.assemble_destination_filename())
        return self.file_to_archive

    def research_for_archival_file(self):
        filename = self.file_to_archive.new_filename
        if not filename:
            filename = ArchiverHelpers.split_path(self.file_to_archive.current_path)[-1]
        files = self.researcher.similar_filename_paths(original_filename= filename, duration= 6,
                                                                   similarity_threshold= 72, max_paths= 7)

        destinations = self.researcher.randomized_destination_examples(
            dest_dir=self.file_to_archive.destination_dir,)

        return files, destinations


    def confirm_chosen_file_destination(self):
        """
        spins up the confirmation screen gui and returns true if the desired path has been confirmed by the user.
        Will perform research if that option was ticked.
        This also will exit the program if the user selects the 'exit' button in the gui.
        :param gui_file_icon:
        :param gui_dir_icon:
        :return:
        """

        try:
            file_destination = self.file_to_archive.assemble_destination_path()
        except Exception as error:
            except_layout = self.gui.error_message_layout(error_message=str(error))
            gui_results = self.gui.make_window(window_name="Invalid Destination Choices", window_layout=except_layout)
            if gui_results["Button Event"].lower() in ["exit", self.gui.window_close_button_event.lower()]:
                self.exit_app()
            return False

        else:
            #if we do research
            similar_files_paths, destination_examples = [], []
            if self.perform_research:
                file_examples, destination_examples = self.research_for_archival_file()
                similar_files_paths = [path['filepath'] for path in file_examples]

                #create tree data structures from directory paths
                destination_examples = [self.gui.directory_treedata('', path) for path in destination_examples]

            confirmation_gui_layout = self.gui.confirmation_layout(destination_path= file_destination,
                                                                   similar_files= similar_files_paths,
                                                                   dir_trees= destination_examples)
            gui_results = self.gui.make_window("Confirm destination choice.", confirmation_gui_layout)
            if gui_results["Button Event"].lower() in ["exit", self.gui.window_close_button_event.lower()]:
                self.exit_app()

        return gui_results["Button Event"].lower() == "ok"

    def archive_file(self):

        #if there is a path collision throw an error
        if self.file_to_archive.destination_path and os.path.exists(self.file_to_archive.destination_path):
            self.display_error(
                error_message=f"A file exists in that location with the same path: {self.file_to_archive.destination_path}")
            return

        #try to archive the file (kinda fraught) and display any isssues that might have come up.
        archiving_successful, archive_exception = self.file_to_archive.archive()
        if not archiving_successful:
            permission_issue = self.file_to_archive.check_permissions()
            permissions_error_message = "When attempting to duplicate the file to the records drive, \n" +\
                                        "the application ran into file access issues: \n"

            if archive_exception:
                permissions_error_message += f"The shutil.copyfile() call produced this error: \n {archive_exception}\n"
            if permission_issue:
                permissions_error_message += f"Testing the permissions of the file yielded: \n {permission_issue}\n"

            self.display_error(error_message=permissions_error_message)
            return False

        return True

    def add_archived_file_to_csv(self, csv_path):
        """

        :param csv_path:
        :return:
        """
        data_dict = self.file_to_archive.attribute_defaultdict()
        data_dict["archiver_email"] = self.email
        archived_file_df = pd.DataFrame(data_dict, index=[0, ])
        archived_file_df.to_csv(csv_path, mode='a', index=False, header=False)

    def retrieve_file_to_archive(self):
        """
        Ensures files exit to be archived and that the next file is queued up as the Archivist.file_to_archive
        :return:
        """
        while not self.files_to_archive():
            no_file_error_message = f"No files to archive. Add files to" + os.linesep + f"{self.files_to_archive_directory}"
            self.display_error(no_file_error_message)

        current_file = self.files_to_archive()[0]
        self.file_to_archive = ArchivalFile(current_path= os.path.join(self.files_to_archive_directory, current_file))

    def exit_app(self):
        """
        process for shutting down the app. Attempts to clear the temporary files directory.
        :return:
        """
        # Attempt to delete all the files in the self.opened_copies_directory.
        open_copies_dir_path = os.path.join(os.getcwd(), self.opened_copies_directory)
        opened_file_copies = [os.path.join(open_copies_dir_path, f) for f in os.listdir(open_copies_dir_path) if
                              os.path.isfile(os.path.join(open_copies_dir_path, f))]
        for opened_filepath in opened_file_copies:
            try:
                os.remove(opened_filepath)
            except Exception as e:
                print(f"Failed at deleting a temp file: \n {opened_filepath}\n Error: \n {e}")
                continue
        exit()


class Tester:

    @staticmethod
    def test_gui():
        dir = r"C:\Users\adankert\Google Drive\GitHub\archives_archiver\app_files"
        file_icon_path = os.path.join(dir, "file_3d_32x32.png")
        folder_icon_path = os.path.join(dir, "folder_3d_32x32.png")
        gui = GuiHandler(file_icon_path=file_icon_path, folder_icon_path=folder_icon_path)

        path_examples = [r"R:\49xx   Long Marine Lab\4900\4900-007\F5 - Drawings and Specifications",
                         r"R:\49xx   Long Marine Lab\4900\4900-021\A - General\A2 - Working File",
                         r"R:\27xx   Applied Sciences Baskin Engineering\2703\2703\F8 - Contract"]

        forest = []
        for example in path_examples:
            forest.append(gui.directory_treedata('', example))

        gui.make_window("Test Confirm",
                        gui.confirmation_layout(r"C:\Users\adankert\Google Drive\GitHub\archives_archiver\app_files",
                                                similar_files=[], dir_trees=forest))



    @staticmethod
    def test_assemble_destination_path():
        project = '2700'
        desired_destination = DIRECTORY_CHOICES[8]
        print(desired_destination)
        new_filename = "2744.G19.Notice of Completion"

        location = os.path.join(os.getcwd(), "files_to_archive")
        file = ArchivalFile(current_location_path=location, project=project, new_filename=new_filename,
                            destination_dir=desired_destination)

        dest_path = file.assemble_destination_path()
        print(dest_path)

    @staticmethod
    def test_researcher():
        print("Similar File Examples: \n")
        og_filename = "20.07.10 Sewer Excavated.pdf"
        searcher = Researcher()
        similar_filenames = searcher.similar_filename_paths(original_filename=og_filename, duration=8)
        [print(x["filepath"]) for x in similar_filenames]

        print("\n \n")
        print("Destination Examples: \n")
        dir_choice = "C1 - Executive Architect"
        directory_examples = searcher.randomized_destination_examples(dest_dir= dir_choice, duration= 18)
        [print(example) for example in directory_examples]

    @staticmethod
    def test_loading_screen():
        pass




def main():
    csv_filename = "archived_files_archive.csv"
    app_files_dir = 'app_files'
    gui_file_icon_filename = "file_3d_32x32.png"
    gui_dir_icon_filename = "folder_3d_32x32.png"
    csv_filepath = os.path.join(os.getcwd(), csv_filename)

    dir_of_files_to_archive = os.path.join(os.getcwd(), "files_to_archive")
    ppdo_archivist = Archivist(files_to_archive_directory=dir_of_files_to_archive,
                               app_files_directory=os.path.join(os.getcwd(), app_files_dir),
                               records_drive_path=RECORDS_SERVER_LOCATION,
                               gui_file_icon=gui_file_icon_filename,
                               gui_dir_icon=gui_dir_icon_filename)

    ppdo_archivist.retrieve_email()
    while True:
        ppdo_archivist.retrieve_file_to_archive()
        ppdo_archivist.retrieve_file_destination_choice()

        # if there is no default project number and no project number was entered, display error message and restart loop
        if not ppdo_archivist.file_to_archive.project_number:
            ppdo_archivist.display_error("No project number selected.")
            continue

        #if no destination directory was chosen display error message
        if not ppdo_archivist.file_to_archive.destination_dir:
            ppdo_archivist.display_error("No destination directory was selected.")
            continue

        destination_confirmed = ppdo_archivist.confirm_chosen_file_destination()
        if destination_confirmed:
            is_archived = ppdo_archivist.archive_file()
            if is_archived:
                ppdo_archivist.add_archived_file_to_csv(csv_filepath)
                print(f"File archived: " + os.linesep + f"{ppdo_archivist.file_to_archive.destination_path}")


if __name__ == "__main__":
    # Tester.test_gui()
    # Tester.test_assemble_destination_path()
    # Tester.test_researcher()
    # Tester.test_loading_screen()
    main()
