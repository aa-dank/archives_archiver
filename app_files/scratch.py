from PIL import Image
#THis was more about making the directory path and not building the plausible path
def get_destination_path(self):
    while not self.destination_path:
        # sort out which root directory to use when searching for result
        project_root_dir_prefix, project_num_prefix = ArchiverHelpers.prefixes_from_project_number(self.project_number)
        root_directories_list = os.listdir(RECORDS_SERVER_LOCATION)
        matching_root_dirs = [dir_name for dir_name in root_directories_list if
                              dir_name.lower().startswith(project_root_dir_prefix)]
        # if we have more than one matching root dir we throw an error
        if len(matching_root_dirs) != 1:
            logging.exception(
                f"{len(matching_root_dirs)} matching directories in {RECORDS_SERVER_LOCATION} for {self.project_number}",
                exc_info=True)
            return

        new_path = os.path.join(RECORDS_SERVER_LOCATION, matching_root_dirs[0])

        # her we look for the directory that would contain the project directory
        for root, dirs, files in os.walk(new_path):
            if project_num_prefix in dirs:
                new_path = os.path.join(root, project_num_prefix)
                break

        # if the project_num_prefix directory doesn't exist
        if not project_num_prefix in ArchiverHelpers.split_path(new_path):
            new_path = os.path.join(new_path, project_num_prefix)



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



def test_gui():
    window_test = GuiHandler()
    # welcome_res = window_test.make_window("Welcome", window_test.welcome_layout())
    dest_layout = window_test.destination_choice_layout(dir_choices=DIRECTORY_CHOICES, default_project_num="3238",
                                                        file_exists_to_archive=True)
    dest_results = window_test.make_window("Choose a file destination.", dest_layout)
    fail_reason = "Could not find necessary sub-directories to reconcile desired destination path."
    window_test.make_window("Could not archive file in desired destination.",
                            window_layout=window_test.failed_destination_layout(fail_reason, str(os.getcwd())))


    def get_destination_filename(self):
        """
        returns the resulting anticipated filename from an anticipated archival process. Handles extensions by copying
        them from current filename to desired new filename
        :return:
        """

        #subroutine check conents of the current location of the file for files that can be archived
        is_archivable_file = lambda filename, dir_path: (os.path.isfile(os.path.join(dir_path, filename)) and (
                len([ignore_file for ignore_file in FILENAMES_TO_IGNORE if ignore_file.lower() == filename.lower()]) == 0))

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


def resize_image(path, new_path, dims = (32,32)):
    foo = Image.open(path)
    foo2 = foo.resize(dims, Image.ANTIALIAS)
    foo2.save(new_path, quality=95)
    return
