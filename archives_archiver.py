import base64
import os
import logging
import psycopg2
import random
import re
import subprocess
import shutil
import sqlite3
import sys
import threading
import time
import pandas as pd
import PySimpleGUI as sg
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import seaborn as sns

from dateutil import parser
from contextlib import closing
from typing import List, Dict, Union
from thefuzz import fuzz
from collections import defaultdict
from datetime import datetime, timedelta

# Version Number
__version__ = "1.5.8"

# Typing Aliases
# pysimplegui_layout

# Environmental Variables
RECORDS_SERVER_LOCATION = r"""R:\\""" #TODO how to prevent the four backslashes
FILENAMES_TO_IGNORE = ["desktop.ini", "desktop.ini"]
DIRECTORY_CHOICES = ['A - General', 'B - Administrative Reviews and Approvals', 'C - Consultants',
                     'D - Environmental Review Process', 'E - Program and Design',
                     'F - Bid Documents and Contract Award', 'G - Construction', "H - Submittals and O&M's",
                     'A1 - Miscellaneous', 'A2 - Working File', 'A3 - Project Directory Matrix & Project Chronology',
                     "B1 - CPS and Chancellor's Approvals", 'B11 - LEED', 'B12 - Outside Regulatory Agencies',
                     'B13 - Coastal Commission', 'B2 - Office of the President UC Regents',
                     'B3 - State Public Works Board', 'B4 - Department of Finance', 'B5 - Legislative Submittals',
                     'B6 - State Fire Marshal', 'B7 - Office of State Architect  (DSA)', 'B8 -  General Counsel',
                     'B8.1 - General Counsel - Confidential',
                     'B9 - Monterey Bay Unified Air Pollution Control District',
                     'B10 - Storm Water Pollution Prevention Plan',
                     'B11 - Leadership in Energy & Environmental Design (LEED)', 'B12 - Outside Regulatory Agencies',
                     'B13 - Coastal Commission Approval', 'C1 - Executive Architect', 'C1.1 - Selection',
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
                     'E9 - Sustainability Measures','F1 - Bid and Contract Award Correspondence',
                     'F1.1 - Executive Architect Correspondences', 'F1.2 - Special Consultants Correspondences',
                     'F1.4 - PPC and PP', 'F1.5 - Office of the President Correspondences',
                     'F1.6 - General Counsel Correspondences', 'F1.7 - Pre-Qualification', 'F1.8 - Other',
                     'F10 - Escrow Agreement', 'F2 - Reviews', 'F2.1 - Constructibility, Code Reviews',
                     'F2.2 - In-house. PP reviews', 'F3 - Structural, Title 24, Mech Calculations',
                     'F4 - Plan Deposits, Planholders, Ads for Bid', 'F2.3 - Independent Cost Review',
                     'F2.4 - Independent Seismic Review', 'F2.5 - Other', 'F5 - Drawings and Spec',
                     'F6 - Affirmative Action', 'F7 - Bid Summary Forms', 'F7.1 - Bid Protest', 'F8 - Contract',
                     'F9 - Builders Risk Insurance', 'G1 - Construction Correspondence',
                     'G1.1 - Contractor Correspondences','G1.2 - Executive Architect Correspondences',
                     'G1.3 - Users.Building Committee.Campus Correspondences', 'G1.4 - PPC and PP. Certified Payroll',
                     'G1.5 - Geotechnical Engineer Correspondences',
                     'G1.6 - Testing and Inspection to Laboratory Correspondences',
                     'G1.7 - General Counsel Correspondences', 'G1.8 - Other',
                     'G10 - Testing and Inspection Reports.Other',
                     'G11 - Proposal Requests. Bulletins. Contractors Response', 'G12 - Request for Information RFI',
                     'G13 - Letter of Instruction LOI', 'G14 - User Request Change in Scope', 'G15 - Change Order',
                     'G16 - Field Orders', 'G17 - Warranties and Guarantees', 'G18 - Punchlist',
                     'G19 - Notice of Completion', 'G2 - Certificate of Payment', 'G20 - Warranty Deficiency',
                     'G21 - Construction Photos', 'G22 - Claims. Public Records Act', 'G22.1 - Claims Confidential',
                     'G23 - Commissioning', 'G24 - Building Permits', "G3 - Contractor's Schedule and Updates",
                     'G4 - Progress Meeting Notes', 'G5 - UCSC Inspectors Daily Reports', 'G5.1 - Hot Work Permits',
                     'G6 - UCSC Memoranda', 'G6.1 - Architects Field Reports', 'G7 - Contractors Daily Reports',
                     'G8 - Testing and Inspection Reports. Geotechnical Engineer',
                     'G9 - Testing and Inspection Reports. Testing Laboratory']


