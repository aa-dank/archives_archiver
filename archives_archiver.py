import os
import logging
import pandas as pd
import PySimpleGUI as sg

from collections import defaultdict

# Typing Aliases


# Environmental Variables
RECORDS_SERVER_LOCATION = r"""R:\\"""
FILENAMES_TO_IGNORE = ["desktop.ini"]
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
            [sg.Text("Personal email address:"), sg.Input(key="Archiver Email")],
            [sg.Button("Ok"), sg.Button("Exit")]
        ]
        return welcome_gui_layout

    def destination_choice_layout(self, dir_choices: list[str], default_project_num: str = None,
                                  file_exists_to_archive: bool = False):
        dir_choices.sort()
        # TODO try auto_size_text and expand_y
        listbox_width = max([len(dir_name) for dir_name in dir_choices])
        listbox_height = 36

        destination_gui_layout = [[sg.Text("Default Project:"), sg.Text(default_project_num)],
                                  [sg.Text("Project Number (Leave Blank to use Default.):"),
                                   sg.Input(key="New Project Number")],
                                  [sg.Text("Choose Directory to for file:"),
                                   sg.Listbox(values=dir_choices, key="Directory Choice",
                                              size=(listbox_width, listbox_height))],
                                  [sg.Text(
                                      "Alternatively, Enter the full path to directory where the file has been archived:")],
                                  [sg.Input(key="Manual Path")]]
        if not file_exists_to_archive:
            destination_gui_layout.append([sg.Text("No file available to archive. Add a file before clicking 'Ok'.")])

        destination_gui_layout.append([sg.Button("Ok"), sg.Button("Exit")])
        return destination_gui_layout

    def confirmation_layout(self):
        # TODO make this window. Should it have
        confirmation_gui_layout = [
            [sg.Text("Personal email address:"), sg.Input(key="user_email")],
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

    def __init__(self, current_location_path: str, project: str, destination_path: str = None, new_filename: str = None,
                 notes: str = None, destination_dir: str = None):
        """

        :param current_location_path: path to directory containing file #TODO will need to change for multi-file functionality
        :param project: project number string
        :param destination_path: the desired path for the file when tit is archived
        :param new_filename: optional file name for the destination file
        :param notes: for recording notes in the database
        :param destination_dir: chosen directory from the directory templates
        """
        self.current_path = current_location_path
        self.project_number = project
        self.destination_dir = destination_dir
        self.new_filename = new_filename
        self.notes = notes  # TODO maybe this should be part of archiver class
        self.destination_path = destination_path

    def archive(self):
        while not self.destination_path:
            pass

    def get_destination_filename(self):
        """
        returns the resulting anticipated filename from an anticipated archival process. Handles extensions by copying
        them from current filename to desired new filename
        :return:
        """

        #subroutine check conents of the current location of the file for files that can be archived
        is_archivable_file = lambda filename, dir_path: (os.path.isfile(os.path.join(dir_path, filename)) and (
                len([file for file in FILENAMES_TO_IGNORE if file.lower() == filename.lower()]) == 0))

        #we assume there is only one matching file
        current_filename = [file for file in os.listdir(self.current_path) if
                            is_archivable_file(file, self.current_path)][0]

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

            # if the destination_dir has a project large template dir parent we need to first try looking for that.
            if not destination_dir_parent_dir == large_template_destination:
                # need to extrapolate the parent directory prefix given the desired destination directory. eg for
                # destination "F5 - Drawings and Specifications" the parent directory prefix is "F - "
                destination_dir_parent_dir_prefix = destination_dir_parent_dir.split(" ")[0] + " - "  # eg "F - ", "G - ", etc
                parent_dirs = [dir_name for dir_name in new_path_dirs if
                               dir_name.upper().startswith(destination_dir_parent_dir_prefix)]
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
                        new_path = os.path.join(new_path, large_template_destination)

            # if the destination_dir doesn't have a project template dir parent...
            else:
                new_path_dirs = [dir_name for dir_name in os.listdir(new_path) if
                                 not os.path.isfile(os.path.join(new_path, dir_name))]
                existing_destination_dirs = [dir_name for dir_name in new_path_dirs if
                                             dir_name.upper().startswith(destination_dir_prefix)]
                if existing_destination_dirs:
                    new_path = os.path.join(new_path, existing_destination_dirs[0])
                else:
                    new_path = os.path.join(new_path, destination_dir)

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


class Archiver:
    """

    """

    def __init__(self, archiving_directory: str, archiving_data_path: str, records_drive_path: str,
                 file_to_archive: ArchivalFile = None):

        self.archiving_directory = archiving_directory
        if not os.path.exists(archiving_directory):
            try:
                os.mkdir(archiving_directory)
            except Exception as e:
                print(e)
                print(f"error from trying to make {archiving_directory}")

        self.archiving_data_path = archiving_data_path
        self.records_drive_path = records_drive_path
        self.gui = GuiHandler()
        self.file_to_archive = file_to_archive
        self.archiver_email = None
        self.archive_data = defaultdict(None, {})
        self.default_project_number = None

    def retrieve_archiver_email(self):

        welcome_window_layout = self.gui.welcome_layout()
        welcome_window_results = self.gui.make_window("Welcome!", welcome_window_layout)

        # if the user clicks exit, shutdown app
        if welcome_window_results["Button Event"].lower() == "exit":
            self.exit_app()
        else:
            self.archiver_email = welcome_window_results["Archiver Email"]
            self.archive_data["Archiver Email"] = welcome_window_results["Archiver Email"]
            return

    def files_to_archive(self, archiver_dir_path=None):  # TODO limit to single file?
        if self.archiving_directory and not archiver_dir_path:
            archiver_dir_path = self.archiving_directory
        files = [os.path.join(archiver_dir_path, file) for file in os.listdir(archiver_dir_path) if
                 not file in FILENAMES_TO_IGNORE]
        files = [filepath for filepath in files if os.path.isfile(filepath)]
        return files

    def elicit_destination_selection(self):

        file_exists = (len(self.files_to_archive()) == 1)
        default_proj_number = ""
        if self.default_project_number:
            default_proj_number = self.default_project_number
        destination_window_layout = self.gui.destination_choice_layout(dir_choices=DIRECTORY_CHOICES,
                                                                       default_project_num=default_proj_number,
                                                                       file_exists_to_archive=file_exists)
        destination_gui_results = self.gui.make_window(window_name="Enter file and destination info.",
                                                       window_layout=destination_window_layout)

        if destination_gui_results["Button Event"].lower() == "exit":
            self.exit_app()
        if destination_gui_results["New Project Number"]:
            self.default_project_number = destination_gui_results["New Project Number"]

        if destination_gui_results["Button Event"].lower() == "back":
            return ""

        if destination_gui_results["Button Event"].lower() == "ok":
            project_num = destination_gui_results["New Project Number"]
            if not project_num:
                project_num = default_proj_number

            directory_choice = destination_gui_results["Directory Choice"]
            manual_archived_path = destination_gui_results["Manual Path"]
            self.file_to_archive = ArchivalFile(current_location_path=self.archiving_directory,
                                                project=project_num,
                                                destination_dir=directory_choice,
                                                destination_path=manual_archived_path)
        return self.file_to_archive

    def confirm_file_destination(self):
        file_destination = ""
        try:
            file_destination = self.file_to_archive.assemble_destination_path()
            self.gui
        except Exception as e:
            pass

    @staticmethod
    def exit_app():
        exit()


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
    project = '5800-001'
    desired_destination = DIRECTORY_CHOICES[44]
    print(desired_destination)

    location = os.path.join(os.getcwd(), "file_to_archive")
    file = ArchivalFile(current_location_path=location, project=project, new_filename=None,
                        destination_dir=desired_destination)

    dest_path = file.assemble_destination_path()
    print(dest_path)


if __name__ == "__main__":
    # test_gui()
    test_assemble_destination_path()
