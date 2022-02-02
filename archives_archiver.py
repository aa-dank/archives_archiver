import os
import pandas as pd
import PySimpleGUI as sg

from collections import defaultdict

#Environmental Variables
FILENAMES_TO_IGNORE = ["desktop.ini"]
DIRECTORY_CHOICES = [""]

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


class GuiHandler:
    """
        This class is used to create and launch the various GUI windows used by the script.

        """

    def __init__(self):
        self.gui_theme = "DarkTeal6"

    def make_window(self, window_layout: list, window_name: str):
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

    def choose_destination_layout(self, dir_choices: list[str], default_project_num: str = None,
                                  file_exists_to_archive: bool = False):

        destination_gui_layout = [[sg.Text("Default Project:"), sg.Text(default_project_num)],
                                  [sg.Text("Project Number (Leave Blank to use Default.):"),
                                   sg.Input(key="New Project Number")],
                                  [sg.Text("Default Project:"), sg.Listbox(values=dir_choices)],
                                  [sg.Text("Alternatively, Enter the full destination path:")],
                                  [sg.Input(key="New Project Number")]
        if not file_exists_to_archive:
            destination_gui_layout.append([sg.Text("No file available to archive. Add a file before clicking 'Ok'.")])

        destination_gui_layout.append([sg.Button("Ok"), sg.Button("Exit")])
        return destination_gui_layout

    def confirmation_layout(self):
        confirmation_gui_layout = [
            [sg.Text("Personal email address:"), sg.Input(key="user_email")],
            [sg.Button("Ok"), sg.Button("Back"), sg.Button("exit")]
        ]
        return confirmation_gui_layout

    def failed_destination_layout(self,  fail_reason: str, fail_path: str):
        failed_gui_layout = [
            [sg.Text("Could not reconcile the given destination choice:")],
            [sg.Text(fail_path)],
            [sg.Text("Reason for not being able to movve file to selected destination:")],
            [sg.Text(fail_reason)],
            [sg.Button("Back"), sg.Button("Exit")]
        ]
        return failed_gui_layout

    def error_message_layout(self, error_message: str):
        error_gui_layout = [
            [sg.Text("Oops, an error occured:")],
            [ sg.Text(error_message)],
            [sg.Button("Back"), sg.Button("Exit")]
        ]
        return error_gui_layout


class ArchivalFile:

    def __init__(self, location_path: str, project: str, destination_dir: str, destination_path: str,
                 new_filename: str, notes: str):
        pass



class Archiver:
    """

    """

    def __init__(self, archiving_directory: str, archiving_data_path: str, records_drive_path: str):

        self.archiving_directory = archiving_directory
        if not os.path.exists(archiving_directory):
            try:
                os.mkdir(archiving_directory)
            except Exception as e:

        self.archiving_data_path = archiving_data_path
        self.records_drive_path = records_drive_path
        self.gui = GuiHandler()
        self.archiver_email = None
        self.archive_data = defaultdict(None, {})
        self.default_project_number = None
        self.file_to_archive = None


    def retrieve_archiver_email(self):

        welcome_window_layout = self.gui.welcome_layout()
        welcome_window_results = self.gui.make_window(welcome_window_layout,"Welcome!")

        #if the user clicks exit, shutdown app
        if welcome_window_results["Button Event"].lower() == "exit":
            self.exit_app()
        else:
            self.archiver_email = welcome_window_results["Archiver Email"]
            self.archive_data["Archiver Email"] = welcome_window_results["Archiver Email"]
            return


    def files_to_archive(self, archiver_dir_path = None):
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
        destination_window_layout = self.gui.choose_destination_layout(dir_choices= DIRECTORY_CHOICES,
                                                                       default_project_num= default_proj_number,
                                                                       file_exists_to_archive= file_exists)
        destination_gui_results = self.gui.make_window(window_layout= destination_window_layout,
                                                       window_name= "Enter file and destination info.")

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


            return ""






    @staticmethod
    def exit_app():
        exit()