class ArchiverUtilities:

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
    def clean_path(path: str):
        """
        Process a path string such that it can be used regardless of the os and regardless of whether its length
        surpasses the limit in windows file systems
        :param path:
        :return:
        """
        path = path.replace('/', os.sep).replace('\\', os.sep)
        if os.sep == '\\' and '\\\\?\\' not in path:
            # fix for Windows 260 char limit
            relative_levels = len([directory for directory in path.split(os.sep) if directory == '..'])
            cwd = [directory for directory in os.getcwd().split(os.sep)] if ':' not in path else []
            path = '\\\\?\\' + os.sep.join(cwd[:len(cwd) - relative_levels] \
                                           + [directory for directory in path.split(os.sep) if directory != ''][
                                             relative_levels:])
        return path

    @staticmethod
    def is_valid_email(potential_email: str):
        email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return re.fullmatch(email_regex, potential_email)

    @staticmethod
    def cleanse_filename(proposed_filename: str):
        """removes illegal filename chars"""
        clean_filename = proposed_filename.strip()
        clean_filename = clean_filename.replace('\n','')
        clean_filename = "".join(i for i in clean_filename if i not in "\/:*?<>|")
        return clean_filename

    @staticmethod
    def project_number_from_path(file_path):
        """
        Extracts a project number from a path
        :param file_path:
        :return: project number string
        """
        path_list = ArchiverUtilities.split_path(file_path)
        project_number = None
        xx_level_idx = None
        proj_number_directory = None
        for idx, path_dir in enumerate(path_list):
            if 'xx' in path_dir and not xx_level_idx:
                xx_level_idx = idx
                continue

            if not xx_level_idx:
                continue

            if idx - 1 == xx_level_idx:
                if path_dir[0].isdigit() and path_dir[1].isdigit() and path_dir[2].isdigit():
                    project_number = path_dir.split(" ")[0]
                    proj_number_directory = path_dir
                else:
                    project_number = None
                    break

            if idx - 2 == xx_level_idx:
                if project_number in path_dir:
                    project_number = path_dir.split(" ")[0]

        return project_number

    @staticmethod
    def get_monitor_dims():
        width, height = sg.Window.get_screen_size()
        return width, height

                    

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

    @staticmethod
    def draw_figure(canvas, figure):
        figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
        figure_canvas_agg.draw()
        figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
        return figure_canvas_agg

    def make_window(self, window_name: str, window_layout: list, figure=None):
        """

        :param window_name:
        :param window_layout:
        :param figure: matplotlib figure to be included in layout, requires sg.Canvas(key='-CANVAS-') element in layout
        :return:
        """

        sg.theme(self.gui_theme)

        # launch gui
        if figure:
            window = sg.Window(window_name, layout=window_layout, finalize=True, enable_close_attempted_event=True)
            fig_canvas_agg = self.draw_figure(window['-CANVAS-'].TKCanvas, figure)
        else:
            window = sg.Window(window_name, layout=window_layout, finalize=True, enable_close_attempted_event=True)
        window.bring_to_front()
        event, values = window.read()
        values["Button Event"] = event
        window.close()
        return defaultdict(None, values)

    def directory_treedata(self, parent_dir, dir_name) -> sg.TreeData:
        """
        Creates PysimpleGUI.TreeData objects from a given directory
        https://github.com/PySimpleGUI/PySimpleGUI/blob/master/DemoPrograms/Demo_Tree_Element.py
        :param parent_dir:
        :param dir_name:
        :return:
        """

        def add_files_in_folder(treedata: sg.TreeData, parent, dirname, file_icon_bytes=None, folder_icon_bytes=None):
            files = os.listdir(dirname)
            for f in files:
                fullpath = ArchiverUtilities.clean_path(os.path.join(dirname, f))
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


    def welcome_layout(self, version_number = __version__):
        welcome_gui_layout = [
            [sg.Text(f"Archives_Archiver Version: {version_number}")],
            [sg.Text("Email address:"), sg.Input(key="Archivist Email")],
            [sg.Text("Database:"), sg.Combo(values=('Postgres', 'Sqlite'), default_value='Postgres', readonly=False, key="Database")],
            [sg.Canvas(key='-CANVAS-')],
            [sg.Button("Ok"), sg.Button("Exit")]
        ]
        return welcome_gui_layout

    def destination_choice_layout(self, dir_choices: list[str], current_filename: str, default_project_num: str = None,
                                  research_default: bool = False):
        dir_choices.sort()
        # TODO try auto_size_text and expand_y
        listbox_width = max([len(dir_name) for dir_name in dir_choices])
        listbox_height = 18
        destination_gui_layout = [
            [sg.Text(f"Choose a location for:")],
            [sg.Input(default_text=current_filename, use_readonly_for_disable=True, disabled=True,
                      background_color='#F7F3EC', text_color="black", key='Inert Filename'), sg.Button("Open Copy")],
            [sg.Text("Default Project Number:"), sg.Text(default_project_num)],
            [sg.Text("Project Number (Leave Blank to use Default.):"), sg.Input(key="New Project Number")],
            [sg.Text("Destination filename"), sg.Input(key="Filename")],
            [sg.Text("Document date:"), sg.Input(key="Document Date")],
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

    def confirmation_layout(self, destination_path: str, destination_tree_data: sg.TreeData = None,
                            similar_files: List[str]=[], dir_trees: Dict[str, sg.TreeData] = {}):
        """

        :param destination_path:
        :param similar_files:
        :param dir_trees:
        :return:
        """
        confirmation_gui_layout = [
            [sg.Text("Confirm this is correct location for this file:"), sg.Input(default_text=destination_path,
                                                                                  size=(len(destination_path),),
                                                                                  use_readonly_for_disable=True,
                                                                                  disabled=True,
                                                                                  background_color='#F7F3EC',
                                                                                  text_color="black",
                                                                                  key='Inert Destination Path')]]

        if destination_tree_data:
            destination_tree_element = sg.Tree(data=destination_tree_data,
                                               headings=['Size (KB)', ],
                                               auto_size_columns=True,
                                               select_mode=sg.TABLE_SELECT_MODE_EXTENDED,
                                               num_rows=6,
                                               col0_width=40,
                                               row_height=32,
                                               show_expanded=False,
                                               enable_events=False,
                                               expand_x=True,
                                               expand_y=True,
                                               )
            confirmation_gui_layout.append([sg.Text("Destination Directory Contents: "), destination_tree_element])


        if similar_files or dir_trees:
            confirmation_gui_layout.append([sg.HorizontalSeparator(pad=0)])
            confirmation_gui_layout.append([sg.Text("Research Results", size=(len(destination_path), 2), justification='center',
                                                    font=('bold'))])


        #if there is a list of similarly named files
        if similar_files:
            confirmation_gui_layout.append([sg.Text("Similar Filenames: ")])
            filepaths_text = ", \n".join(similar_files)
            confirmation_gui_layout.append([sg.Text(filepaths_text)])

        #create and append directory example structures into layout
        if dir_trees:
            confirmation_gui_layout.append([sg.Text("Examples of directories with the same filing codes: ")])
            tab_group_layout = []
            for tree_path, tree in dir_trees.items():
                #only use max of three examples
                if len(tab_group_layout) == 3:
                    break

                tree_element = sg.Tree(data= tree,
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
                                       )

                tab_group_layout.append(sg.Tab(tree_path, layout=[[tree_element]]))

            confirmation_gui_layout.append([sg.TabGroup([tab_group_layout])])

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

    def info_message_layout(self, info_message: str, error: bool = False):
        """

        :param info_message: Message for window
        :param error: whether the info message is error
        :return:
        """
        info_gui_layout = [
            [sg.Text(info_message)],
            [sg.Button("Back"), sg.Button("Exit")]
        ]
        if error:
            info_gui_layout = [[sg.Text("Oops, an error occured:")]] + info_gui_layout
        return info_gui_layout

    def loading_screen(self, long_func, loading_window_name: str, loading_text: str):
        """
        This function opens a simply test window for the duration of the long-func function.
        It cannot return a value; long_func would need to be written to avoid having to use its return value.
        :param long_func: the function during which the loading screen will render.
        :param loading_window_name: text along the top of the window
        :param loading_text: Text that appears within the window
        :return: None
        """
        sg.theme(self.gui_theme)
        layout = [[sg.Text(loading_text)]]
        window = sg.Window(loading_window_name, layout)

        def close_window_after_function(some_func):
            time.sleep(.001)
            some_func()
            window.write_event_value('-THREAD DONE-', '')

        threading.Thread(target=close_window_after_function, args=(long_func,), daemon=True).start()
        while True:
            event, values = window.read()
            window.bring_to_front()
            if event in (sg.WIN_CLOSED, '-THREAD DONE-'):
                window.close()
                return


class ArchivalFile:

    def __init__(self, current_path: str, project: str = None, destination_path: str = None, new_filename: str = None,
                 notes: str = None, destination_dir: str = None, document_date: str = None):
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
        self.cached_destination_path = destination_path
        self.datetime_archived = None
        self.file_code = None
        if destination_dir:
            self.file_code = ArchiverUtilities.file_code_from_destination_dir(destination_dir)
        self.document_date = None
        if document_date:
            self.document_date = parser.parse(document_date)

    def assemble_destination_filename(self):
        """
        returns the resulting anticipated filename from an anticipated archival process. Handles extensions by copying
        them from current filename to desired new filename
        :return:
        """
        current_filename = ArchiverUtilities.split_path(self.current_path)[-1]
        dest_filename = current_filename
        if self.new_filename:
            dest_filename = self.new_filename

        current_filename_list = current_filename.split(".")
        extension = current_filename_list[-1]
        split_dest_components = dest_filename.split(".")

        # if the filename already starts with the project number and filing code prefix, remove them.
        if len(split_dest_components) > 2 and dest_filename.lower().startswith(self.project_number.lower() + "."):
            no_prefix_name = dest_filename[len(self.project_number) + 1:]
            if no_prefix_name.lower().startswith(self.file_code.lower() + "."):
                no_prefix_name = no_prefix_name[len(self.file_code) + 1:]
                split_dest_components = no_prefix_name.split(".")

        # if the destination filename didn't include the file extension add it to the filename component list
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
        # TODO handle situation when there is a cached_destination_path but no destination_dir_name

        nested_dirs = self.destination_dir
        if nested_dirs[1].isdigit():
            # a directory from DIRECTORY_CHOICES is parent directory if it shares same first char and doesn't have a
            # digit in second char position
            is_parent_dir = lambda child_dir, dir: dir[0] == child_dir[0] and not dir[1].isdigit()
            parent_dir = [dir for dir in DIRECTORY_CHOICES if is_parent_dir(nested_dirs, dir)][0]
            nested_dirs = os.path.join(parent_dir, nested_dirs)
        return str(nested_dirs)

    def get_destination_path(self):
        """
        Major function that builds a plausible path string in the following steps:
        Step 1: If it already has a cached destination path, return that
        Step 2: Looks for xx directory in root (RECORDS_SERVER_LOCATION) and adds to path
        Step 3: Looks through next two levels in directory hierarchy for directories that start with the project number
            or a project number prefix and add them to the path.
        Step 4: Looks for desired directory location in nested levels and adds it to new path

        ...unless there is already a path in cached_destination_path attribute, in which case that will be returned
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
            destination_dir = ArchiverUtilities.split_path(large_template_destination)[-1]
            destination_dir_prefix = destination_dir.split(" ")[0] + " - "  # eg "F5 - ", "G12 - ", "H - ", etc
            destination_dir_parent_dir = ArchiverUtilities.split_path(large_template_destination)[0]

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
                    # assumes only one destination dir. Could be more sophisticated.
                    new_path = os.path.join(new_path, existing_destination_dirs[0])
                else:
                    file_num_dirs = [dir for dir in new_path_dirs if
                                     dir.lower().startswith(self.project_number.lower())]
                    if not file_num_dirs:
                        new_path = os.path.join(new_path, large_template_destination)
                    else:
                        # If there are multiple directories that match the project number, how should we go about
                        # deciding which one is the next part of destination path?
                        next_dir = ''
                        for next_dir in file_num_dirs:
                            # if the next dir and project number are the same we use this next_dir.
                            if len(next_dir) == len(self.project_number):
                                break

                            # if the character after project_number in the next_dir string is in this list, we will use this directory
                            char_after_number = next_dir[len(self.project_number):][0]
                            if char_after_number in [' ', ':']:
                                break
                            # if no next_dir breaks the loop, automatically use last entry from file_num_dirs

                        new_path = os.path.join(new_path, next_dir)
                        return path_from_project_num_dir_to_destination(path_to_project_num_dir=new_path,
                                                                        large_template_destination=large_template_destination,
                                                                        destination_filename=destination_filename)

            return os.path.join(new_path, destination_filename)

        ############### Start of get_destination_path() #################
        if not self.cached_destination_path:

            # sept
            xx_level_dir_prefix, project_num_prefix = ArchiverUtilities.prefixes_from_project_number(self.project_number)
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
                    self.cached_destination_path = new_path
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
                    self.cached_destination_path = new_path
                    return self.cached_destination_path

                if len(dirs_matching_proj_num) == 1:
                    new_path = os.path.join(new_path, dirs_matching_proj_num[0])
                    new_path = path_from_project_num_dir_to_destination(new_path,
                                                                        self.nested_large_template_destination_dir(),
                                                                        self.assemble_destination_filename())
                    self.cached_destination_path = new_path
                    return self.cached_destination_path

            # if we do find a dir that corresponds with the project number...
            if len(dirs_matching_proj_num) == 1:
                new_path = os.path.join(new_path, dirs_matching_proj_num[0])
                #look for another project number directory in the dirs of this project number directory
                proj_num_dir_dirs = list_of_child_dirs(new_path)
                dirs_matching_proj_num = [dir_name for dir_name in proj_num_dir_dirs if proj_num_in_dir_name(dir_name)]

                # if more than one directory starts with the same project number...
                if len(dirs_matching_proj_num) not in (0,1):
                    raise Exception(
                        f"{len(dirs_matching_proj_num)} matching directories in {new_path} for project number {self.project_number}; expected 0 or 1.")

                if len(dirs_matching_proj_num) == 0:
                    new_path = os.path.join(new_path, self.project_number)

                if len(dirs_matching_proj_num) == 1:
                    new_path = os.path.join(new_path, dirs_matching_proj_num[0])

                new_path = path_from_project_num_dir_to_destination(path_to_project_num_dir= new_path,
                                                                    large_template_destination= self.nested_large_template_destination_dir(),
                                                                    destination_filename= self.assemble_destination_filename())
                self.cached_destination_path = new_path
                return self.cached_destination_path


            self.cached_destination_path = new_path
        return self.cached_destination_path

    def attribute_defaultdict(self):
        date_stamp = ''
        doc_date = ''
        if self.datetime_archived:
            date_stamp = self.datetime_archived.strftime("%m/%d/%Y, %H:%M:%S")
        if self.document_date:
            doc_date = self.document_date.strftime("%m/%d/%Y, %H:%M:%S")
        if (self.get_destination_path() or self.current_path) and not self.size:
            if not os.path.isfile(self.get_destination_path()):
                self.size = str(os.path.getsize(self.current_path))
            else:
                self.size = str(os.path.getsize(self.get_destination_path()))

        #if we don't have a file code, generate one from the destination
        if self.destination_dir and not self.file_code:
            self.file_code = ArchiverUtilities.file_code_from_destination_dir(self.destination_dir)

        if not self.project_number:
            self.project_number = ArchiverUtilities.project_number_from_path(self.get_destination_path())

        attribute_dict = {"date_archived": date_stamp, "project_number": self.project_number,
                          "destination_path": self.get_destination_path(), "document_date": doc_date,
                          "destination_directory": self.destination_dir, "file_code": self.file_code,
                          "file_size": self.size, "notes": self.notes}
        return defaultdict(lambda: None, attribute_dict)

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

    def archive_in_destination(self):

        # if the file has already been archived return the destination path
        if self.datetime_archived:
            return self.get_destination_path()

        destination_path_list = ArchiverUtilities.split_path(self.get_destination_path())
        destination_dir_path = os.path.join(*destination_path_list[:-1])

        if not os.path.exists(destination_dir_path):
            os.makedirs(destination_dir_path)
        self.datetime_archived = datetime.now()
        try:
            shutil.copyfile(src=self.current_path, dst=self.get_destination_path())
        except Exception as e:
            return False, e
        try:
            os.remove(self.current_path)
            return True, ''
        except Exception as e:
            return False, e


class SqliteDatabase:

    def __init__(self, path):
        self.datetime_format = "%m/%d/%Y, %H:%M:%S"
        self.path = path
        self.archivist_tablename = 'archivists'
        self.document_tablename = 'arcd_files'
        self.connection = sqlite3.connect(self.path)
        self.archivists_table_cols = {'email': 'TEXT NOT NULL'}
        self.archived_doc_table_cols = {'destination_path': 'TEXT', 'project_number': 'TEXT',
                                        'document_date': 'TEXT', 'destination_directory': 'TEXT',
                                        'file_code': 'TEXT', 'file_size': 'REAL', 'date_archived': 'TEXT',
                                        'archivist_id': 'INTEGER NOT NULL', 'notes' : 'TEXT'
                                        }

        # Creates tables if they do not exist yet
        with closing(sqlite3.connect(self.path)) as conn:
            c = conn.cursor()
            archivists_setup_sql = f"""CREATE TABLE IF NOT EXISTS {self.archivist_tablename} (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE, """
            for col, col_type in self.archivists_table_cols.items():
                col = col.strip()
                col_type = col_type.strip()
                archivists_setup_sql += f"{col} {col_type}," + os.linesep
            # replace comma and newline with back-parenthese and semi-colon to end sql string
            archivists_setup_sql = archivists_setup_sql[:-3] + r"); "
            c.execute(archivists_setup_sql)

            archival_docs_setup_sql = f"""CREATE TABLE IF NOT EXISTS {self.document_tablename} (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE, """
            foreign_key_string = ""
            for col, col_type in self.archived_doc_table_cols.items():
                col = col.strip()
                col_type = col_type.strip()
                archival_docs_setup_sql += f"{col} {col_type}," + os.linesep
                if col.lower().endswith('id'):
                    foreign_key_string += f"""FOREIGN KEY({col}) REFERENCES {self.archivist_tablename}(id), """
                    foreign_key_string += os.linesep
            archival_docs_setup_sql += foreign_key_string
            archival_docs_setup_sql = archival_docs_setup_sql[:-4] + r"); "
            c.execute(archival_docs_setup_sql)

    def add_archivist(self, archivist_dict):
        column_names = list(self.archivists_table_cols.keys())
        questionmark_placeholders = ",".join(['?' for _ in column_names])
        sql_cols = ",".join(column_names)
        insert_sql = f""" INSERT INTO {self.archivist_tablename}({sql_cols}) VALUES({questionmark_placeholders}) """
        with sqlite3.connect(self.path) as conn:
            c = conn.cursor()
            vals = tuple([archivist_dict[k] for k in column_names])
            c.execute(insert_sql, vals)

    def archivist_id_from_email(self, user_email):

        with closing(sqlite3.connect(self.path)) as conn:
            c = conn.cursor()
            user_id = None
            get_user_id_sql = f"""SELECT id FROM {self.archivist_tablename} WHERE email = ?"""
            c.execute(get_user_id_sql, (user_email,))
            sql_results = c.fetchone()
            if sql_results:
                user_id = sql_results[0]
        return user_id

    def record_document(self, arch_document: ArchivalFile, archivist_email: str):
        """
        :param arch_document:
        :param archivist_email:
        :return:
        """

        column_names = list(self.archived_doc_table_cols.keys())
        questionmark_placeholders = ",".join(['?' for _ in column_names])
        sql_cols = ",".join(column_names)
        insert_sql = f""" INSERT INTO {self.document_tablename}({sql_cols}) VALUES({questionmark_placeholders}) """
        with sqlite3.connect(self.path) as conn:
            c = conn.cursor()
            attribute_val_dict = arch_document.attribute_defaultdict()
            attribute_val_dict['archivist_id'] = self.archivist_id_from_email(archivist_email)
            archived_doc_vals = []
            for col in column_names:

                if col == 'date_archived':
                    archived_doc_vals.append(datetime.now().strftime(self.datetime_format))
                    continue

                archived_doc_vals.append(attribute_val_dict[col])
            c.execute(insert_sql, archived_doc_vals)

    def generate_archived_stat_barchart(self, days=60):
        """

        :param days: number of past days from which we aggregate data
        :return:
        """

        def generate_daily_sum_dataframe(conn, days):
            # copy data to dataframes from database connection
            archived_files_df = pd.read_sql('''SELECT * FROM archived_files''', conn)
            archivists_df = pd.read_sql('''SELECT * FROM archivists''', conn)

            # This is for creating a column of archivist emails in the archived_files_df
            archived_files_df["archivist_email"] = ""
            id_df = None
            for idx, row in archived_files_df.iterrows():  # loop over dataframe rows
                archivist_id = row["archivist_id"]
                id_df = archivists_df[archivists_df["id"] == archivist_id]
                archivist_email = id_df["email"].iloc[0]
                archived_files_df.at[idx, "archivist_email"] = archivist_email

            # creates a column of datetime objects that have been created by parsing the string date in "date_archived" column
            archived_files_df["archived_dt"] = archived_files_df["date_archived"].map(parser.parse)
            daily_data = []
            for x in range(0, days):
                day = datetime.now() - timedelta(days=x)
                is_same_day = lambda dt: dt.date() == day.date()
                day_df = archived_files_df[archived_files_df["archived_dt"].map(is_same_day)]

                if day_df.shape[0] != 0:
                    # create a dictionary of the values we will add to our dictionary
                    day_row = {"datetime": day, "bytes_archived": day_df["file_size"].sum(),
                               "files_archived": day_df.shape[0]}
                    daily_data.append(day_row)

            # create a dataframe of number of files and size of files archived per day
            aggregate_daily_archived_df = pd.DataFrame(daily_data, columns=["datetime", "bytes_archived", "files_archived"])

            bytes_to_megabytes = lambda b: b / 10000000
            aggregate_daily_archived_df["bytes_archived"] = aggregate_daily_archived_df["bytes_archived"].map(
                bytes_to_megabytes)
            return aggregate_daily_archived_df

        conn = sqlite3.connect(self.path)
        daily_sum_df = generate_daily_sum_dataframe(conn=conn, days=days)
        conn.close()

        #plot settings
        sns.set(font_scale=1.3)
        sns.set_style("ticks")
        fig = plt.figure(figsize=(15, 8))
        width_scale = .45

        # create bytes charts
        bytes_axis = sns.barplot(x="datetime", y="bytes_archived", data=daily_sum_df)
        bytes_axis.set(title="Files and Megabytes Archived in last 60 Days", xlabel="Date", ylabel="MegaBytes")
        for bar in bytes_axis.containers[0]:
            bar.set_width(bar.get_width() * width_scale)

        # create files axis
        file_num_axis = bytes_axis.twinx()
        files_axis = sns.barplot(x="datetime", y="files_archived", data=daily_sum_df, hatch='xx',
                                 ax=file_num_axis)
        files_axis.set(ylabel="Files")
        for bar in files_axis.containers[0]:
            bar_x = bar.get_x()
            bar_w = bar.get_width()
            bar.set_x(bar_x + bar_w * (1 - width_scale))
            bar.set_width(bar_w * width_scale)

        reformat_label_str = lambda x: parser.parse(x.get_text()).strftime("%m/%d/%Y")
        bytes_axis.set_xticklabels([reformat_label_str(x) for x in bytes_axis.get_xticklabels()], rotation=30)

        a_val = 0.6
        colors = ['#EA5739', '#FEFFBE', '#4BB05C']
        legend_patch_files = mpatches.Patch(facecolor=colors[0], alpha=a_val, hatch=r'xx', label='Files')
        legend_patch_bytes = mpatches.Patch(facecolor=colors[0], alpha=a_val, label='Megabytes')

        plt.legend(handles=[legend_patch_files, legend_patch_bytes])
        return fig


class PostgresDatabase:

    def __init__(self, host, username, password, port, db_name):
        self.datetime_format = "%m/%d/%Y, %H:%M:%S"
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.db_name = db_name
        self.user_tablename = 'users'
        self.user_table_cols = {'email':'CHARACTER VARYING NOT NULL',
                                'first_name': 'CHARACTER VARYING',
                                'last_name':'CHARACTER VARYING',
                                'roles': 'CHARACTER VARYING',
                                'password': 'CHARACTER VARYING(60)'}
        self.archived_files_tablename = 'archived_files'
        self.archived_files_table_cols = {'destination_path': 'CHARACTER VARYING NOT NULL',
                                          'project_number': 'CHARACTER VARYING NOT NULL',
                                          'document_date': 'CHARACTER VARYING',
                                          'destination_directory':'CHARACTER VARYING NOT NULL',
                                          'file_code':'CHARACTER VARYING NOT NULL',
                                          'file_size': 'CHARACTER VARYING NOT NULL',
                                          'date_archived': 'TIMESTAMP WITHOUT TIME ZONE NOT NULL',
                                          'archivist_id': 'INTEGER NOT NULL',
                                          'notes': 'CHARACTER VARYING',
                                          'filename':'CHARACTER VARYING',
                                          'extension': 'CHARACTER VARYING'}
        self.conn = None

    def get_connection(self):
        """
        Connect to a Postgres database.
        https://hackersandslackers.com/psycopg2-postgres-python/
        :return:
        """
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(
                host=self.host,
                user=self.username,
                password=self.password,
                port=self.port,
                dbname=self.db_name
            )

        return self.conn

    def add_user(self, user_dict: dict):
        """

        :param user_dict:
        :return:
        """
        column_names = list(self.user_table_cols.keys())
        questionmark_placeholders = ",".join(['?' for _ in column_names])
        sql_cols = ",".join(column_names)
        insert_sql = f""" INSERT INTO {self.user_tablename}({sql_cols}) VALUES({questionmark_placeholders}) """
        with closing(self.get_connection()) as conn:
            c = conn.cursor()
            vals = tuple([user_dict[k] for k in column_names])
            c.execute(insert_sql, vals)

    def archivist_id_from_email(self, email):
        with closing(self.get_connection()) as conn:
            c = conn.cursor()
            user_id = None
            get_user_id_sql = f"""SELECT id FROM {self.user_tablename} WHERE email = '{email}';"""
            c.execute(get_user_id_sql)
            sql_results = c.fetchone()
            if sql_results:
                    user_id = sql_results[0]
        return user_id

    def record_document(self, arch_document: ArchivalFile, archivist_email: str):
        """
        :param arch_document:
        :param archivist_email:
        :return:
        """

        column_names = list(self.archived_files_table_cols.keys())
        placeholders = ",".join(['%s' for _ in column_names])
        sql_cols = ",".join(column_names)
        insert_sql = f"""INSERT INTO {self.archived_files_tablename}({sql_cols}) VALUES ({placeholders})"""
        attribute_val_dict = arch_document.attribute_defaultdict()
        attribute_val_dict['archivist_id'] = self.archivist_id_from_email(archivist_email)
        with closing(self.get_connection()) as conn:
            archived_doc_vals = []
            for col in column_names:

                if col == 'date_archived':
                    archived_doc_vals.append(datetime.now().strftime(self.datetime_format))
                    continue

                archived_doc_vals.append(attribute_val_dict[col])

            c = conn.cursor()
            c.execute(insert_sql, archived_doc_vals)


    def generate_archived_stat_barchart(self, days=60):
        """

        :param days: number of past days from which we aggregate data
        :return:
        """


        def generate_daily_sum_dataframe(conn, days):
            # copy data to dataframes from database connection
            archived_files_df = pd.read_sql(f'''SELECT * FROM {self.archived_files_tablename}''', conn)
            archivists_df = pd.read_sql(f'''SELECT * FROM {self.user_tablename}''', conn)
            #TODO use sql query to only get relevant records

            # This is for creating a column of archivist emails in the archived_files_df
            archived_files_df["archivist_email"] = ""
            id_df = None
            for idx, row in archived_files_df.iterrows():  # loop over dataframe rows
                archivist_id = row["archivist_id"]
                id_df = archivists_df[archivists_df["id"] == archivist_id]
                archivist_email = id_df["email"].iloc[0]
                archived_files_df.at[idx, "archivist_email"] = archivist_email

            # creates a column of datetime objects that have been created by parsing the string date in "date_archived" column
            archived_files_df["archived_dt"] = archived_files_df["date_archived"].map(parser.parse)
            daily_data = []
            for x in range(0, days):
                day = datetime.now() - timedelta(days=x)
                is_same_day = lambda dt: dt.date() == day.date()
                day_df = archived_files_df[archived_files_df["archived_dt"].map(is_same_day)]

                if day_df.shape[0] != 0:
                    # create a dictionary of the values we will add to our dictionary
                    day_row = {"datetime": day, "bytes_archived": day_df["file_size"].sum(),
                               "files_archived": day_df.shape[0]}
                    daily_data.append(day_row)

            # create a dataframe of number of files and size of files archived per day
            aggregate_daily_archived_df = pd.DataFrame(daily_data, columns=["datetime", "bytes_archived", "files_archived"])

            bytes_to_megabytes = lambda b: b / 10000000
            aggregate_daily_archived_df["bytes_archived"] = aggregate_daily_archived_df["bytes_archived"].map(
                bytes_to_megabytes)
            return aggregate_daily_archived_df

        conn = self.get_connection()
        daily_sum_df = generate_daily_sum_dataframe(conn=conn, days=days)
        conn.close()

        #plot settings
        sns.set(font_scale=1.3)
        sns.set_style("ticks")
        fig = plt.figure(figsize=(15, 8))
        width_scale = .45

        # create bytes charts
        bytes_axis = sns.barplot(x="datetime", y="bytes_archived", data=daily_sum_df)
        bytes_axis.set(title="Files and Megabytes Archived in last 60 Days", xlabel="Date", ylabel="MegaBytes")
        for bar in bytes_axis.containers[0]:
            bar.set_width(bar.get_width() * width_scale)

        # create files axis
        file_num_axis = bytes_axis.twinx()
        files_axis = sns.barplot(x="datetime", y="files_archived", data=daily_sum_df, hatch='xx',
                                 ax=file_num_axis)
        files_axis.set(ylabel="Files")
        for bar in files_axis.containers[0]:
            bar_x = bar.get_x()
            bar_w = bar.get_width()
            bar.set_x(bar_x + bar_w * (1 - width_scale))
            bar.set_width(bar_w * width_scale)

        reformat_label_str = lambda x: parser.parse(x.get_text()).strftime("%m/%d/%Y")
        bytes_axis.set_xticklabels([reformat_label_str(x) for x in bytes_axis.get_xticklabels()], rotation=30)

        a_val = 0.6
        colors = ['#EA5739', '#FEFFBE', '#4BB05C']
        legend_patch_files = mpatches.Patch(facecolor=colors[0], alpha=a_val, hatch=r'xx', label='Files')
        legend_patch_bytes = mpatches.Patch(facecolor=colors[0], alpha=a_val, label='Megabytes')

        plt.legend(handles=[legend_patch_files, legend_patch_bytes])
        return fig


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
            example_dir_name = ArchiverUtilities.split_path(dir_example_path)[-1]
            if not probably_has_filing_code(example_dir_name):
                return False

            # if the directory doesn't share a filing code with chosen destination dir, it is not a good example
            example_file_code = ArchiverUtilities.file_code_from_destination_dir(example_dir_name)
            if not ArchiverUtilities.file_code_from_destination_dir(chosen_destination_dir) == example_file_code:
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
                 gui_file_icon: str, gui_dir_icon: str, database: Union[SqliteDatabase, PostgresDatabase],
                 file_to_archive: ArchivalFile = None):

        ##Build necessary directory structure###
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
        self.database = database
        self.datetime_format = "%m/%d/%Y, %H:%M:%S"

    def info_window(self, window_name="ERROR", info_message='', is_error=True) -> bool:
        """

        :param is_error: Should it use special configuration for displaying errors.
        :param window_name:
        :param info_message: string message to display
        :return: bool whether user hit 'ok' button or not
        """
        info_layout = self.gui.info_message_layout(info_message=info_message, error=is_error)
        info_window_results = self.gui.make_window(window_name=window_name, window_layout=info_layout)
        if info_window_results["Button Event"].lower() in ["exit", self.gui.window_close_button_event.lower()]:
            self.exit_app()
        return info_window_results["Button Event"].lower() == "ok"

    def get_setup_info(self):

        def validate_email(email_str):
            if (not 'ucsc' in email_str) or (not '@' in email_str):
                return False
            return True

        while not self.email:
            welcome_window_layout = self.gui.welcome_layout()
            welcome_window_results = self.gui.make_window(window_name="Welcome!", window_layout=welcome_window_layout)
            # if the user clicks exit, shutdown app
            if welcome_window_results["Button Event"].lower() in ["exit", self.gui.window_close_button_event.lower()]:
                self.exit_app()
            else:
                email_entry = welcome_window_results["Archivist Email"].lower().strip()
                database_choice = welcome_window_results["Database"]

                if not validate_email(email_entry):
                    self.info_window(info_message="Please enter your UCSC email. Cannot continue without ucsc email.")
                else:
                    self.email = email_entry
        return email_entry, database_choice

    def open_file_copy(self, filepath: str = ''):
        """
        Creates a copy of the file in the opened_copies_directory directory and opens that copy. Will open
        self.file_to_archive if no filepath parameter is given
        :return: None
        """
        if not filepath:
            filepath = self.file_to_archive.current_path
        timestamp = str(time.time()).split(".")[0]
        filename = ArchiverUtilities.split_path(filepath)[-1]
        copies_dir = os.path.join(os.getcwd(), self.opened_copies_directory)
        copy_path = os.path.join(copies_dir, (timestamp + "_" + filename))
        shutil.copyfile(src=filepath, dst=copy_path)
        ArchiverUtilities.open_file_with_system_application(copy_path)
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

        current_file = ArchiverUtilities.split_path(files_in_archiving_dir[0])[-1]
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
            file_code = ''
            if destination_gui_results["Directory Choice"]:
                directory_choice = destination_gui_results["Directory Choice"][0]

            # If there was a manually entered path, populate the file_code, destination_dir, and cached_destination_path
            # attribute for the file_to_archive attribute.
            manual_archived_path = destination_gui_results["Manual Path"]
            doc_date = destination_gui_results["Document Date"]
            if manual_archived_path:

                # Need to attempt to extract the destination directory from manual filepath
                # Do this by moving in reverse through the path and grabbing highest level directory that starts with
                # with a filing code
                file_codes_list = [ArchiverUtilities.file_code_from_destination_dir(dir) for dir in DIRECTORY_CHOICES]
                file_codes_list = [code + " " if len(code) == 1 else code for code in file_codes_list]
                directory_choice = ""
                manual_path_list = ArchiverUtilities.split_path(manual_archived_path)
                manual_path_list.reverse()
                for idx, dirname in enumerate(manual_path_list):
                    if (dirname[:3] in file_codes_list) or (dirname[:2] in file_codes_list):
                        directory_choice = dirname
                        break

                if not directory_choice:
                    raise Exception(f"Could not parse a filing code from the given directory path: \n{manual_archived_path}")

                file_code = ArchiverUtilities.file_code_from_destination_dir(directory_choice)

                # Attempt to get the project number from the path.
                # If no project number then request archivist enter one.
                project_num = ArchiverUtilities.project_number_from_path(manual_archived_path)

            if not project_num:
                error = "Missing a project number. Please enter a project number"
                no_proj_num_layout = self.gui.info_message_layout(info_message=str(error), error=True)
                self.gui.make_window("Missing project number", window_layout=no_proj_num_layout)
                return ""

            file_notes = destination_gui_results["Notes"]
            new_filename = None
            if destination_gui_results["Filename"]:
                new_filename = ArchiverUtilities.cleanse_filename(destination_gui_results["Filename"])
            self.file_to_archive = ArchivalFile(current_path=files_in_archiving_dir[0],
                                                project=project_num,
                                                new_filename=new_filename,
                                                destination_dir=directory_choice,
                                                document_date=doc_date,
                                                notes=file_notes)

            if not self.file_to_archive.destination_dir:
                error = "Missing a destination directory. Please select a destination form filing codes"
                no_destination_layout = self.gui.info_message_layout(info_message=str(error), error=True)
                self.gui.make_window("Missing filing code or destination", window_layout=no_destination_layout)
                return ""

            if manual_archived_path:
                if file_code:
                    self.file_to_archive.file_code = file_code
                self.file_to_archive.cached_destination_path = os.path.join(manual_archived_path,
                                                                            self.file_to_archive.assemble_destination_filename())
        return self.file_to_archive

    def research_for_archival_file(self, files=[], destinations=[]):
        """
        This wrapper function packages the results of the researcher so that it can be called within the
        GuiHandler.Loading_screen() which cannot return values
        :param files:
        :param destinations:
        :return:
        """
        filename = self.file_to_archive.new_filename
        if not filename:
            filename = ArchiverUtilities.split_path(self.file_to_archive.current_path)[-1]
        files += self.researcher.similar_filename_paths(original_filename=filename, duration=6, similarity_threshold=72,
                                                        max_paths=7)

        destinations += self.researcher.randomized_destination_examples(
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
            file_destination = self.file_to_archive.get_destination_path()
        except Exception as error:
            except_layout = self.gui.info_message_layout(info_message=str(error), error=True)
            gui_results = self.gui.make_window(window_name="Invalid Destination Choices", window_layout=except_layout)
            if gui_results["Button Event"].lower() in ["exit", self.gui.window_close_button_event.lower()]:
                self.exit_app()
            return False

        else:
            # If the destination directory exists, we'll display its contents as a tree element. First need to extract
            # the path to the destination directory and see if it already exists.
            destination_tree = None
            destination_list = ArchiverUtilities.split_path(self.file_to_archive.get_destination_path())
            path_to_destination_dir = os.path.join(*destination_list[:-1])
            if os.path.exists(path_to_destination_dir):
                destination_tree = self.gui.directory_treedata('', path_to_destination_dir)

            #if user chose to do research...
            similar_files_paths, destination_examples = [], []
            if self.perform_research:

                # The loading screen gui cannot return values. hence some jiggery-pokery to make the functions change
                # existing objects en lieu of returning the research results
                perform_research = lambda : self.research_for_archival_file(files=similar_files_paths,
                                                                            destinations=destination_examples)
                self.gui.loading_screen(long_func=perform_research, loading_window_name="Researching...",
                                        loading_text= "Performing research. Please wait...")
                similar_files_paths = [path['filepath'] for path in similar_files_paths]
                # create tree data structures from directory paths
                destination_examples = {path: self.gui.directory_treedata('', path) for path in destination_examples}

            confirmation_gui_layout = self.gui.confirmation_layout(destination_path=file_destination,
                                                                   destination_tree_data=destination_tree,
                                                                   similar_files=similar_files_paths,
                                                                   dir_trees=destination_examples)
            gui_results = self.gui.make_window("Confirm destination choice.", confirmation_gui_layout)
            if gui_results["Button Event"].lower() in ["exit", self.gui.window_close_button_event.lower()]:
                self.exit_app()

        return gui_results["Button Event"].lower() == "ok"

    def archive_file(self):

        #if there is a path collision throw an error
        if self.file_to_archive.cached_destination_path and os.path.exists(self.file_to_archive.cached_destination_path):
            self.info_window(
                info_message=f"A file exists in that location with the same path: {self.file_to_archive.cached_destination_path}")
            return

        #try to archive the file (kinda fraught) and display any isssues that might have come up.
        archiving_successful, archive_exception = self.file_to_archive.archive_in_destination()
        if not archiving_successful:
            permission_issue = self.file_to_archive.check_permissions()
            permissions_error_message = "When attempting to duplicate the file to the records drive, \n" +\
                                        "the application ran into file access issues: \n"

            if archive_exception:
                permissions_error_message += f"The shutil.copyfile() call produced this error: \n {archive_exception}\n"
            if permission_issue:
                permissions_error_message += f"Testing the permissions of the file yielded: \n {permission_issue}\n"

            self.info_window(info_message=permissions_error_message)
            return False

        return True

    def add_archived_file_to_csv(self, csv_path):
        """
        Method for saving the metadata from a file to archive in a csv file.
        Deprecated en lieu of using sql storage solution.
        :param csv_path:
        :return:
        """
        data_dict = self.file_to_archive.attribute_defaultdict()
        data_dict["archiver_email"] = self.email

        # make csv file if it doesn't yet exist
        if not os.path.exists(csv_path):
            df = pd.DataFrame(columns= list(data_dict.keys()))
            df.to_csv(csv_path)

        archived_file_df = pd.DataFrame(data_dict, index=[0, ])
        archived_file_df.to_csv(csv_path, mode='a', index=False, header=False)

    def add_archived_file_to_database(self):
        """
        Stores archival metadata in the database
        :return:
        """
        self.database.record_document(arch_document= self.file_to_archive, archivist_email= self.email)

    def retrieve_file_to_archive(self):
        """
        Ensures files exit to be archived and that the next file is queued up as the Archivist.file_to_archive
        :return:
        """
        while not self.files_to_archive():
            no_file_error_message = f"No files to archive. To archive additional files, add them to: " + os.linesep +\
                                    f"{self.files_to_archive_directory}"

            self.info_window(window_name="Directory Empty", info_message=no_file_error_message, is_error=False)

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

        dest_path = file.get_destination_path()
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
        def wait_eight():
            print("waiting 8 seconds.")
            time.sleep(8)
            print("wait over")
        gui = GuiHandler()


        gui.loading_screen(wait_eight)
        return

    @staticmethod
    def test_layout(some_layout):
        window = sg.Window("test", some_layout)
        event, values = window.read()
        time.sleep(2)
        window.close()
        return event, values

    @staticmethod
    def test_sqlitedb():
        location = r"\\128.114.170.27\Cannon_Scans\test_db"
        datetime_format = "%m/%d/%Y, %H:%M:%S"
        DB = SqliteDatabase(location, "test.db", datetime_format)
        test_file = ArchivalFile(
            current_path=r"C:\Users\adankert\Google Drive\GitHub\archives_archiver\files_to_archive\20220317103244.pdf",
            project='2512',destination_path=r"R:\24xx   Physical Plant Buildings\2512\F8 - Contract",
            new_filename= "RFI 061",notes="These are test notes",destination_dir="F8 - Contract",
            document_date="December 5, 2012")
        DB.record_document(test_file, 'testemail2@ucsc.edu')


def main():
    app_files_dir = 'app_files'
    gui_file_icon_filename = "file_3d_32x32.png"
    gui_dir_icon_filename = "folder_3d_32x32.png"

    # Use this code to replace the application database with a sqlite database
    # sqlite_database_path = r"\\ppcou.ucsc.edu\Data\Archive_Data\archives_archiver.db"
    # db = SqliteDatabase(sqlite_database_path)

    # create PostgresDatabase object
    prod_postgres_db_info = {"host":r"128.114.128.27",
                             "username":"archives",
                             "password":"1156High",
                             "port":"5432",
                             "db_name":"archives"}

    test_postgres_db_info = {"host": r"localhost",
                             "username": "archives",
                             "password": "1156high",
                             "port": "5432",
                             "db_name": "archives"}

    sqlite_db_path = ""

    db = PostgresDatabase(**prod_postgres_db_info)

    dir_of_files_to_archive = os.path.join(os.getcwd(), "files_to_archive")
    ppdo_archivist = Archivist(files_to_archive_directory=dir_of_files_to_archive,
                               app_files_directory=os.path.join(os.getcwd(), app_files_dir),
                               records_drive_path=RECORDS_SERVER_LOCATION,
                               gui_file_icon=gui_file_icon_filename,
                               gui_dir_icon=gui_dir_icon_filename,
                               database=None)

    user_email = None
    while not user_email:
        user_email, db_choice = ppdo_archivist.get_setup_info()
        if db_choice == 'Postgres':
            ppdo_archivist.database = PostgresDatabase(**prod_postgres_db_info)
        else:
            ppdo_archivist.database = SqliteDatabase(path=sqlite_db_path)

        # Test the connection to the database.
        try:
            with closing(ppdo_archivist.database.get_connection()) as conn:
                pass
        except Exception as e:
            msg = "There was an error connecting to the database. (Are you connected to the VPN?)"
            ppdo_archivist.info_window(window_name="DB connection error",
                                       info_message=msg)
            continue

        # see if a user account exists for the input email
        user_idx = ppdo_archivist.database.archivist_id_from_email(user_email)
        if not user_idx:
            ppdo_archivist.info_window(window_name="No account for this email.",
                                       info_message=f"There is no account found for this email: {user_email}.")
            user_email = None

    while True:
        ppdo_archivist.retrieve_file_to_archive()
        retrieved_dest = ppdo_archivist.retrieve_file_destination_choice()

        # if no destination directory or project number was chosen display error message
        if not retrieved_dest:
            continue

        destination_confirmed = ppdo_archivist.confirm_chosen_file_destination()
        if destination_confirmed:
            is_archived = ppdo_archivist.archive_file()
            if is_archived:
                ppdo_archivist.add_archived_file_to_database()
                print(f"File archived: " + os.linesep + f"{ppdo_archivist.file_to_archive.cached_destination_path}")


if __name__ == "__main__":
    # Tester.test_gui()
    # Tester.test_assemble_destination_path()
    # Tester.test_researcher()
    # Tester.test_loading_screen()
    #Tester.test_sqlitedb()
    main()
