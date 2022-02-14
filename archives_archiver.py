import os
import logging
import shutil
import pandas as pd
import PySimpleGUI as sg

from collections import defaultdict
from datetime import datetime


# Typing Aliases


# Environmental Variables
RECORDS_SERVER_LOCATION = r"""R:\\"""
FILENAMES_TO_IGNORE = ["desktop.ini", "desktop.ini"]
DIRECTORY_CHOICES = ['A - General', 'B - Administrative Reviews and Approvals', 'C - Consultants',
                     'D - Environmental Review Process', 'E - Program and Design',
                     'F - Bid Documents and Contract Award', 'G - Construction', "H - Submittals and O&M's",
                     'A1 - Miscellaneous', 'A2 - Working File', 'A3 - Project Directory Matrix & Project Chronology',
                     "B1 - CPS and Chancellor's Approvals", 'B100 - Other', 'B11 - LEED',
                     'B12 - Outside Regulatory Agencies', 'B13 - Coastal Commission',
                     'B2 - Office of the President UC Regents', 'B3 - State Public Works Board',
                     'B4 - Department of Finance', 'B5 - Legislavtive Submittals', 'B6 - State Fire Marshal',
                     'B7 - Office of State Architect  (DSA)', 'B8 -  General Counsel',
                     'B8.1 - General Counsel - Confidential', 'C1 - Executive Architect', 'C1.1 - Selection',
                     'C1.2 - Correspondence', 'C1.3 - Agreement', 'C2 - Other Consultants', 'C2.1 - Selection',
                     'C2.2 - Correspondence', 'C2.3 - Agreement', 'D1 - Environmental Correspondence',
                     'D2 - EIC Forms', 'D3 - CEQA Documentation', 'D4 - Mitigation Monitoring Program', 'E1 - DPP',
                     'E2 - PPG', 'E3 - Budget Cost Estimates', 'E4 - Planning Schedules',
                     'E5 - Program and Design Correspondence', 'E5.1 - Executive Architect to.from',
                     'E5.2 - Special Consultants', 'E5.3 - Users. Building Committee. Campus to.from',
                     'E5.4 - PPC and PP', 'E5.5 - Office of the President to.from', 'E5.6 - Building Committee to.from',
                     'E5.7 - Other', 'E5.8 - Office of General Counsel', 'E6 - Reports (soils, structural, calcs)',
                     'E7 - Value Engineering', 'E7.1 - Value Engineering Correspondence',
                     'E7.2 - VE Workshop Minutes, Summaries, Final Reports', 'E8 - Program and Design Meeting Minutes',
                     'F1 - Bid and Contract Award Correspondence', 'F1.1 - Executive Architect to.from',
                     'F1.2 - Special Consultatns to.from', 'F1.4 - PPC and PP',
                     'F1.5 - Office of the President to.from', 'F1.6 - General Cousel to.from',
                     'F1.6A - Gerneal Counsel Confidential', 'F1.7 - Pre-Qualification', 'F1.8 - Other',
                     'F10 - Escrow Agreement', 'F2 - Reviews', 'F2.1 - Constructibility, Code Reviews',
                     'F2.2 - In-house. PP reviews', 'F2.3 - Independent Cost Review',
                     'F2.4 - Independent Seismic Review', 'F2.5 - Other', 'F5 - Drawings and Spec',
                     'F7 - Bid Summary Forms', 'F7.1 - Bid Protest', 'F8 - Contract', 'F9 - Builders Risk Insurance',
                     'G1 - Construction Correspondence', 'G1.1 - Contractor to.from',
                     'G1.2 - Executive Architect to.from', 'G1.3 - Users.Building Committee.Campus to.from',
                     'G1.4 - PPC and PP. Certified Payroll', 'G1.5 - Geotechnical Engineer to.from',
                     'G1.6 - Testing and Inspection to Laboratory to.from', 'G1.7 - General Counsel to.from',
                     'G1.7A - General Counsel Confidential', 'G1.8 - Other',
                     'G10 - Testing and Inspection Reports.Other',
                     'G11 - Proposal Request. Bulletins. Contractors Response',
                     'G11.1 - Proposal Request 1 with back up', 'G11.2 - Proposal Request 2',
                     'G11.3 - Proposal Request 3', 'G12 - Request for Information RFI',
                     'G13 - Letter of Instruction LOI', 'G14 - User Request Change in Scope', 'G15 - Change Order',
                     'G15.1 - Change Order 1 with back up', 'G15.2 - Change Order 2', 'G15.3 - Change Order 3',
                     'G16 - Field Orders', 'G17 - Warranties and Guarantees', 'G18 - Punchlist', 'G19 - NOC',
                     'G2 - Certificate of Payment', 'G20 - Warrranty Deficiency', 'G21 - Construction Photos',
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
        return (prefix + 'xx', project_no)


class GuiHandler:
    """
        This class is used to create and launch the various GUI windows used by the script.

        """

    def __init__(self):
        self.gui_theme = "DarkTeal6"


    def make_window(self, window_name: str, window_layout: list):
        sg.theme(self.gui_theme)
        # launch gui
        dist_window = sg.Window(window_name, window_layout)
        event, values = dist_window.read()
        values["Button Event"] = event
        dist_window.close()
        return defaultdict(None, values)


    def welcome_layout(self):
        welcome_gui_layout = [
            [sg.Text("Email address:"), sg.Input(key="Archivist Email")],
            [sg.Button("Ok"), sg.Button("Exit")]
        ]
        return welcome_gui_layout


    def destination_choice_layout(self, dir_choices: list[str], current_filename: str, default_project_num: str = None):
        dir_choices.sort()
        # TODO try auto_size_text and expand_y
        listbox_width = max([len(dir_name) for dir_name in dir_choices])
        listbox_height = 20

        destination_gui_layout = [[sg.Text(f"Choose a destination location for {current_filename}",
                                           auto_size_text= True, justification= 'center')],
                                  [sg.Text("Default Project:"), sg.Text(default_project_num)],
                                  [sg.Text("Project Number (Leave Blank to use Default.):"),
                                   sg.Input(key="New Project Number")],
                                  [sg.Text("Choose Directory to for file:"),
                                   sg.Listbox(values=dir_choices, key="Directory Choice",
                                              size=(listbox_width, listbox_height))],
                                  [sg.Text(
                                      "Alternatively, Enter the full path to directory where the file has been archived:")],
                                  [sg.Input(key="Manual Path")]]

        destination_gui_layout.append([sg.Button("Ok"), sg.Button("Exit")])
        return destination_gui_layout


    def confirmation_layout(self, destination_path):
        # TODO make this window. Should it have
        treedata = sg.TreeData()

        confirmation_gui_layout = [
            [sg.Text("Confirm this is correct location for this file:")],
            [sg.Text(destination_path)],
            [sg.Text("Similar directories:")],
            #[sg.Tree(data= treedata)],
            [sg.Button("Ok"), sg.Button("Back"), sg.Button("exit")]
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

    def __init__(self, current_path: str, project: str, destination_path: str = None, new_filename: str = None,
                 notes: str = None, destination_dir: str = None):
        """

        :param current_path: path to  file
        :param project: project number string
        :param destination_path: the desired path for the file when tit is archived
        :param new_filename: optional file name for the destination file
        :param notes: for recording notes in the database
        :param destination_dir: chosen directory from the directory templates
        """
        self.current_path      = current_path
        self.project_number    = project
        self.destination_dir   = destination_dir
        self.new_filename      = new_filename
        self.notes             = notes
        self.destination_path  = destination_path
        self.datetime_archived = None


    def get_destination_filename(self):
        """
        returns the resulting anticipated filename from an anticipated archival process. Handles extensions by copying
        them from current filename to desired new filename
        :return:
        """

        current_filename = ArchiverHelpers.split_path(self.current_path)[-1]

        if not self.new_filename:
            return current_filename

        extension = current_filename.split(".")[-1]
        destination_filename = self.new_filename
        split_filename = self.new_filename.split(".")
        if split_filename[-1] == extension:
            return destination_filename

        split_filename.append(extension)
        destination_filename = ".".join(split_filename)
        return destination_filename

    def nested_large_template_destination_dir(self):
        """
        eg  "E - Program and Design\E5 - Correspondence"

        :return:
        """
        # TODO handle situation when there is a destination_path but no destination_dir

        nested_dirs = self.destination_dir
        if nested_dirs[1].isdigit():
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
            :param destination_filename: given by ArchivalFile.get_destination_filename()
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
                            new_path = path_from_project_num_dir_to_destination(path_to_project_num_dir= new_path,
                                                                                large_template_destination= large_template_destination,
                                                                                destination_filename= destination_filename)

            # if the destination_dir doesn't have a project template dir parent...
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


        if not self.destination_path:

            # sept
            xx_level_dir_prefix, project_num_prefix = ArchiverHelpers.prefixes_from_project_number(self.project_number)
            root_directories_list = list_of_child_dirs(RECORDS_SERVER_LOCATION)
            matching_root_dirs = [dir_name for dir_name in root_directories_list if
                                  dir_name.lower().startswith(xx_level_dir_prefix.lower())]

            # if we have more than one matching root dir we throw an error
            if len(matching_root_dirs) != 1:
                logging.exception(
                    f"{len(matching_root_dirs)} matching directories in {RECORDS_SERVER_LOCATION} for project number {self.project_number}",
                    exc_info=True)
                return ''

            new_path = os.path.join(RECORDS_SERVER_LOCATION, matching_root_dirs[0])
            # list of contents of xx level directory which are not files (ie directories in xx level directory)
            xx_dir_dirs = list_of_child_dirs(new_path)

            # lambda functions that check a directory name starts with either project number or prefix respectively
            proj_num_in_dir_name = lambda dir_name: self.project_number == dir_name.split(" ")[0]
            prefix_in_dir_name = lambda dir_name: project_num_prefix == dir_name.split(" ")[0]
            dirs_matching_proj_num = [dir_name for dir_name in xx_dir_dirs if proj_num_in_dir_name(dir_name)]

            # if more than one directory starts with the same project number...
            if len(dirs_matching_proj_num) > 1:
                logging.exception(
                    f"{len(dirs_matching_proj_num)} matching directories in {new_path} for project number {self.project_number}; expected 0 or 1.",
                    exc_info=True)
                return ''

            # if no directories match the project number...
            if len(dirs_matching_proj_num) == 0:
                dirs_matching_prefix = [dir_name for dir_name in xx_dir_dirs if prefix_in_dir_name(dir_name)]
                if len(dirs_matching_prefix) > 1:
                    logging.exception(
                        f"{len(dirs_matching_prefix)} matching directories in {new_path} for prefix for project number {self.project_number}; expected 0 or 1.",
                        exc_info=True)
                    return ''

                # if there is now project number or prefix directory at the 'xx' level, it will need to be made
                if len(dirs_matching_prefix) == 0:
                    new_path = os.path.join(new_path, project_num_prefix)
                    new_path = os.path.join(new_path, self.project_number)
                    new_path = os.path.join(new_path, self.nested_large_template_destination_dir())
                    new_path = os.path.join(new_path, self.get_destination_filename())
                    self.destination_path = new_path
                    return new_path

                if len(dirs_matching_prefix) == 1:
                    # if a dir exists that does begin with the prefix, we'll add it to our path and look again for
                    # directories that begin with the project number #TODO ..and prefix?

                    new_path = os.path.join(new_path, dirs_matching_prefix[0])
                    prefix_dir_dirs = list_of_child_dirs(new_path)
                    dirs_matching_proj_num = [dir_name for dir_name in prefix_dir_dirs if
                                              proj_num_in_dir_name(dir_name)]
                    if len(dirs_matching_proj_num) > 1:
                        logging.exception(
                            f"{len(dirs_matching_proj_num)} matching directories in {new_path} for project number {self.project_number}; expected 0 or 1.",
                            exc_info=True)
                        return ''

                if len(dirs_matching_proj_num) == 0:
                    new_path = os.path.join(new_path, self.project_number)
                    new_path = path_from_project_num_dir_to_destination(new_path,
                                                                        self.nested_large_template_destination_dir(),
                                                                        self.get_destination_filename())
                if len(dirs_matching_proj_num) == 1:
                    new_path = os.path.join(new_path, dirs_matching_proj_num[0])
                    new_path = path_from_project_num_dir_to_destination(new_path,
                                                                        self.nested_large_template_destination_dir(),
                                                                        self.get_destination_filename())

            # if we do find a dir that corresponds with the project number...
            if len(dirs_matching_proj_num) == 1:
                new_path = os.path.join(new_path, dirs_matching_proj_num[0])
                new_path = path_from_project_num_dir_to_destination(new_path,
                                                                    self.nested_large_template_destination_dir(),
                                                                    self.get_destination_filename())

            self.destination_path = new_path

        return self.destination_path

    def attribute_defaultdict(self):
        dict = {"time_archived": self.datetime_archived.strftime("%m/%d/%Y, %H:%M:%S"), "project_number": self.project_number,
                "destination_path": self.destination_path, "destination_directory": self.destination_dir,
                "notes": self.notes}
        return defaultdict(None, dict)

    def archive(self, destination= None):

        #if the file has already been archived return the destination path
        if self.datetime_archived:
            return self.destination_path

        #process optional parameter destination
        if destination:
            if destination in DIRECTORY_CHOICES:
                self.destination_dir = destination
            else:
                self.destination_path = destination

        if not self.destination_path:
            self.assemble_destination_path()

        destination_path_list = ArchiverHelpers.split_path(self.destination_path)
        destination_dir_path = os.path.join(*destination_path_list[:-1])

        os.makedirs(destination_dir_path)
        self.datetime_archived = datetime.now()
        return  shutil.move(self.current_path, self.destination_path)


class Researcher:

    def __init__(self, research_cache_filepath):
        self.research_cache_filepath = research_cache_filepath
        pass

    def similar_filename_paths(self):
        pass

    def destination_examples(self):
        pass

class Archivist:
    """
    Class for executing main archiving procedure
    """

    def __init__(self, files_to_archive_directory: str, records_drive_path: str,
                 file_to_archive: ArchivalFile = None):

        self.files_to_archive_directory = files_to_archive_directory
        if not os.path.exists(files_to_archive_directory):
            try:
                os.mkdir(files_to_archive_directory)
            except Exception as e:
                print(e)
                print(f"error from trying to make {files_to_archive_directory}")

        self.records_drive_path = records_drive_path
        self.gui = GuiHandler()
        self.file_to_archive = file_to_archive
        self.email = None
        self.default_project_number = None

    def display_error(self, error_message):
        """

        :param error_message:
        :return: bool whether user hit 'ok' button or not
        """
        error_layout = self.gui.error_message_layout(error_message= error_message)
        error_window_results = self.gui.make_window(window_name= "ERROR",window_layout= error_layout)
        if error_window_results["Button Event"].lower() == "exit":
            self.exit_app()
        return error_window_results["Button Event"].lower() == "ok"

    def retrieve_email(self):

        welcome_window_layout = self.gui.welcome_layout()
        welcome_window_results = self.gui.make_window("Welcome!", welcome_window_layout)

        # if the user clicks exit, shutdown app
        if welcome_window_results["Button Event"].lower() == "exit":
            self.exit_app()
        else:
            self.email = welcome_window_results["Archivist Email"]
            return

    def files_to_archive(self, archiver_dir_path=None):
        """
        return a list of paths to files to archive in the self.files_to_archive_directory or achiver_dir_path
        :param archiver_dir_path: path to directory with files to archive
        :return: List of filepaths
        """
        if self.files_to_archive_directory and not archiver_dir_path:
            archiver_dir_path = self.files_to_archive_directory

        if archiver_dir_path:
            self.files_to_archive_directory = archiver_dir_path

        files = [os.path.join(archiver_dir_path, file) for file in os.listdir(archiver_dir_path) if
                 not (file in FILENAMES_TO_IGNORE or os.path.isdir(os.path.join(archiver_dir_path, file)))]
        return files

    def elicit_destination_selection(self):
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
                                                                       current_filename= current_file,
                                                                       default_project_num=default_proj_number)
        destination_gui_results = self.gui.make_window(window_name="Enter file and destination info.",
                                                       window_layout=destination_window_layout)

        if destination_gui_results["Button Event"].lower() == "exit":
            self.exit_app()

        self.default_project_number = destination_gui_results["New Project Number"]

        if destination_gui_results["Button Event"].lower() == "back":
            return ""

        if destination_gui_results["Button Event"].lower() == "ok":
            project_num = destination_gui_results["New Project Number"]
            if not project_num:
                project_num = default_proj_number

            self.default_project_number = project_num

            #TODO following line needs to be changed if the directory list item in gui layout changes
            directory_choice = destination_gui_results["Directory Choice"][0]
            manual_archived_path = destination_gui_results["Manual Path"]
            self.file_to_archive = ArchivalFile(current_path=files_in_archiving_dir[0],
                                                project=project_num,
                                                destination_dir=directory_choice,
                                                destination_path=manual_archived_path)
        return self.file_to_archive

    def confirmed_desired_file_destination(self):
        """
        spins up the confirmation screen gui and returns true if the desired path has been confirmed by the user.
        This also will exit the program if the user selects the 'exit' button in the gui.
        :return: bool value of whether to move the file_to_archive to the destination
        """
        file_destination = self.file_to_archive.assemble_destination_path()
        confirmation_gui_layout = self.gui.confirmation_layout(destination_path= file_destination)
        confirmation_gui_results = self.gui.make_window("Confirm destination choice.", confirmation_gui_layout)
        if confirmation_gui_results["Button Event"].lower() == "exit":
            self.exit_app()
        return confirmation_gui_results["Button Event"].lower() == "ok"

    def archive_file(self):
        self.file_to_archive.archive()

    def add_archived_file_to_csv(self, csv_path):
        """

        :param csv_path:
        :return:
        """
        data_dict = self.file_to_archive.attribute_defaultdict()
        data_dict["archiver_email"] = self.email
        archived_file_df = pd.DataFrame(data_dict, index= [0,])
        archived_file_df.to_csv(csv_path, mode='a', index=False, header=False)

    def elicit_files_to_archive(self):
        while not self.files_to_archive():
            no_file_error_message = f"No files to archive. Add files to" + os.linesep + f"{self.files_to_archive_directory}"
            self.display_error(no_file_error_message)

    @staticmethod
    def exit_app():
        exit()


def main():
    csv_filename = "archived_files_archive.csv"
    csv_filepath = os.path.join(os.getcwd(), csv_filename)

    dir_of_files_to_archive = os.path.join(os.getcwd(), "files_to_archive")
    ppdo_archivist = Archivist(files_to_archive_directory= dir_of_files_to_archive,
                               records_drive_path= RECORDS_SERVER_LOCATION)

    ppdo_archivist.retrieve_email()
    while True:
        ppdo_archivist.elicit_files_to_archive()
        ppdo_archivist.elicit_destination_selection()

        #if there is no default project number and no project number was entered, display error message and restart loop
        if not ppdo_archivist.file_to_archive.project_number:
            ppdo_archivist.display_error("No project number selected.")
            continue

        destination_confirmed = ppdo_archivist.confirmed_desired_file_destination()
        if destination_confirmed:
            ppdo_archivist.archive_file()
            ppdo_archivist.add_archived_file_to_csv(csv_filepath)
        print(f"File archived: " + os.linesep + f"{ppdo_archivist.file_to_archive.destination_path}")






def test_gui():
    window_test = GuiHandler()
    # welcome_res = window_test.make_window("Welcome", window_test.welcome_layout())
    dest_layout = window_test.destination_choice_layout(dir_choices=DIRECTORY_CHOICES, default_project_num="3238",
                                                        file_exists_to_archive=True)
    dest_results = window_test.make_window("Choose a file destination.", dest_layout)
    fail_reason = "Could not find necessary sub-directories to reconcile desired destination path."
    window_test.make_window("Could not archive file in desired destination.",
                            window_layout=window_test.failed_destination_layout(fail_reason, str(os.getcwd())))




def test_assemble_destination_path():
    project = '2700'
    desired_destination = DIRECTORY_CHOICES[8]
    print(desired_destination)
    new_filename = "2744.G19.Notice of Completion"

    location = os.path.join(os.getcwd(), "file_to_archive")
    file = ArchivalFile(current_location_path=location, project=project, new_filename= new_filename,
                        destination_dir=desired_destination)

    dest_path = file.assemble_destination_path()
    print(dest_path)


if __name__ == "__main__":
    #test_gui()
    #test_assemble_destination_path()
    main()